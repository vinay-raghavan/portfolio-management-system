"""Celery tasks for stock screener execution.

This module handles async screener execution for large universes (2200+ stocks).
Tasks call the backend API's screener endpoints for execution.

Flow: Celery Worker → Backend API :8000/api/v1/screener
"""

import hashlib
import json
import logging
from datetime import UTC, datetime

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
    now = datetime.now(UTC)
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


# Preset to category mapping for recommendations
PRESET_TO_CATEGORY = {
    "momentum": "momentum",
    "breakout": "breakout",
    "value": "pullback",
    "sector_rotation": "sector",
}


def _store_recommendations(date: str, category: str, results: list[dict]) -> dict:
    """Store recommendations in the database via API."""
    endpoint = f"{BACKEND_API_URL}/api/v1/screener/recommendations/store"
    payload = {
        "date": date,
        "category": category,
        "results": results,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                endpoint,
                json=payload,
                headers=_get_internal_headers(),
            )

            if response.status_code != 200:
                logger.error(
                    f"Store recommendations error: {response.status_code} - {response.text}"
                )
                return {"status": "error", "message": f"API returned {response.status_code}"}

            return {"status": "success", **response.json()}
    except Exception as e:
        logger.exception(f"Error storing recommendations: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.screener.generate_daily_recommendations")
def generate_daily_recommendations(self) -> dict:
    """Generate daily stock recommendations by running all preset screeners.

    This task runs at market open (9:15 AM IST / 3:45 UTC) to generate
    daily stock picks across all categories:
    - Momentum: Top momentum stocks
    - Breakout: Potential breakout candidates
    - Pullback: Value/oversold entry points
    - Sector: Strong sector leaders

    Results are stored in the daily_recommendations table for the dashboard widget.
    """
    logger.info("Starting daily recommendations generation")

    from datetime import date

    today = date.today().isoformat()

    categories_generated = []
    errors = []

    # Run each preset screener and store results
    presets = ["momentum", "breakout", "value", "sector_rotation"]
    universe = "nifty500"  # Use Nifty 500 for daily recommendations

    for preset in presets:
        category = PRESET_TO_CATEGORY.get(preset, preset)
        logger.info(f"Running {preset} screener for {category} category")

        try:
            # Run the screener
            result = _run_screener_sync(
                user_id="system",  # System-generated recommendations
                universe=universe,
                filters=[],  # Preset handles filters
                min_score=50.0,
                top_n=10,  # Top 10 per category
                preset=preset,
            )

            if result.get("status") == "error":
                errors.append(f"{preset}: {result.get('message')}")
                continue

            # Store the recommendations
            recommendations = result.get("results", [])
            if recommendations:
                store_result = _store_recommendations(today, category, recommendations)
                if store_result.get("status") == "success":
                    categories_generated.append(category)
                    logger.info(f"Stored {len(recommendations)} {category} recommendations")
                else:
                    errors.append(f"{category}: {store_result.get('message')}")
            else:
                logger.warning(f"No results for {preset} screener")

        except Exception as e:
            logger.exception(f"Error running {preset} screener: {e}")
            errors.append(f"{preset}: {str(e)}")

    result = {
        "status": "completed" if categories_generated else "failed",
        "date": today,
        "categories_generated": categories_generated,
        "total_categories": len(presets),
    }

    if errors:
        result["errors"] = errors

    logger.info(
        f"Daily recommendations complete: {len(categories_generated)}/{len(presets)} categories"
    )
    return result


@celery_app.task(bind=True, name="worker.tasks.screener.update_recommendation_returns")
def update_recommendation_returns(self) -> dict:
    """Update return metrics for past recommendations.

    This task runs daily after market close (4:00 PM IST / 10:30 UTC) to:
    - Update 1-day returns for recommendations from yesterday
    - Update 1-week returns for recommendations from 1 week ago
    - Update 1-month returns for recommendations from 1 month ago

    Uses the internal API to fetch current prices and update the database.
    """
    logger.info("Starting recommendation returns update")

    endpoint = f"{BACKEND_API_URL}/api/v1/screener/recommendations/update-returns"

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                endpoint,
                headers=_get_internal_headers(),
            )

            if response.status_code != 200:
                logger.error(f"Update returns error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"API returned {response.status_code}",
                }

            result = response.json()
            logger.info(
                f"Returns update complete: {result.get('updated_1d', 0)} 1d, "
                f"{result.get('updated_1w', 0)} 1w, {result.get('updated_1m', 0)} 1m"
            )
            return {"status": "success", **result}

    except httpx.TimeoutException:
        logger.error("Timeout updating recommendation returns")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error updating recommendation returns: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.screener.process_screener_alerts")
def process_screener_alerts(self) -> dict:
    """Process all enabled screener alerts.

    This task runs periodically to:
    1. Fetch all enabled screener alerts
    2. Run the associated screener for each alert
    3. Compare results with last_symbols
    4. Send notifications for new/removed symbols
    5. Update last_symbols and last_run_at

    Runs every 15 minutes during market hours, hourly otherwise.
    """
    logger.info("Starting screener alerts processing")

    endpoint = f"{BACKEND_API_URL}/api/v1/screener/alerts/process"

    try:
        with httpx.Client(timeout=300.0) as client:  # 5 min timeout
            response = client.post(
                endpoint,
                headers=_get_internal_headers(),
            )

            if response.status_code != 200:
                logger.error(
                    f"Process alerts error: {response.status_code} - {response.text}"
                )
                return {
                    "status": "error",
                    "message": f"API returned {response.status_code}",
                }

            result = response.json()
            logger.info(
                f"Alerts processing complete: {result.get('alerts_processed', 0)} processed, "
                f"{result.get('notifications_sent', 0)} notifications sent"
            )
            return {"status": "success", **result}

    except httpx.TimeoutException:
        logger.error("Timeout processing screener alerts")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error processing screener alerts: {e}")
        return {"status": "error", "message": str(e)}
