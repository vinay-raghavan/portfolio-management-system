"""Celery tasks for stock screener execution.

This module handles async screener execution for large universes (2200+ stocks).
Tasks call the backend API's screener endpoints for execution.

Flow: Celery Worker → Backend API :8000/api/v1/screener
"""

import hashlib
import json
import logging
from datetime import datetime, timezone

import httpx

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

BACKEND_API_URL = settings.BACKEND_API_URL
INTERNAL_API_KEY = settings.INTERNAL_API_KEY


def _get_internal_headers(user_id: str | None = None) -> dict:
    """Get headers for internal API calls."""
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Key": INTERNAL_API_KEY,
    }
    if user_id:
        headers["X-User-Id"] = user_id
    return headers


def _generate_cache_key(
    universe: str,
    filters: list[dict],
    min_score: float,
    top_n: int,
) -> str:
    """Generate a cache key for screener results."""
    # Create a stable hash of the filter config
    filter_str = json.dumps(filters, sort_keys=True)
    config_str = f"{universe}:{filter_str}:{min_score}:{top_n}"
    hash_val = hashlib.md5(config_str.encode()).hexdigest()[:12]
    return f"screener:results:{universe}:{hash_val}"


def _is_market_hours() -> bool:
    """Check if we're in Indian market hours (9:15 AM - 3:30 PM IST)."""
    now = datetime.now(timezone.utc)
    # Convert to IST (UTC+5:30)
    ist_hour = (now.hour + 5) % 24 + (1 if now.minute >= 30 else 0)
    ist_minute = (now.minute + 30) % 60
    
    # Market open: 9:15, Market close: 15:30
    market_open = 9 * 60 + 15  # 555 minutes
    market_close = 15 * 60 + 30  # 930 minutes
    current_time = ist_hour * 60 + ist_minute
    
    # Check weekday (0=Monday, 6=Sunday)
    weekday = now.weekday()
    if weekday >= 5:  # Weekend
        return False
    
    return market_open <= current_time <= market_close


def _get_cache_ttl() -> int:
    """Get cache TTL based on market hours."""
    if _is_market_hours():
        return 300  # 5 minutes during market hours
    return 3600  # 1 hour outside market hours


def _run_screener_sync(
    user_id: str,
    universe: str,
    filters: list[dict],
    min_score: float,
    top_n: int,
    preset: str | None = None,
) -> dict:
    """Synchronous implementation of screener execution."""
    logger.info(f"Running screener for user {user_id}, universe: {universe}")
    
    try:
        # Determine endpoint based on preset or custom
        if preset:
            endpoint = f"{BACKEND_API_URL}/api/v1/screener/run/preset"
            payload = {
                "preset": preset,
                "universe": universe,
                "min_score": min_score,
                "top_n": top_n,
            }
        else:
            endpoint = f"{BACKEND_API_URL}/api/v1/screener/run"
            payload = {
                "universe": universe,
                "filters": filters,
                "min_score": min_score,
                "top_n": top_n,
            }
        
        with httpx.Client(timeout=300.0) as client:  # 5 min timeout for large universes
            response = client.post(
                endpoint,
                json=payload,
                headers=_get_internal_headers(user_id),
            )
            
            if response.status_code != 200:
                logger.error(f"Screener API error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"API returned {response.status_code}",
                }
            
            result = response.json()
            logger.info(
                f"Screener complete: {result.get('passed_count', 0)} stocks passed "
                f"out of {result.get('total_screened', 0)}"
            )
            return {"status": "success", **result}
    
    except httpx.TimeoutException:
        logger.error("Timeout running screener")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error running screener: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.screener.run_screener_async")
def run_screener_async(
    self,
    user_id: str,
    universe: str,
    filters: list[dict],
    min_score: float = 50.0,
    top_n: int = 50,
    preset: str | None = None,
) -> dict:
    """Run a screener asynchronously for large universes.
    
    This task is queued when screening large universes (2200+ stocks)
    that would otherwise timeout in a synchronous API call.
    
    Args:
        user_id: User ID making the request
        universe: Universe identifier
        filters: List of filter configurations
        min_score: Minimum score threshold
        top_n: Maximum results to return
        preset: Optional preset name to use instead of filters
    """
    logger.info(f"Starting async screener: user={user_id}, universe={universe}")
    return _run_screener_sync(user_id, universe, filters, min_score, top_n, preset)

