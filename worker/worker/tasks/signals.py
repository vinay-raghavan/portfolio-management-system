"""Signal generation background tasks.

This module provides Celery tasks for:
- Scheduled signal generation across user watchlists
- On-demand signal generation for specific symbols
- Signal expiration cleanup
"""

import logging
from datetime import time
from zoneinfo import ZoneInfo

import httpx
from redis import Redis

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

# Indian Standard Time
IST = ZoneInfo("Asia/Kolkata")

# Market timing
MARKET_OPEN_TIME = time(9, 15)  # 9:15 AM IST
MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM IST


def is_market_hours() -> bool:
    """Check if current time is within Indian market hours."""
    from datetime import datetime

    now_ist = datetime.now(IST)

    # Skip weekends
    if now_ist.weekday() >= 5:
        return False

    current_time = now_ist.time()
    return MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME


@celery_app.task(bind=True, name="worker.tasks.signals.generate_signals_for_user")
def generate_signals_for_user(self, user_id: str, symbols: list[str], strategy_name: str | None = None) -> dict:
    """Generate signals for a user's watchlist symbols.

    Args:
        user_id: User ID to generate signals for
        symbols: List of symbols to analyze
        strategy_name: Optional specific strategy (None = all strategies)

    Returns:
        Dictionary with generation results
    """
    logger.info(f"Generating signals for user {user_id} with {len(symbols)} symbols")

    if not symbols:
        return {"status": "no_symbols", "signals_generated": 0}

    try:
        api_url = "http://api:8000/api/v1/signals/generate"

        payload = {
            "symbols": symbols,
            "strategy_name": strategy_name,
            "timeframe": "1d",
        }

        # Call internal API (need to handle auth for this)
        # In production, use internal service tokens
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Generated {result.get('signals_generated', 0)} signals for user {user_id}")
                return {
                    "status": "success",
                    "user_id": user_id,
                    "signals_generated": result.get("signals_generated", 0),
                }
            else:
                logger.error(f"Signal generation failed: {response.status_code}")
                return {"status": "error", "message": f"API error: {response.status_code}"}

    except Exception as e:
        logger.error(f"Error generating signals for user {user_id}: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.signals.generate_daily_signals")
def generate_daily_signals(self) -> dict:
    """Generate daily signals for all users with watchlists.

    This task runs after market close to analyze all watched symbols
    and generate signals for the next trading day.
    """
    logger.info("Starting daily signal generation")

    redis_client = Redis.from_url(settings.REDIS_URL)

    # Get all user watchlists from Redis
    user_keys = redis_client.keys("watchlist:*")

    if not user_keys:
        logger.info("No user watchlists found")
        return {"status": "no_users", "users_processed": 0, "total_signals": 0}

    users_processed = 0

    for key in user_keys:
        try:
            user_id = key.decode().replace("watchlist:", "")
            symbols = redis_client.smembers(key)
            symbol_list = [s.decode() if isinstance(s, bytes) else s for s in symbols]

            if symbol_list:
                generate_signals_for_user.delay(user_id, symbol_list)
                users_processed += 1

        except Exception as e:
            logger.error(f"Error queuing signals for {key}: {e}")

    logger.info(f"Daily signal generation queued for {users_processed} users")
    return {
        "status": "success",
        "users_processed": users_processed,
    }


@celery_app.task(bind=True, name="worker.tasks.signals.expire_old_signals")
def expire_old_signals(self) -> dict:
    """Expire signals that have passed their expiration date.

    This task runs periodically to mark expired signals.
    """
    logger.info("Expiring old signals")

    try:
        api_url = "http://api:8000/api/v1/signals/expire"

        with httpx.Client(timeout=30.0) as client:
            response = client.post(api_url)

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Expired {result.get('expired_count', 0)} signals")
                return {"status": "success", "expired_count": result.get("expired_count", 0)}
            else:
                return {"status": "error", "message": f"API error: {response.status_code}"}

    except Exception as e:
        logger.error(f"Error expiring signals: {e}")
        return {"status": "error", "message": str(e)}

