"""Research module background tasks.

This module provides Celery tasks for:
- Daily digest generation at market close
- Research data refresh
"""

import logging
from datetime import datetime

import httpx

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

BACKEND_API_URL = settings.BACKEND_API_URL
INTERNAL_API_KEY = settings.INTERNAL_API_KEY


def _get_internal_headers() -> dict:
    """Get headers for internal API calls."""
    return {
        "Content-Type": "application/json",
        "X-Internal-Key": INTERNAL_API_KEY,
    }


def _is_market_closed() -> bool:
    """Check if Indian market is closed (after 3:30 PM IST).

    Daily digest should run after market close.
    """
    from zoneinfo import ZoneInfo

    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)

    # Market closes at 15:30 IST
    market_close_hour = 15
    market_close_minute = 30

    current_minutes = now.hour * 60 + now.minute
    close_minutes = market_close_hour * 60 + market_close_minute

    return current_minutes >= close_minutes


@celery_app.task(bind=True, name="worker.tasks.research.generate_daily_digest")
def generate_daily_digest(self) -> dict:
    """Generate daily research digest.

    This task runs at market close (4:00 PM IST / 10:30 UTC) to generate
    a comprehensive daily market digest with:
    - Market summary (index performance)
    - Top gainers and losers
    - Sector performance
    - Volume leaders
    - Breakout candidates
    - News highlights

    Results are stored in the daily_digests table.
    """
    logger.info("Starting daily digest generation")

    try:
        # Call backend API to generate digest
        endpoint = f"{BACKEND_API_URL}/api/v1/research/digest/generate"

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                endpoint,
                headers=_get_internal_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Daily digest generated successfully: {result.get('id')}")
                return {
                    "status": "success",
                    "digest_id": result.get("id"),
                    "digest_date": result.get("digest_date"),
                }
            elif response.status_code == 409:
                # Digest already exists for today
                logger.info("Daily digest already exists for today")
                return {
                    "status": "already_exists",
                    "message": "Digest already generated for today",
                }
            else:
                error_msg = response.text
                logger.error(f"Failed to generate digest: {response.status_code} - {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "status_code": response.status_code,
                }

    except httpx.TimeoutException as e:
        logger.error(f"Timeout generating daily digest: {e}")
        return {"status": "error", "error": "Timeout generating digest"}
    except Exception as e:
        logger.error(f"Error generating daily digest: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True, name="worker.tasks.research.generate_digest_manual")
def generate_digest_manual(self, target_date: str | None = None) -> dict:
    """Manually trigger digest generation for a specific date.

    Args:
        target_date: ISO format date (YYYY-MM-DD). Defaults to today.

    Returns:
        Task result with status and digest info.
    """
    logger.info(f"Manual digest generation requested for date: {target_date or 'today'}")

    try:
        endpoint = f"{BACKEND_API_URL}/api/v1/research/digest/generate"
        params = {}
        if target_date:
            params["date"] = target_date

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                endpoint,
                headers=_get_internal_headers(),
                params=params,
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Manual digest generated: {result.get('id')}")
                return {
                    "status": "success",
                    "digest_id": result.get("id"),
                    "digest_date": result.get("digest_date"),
                }
            else:
                return {
                    "status": "error",
                    "error": response.text,
                    "status_code": response.status_code,
                }

    except Exception as e:
        logger.error(f"Error in manual digest generation: {e}")
        return {"status": "error", "error": str(e)}
