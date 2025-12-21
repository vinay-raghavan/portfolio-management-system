"""Trading-related background tasks.

This module provides Celery tasks for:
- SL/TP monitoring and execution
- GTT order checking
- Auto square-off of intraday positions at 3:15 PM IST
"""

import logging
from datetime import datetime, time
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from redis import Redis

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

# Indian Standard Time
IST = ZoneInfo("Asia/Kolkata")

# Market timing constants
INTRADAY_SQUARE_OFF_TIME = time(15, 15)  # 3:15 PM IST
MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM IST
MARKET_OPEN_TIME = time(9, 15)  # 9:15 AM IST


def is_market_hours() -> bool:
    """Check if current time is within market hours (9:15 AM - 3:30 PM IST)."""
    now_ist = datetime.now(IST).time()
    return MARKET_OPEN_TIME <= now_ist <= MARKET_CLOSE_TIME


def is_square_off_time() -> bool:
    """Check if current time is past intraday square-off time."""
    now_ist = datetime.now(IST).time()
    return now_ist >= INTRADAY_SQUARE_OFF_TIME


@celery_app.task(bind=True, name="worker.tasks.trading.check_sl_tp_orders")
def check_sl_tp_orders(self) -> dict:
    """Check and execute stop loss/take profit orders.
    
    This task runs every minute during market hours to:
    1. Get all positions with SL/TP set
    2. Fetch current prices
    3. Trigger execution if SL/TP is hit
    """
    if not is_market_hours():
        logger.debug("Market closed, skipping SL/TP check")
        return {"status": "market_closed", "checked": 0, "triggered": 0}
    
    logger.info("Checking SL/TP orders")
    
    # Use internal API URL
    api_url = "http://api:8000/api/v1"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            # Get positions with SL/TP set
            response = client.get(f"{api_url}/trading/positions-with-sl-tp")
            
            if response.status_code != 200:
                logger.warning(f"Failed to get positions: {response.status_code}")
                return {"status": "error", "message": "Failed to get positions"}
            
            positions = response.json()
            checked = 0
            triggered = 0
            
            for pos in positions:
                checked += 1
                symbol = pos["symbol"]
                quantity = Decimal(str(pos["quantity"]))
                stop_loss = Decimal(str(pos["stop_loss"])) if pos.get("stop_loss") else None
                take_profit = Decimal(str(pos["take_profit"])) if pos.get("take_profit") else None
                user_id = pos["user_id"]
                
                # Get current price
                price_response = client.get(f"{api_url}/data/quote/{symbol}")
                if price_response.status_code != 200:
                    continue
                
                current_price = Decimal(str(price_response.json().get("price", 0)))
                if current_price <= 0:
                    continue
                
                # Check SL condition
                if stop_loss and current_price <= stop_loss:
                    logger.info(f"SL triggered for {symbol} @ {current_price} (SL: {stop_loss})")
                    # Execute sell order
                    order_data = {
                        "symbol": symbol,
                        "side": "SELL",
                        "order_type": "MARKET",
                        "quantity": int(quantity),
                        "notes": f"Auto SL triggered at {current_price}",
                    }
                    sell_response = client.post(
                        f"{api_url}/trading/orders",
                        json=order_data,
                        headers={"X-User-ID": user_id}  # Would need proper auth in production
                    )
                    if sell_response.status_code == 200:
                        triggered += 1
                        logger.info(f"SL order executed for {symbol}")
                
                # Check TP condition
                elif take_profit and current_price >= take_profit:
                    logger.info(f"TP triggered for {symbol} @ {current_price} (TP: {take_profit})")
                    # Execute sell order
                    order_data = {
                        "symbol": symbol,
                        "side": "SELL",
                        "order_type": "MARKET",
                        "quantity": int(quantity),
                        "notes": f"Auto TP triggered at {current_price}",
                    }
                    sell_response = client.post(
                        f"{api_url}/trading/orders",
                        json=order_data,
                        headers={"X-User-ID": user_id}
                    )
                    if sell_response.status_code == 200:
                        triggered += 1
                        logger.info(f"TP order executed for {symbol}")
            
            logger.info(f"SL/TP check complete. Checked: {checked}, Triggered: {triggered}")
            return {"status": "success", "checked": checked, "triggered": triggered}

    except Exception as e:
        logger.error(f"Error checking SL/TP orders: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.trading.auto_square_off_intraday")
def auto_square_off_intraday(self) -> dict:
    """Auto square-off all intraday positions at 3:15 PM IST.

    This task runs once at 3:15 PM IST to:
    1. Get all INTRADAY positions
    2. Place market sell orders to close them
    """
    now_ist = datetime.now(IST)

    # Only run between 3:15 PM and 3:20 PM IST
    if not (time(15, 15) <= now_ist.time() <= time(15, 20)):
        logger.debug("Not square-off time, skipping")
        return {"status": "skipped", "reason": "Not square-off time"}

    logger.info("Starting auto square-off of intraday positions")

    api_url = "http://api:8000/api/v1"

    try:
        with httpx.Client(timeout=30.0) as client:
            # Get all intraday positions
            response = client.get(f"{api_url}/trading/intraday-positions")

            if response.status_code != 200:
                logger.warning(f"Failed to get intraday positions: {response.status_code}")
                return {"status": "error", "message": "Failed to get positions"}

            positions = response.json()
            squared_off = 0
            failed = 0

            for pos in positions:
                symbol = pos["symbol"]
                quantity = int(pos["quantity"])
                user_id = pos["user_id"]

                if quantity <= 0:
                    continue

                logger.info(f"Squaring off {quantity} shares of {symbol} for user {user_id}")

                # Place market sell order
                order_data = {
                    "symbol": symbol,
                    "side": "SELL",
                    "order_type": "MARKET",
                    "quantity": quantity,
                    "notes": "Auto square-off at 3:15 PM",
                }

                sell_response = client.post(
                    f"{api_url}/trading/orders",
                    json=order_data,
                    headers={"X-User-ID": user_id}
                )

                if sell_response.status_code == 200:
                    squared_off += 1
                    logger.info(f"Squared off {symbol}")
                else:
                    failed += 1
                    logger.error(f"Failed to square off {symbol}: {sell_response.text}")

            logger.info(f"Auto square-off complete. Squared off: {squared_off}, Failed: {failed}")
            return {"status": "success", "squared_off": squared_off, "failed": failed}

    except Exception as e:
        logger.error(f"Error in auto square-off: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.trading.check_gtt_orders")
def check_gtt_orders(self) -> dict:
    """Check and execute GTT (Good Till Triggered) orders.

    This task runs every minute to check GTT orders against current prices.
    """
    if not is_market_hours():
        logger.debug("Market closed, skipping GTT check")
        return {"status": "market_closed", "checked": 0, "triggered": 0}

    logger.info("Checking GTT orders")

    api_url = "http://api:8000/api/v1"

    try:
        with httpx.Client(timeout=30.0) as client:
            # Get all pending GTT orders
            response = client.get(f"{api_url}/trading/gtt-orders")

            if response.status_code != 200:
                logger.warning(f"Failed to get GTT orders: {response.status_code}")
                return {"status": "error", "message": "Failed to get GTT orders"}

            orders = response.json()
            checked = 0
            triggered = 0

            for order in orders:
                checked += 1
                symbol = order["symbol"]
                trigger_price = Decimal(str(order["trigger_price"]))
                side = order["side"]
                order_id = order["id"]

                # Get current price
                price_response = client.get(f"{api_url}/data/quote/{symbol}")
                if price_response.status_code != 200:
                    continue

                current_price = Decimal(str(price_response.json().get("price", 0)))
                if current_price <= 0:
                    continue

                # Check trigger condition
                should_trigger = False
                if side == "BUY" and current_price >= trigger_price:
                    should_trigger = True
                elif side == "SELL" and current_price <= trigger_price:
                    should_trigger = True

                if should_trigger:
                    logger.info(f"GTT triggered for {symbol}: {side} @ {current_price}")
                    # Trigger the GTT order
                    trigger_response = client.post(
                        f"{api_url}/trading/gtt-orders/{order_id}/trigger"
                    )
                    if trigger_response.status_code == 200:
                        triggered += 1

            logger.info(f"GTT check complete. Checked: {checked}, Triggered: {triggered}")
            return {"status": "success", "checked": checked, "triggered": triggered}

    except Exception as e:
        logger.error(f"Error checking GTT orders: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.trading.check_pending_trigger_orders")
def check_pending_trigger_orders(self) -> dict:
    """Check pending SL/SL-M trigger orders for execution.

    This task monitors limit and stop-loss orders that are waiting
    for price conditions to be met.
    """
    if not is_market_hours():
        return {"status": "market_closed"}

    logger.info("Checking pending trigger orders")

    api_url = "http://api:8000/api/v1"

    try:
        with httpx.Client(timeout=30.0) as client:
            # Trigger check via API
            response = client.post(f"{api_url}/trading/check-trigger-orders")

            if response.status_code == 200:
                result = response.json()
                return {"status": "success", "triggered": result.get("triggered", 0)}
            else:
                return {"status": "error", "message": f"API returned {response.status_code}"}

    except Exception as e:
        logger.error(f"Error checking trigger orders: {e}")
        return {"status": "error", "message": str(e)}

