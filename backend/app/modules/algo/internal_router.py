"""Internal API routes for algo trading.

These endpoints are called by the Celery worker and should not be exposed
to external clients. They bypass user authentication and use internal
service-to-service communication.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from redis.asyncio import Redis

from app.api.deps import DbSession
from app.core.config import settings
from app.core.redis import get_redis
from app.modules.algo.executor import StrategyExecutor
from app.modules.algo.models import UserStrategy
from app.modules.algo.safety import AlgoKillSwitch
from app.modules.algo.scheduler import StrategyScheduler
from app.providers.broker.factory import get_broker
from app.providers.data.factory import get_data_provider

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple internal API key validation (in production, use proper service auth)
INTERNAL_API_KEY = getattr(settings, "INTERNAL_API_KEY", "internal-worker-key")


async def verify_internal_request(
    x_internal_key: Annotated[str | None, Header()] = None,
) -> None:
    """Verify the request is from an internal service."""
    # In development/Docker, we trust requests from the internal network
    # In production, you'd want proper service-to-service auth (mTLS, JWT, etc.)
    if x_internal_key and x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal API key")


@router.post("/run-scheduled")
async def run_scheduled_strategies(
    db: DbSession,
    redis: Annotated[Redis, Depends(get_redis)],
    _: Annotated[None, Depends(verify_internal_request)],
) -> dict:
    """Run all strategies that are due for execution.
    
    This endpoint is called by the Celery beat scheduler.
    """
    kill_switch = AlgoKillSwitch(redis)
    scheduler = StrategyScheduler(db)
    
    # Get strategies due to run
    due_strategies = await scheduler.get_due_strategies()
    logger.info(f"Found {len(due_strategies)} strategies due for execution")
    
    results = []
    for strategy in due_strategies:
        try:
            # Check kill switch for user
            if await kill_switch.is_active(strategy.user_id):
                logger.warning(
                    f"Kill switch active for user {strategy.user_id}, skipping strategy"
                )
                results.append({
                    "strategy_id": strategy.id,
                    "status": "SKIPPED",
                    "reason": "kill_switch_active",
                })
                continue
            
            # Check if market is open for non-CRON strategies
            if not scheduler.is_market_hours() and strategy.schedule_type.value not in [
                "CRON",
                "MARKET_OPEN",
                "MARKET_CLOSE",
            ]:
                logger.debug(f"Market closed, skipping strategy {strategy.id}")
                results.append({
                    "strategy_id": strategy.id,
                    "status": "SKIPPED",
                    "reason": "market_closed",
                })
                continue
            
            # Get broker and data provider
            broker = get_broker()
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
    
    return {"executed": len(results), "results": results}


@router.post("/execute/{strategy_id}")
async def execute_strategy(
    strategy_id: str,
    db: DbSession,
    redis: Annotated[Redis, Depends(get_redis)],
    _: Annotated[None, Depends(verify_internal_request)],
    symbols_override: Annotated[list[str] | None, Query()] = None,
) -> dict:
    """Execute a specific strategy.
    
    This endpoint is called by the Celery worker for on-demand execution.
    """
    from sqlalchemy import select
    
    # Get strategy
    result = await db.execute(
        select(UserStrategy).where(UserStrategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        return {"status": "error", "message": f"Strategy {strategy_id} not found"}
    
    # Check kill switch
    kill_switch = AlgoKillSwitch(redis)
    if await kill_switch.is_active(strategy.user_id):
        return {"status": "blocked", "message": "Kill switch is active"}
    
    try:
        broker = get_broker()
        data_provider = get_data_provider()
        
        executor = StrategyExecutor(db, broker, data_provider)
        exec_result = await executor.execute(strategy, symbols_override)
        
        # Update next run time
        scheduler = StrategyScheduler(db)
        await scheduler.update_next_run(strategy)
        await db.commit()
        
        return {
            "status": "success",
            "execution_id": exec_result.execution_id,
            "execution_status": exec_result.status.value,
            "signals_generated": exec_result.signals_generated,
            "orders_placed": exec_result.orders_placed,
        }
    
    except Exception as e:
        logger.exception(f"Error executing strategy {strategy_id}: {e}")
        return {"status": "error", "message": str(e)}

