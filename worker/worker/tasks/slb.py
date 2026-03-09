"""Celery tasks for SLB (Securities Lending & Borrowing) management.

This module handles:
- Daily fee accrual for active SLB positions
- Expiry warnings for approaching return dates
- Auto-close of expiring SLB positions

Flow: Celery Worker → Trading Engine :8001
"""

import logging

import httpx
import pytz

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

# Trading Engine URL
TRADING_ENGINE_URL = getattr(settings, "INTERNAL_API_URL", "http://trading-engine:8001")
INTERNAL_API_KEY = getattr(settings, "INTERNAL_API_KEY", "internal-worker-key")

# SLB constants
IST = pytz.timezone("Asia/Kolkata")
SLB_EXPIRY_WARNING_DAYS = 3  # Warn when this many days left


def _get_internal_headers() -> dict:
    """Get headers for internal API calls."""
    return {
        "Content-Type": "application/json",
        "X-Internal-Key": INTERNAL_API_KEY,
    }


@celery_app.task(name="worker.tasks.slb.accrue_slb_fees")
def accrue_slb_fees() -> dict:
    """Daily task to accrue SLB borrowing fees.

    This task should run once daily (preferably after market close).
    It:
    1. Queries all ACTIVE SLB positions
    2. Adds daily_fee to total_fee_accrued for each
    3. Returns summary of fees accrued

    Returns:
        dict: Summary with positions_updated count and total_fees_accrued
    """
    logger.info("Starting daily SLB fee accrual")

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{TRADING_ENGINE_URL}/internal/slb/accrue-fees",
                headers=_get_internal_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                positions_updated = result.get("positions_updated", 0)
                total_accrued = result.get("total_fees_accrued", 0)
                logger.info(
                    f"SLB fee accrual completed: "
                    f"{positions_updated} positions, total ₹{total_accrued:.2f}"
                )
                return result
            else:
                logger.error(f"SLB fee accrual failed: {response.status_code} - {response.text}")
                return {"error": response.text, "status_code": response.status_code}

    except Exception as e:
        logger.error(f"Error in SLB fee accrual: {e}")
        return {"error": str(e)}


@celery_app.task(name="worker.tasks.slb.check_slb_expiry")
def check_slb_expiry() -> dict:
    """Check for SLB positions approaching expiry and send warnings.

    This task should run daily. It:
    1. Finds SLB positions expiring within SLB_EXPIRY_WARNING_DAYS
    2. Sends notification to users about upcoming expiry
    3. Returns list of positions with expiry warnings

    Returns:
        dict: Summary with warnings_sent count and position details
    """
    logger.info(f"Checking for SLB positions expiring within {SLB_EXPIRY_WARNING_DAYS} days")

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{TRADING_ENGINE_URL}/internal/slb/check-expiry",
                headers=_get_internal_headers(),
                json={"warning_days": SLB_EXPIRY_WARNING_DAYS},
            )

            if response.status_code == 200:
                result = response.json()
                warnings_sent = result.get("warnings_sent", 0)
                if warnings_sent > 0:
                    logger.warning(f"SLB expiry warnings sent for {warnings_sent} positions")
                else:
                    logger.info("No SLB positions approaching expiry")
                return result
            else:
                logger.error(f"SLB expiry check failed: {response.status_code}")
                return {"error": response.text}

    except Exception as e:
        logger.error(f"Error checking SLB expiry: {e}")
        return {"error": str(e)}


@celery_app.task(
    name="worker.tasks.slb.auto_close_expiring_slb",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def auto_close_expiring_slb(self) -> dict:
    """Auto-close SLB positions expiring today.

    This task should run early on expiry day (before market open).
    It forces closure of any SLB positions that must be returned today
    to avoid default penalties.

    Returns:
        dict: Summary with positions_closed count
    """
    logger.info("Checking for SLB positions that must be closed today")

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{TRADING_ENGINE_URL}/internal/slb/auto-close-expiring",
                headers=_get_internal_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                positions_closed = result.get("positions_closed", 0)
                if positions_closed > 0:
                    logger.warning(f"Auto-closed {positions_closed} expiring SLB positions")
                else:
                    logger.info("No SLB positions need auto-close today")
                return result
            else:
                logger.error(f"SLB auto-close failed: {response.status_code}")
                raise Exception(f"SLB auto-close failed: {response.text}")

    except Exception as e:
        logger.error(f"Error in SLB auto-close: {e}")
        raise self.retry(exc=e) from e
