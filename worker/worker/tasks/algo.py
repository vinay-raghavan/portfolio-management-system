"""Celery tasks for algo trading execution."""

import asyncio
import logging
from datetime import UTC, datetime

from redis import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

# Create async engine for database operations
engine = create_async_engine(settings.DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _run_scheduled_strategies_async() -> dict:
    """Async implementation of scheduled strategy execution."""
    from app.modules.algo.executor import StrategyExecutor
    from app.modules.algo.models import StrategyStatus, UserStrategy
    from app.modules.algo.safety import AlgoKillSwitch
    from app.modules.algo.scheduler import StrategyScheduler
    from app.providers.broker.factory import get_broker
    from app.providers.data.factory import get_data_provider

    async with async_session() as db:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        kill_switch = AlgoKillSwitch(redis_client)
        scheduler = StrategyScheduler(db)

        # Get strategies due to run
        due_strategies = await scheduler.get_due_strategies()
        logger.info(f"Found {len(due_strategies)} strategies due for execution")

        results = []
        for strategy in due_strategies:
            try:
                # Check kill switch for user
                if await kill_switch.is_active(strategy.user_id):
                    logger.warning(f"Kill switch active for user {strategy.user_id}, skipping strategy")
                    continue

                # Check if market is open for non-CRON strategies
                if not scheduler.is_market_hours() and strategy.schedule_type.value not in [
                    "CRON",
                    "MARKET_OPEN",
                    "MARKET_CLOSE",
                ]:
                    logger.debug(f"Market closed, skipping strategy {strategy.id}")
                    continue

                # Get broker and data provider
                broker = await get_broker(db, strategy.user_id, paper=strategy.is_paper_trading)
                data_provider = get_data_provider()

                # Execute strategy
                executor = StrategyExecutor(db, broker, data_provider)
                result = await executor.execute(strategy)

                # Update next run time
                await scheduler.update_next_run(strategy)
                await db.commit()

                results.append({
                    "strategy_id": strategy.id,
                    "status": result.status.value,
                    "signals": result.signals_generated,
                    "orders": result.orders_placed,
                })

            except Exception as e:
                logger.exception(f"Error executing strategy {strategy.id}: {e}")
                results.append({
                    "strategy_id": strategy.id,
                    "status": "ERROR",
                    "error": str(e),
                })

        redis_client.close()
        return {"executed": len(results), "results": results}


@celery_app.task(bind=True, name="worker.tasks.algo.run_scheduled_strategies")
def run_scheduled_strategies(self) -> dict:
    """Run all scheduled strategies that are due."""
    logger.info("Starting scheduled strategy execution check")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_run_scheduled_strategies_async())


async def _execute_strategy_async(strategy_id: str, symbols_override: list[str] | None = None) -> dict:
    """Async implementation of single strategy execution."""
    from app.modules.algo.executor import ExecutionResult, StrategyExecutor
    from app.modules.algo.models import UserStrategy
    from app.modules.algo.safety import AlgoKillSwitch
    from app.modules.algo.scheduler import StrategyScheduler
    from app.providers.broker.factory import get_broker
    from app.providers.data.factory import get_data_provider

    async with async_session() as db:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

        # Get strategy
        result = await db.execute(select(UserStrategy).where(UserStrategy.id == strategy_id))
        strategy = result.scalar_one_or_none()

        if not strategy:
            redis_client.close()
            return {"status": "error", "message": f"Strategy {strategy_id} not found"}

        # Check kill switch
        kill_switch = AlgoKillSwitch(redis_client)
        if await kill_switch.is_active(strategy.user_id):
            redis_client.close()
            return {"status": "blocked", "message": "Kill switch is active"}

        try:
            broker = await get_broker(db, strategy.user_id, paper=strategy.is_paper_trading)
            data_provider = get_data_provider()

            executor = StrategyExecutor(db, broker, data_provider)
            exec_result = await executor.execute(strategy, symbols_override)

            # Update next run time
            scheduler = StrategyScheduler(db)
            await scheduler.update_next_run(strategy)
            await db.commit()

            redis_client.close()
            return {
                "status": "success",
                "execution_id": exec_result.execution_id,
                "execution_status": exec_result.status.value,
                "signals_generated": exec_result.signals_generated,
                "orders_placed": exec_result.orders_placed,
            }

        except Exception as e:
            logger.exception(f"Error executing strategy {strategy_id}: {e}")
            redis_client.close()
            return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.algo.execute_strategy")
def execute_strategy(self, strategy_id: str, symbols_override: list[str] | None = None) -> dict:
    """Execute a specific strategy.

    Args:
        strategy_id: ID of the strategy to execute
        symbols_override: Optional list of symbols to trade instead of universe
    """
    logger.info(f"Executing strategy {strategy_id}")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_execute_strategy_async(strategy_id, symbols_override))

