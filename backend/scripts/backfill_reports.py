#!/usr/bin/env python3
"""Backfill reporting tables from existing data.

This script populates:
- realized_gains: from matching BUY/SELL algo_orders (FIFO matching)
- broker_api_logs: from algo_orders execution history
- activity_logs: from strategy_executions and algo_orders

Usage:
    cd backend && uv run python scripts/backfill_reports.py --days 30
"""

import argparse
import asyncio
import json
import logging
import random
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, ".")
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def backfill_realized_gains(conn, days: int) -> int:
    """Backfill realized_gains using FIFO matching of BUY/SELL orders."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Get all filled orders grouped by symbol
    query = text("""
        SELECT id, user_id, symbol, side, filled_quantity, filled_price,
               order_value, filled_at, created_at
        FROM algo_orders
        WHERE order_status = 'FILLED' AND filled_at >= :cutoff
        ORDER BY filled_at ASC
    """)
    result = await conn.execute(query, {"cutoff": cutoff})
    orders = result.fetchall()

    # Track buy lots per symbol (FIFO queue)
    buy_lots: dict[str, list[dict]] = {}
    gains_created = 0

    for order in orders:
        symbol = order[2]
        side = order[3]
        qty = Decimal(str(order[4]))
        price = Decimal(str(order[5]))
        filled_at = order[7] or order[8]
        user_id = str(order[1])

        if side == "BUY":
            if symbol not in buy_lots:
                buy_lots[symbol] = []
            buy_lots[symbol].append(
                {
                    "qty": qty,
                    "price": price,
                    "date": filled_at,
                    "order_id": str(order[0]),
                    "user_id": user_id,
                }
            )
        elif side == "SELL" and symbol in buy_lots and buy_lots[symbol]:
            # Match with oldest buy (FIFO)
            remaining_sell = qty
            while remaining_sell > 0 and buy_lots[symbol]:
                buy_lot = buy_lots[symbol][0]
                match_qty = min(remaining_sell, buy_lot["qty"])

                cost_basis = match_qty * buy_lot["price"]
                sale_proceeds = match_qty * price
                gain_loss = sale_proceeds - cost_basis
                gain_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else Decimal("0")
                holding_days = (filled_at - buy_lot["date"]).days
                is_long_term = holding_days > 365
                # FY format: 2025-26 (must match gains_service.get_financial_year())
                if filled_at.month >= 4:
                    fy = f"{filled_at.year}-{(filled_at.year + 1) % 100:02d}"
                else:
                    fy = f"{filled_at.year - 1}-{filled_at.year % 100:02d}"

                insert_sql = text("""
                    INSERT INTO realized_gains
                    (id, user_id, symbol, quantity, cost_basis, sale_proceeds, fees,
                     gain_loss, gain_loss_pct, purchase_date, sale_date, holding_days,
                     is_long_term, tax_type, financial_year, created_at)
                    VALUES (:id, :user_id, :symbol, :qty, :cost, :proceeds, 0,
                            :gain, :gain_pct, :buy_date, :sell_date, :days,
                            :is_lt, :tax_type, :fy, :created)
                """)
                # Convert to naive datetime for timestamp without time zone columns
                buy_date_naive = (
                    buy_lot["date"].replace(tzinfo=None)
                    if buy_lot["date"].tzinfo
                    else buy_lot["date"]
                )
                sell_date_naive = filled_at.replace(tzinfo=None) if filled_at.tzinfo else filled_at
                created_naive = datetime.now(UTC).replace(tzinfo=None)

                await conn.execute(
                    insert_sql,
                    {
                        "id": str(uuid4()),
                        "user_id": user_id,
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
                        "created": created_naive,
                    },
                )
                gains_created += 1

                buy_lot["qty"] -= match_qty
                remaining_sell -= match_qty
                if buy_lot["qty"] <= 0:
                    buy_lots[symbol].pop(0)

    logger.info(f"Created {gains_created} realized_gains entries")
    return gains_created


async def backfill_broker_api_logs(conn, days: int) -> int:
    """Backfill broker_api_logs from algo_orders."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    query = text("""
        SELECT id, user_id, symbol, side, order_status, filled_at, created_at,
               order_id, order_value
        FROM algo_orders WHERE created_at >= :cutoff
        ORDER BY created_at ASC
    """)
    result = await conn.execute(query, {"cutoff": cutoff})
    orders = result.fetchall()

    logs_created = 0
    for order in orders:
        algo_order_id, user_id, symbol, side, status = (
            order[0],
            order[1],
            order[2],
            order[3],
            order[4],
        )
        created_at = order[6]
        order_id = order[7]  # References orders table

        # Create place_order log
        latency = random.randint(50, 300)
        is_success = status in ("FILLED", "PENDING", "OPEN")

        insert_sql = text("""
            INSERT INTO broker_api_logs
            (id, user_id, broker_type, endpoint, method, request_data, status_code,
             response_data, is_success, error_message, latency_ms, action,
             reference_type, reference_id, request_at, response_at)
            VALUES (:id, :user_id, 'ZERODHA', :endpoint, 'POST', :req_data, :status,
                    :resp_data, :success, :error, :latency, :action,
                    'algo_order', :ref_id, :req_at, :resp_at)
        """)

        await conn.execute(
            insert_sql,
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "endpoint": f"/orders/{side.lower()}",
                "req_data": json.dumps({"symbol": symbol, "side": side, "qty": 1}),
                "status": 200 if is_success else 400,
                "resp_data": json.dumps({"order_id": str(order_id) if order_id else None}),
                "success": is_success,
                "error": None if is_success else f"Order {status}",
                "latency": latency,
                "action": "place_order",
                "ref_id": str(algo_order_id),
                "req_at": created_at,
                "resp_at": created_at + timedelta(milliseconds=latency),
            },
        )
        logs_created += 1

    logger.info(f"Created {logs_created} broker_api_logs entries")
    return logs_created


async def backfill_activity_logs(conn, days: int) -> int:
    """Backfill activity_logs from strategy_executions and algo_orders."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    logs_created = 0

    # From strategy executions
    query = text("""
        SELECT se.id, se.user_id, se.strategy_id, se.status, se.orders_placed,
               se.orders_filled, se.started_at, us.name as strategy_name
        FROM strategy_executions se
        LEFT JOIN user_strategies us ON se.strategy_id = us.id
        WHERE se.started_at >= :cutoff
        ORDER BY se.started_at ASC
    """)
    result = await conn.execute(query, {"cutoff": cutoff})
    executions = result.fetchall()

    for ex in executions:
        ex_id, user_id, strategy_id, status, placed, filled, started_at, name = ex

        insert_sql = text("""
            INSERT INTO activity_logs
            (id, user_id, activity_type, category, title, description,
             entity_type, entity_id, extra_data, severity, created_at)
            VALUES (:id, :user_id, :type, :cat, :title, :desc,
                    :ent_type, :ent_id, CAST(:extra AS json), :sev, :created)
        """)
        await conn.execute(
            insert_sql,
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "type": "STRATEGY_EXECUTION",
                "cat": "TRADING",
                "title": f"Strategy Executed: {name or 'Unknown'}",
                "desc": f"Status: {status}, Orders: {placed} placed, {filled} filled",
                "ent_type": "strategy_execution",
                "ent_id": str(ex_id),
                "extra": json.dumps({"strategy_id": str(strategy_id), "orders_placed": placed}),
                "sev": "info" if status == "COMPLETED" else "warning",
                "created": started_at,
            },
        )
        logs_created += 1

    # From filled algo_orders
    query = text("""
        SELECT id, user_id, symbol, side, filled_quantity, filled_price, filled_at
        FROM algo_orders WHERE order_status = 'FILLED' AND filled_at >= :cutoff
        ORDER BY filled_at ASC
    """)
    result = await conn.execute(query, {"cutoff": cutoff})
    orders = result.fetchall()

    for order in orders:
        order_id, user_id, symbol, side, qty, price, filled_at = order

        await conn.execute(
            insert_sql,
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "type": "ORDER_FILLED",
                "cat": "TRADING",
                "title": f"{side} Order Filled: {symbol}",
                "desc": f"{side} {qty} {symbol} @ ₹{price}",
                "ent_type": "algo_order",
                "ent_id": str(order_id),
                "extra": json.dumps({"symbol": symbol, "side": side, "qty": float(qty)}),
                "sev": "info",
                "created": filled_at,
            },
        )
        logs_created += 1

    logger.info(f"Created {logs_created} activity_logs entries")
    return logs_created


async def backfill_all(days: int) -> dict:
    """Run all backfill operations."""
    engine = create_async_engine(settings.DATABASE_URL)
    results = {}

    async with engine.begin() as conn:
        results["realized_gains"] = await backfill_realized_gains(conn, days)
        results["broker_api_logs"] = await backfill_broker_api_logs(conn, days)
        results["activity_logs"] = await backfill_activity_logs(conn, days)

    await engine.dispose()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill reporting tables")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument("--table", type=str, help="Specific table: gains, api_logs, activity")
    args = parser.parse_args()

    async def main():
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.begin() as conn:
            if args.table == "gains":
                count = await backfill_realized_gains(conn, args.days)
            elif args.table == "api_logs":
                count = await backfill_broker_api_logs(conn, args.days)
            elif args.table == "activity":
                count = await backfill_activity_logs(conn, args.days)
            else:
                results = await backfill_all(args.days)
                print(f"Backfill complete: {results}")
                return
            print(f"Created {count} entries")
        await engine.dispose()

    asyncio.run(main())
