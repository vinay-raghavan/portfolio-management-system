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
