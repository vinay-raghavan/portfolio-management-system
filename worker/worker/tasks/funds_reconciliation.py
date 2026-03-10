"""Funds reconciliation tasks.

Periodic tasks to ensure user_funds table is in sync with actual positions.
This catches any discrepancies caused by failed transactions or bugs.

Calls the Trading Engine internal API to perform reconciliation.
"""

import logging

import httpx

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

# Trading Engine URL
TRADING_ENGINE_URL = getattr(settings, "INTERNAL_API_URL", "http://trading-engine:8001")
INTERNAL_API_KEY = getattr(settings, "INTERNAL_API_KEY", "internal-worker-key")


def _get_internal_headers() -> dict:
    """Get headers for internal API calls."""
    return {
        "Content-Type": "application/json",
        "X-Internal-Key": INTERNAL_API_KEY,
    }


@celery_app.task(name="funds.reconcile_all_users")
def reconcile_all_users_funds() -> dict:
    """Reconcile funds for all users with algo positions.

    Calls the Trading Engine to reconcile margin_used with actual open positions.

    Returns:
        dict: Summary of reconciliation results
    """
    logger.info("Starting funds reconciliation for all users")

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{TRADING_ENGINE_URL}/internal/reconcile-funds",
                headers=_get_internal_headers(),
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Funds reconciliation completed: {result}")
            return result
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during funds reconciliation: {e.response.status_code}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error during funds reconciliation: {e}")
        return {"status": "error", "message": str(e)}
