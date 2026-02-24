"""Celery tasks for algo trading execution.

This module calls the Trading Engine microservice for all strategy execution.
The trading engine handles:
- Querying due strategies from the database
- Executing strategies and placing orders
- Updating next run times

Flow: Celery Worker → Trading Engine :8001
"""

import logging

import httpx

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

# Trading Engine URL - the dedicated strategy execution service
TRADING_ENGINE_URL = getattr(settings, "INTERNAL_API_URL", "http://trading-engine:8001")
INTERNAL_API_KEY = getattr(settings, "INTERNAL_API_KEY", "internal-worker-key")


def _get_internal_headers() -> dict:
    """Get headers for internal API calls."""
    return {
        "Content-Type": "application/json",
        "X-Internal-Key": INTERNAL_API_KEY,
    }


def _run_scheduled_strategies_sync() -> dict:
    """Synchronous implementation of scheduled strategy execution.

    Calls the trading engine's /internal/run-scheduled endpoint.
    The trading engine handles:
    - Querying due strategies from database
    - Checking kill switches
    - Executing strategies
    - Updating next run times
    """
    logger.info("Calling trading engine to run scheduled strategies")

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{TRADING_ENGINE_URL}/internal/run-scheduled",
                headers=_get_internal_headers(),
            )

            if response.status_code != 200:
                logger.error(f"Trading engine error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Trading engine returned {response.status_code}",
                }

            result = response.json()
            logger.info(
                f"Scheduled execution complete: {result.get('executed', 0)} strategies executed"
            )
            return {"status": "success", **result}

    except httpx.TimeoutException:
        logger.error("Timeout calling trading engine")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error in scheduled strategy execution: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.algo.run_scheduled_strategies")
def run_scheduled_strategies(self) -> dict:
    """Run all scheduled strategies that are due.

    This task is called by Celery beat every 30 seconds.
    It calls the trading engine's /internal/run-scheduled endpoint.
    """
    logger.info("Starting scheduled strategy execution check")
    return _run_scheduled_strategies_sync()


def _execute_strategy_by_id_sync(strategy_id: str) -> dict:
    """Execute a strategy by ID via trading engine."""
    logger.info(f"Calling trading engine to execute strategy {strategy_id}")

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{TRADING_ENGINE_URL}/internal/execute/{strategy_id}",
                headers=_get_internal_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Strategy {strategy_id} execution result: {result.get('status')}")
                return result
            elif response.status_code == 404:
                logger.error(f"Strategy {strategy_id} not found")
                return {"status": "error", "message": "Strategy not found"}
            else:
                logger.error(f"Trading engine error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Trading engine returned {response.status_code}",
                }

    except httpx.TimeoutException:
        logger.error(f"Timeout executing strategy {strategy_id}")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error executing strategy {strategy_id}: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.algo.execute_strategy")
def execute_strategy(self, strategy_id: str) -> dict:
    """Execute a specific strategy by ID.

    This task is queued when a user manually triggers a strategy.
    It calls the trading engine's /internal/execute/{strategy_id} endpoint.

    Args:
        strategy_id: ID of the strategy to execute
    """
    logger.info(f"Executing strategy {strategy_id}")
    return _execute_strategy_by_id_sync(strategy_id)


def _sync_circuit_breakers_sync() -> dict:
    """Synchronous implementation of circuit breaker sync.

    Calls the trading engine's /internal/circuit-breaker/sync-all endpoint.
    """
    logger.info("Syncing circuit breaker states to database")

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{TRADING_ENGINE_URL}/internal/circuit-breaker/sync-all",
                headers=_get_internal_headers(),
            )

            if response.status_code != 200:
                logger.error(f"Trading engine error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Trading engine returned {response.status_code}",
                }

            result = response.json()
            logger.info(f"Circuit breaker sync complete: {result.get('synced', 0)} synced")
            return {"status": "success", **result}

    except httpx.TimeoutException:
        logger.error("Timeout calling trading engine for circuit breaker sync")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error syncing circuit breakers: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.algo.sync_circuit_breakers")
def sync_circuit_breakers(self) -> dict:
    """Sync all circuit breaker states from Redis to DB.

    This task is called by Celery beat every 5 minutes to persist
    circuit breaker state for recovery after restarts.
    """
    logger.info("Starting circuit breaker sync")
    return _sync_circuit_breakers_sync()


def _is_market_hours() -> bool:
    """Check if current time is within Indian market hours (9:15 AM - 3:30 PM IST).

    Also skips weekends.
    """
    from datetime import datetime, time
    from zoneinfo import ZoneInfo

    IST = ZoneInfo("Asia/Kolkata")
    now_ist = datetime.now(IST)

    # Skip weekends
    if now_ist.weekday() >= 5:
        return False

    market_open = time(9, 15)
    market_close = time(15, 30)
    current_time = now_ist.time()

    return market_open <= current_time <= market_close


def _check_stop_monitors_sync() -> dict:
    """Synchronous implementation of stop monitor check.

    Calls the trading engine's /internal/check-stop-monitors endpoint.
    """
    if not _is_market_hours():
        logger.debug("Market closed, skipping stop monitor check")
        return {"status": "market_closed", "checked": 0}

    logger.info("Checking trailing stops and circuit breakers for all active strategies")

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{TRADING_ENGINE_URL}/internal/check-stop-monitors",
                headers=_get_internal_headers(),
            )

            if response.status_code != 200:
                logger.error(f"Trading engine error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Trading engine returned {response.status_code}",
                }

            result = response.json()
            if result.get("positions_closed", 0) > 0:
                logger.info(
                    f"Stop monitor: Closed {result['positions_closed']} positions, "
                    f"{result.get('circuit_breakers_triggered', 0)} CB triggered"
                )
            else:
                logger.debug(
                    f"Stop monitor complete: {result.get('checked', 0)} strategies checked"
                )
            return {"status": "success", **result}

    except httpx.TimeoutException:
        logger.error("Timeout calling trading engine for stop monitor")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error in stop monitor check: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.algo.check_stop_monitors")
def check_stop_monitors(self) -> dict:
    """Check trailing stops and circuit breakers for all active strategies.

    This task is called by Celery beat every 5 minutes during market hours.
    It ensures trailing stops and unrealized loss circuit breakers are
    checked frequently, even for strategies with longer execution intervals.
    """
    logger.info("Starting stop monitor check")
    return _check_stop_monitors_sync()


# =============================================================================
# Auto-Trade Pipeline Tasks
# =============================================================================


def _process_auto_trades_sync(category: str, symbols: list[str], date_str: str) -> dict:
    """Process auto-trades for a category after recommendations are generated.

    Calls the backend's internal API to process auto-trades for all users
    with auto-trade enabled for this category.
    """
    from worker.config import settings as worker_settings

    backend_url = worker_settings.BACKEND_API_URL
    logger.info(f"Processing auto-trades for category '{category}' with {len(symbols)} symbols")

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{backend_url}/auto-trade/internal/process",
                headers=_get_internal_headers(),
                json={
                    "category": category,
                    "symbols": symbols,
                    "date": date_str,
                },
            )

            if response.status_code != 200:
                logger.error(
                    f"Auto-trade processing error: {response.status_code} - {response.text}"
                )
                return {
                    "status": "error",
                    "message": f"Backend returned {response.status_code}",
                }

            result = response.json()
            logger.info(
                f"Auto-trade processing complete: "
                f"{result.get('users_processed', 0)} users processed, "
                f"{result.get('status', 'unknown')} status"
            )
            return {"status": "success", **result}

    except httpx.TimeoutException:
        logger.error("Timeout processing auto-trades")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error processing auto-trades: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.algo.process_auto_trades")
def process_auto_trades(self, category: str, symbols: list[str], date_str: str) -> dict:
    """Process auto-trades after daily recommendations are generated.

    Called by generate_daily_recommendations task after storing recommendations.

    For each user with auto-trade enabled for this category:
    1. Check daily limits (positions, capital)
    2. If confirmation_mode == AUTO:
       - Create strategy from template immediately
       - Activate strategy
    3. If confirmation_mode == NOTIFY:
       - Create pending auto-trade
       - Send notification to user

    Args:
        category: Recommendation category (momentum, breakout, value, sector)
        symbols: List of recommended symbols
        date_str: Date string in ISO format

    Returns:
        Summary of processing results
    """
    logger.info(f"Starting auto-trade processing for {category}")
    return _process_auto_trades_sync(category, symbols, date_str)


def _expire_pending_auto_trades_sync() -> dict:
    """Expire pending auto-trades that have passed their expiry time."""
    from worker.config import settings as worker_settings

    backend_url = worker_settings.BACKEND_API_URL
    logger.info("Checking for expired pending auto-trades")

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{backend_url}/auto-trade/internal/expire-pending",
                headers=_get_internal_headers(),
            )

            if response.status_code != 200:
                logger.error(f"Expire pending error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Backend returned {response.status_code}",
                }

            result = response.json()
            if result.get("expired_count", 0) > 0:
                logger.info(f"Expired {result['expired_count']} pending auto-trades")
            return {"status": "success", **result}

    except httpx.TimeoutException:
        logger.error("Timeout expiring pending auto-trades")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error expiring pending auto-trades: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.algo.expire_pending_auto_trades")
def expire_pending_auto_trades(self) -> dict:
    """Expire pending auto-trades that have passed their expiry time.

    Scheduled to run every hour.

    Returns:
        {expired_count: int, notifications_sent: list}
    """
    logger.info("Starting pending auto-trade expiration check")
    return _expire_pending_auto_trades_sync()
