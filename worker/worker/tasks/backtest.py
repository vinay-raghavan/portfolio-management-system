"""Backtest background tasks.

This module provides Celery tasks for:
- Async backtest execution
- Batch backtest runs
"""

import logging

import httpx

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.backtest.run_backtest_async")
def run_backtest_async(self, backtest_id: str) -> dict:
    """Run a backtest asynchronously.

    Args:
        backtest_id: ID of the backtest to run

    Returns:
        Dictionary with backtest results
    """
    logger.info(f"Starting async backtest {backtest_id}")

    try:
        api_url = f"http://api:8000/api/v1/backtest/{backtest_id}/run"

        with httpx.Client(timeout=300.0) as client:
            response = client.post(api_url)

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Backtest {backtest_id} completed successfully")
                return {
                    "status": "success",
                    "backtest_id": backtest_id,
                    "total_return": result.get("performance", {}).get("total_return"),
                    "sharpe_ratio": result.get("performance", {}).get("sharpe_ratio"),
                }
            else:
                logger.error(f"Backtest {backtest_id} failed: {response.status_code}")
                return {
                    "status": "error",
                    "backtest_id": backtest_id,
                    "message": f"API error: {response.status_code}",
                }

    except Exception as e:
        logger.error(f"Error running backtest {backtest_id}: {e}")
        return {"status": "error", "backtest_id": backtest_id, "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.backtest.run_batch_backtests")
def run_batch_backtests(
    self,
    user_id: str,
    symbol: str,
    strategy_names: list[str],
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0,
) -> dict:
    """Run multiple backtests for different strategies on the same symbol.

    Args:
        user_id: User ID
        symbol: Symbol to backtest
        strategy_names: List of strategy names to test
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        initial_capital: Initial capital for each backtest

    Returns:
        Dictionary with batch results
    """
    logger.info(f"Starting batch backtest for {symbol} with {len(strategy_names)} strategies")

    results = []

    for strategy_name in strategy_names:
        try:
            api_url = "http://api:8000/api/v1/backtest"

            payload = {
                "symbol": symbol,
                "strategy_name": strategy_name,
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
            }

            with httpx.Client(timeout=300.0) as client:
                response = client.post(
                    api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 201:
                    result = response.json()
                    results.append(
                        {
                            "strategy": strategy_name,
                            "status": "success",
                            "backtest_id": result.get("id"),
                            "total_return": result.get("performance", {}).get("total_return"),
                            "sharpe_ratio": result.get("performance", {}).get("sharpe_ratio"),
                        }
                    )
                else:
                    results.append(
                        {
                            "strategy": strategy_name,
                            "status": "error",
                            "message": f"API error: {response.status_code}",
                        }
                    )

        except Exception as e:
            logger.error(f"Error running backtest for {strategy_name}: {e}")
            results.append(
                {
                    "strategy": strategy_name,
                    "status": "error",
                    "message": str(e),
                }
            )

    logger.info(f"Batch backtest completed: {len(results)} strategies tested")
    return {
        "status": "success",
        "symbol": symbol,
        "strategies_tested": len(results),
        "results": results,
    }
