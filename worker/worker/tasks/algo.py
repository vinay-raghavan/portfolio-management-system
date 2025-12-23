"""Celery tasks for algo trading execution.

This module uses HTTP calls to the backend's internal API endpoints
to execute trading strategies. This avoids circular dependencies between
the worker and backend packages.
"""

import logging

import httpx

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

# Internal API URL for the backend service
# In Docker, this resolves to the api container
INTERNAL_API_URL = getattr(settings, "INTERNAL_API_URL", "http://api:8000")
INTERNAL_API_KEY = getattr(settings, "INTERNAL_API_KEY", "internal-worker-key")


def _get_internal_headers() -> dict:
    """Get headers for internal API calls."""
    return {
        "Content-Type": "application/json",
        "X-Internal-Key": INTERNAL_API_KEY,
    }


def _run_scheduled_strategies_sync() -> dict:
    """Synchronous implementation of scheduled strategy execution via HTTP."""
    logger.info("Calling internal API to run scheduled strategies")

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{INTERNAL_API_URL}/internal/algo/run-scheduled",
                headers=_get_internal_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Scheduled strategies executed: {result.get('executed', 0)}")
                return result
            else:
                logger.error(f"Internal API error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Internal API returned {response.status_code}",
                }

    except httpx.TimeoutException:
        logger.error("Timeout calling internal API for scheduled strategies")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error calling internal API: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.algo.run_scheduled_strategies")
def run_scheduled_strategies(self) -> dict:
    """Run all scheduled strategies that are due.

    This task is called by Celery beat every 30 seconds.
    It calls the backend's internal API to execute due strategies.
    """
    logger.info("Starting scheduled strategy execution check")
    return _run_scheduled_strategies_sync()


def _execute_strategy_sync(
    strategy_id: str, symbols_override: list[str] | None = None
) -> dict:
    """Synchronous implementation of single strategy execution via HTTP."""
    logger.info(f"Calling internal API to execute strategy {strategy_id}")

    try:
        with httpx.Client(timeout=120.0) as client:
            # Build URL with optional symbols override
            url = f"{INTERNAL_API_URL}/internal/algo/execute/{strategy_id}"

            # Add symbols_override as query params if provided
            params = {}
            if symbols_override:
                params["symbols_override"] = symbols_override

            response = client.post(
                url,
                headers=_get_internal_headers(),
                params=params,
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Strategy {strategy_id} execution result: {result.get('status')}")
                return result
            else:
                logger.error(f"Internal API error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Internal API returned {response.status_code}",
                }

    except httpx.TimeoutException:
        logger.error(f"Timeout executing strategy {strategy_id}")
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        logger.exception(f"Error executing strategy {strategy_id}: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.algo.execute_strategy")
def execute_strategy(self, strategy_id: str, symbols_override: list[str] | None = None) -> dict:
    """Execute a specific strategy.

    This task is queued when a user manually triggers a strategy.
    It calls the backend's internal API to execute the strategy.

    Args:
        strategy_id: ID of the strategy to execute
        symbols_override: Optional list of symbols to trade instead of universe
    """
    logger.info(f"Executing strategy {strategy_id}")
    return _execute_strategy_sync(strategy_id, symbols_override)
