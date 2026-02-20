#!/usr/bin/env python3
"""Backfill transaction_ledger from algo_orders with FILLED status.

This script populates the transaction_ledger table with historical trade data
from algo_orders that were executed in the last N days.

Usage:
    cd backend && uv run python scripts/backfill_ledger.py [--days 3]
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add backend to path
sys.path.insert(0, ".")

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def get_filled_orders(conn, days: int) -> list[dict]:
    """Get all FILLED algo_orders from the last N days."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    query = text("""
        SELECT
            ao.id, ao.user_id, ao.symbol, ao.side, ao.quantity,
            ao.filled_price, ao.filled_quantity, ao.order_value,
            ao.created_at, ao.filled_at, ao.execution_id,
            COALESCE(o.fees, 0) as fees
        FROM algo_orders ao
        LEFT JOIN orders o ON ao.order_id = o.id
        WHERE ao.order_status = 'FILLED'
          AND ao.filled_at >= :cutoff
        ORDER BY ao.filled_at ASC
    """)

    result = await conn.execute(query, {"cutoff": cutoff})
    rows = result.fetchall()

    return [
        {
            "id": str(row[0]),
            "user_id": str(row[1]),
            "symbol": row[2],
            "side": row[3],
            "quantity": row[4],
            "filled_price": row[5],
            "filled_quantity": row[6],
            "order_value": row[7],
            "created_at": row[8],
            "filled_at": row[9],
            "execution_id": str(row[10]) if row[10] else None,
            "fees": row[11] or Decimal("0"),
        }
        for row in rows
    ]


async def backfill_ledger(days: int = 3, initial_balance: Decimal = Decimal("10000")) -> int:
    """Backfill transaction_ledger from filled algo_orders.

    Args:
        days: Number of days to look back
        initial_balance: Starting cash balance before first trade
    """
    engine = create_async_engine(settings.DATABASE_URL)

    async with engine.begin() as conn:
        # Get filled orders
        orders = await get_filled_orders(conn, days)
        logger.info(f"Found {len(orders)} filled orders in last {days} days")

        if not orders:
            logger.info("No orders to backfill")
            return 0

        # Track running balances per user - start with initial deposit
        user_balances: dict[str, tuple[Decimal, Decimal]] = {}
        created_count = 0

        for order in orders:
            user_id = order["user_id"]

            # Initialize with starting balance (before any trades)
            if user_id not in user_balances:
                user_balances[user_id] = (initial_balance, Decimal("0"))
                logger.info(f"User {user_id}: Starting balance = {initial_balance}")

            cash_balance, margin_used = user_balances[user_id]

            # Calculate transaction amount
            amount = Decimal(str(order["order_value"]))
            fees = Decimal(str(order["fees"]))

            if order["side"] == "BUY":
                txn_type = "BUY"
                signed_amount = -amount  # Debit for buys (cash goes out)
                description = (
                    f"Buy {order['filled_quantity']} {order['symbol']} @ ₹{order['filled_price']}"
                )
            else:
                txn_type = "SELL"
                signed_amount = amount  # Credit for sells (cash comes in)
                description = (
                    f"Sell {order['filled_quantity']} {order['symbol']} @ ₹{order['filled_price']}"
                )

            # Update running cash balance (simple cash tracking)
            cash_balance += signed_amount - fees
            # Keep margin as 0 for this backfill (we don't have position data)
            total_balance = cash_balance
            user_balances[user_id] = (cash_balance, margin_used)

            # Create ledger entry using raw SQL
            txn_date = order["filled_at"] or order["created_at"]
            extra_data = json.dumps({"execution_id": order["execution_id"], "fees": float(fees)})

            insert_sql = text("""
                INSERT INTO transaction_ledger
                (id, user_id, transaction_type, amount, running_cash_balance,
                 running_margin_used, running_total_balance, reference_type,
                 reference_id, symbol, description, extra_data, transaction_date)
                VALUES (:id, :user_id, :txn_type, :amount, :cash_bal,
                        :margin, :total_bal, :ref_type, :ref_id, :symbol,
                        :desc, CAST(:extra AS json), :txn_date)
            """)

            await conn.execute(
                insert_sql,
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "txn_type": txn_type,
                    "amount": abs(amount),
                    "cash_bal": cash_balance,
                    "margin": margin_used,
                    "total_bal": total_balance,
                    "ref_type": "algo_order",
                    "ref_id": order["id"],
                    "symbol": order["symbol"],
                    "desc": description,
                    "extra": extra_data,
                    "txn_date": txn_date,
                },
            )
            created_count += 1

            # Also create fee entry if fees > 0
            if fees > 0:
                await conn.execute(
                    insert_sql,
                    {
                        "id": str(uuid4()),
                        "user_id": user_id,
                        "txn_type": "FEE",
                        "amount": fees,
                        "cash_bal": cash_balance,
                        "margin": margin_used,
                        "total_bal": total_balance,
                        "ref_type": "algo_order",
                        "ref_id": order["id"],
                        "symbol": order["symbol"],
                        "desc": f"Trading fee for {order['symbol']}",
                        "extra": "{}",
                        "txn_date": txn_date,
                    },
                )
                created_count += 1

        logger.info(f"Created {created_count} ledger entries")
        return created_count

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill transaction ledger from algo orders")
    parser.add_argument("--days", type=int, default=3, help="Number of days to look back")
    parser.add_argument(
        "--initial-balance", type=float, default=10000, help="Starting cash balance"
    )
    args = parser.parse_args()

    count = asyncio.run(backfill_ledger(args.days, Decimal(str(args.initial_balance))))
    print(f"Backfilled {count} ledger entries")
