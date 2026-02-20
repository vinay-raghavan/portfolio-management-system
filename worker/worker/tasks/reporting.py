"""Reporting sync background tasks.

Periodically syncs reporting tables from source data:
- transaction_ledger: from filled algo_orders
- realized_gains: FIFO-matched capital gains from BUY/SELL orders

Uses Redis to track last sync timestamp for incremental updates.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from redis import Redis
from sqlalchemy import create_engine, text

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

LAST_SYNC_KEY = "reporting:last_sync_timestamp"
SYNC_LOOKBACK_HOURS = 1  # Safety overlap to catch any missed orders


def get_sync_engine():
    """Get synchronous SQLAlchemy engine for Celery tasks."""
    # Convert asyncpg URL to psycopg2
    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    return create_engine(db_url)


@celery_app.task(bind=True, name="worker.tasks.reporting.sync_reporting_tables")
def sync_reporting_tables(self) -> dict:
    """Sync reporting tables incrementally from source data.

    This task:
    1. Gets last sync timestamp from Redis
    2. Fetches new filled orders since last sync
    3. Creates transaction_ledger entries
    4. Creates realized_gains entries (FIFO matching)
    5. Updates last sync timestamp
    """
    redis = Redis.from_url(settings.REDIS_URL)
    engine = get_sync_engine()

    # Get last sync time (default to 24 hours ago if never synced)
    last_sync_str = redis.get(LAST_SYNC_KEY)
    if last_sync_str:
        last_sync = datetime.fromisoformat(last_sync_str.decode())
    else:
        last_sync = datetime.now(UTC) - timedelta(hours=24)

    # Add overlap to catch any edge cases
    sync_from = last_sync - timedelta(hours=SYNC_LOOKBACK_HOURS)
    logger.info(f"Syncing reporting tables from {sync_from}")

    results = {"ledger_created": 0, "gains_created": 0, "errors": []}

    try:
        with engine.begin() as conn:
            # Sync transaction ledger
            results["ledger_created"] = _sync_ledger(conn, sync_from)

            # Sync realized gains
            results["gains_created"] = _sync_realized_gains(conn, sync_from)

        # Update last sync timestamp
        redis.set(LAST_SYNC_KEY, datetime.now(UTC).isoformat())
        logger.info(f"Reporting sync complete: {results}")

    except Exception as e:
        logger.error(f"Reporting sync failed: {e}")
        results["errors"].append(str(e))

    return results


def _sync_ledger(conn, sync_from: datetime) -> int:
    """Sync transaction_ledger from filled algo_orders."""
    # Get filled orders not yet in ledger
    query = text("""
        SELECT ao.id, ao.user_id, ao.symbol, ao.side, ao.filled_quantity,
               ao.filled_price, ao.order_value, ao.filled_at,
               COALESCE(o.fees, 0) as fees
        FROM algo_orders ao
        LEFT JOIN orders o ON ao.order_id = o.id
        WHERE ao.order_status = 'FILLED'
          AND ao.filled_at >= :sync_from
          AND NOT EXISTS (
              SELECT 1 FROM transaction_ledger tl
              WHERE tl.reference_id = ao.id AND tl.reference_type = 'algo_order'
          )
        ORDER BY ao.filled_at ASC
    """)

    result = conn.execute(query, {"sync_from": sync_from})
    orders = result.fetchall()

    if not orders:
        return 0

    created = 0
    for order in orders:
        order_id, user_id, symbol, side, qty, price, value, filled_at, fees = order

        # Get current running balance for user
        bal_query = text("""
            SELECT running_cash_balance, running_margin_used
            FROM transaction_ledger
            WHERE user_id = :user_id
            ORDER BY transaction_date DESC
            LIMIT 1
        """)
        bal_result = conn.execute(bal_query, {"user_id": str(user_id)})
        bal_row = bal_result.fetchone()

        if bal_row:
            cash_balance = Decimal(str(bal_row[0]))
            margin_used = Decimal(str(bal_row[1]))
        else:
            # First entry - get from user_funds
            funds_query = text("SELECT cash_balance FROM user_funds WHERE user_id = :uid")
            funds_result = conn.execute(funds_query, {"uid": str(user_id)})
            funds_row = funds_result.fetchone()
            cash_balance = Decimal(str(funds_row[0])) if funds_row else Decimal("0")
            margin_used = Decimal("0")

        amount = Decimal(str(value))
        fees_dec = Decimal(str(fees))

        if side == "BUY":
            txn_type = "BUY"
            cash_balance -= amount + fees_dec
            desc = f"Buy {qty} {symbol} @ ₹{price}"
        else:
            txn_type = "SELL"
            cash_balance += amount - fees_dec
            desc = f"Sell {qty} {symbol} @ ₹{price}"

        total_balance = cash_balance - margin_used
        extra_data = json.dumps({"fees": float(fees_dec)})

        insert_sql = text("""
            INSERT INTO transaction_ledger
            (id, user_id, transaction_type, amount, running_cash_balance,
             running_margin_used, running_total_balance, reference_type,
             reference_id, symbol, description, extra_data, transaction_date)
            VALUES (:id, :user_id, :txn_type, :amount, :cash_bal,
                    :margin, :total_bal, 'algo_order', :ref_id, :symbol,
                    :desc, CAST(:extra AS json), :txn_date)
        """)

        conn.execute(
            insert_sql,
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "txn_type": txn_type,
                "amount": abs(amount),
                "cash_bal": cash_balance,
                "margin": margin_used,
                "total_bal": total_balance,
                "ref_id": str(order_id),
                "symbol": symbol,
                "desc": desc,
                "extra": extra_data,
                "txn_date": filled_at,
            },
        )
        created += 1

    logger.info(f"Created {created} ledger entries")
    return created


def _sync_realized_gains(conn, sync_from: datetime) -> int:
    """Sync realized_gains using FIFO matching of BUY/SELL orders."""
    # Get SELL orders not yet in realized_gains
    query = text("""
        SELECT ao.id, ao.user_id, ao.symbol, ao.filled_quantity, ao.filled_price, ao.filled_at
        FROM algo_orders ao
        WHERE ao.order_status = 'FILLED'
          AND ao.side = 'SELL'
          AND ao.filled_at >= :sync_from
          AND NOT EXISTS (
              SELECT 1 FROM realized_gains rg
              WHERE rg.sell_trade_id = ao.id
          )
        ORDER BY ao.filled_at ASC
    """)

    result = conn.execute(query, {"sync_from": sync_from})
    sell_orders = result.fetchall()

    if not sell_orders:
        return 0

    created = 0
    for sell in sell_orders:
        sell_id, user_id, symbol, sell_qty, sell_price, sell_date = sell
        sell_qty = Decimal(str(sell_qty))
        sell_price = Decimal(str(sell_price))

        # Find matching BUY orders (FIFO) that haven't been fully consumed
        buy_query = text("""
            SELECT ao.id, ao.filled_quantity, ao.filled_price, ao.filled_at,
                   COALESCE(SUM(rg.quantity), 0) as consumed
            FROM algo_orders ao
            LEFT JOIN realized_gains rg ON rg.buy_trade_id = ao.id
            WHERE ao.user_id = :user_id
              AND ao.symbol = :symbol
              AND ao.side = 'BUY'
              AND ao.order_status = 'FILLED'
              AND ao.filled_at < :sell_date
            GROUP BY ao.id, ao.filled_quantity, ao.filled_price, ao.filled_at
            HAVING ao.filled_quantity > COALESCE(SUM(rg.quantity), 0)
            ORDER BY ao.filled_at ASC
        """)

        buy_result = conn.execute(
            buy_query,
            {
                "user_id": str(user_id),
                "symbol": symbol,
                "sell_date": sell_date,
            },
        )
        buy_orders = buy_result.fetchall()

        remaining = sell_qty
        for buy in buy_orders:
            if remaining <= 0:
                break

            buy_id, buy_qty, buy_price, buy_date, consumed = buy
            available = Decimal(str(buy_qty)) - Decimal(str(consumed))
            match_qty = min(remaining, available)

            cost_basis = match_qty * Decimal(str(buy_price))
            sale_proceeds = match_qty * sell_price
            gain_loss = sale_proceeds - cost_basis
            gain_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else Decimal("0")
            holding_days = (sell_date - buy_date).days
            is_long_term = holding_days > 365

            # FY format: 2025-26
            if sell_date.month >= 4:
                fy = f"{sell_date.year}-{(sell_date.year + 1) % 100:02d}"
            else:
                fy = f"{sell_date.year - 1}-{sell_date.year % 100:02d}"

            insert_sql = text("""
                INSERT INTO realized_gains
                (id, user_id, symbol, quantity, cost_basis, sale_proceeds, fees,
                 gain_loss, gain_loss_pct, purchase_date, sale_date, holding_days,
                 is_long_term, tax_type, financial_year, buy_trade_id, sell_trade_id, created_at)
                VALUES (:id, :user_id, :symbol, :qty, :cost, :proceeds, 0,
                        :gain, :gain_pct, :buy_date, :sell_date, :days,
                        :is_lt, :tax_type, :fy, :buy_id, :sell_id, :created)
            """)

            # Convert to naive datetime for DB
            buy_date_naive = buy_date.replace(tzinfo=None) if buy_date.tzinfo else buy_date
            sell_date_naive = sell_date.replace(tzinfo=None) if sell_date.tzinfo else sell_date

            conn.execute(
                insert_sql,
                {
                    "id": str(uuid4()),
                    "user_id": str(user_id),
                    "symbol": symbol,
                    "qty": match_qty,
                    "cost": cost_basis,
                    "proceeds": sale_proceeds,
                    "gain": gain_loss,
                    "gain_pct": gain_pct,
                    "buy_date": buy_date_naive,
                    "sell_date": sell_date_naive,
                    "days": holding_days,
                    "is_lt": is_long_term,
                    "tax_type": "LTCG" if is_long_term else "STCG",
                    "fy": fy,
                    "buy_id": str(buy_id),
                    "sell_id": str(sell_id),
                    "created": datetime.now(UTC).replace(tzinfo=None),
                },
            )
            created += 1
            remaining -= match_qty

    logger.info(f"Created {created} realized_gains entries")
    return created
