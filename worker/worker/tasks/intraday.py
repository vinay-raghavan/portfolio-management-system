"""Celery tasks for intraday position management.

This module handles:
- Auto square-off of INTRADAY positions before market close (3:15 PM IST)
- Position reconciliation for intraday trades

Flow: Celery Worker → Trading Engine :8001
"""

import logging
from datetime import datetime, time

import httpx
import pytz

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

# Trading Engine URL
TRADING_ENGINE_URL = getattr(settings, "INTERNAL_API_URL", "http://trading-engine:8001")
INTERNAL_API_KEY = getattr(settings, "INTERNAL_API_KEY", "internal-worker-key")

# Market timing constants (IST)
IST = pytz.timezone("Asia/Kolkata")
MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM IST
DEFAULT_SQUARE_OFF_TIME = time(15, 15)  # 3:15 PM IST - 15 mins before close


def _get_internal_headers() -> dict:
    """Get headers for internal API calls."""
    return {
        "Content-Type": "application/json",
        "X-Internal-Key": INTERNAL_API_KEY,
    }


def _is_market_hours() -> bool:
    """Check if current time is within market hours."""
    now_ist = datetime.now(IST).time()
    market_open = time(9, 15)
    return market_open <= now_ist <= MARKET_CLOSE_TIME


def _square_off_intraday_positions_sync() -> dict:
    """Synchronous implementation of intraday square-off.

    Calls the trading engine's /internal/square-off-intraday endpoint.
    The trading engine handles:
    - Querying all OPEN positions with product_type=INTRADAY
    - Placing market orders to close each position
    - Updating position status and funds
    """
    logger.info("Calling trading engine to square off intraday positions")

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{TRADING_ENGINE_URL}/internal/square-off-intraday",
                headers=_get_internal_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                positions_closed = result.get("positions_closed", 0)
                total_pnl = result.get("total_pnl", 0)
                logger.info(
                    f"Intraday square-off completed: "
                    f"{positions_closed} positions closed, total P&L: {total_pnl}"
                )
                return result
            else:
                logger.error(
                    f"Trading engine square-off failed: {response.status_code} - {response.text}"
                )
                return {"error": response.text, "status_code": response.status_code}

    except httpx.TimeoutException:
        logger.error("Timeout calling trading engine for intraday square-off")
        return {"error": "Timeout connecting to trading engine"}
    except Exception as e:
        logger.error(f"Error in intraday square-off: {e}")
        return {"error": str(e)}


@celery_app.task(
    name="worker.tasks.intraday.square_off_intraday_positions",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def square_off_intraday_positions(self) -> dict:
    """Auto square-off all INTRADAY positions before market close.

    This task should be scheduled to run at 3:15 PM IST (9:45 UTC).
    It will:
    1. Find all OPEN positions with product_type=INTRADAY
    2. Place MARKET orders to close each position
    3. Update funds (release margin, credit/debit P&L)
    4. Send notifications to users

    Returns:
        dict: Result with positions_closed count and total_pnl
    """
    # Safety check: only run during market hours
    if not _is_market_hours():
        logger.warning(
            "Square-off task called outside market hours, skipping. "
            "This might indicate a timezone configuration issue."
        )
        return {"skipped": True, "reason": "outside_market_hours"}

    try:
        result = _square_off_intraday_positions_sync()
        return result
    except Exception as e:
        logger.error(f"Intraday square-off task failed: {e}")
        # Retry on failure - this is critical for risk management
        raise self.retry(exc=e) from e


@celery_app.task(name="worker.tasks.intraday.check_intraday_positions")
def check_intraday_positions() -> dict:
    """Check for any remaining INTRADAY positions after market close.

    This is a safety check that runs after market close to alert
    if any intraday positions were not squared off.
    """
    logger.info("Checking for remaining intraday positions after market close")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{TRADING_ENGINE_URL}/internal/intraday-positions-count",
                headers=_get_internal_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                count = result.get("count", 0)
                if count > 0:
                    logger.error(
                        f"ALERT: {count} INTRADAY positions still open after market close!"
                    )
                else:
                    logger.info("All intraday positions have been squared off")
                return result
            else:
                logger.error(f"Failed to check intraday positions: {response.text}")
                return {"error": response.text}

    except Exception as e:
        logger.error(f"Error checking intraday positions: {e}")
        return {"error": str(e)}
