"""API routes for algo trading."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis

from app.api.deps import CurrentUser, DbSession
from app.core.redis import get_redis
from app.modules.algo.models import StrategyStatus
from app.modules.algo.notifications import AlgoNotificationService
from app.modules.algo.safety import AlgoKillSwitch, CircuitBreaker
from app.modules.algo.schemas import (
    CircuitBreakerStatus,
    ExecutionHistoryResponse,
    KillSwitchResponse,
    KillSwitchToggle,
    StrategyCreate,
    StrategyResponse,
    StrategyUpdate,
    UniverseCreate,
    UniverseResponse,
    UniverseUpdate,
)
from app.modules.algo.service import AlgoService
from app.modules.algo.universe_service import UniverseService

logger = logging.getLogger(__name__)

# Notification service instance
_notification_service = AlgoNotificationService()

router = APIRouter()


# ============== Strategy Endpoints ==============


@router.get("/strategies", response_model=list[StrategyResponse])
async def list_strategies(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: StrategyStatus | None = None,
) -> list[StrategyResponse]:
    """List all strategies for the current user."""
    service = AlgoService(db)
    strategies = await service.get_user_strategies(current_user.id, status_filter)
    return [StrategyResponse.model_validate(s) for s in strategies]


@router.post("/strategies", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    db: DbSession,
    current_user: CurrentUser,
    data: StrategyCreate,
) -> StrategyResponse:
    """Create a new algo strategy."""
    service = AlgoService(db)
    strategy = await service.create_strategy(current_user.id, data)
    await db.commit()
    return StrategyResponse.model_validate(strategy)


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
) -> StrategyResponse:
    """Get a specific strategy."""
    service = AlgoService(db)
    strategy = await service.get_strategy(current_user.id, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return StrategyResponse.model_validate(strategy)


@router.patch("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
    data: StrategyUpdate,
) -> StrategyResponse:
    """Update a strategy."""
    service = AlgoService(db)
    strategy = await service.update_strategy(current_user.id, strategy_id, data)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await db.commit()
    return StrategyResponse.model_validate(strategy)


@router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
) -> None:
    """Delete a strategy."""
    service = AlgoService(db)
    deleted = await service.delete_strategy(current_user.id, strategy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await db.commit()


@router.post("/strategies/{strategy_id}/enable", response_model=StrategyResponse)
async def enable_strategy(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
) -> StrategyResponse:
    """Enable a strategy for execution."""
    service = AlgoService(db)
    strategy = await service.enable_strategy(current_user.id, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await db.commit()
    return StrategyResponse.model_validate(strategy)


@router.post("/strategies/{strategy_id}/disable", response_model=StrategyResponse)
async def disable_strategy(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
) -> StrategyResponse:
    """Disable a strategy."""
    service = AlgoService(db)
    strategy = await service.disable_strategy(current_user.id, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await db.commit()
    return StrategyResponse.model_validate(strategy)


@router.post("/strategies/{strategy_id}/trigger")
async def trigger_strategy(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
    symbols: list[str] | None = None,
) -> dict:
    """Manually trigger a strategy execution."""
    from worker.tasks.algo import execute_strategy

    service = AlgoService(db)
    strategy = await service.get_strategy(current_user.id, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Queue the execution
    task = execute_strategy.delay(strategy_id, symbols)
    return {"task_id": task.id, "status": "queued", "strategy_id": strategy_id}


@router.get("/strategies/{strategy_id}/executions", response_model=list[ExecutionHistoryResponse])
async def get_execution_history(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
    limit: int = Query(default=50, le=200),
) -> list[ExecutionHistoryResponse]:
    """Get execution history for a strategy."""
    service = AlgoService(db)
    executions = await service.get_execution_history(current_user.id, strategy_id, limit)
    return [ExecutionHistoryResponse.model_validate(e) for e in executions]


@router.get("/strategies/{strategy_id}/circuit-breaker", response_model=CircuitBreakerStatus)
async def get_circuit_breaker_status(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
    redis: Annotated[Redis, Depends(get_redis)],
) -> CircuitBreakerStatus:
    """Get circuit breaker status for a strategy."""
    service = AlgoService(db)
    strategy = await service.get_strategy(current_user.id, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    circuit_breaker = CircuitBreaker(redis)
    state = await circuit_breaker.get_state(strategy)

    return CircuitBreakerStatus(
        strategy_id=strategy_id,
        is_triggered=state.is_triggered,
        trigger_reason=state.trigger_reason,
        daily_loss=state.daily_loss,
        consecutive_losses=state.consecutive_losses,
        triggered_at=state.triggered_at,
        max_daily_loss=strategy.max_daily_loss,
        max_consecutive_losses=strategy.max_consecutive_losses,
    )


@router.post("/strategies/{strategy_id}/circuit-breaker/reset")
async def reset_circuit_breaker(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict:
    """Reset circuit breaker for a strategy."""
    service = AlgoService(db)
    strategy = await service.get_strategy(current_user.id, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    circuit_breaker = CircuitBreaker(redis)
    await circuit_breaker.reset(strategy_id)

    return {"status": "reset", "strategy_id": strategy_id}


# ============== Kill Switch Endpoints ==============


@router.get("/kill-switch", response_model=KillSwitchResponse)
async def get_kill_switch_status(
    current_user: CurrentUser,
    redis: Annotated[Redis, Depends(get_redis)],
) -> KillSwitchResponse:
    """Get kill switch status for current user."""
    kill_switch = AlgoKillSwitch(redis)
    state = await kill_switch.get_state(current_user.id)
    return KillSwitchResponse(
        is_active=state.is_active,
        activated_at=state.activated_at,
        reason=state.reason,
        square_off_initiated=state.square_off_initiated,
    )


@router.post("/kill-switch", response_model=KillSwitchResponse)
async def toggle_kill_switch(
    current_user: CurrentUser,
    redis: Annotated[Redis, Depends(get_redis)],
    data: KillSwitchToggle,
) -> KillSwitchResponse:
    """Activate or deactivate kill switch."""
    kill_switch = AlgoKillSwitch(redis)

    if data.activate:
        state = await kill_switch.activate(
            current_user.id,
            reason=data.reason,
            square_off=data.square_off,
        )
        logger.warning(f"Kill switch ACTIVATED by user {current_user.id}")
        # Send notification
        await _notification_service.notify_kill_switch_activated(
            user_id=current_user.id,
            reason=data.reason,
        )
    else:
        state = await kill_switch.deactivate(current_user.id)
        logger.info(f"Kill switch DEACTIVATED by user {current_user.id}")

    return KillSwitchResponse(
        is_active=state.is_active,
        activated_at=state.activated_at,
        reason=state.reason,
        square_off_initiated=state.square_off_initiated,
    )


@router.post("/emergency-stop")
async def emergency_stop(
    db: DbSession,
    current_user: CurrentUser,
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict:
    """Emergency stop: activate kill switch and disable all strategies."""
    # Activate kill switch with square-off
    kill_switch = AlgoKillSwitch(redis)
    await kill_switch.activate(
        current_user.id,
        reason="Emergency stop triggered",
        square_off=True,
    )

    # Disable all active strategies
    service = AlgoService(db)
    disabled_count = await service.disable_all_strategies(current_user.id)
    await db.commit()

    logger.critical(
        f"EMERGENCY STOP by user {current_user.id}: {disabled_count} strategies disabled"
    )

    # Send notification
    await _notification_service.notify_kill_switch_activated(
        user_id=current_user.id,
        reason="Emergency stop triggered",
        strategies_disabled=disabled_count,
    )

    return {
        "status": "emergency_stop_activated",
        "strategies_disabled": disabled_count,
        "kill_switch_active": True,
        "square_off_initiated": True,
    }


# ============== Universe Endpoints ==============


@router.get("/universes", response_model=list[UniverseResponse])
async def list_universes(
    db: DbSession,
    current_user: CurrentUser,
) -> list[UniverseResponse]:
    """List all universes accessible to the user."""
    service = UniverseService(db)
    universes = await service.get_user_universes(current_user.id)
    return [UniverseResponse.model_validate(u) for u in universes]


@router.post("/universes", response_model=UniverseResponse, status_code=status.HTTP_201_CREATED)
async def create_universe(
    db: DbSession,
    current_user: CurrentUser,
    data: UniverseCreate,
) -> UniverseResponse:
    """Create a custom universe."""
    service = UniverseService(db)
    universe = await service.create(current_user.id, data)
    await db.commit()
    return UniverseResponse.model_validate(universe)


@router.get("/universes/{universe_id}", response_model=UniverseResponse)
async def get_universe(
    db: DbSession,
    current_user: CurrentUser,
    universe_id: str,
) -> UniverseResponse:
    """Get a specific universe."""
    service = UniverseService(db)
    universe = await service.get_by_id(universe_id)
    if not universe:
        raise HTTPException(status_code=404, detail="Universe not found")
    # Check access
    if universe.user_id and universe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return UniverseResponse.model_validate(universe)


@router.patch("/universes/{universe_id}", response_model=UniverseResponse)
async def update_universe(
    db: DbSession,
    current_user: CurrentUser,
    universe_id: str,
    data: UniverseUpdate,
) -> UniverseResponse:
    """Update a custom universe."""
    service = UniverseService(db)
    universe = await service.update(current_user.id, universe_id, data)
    if not universe:
        raise HTTPException(status_code=404, detail="Universe not found or access denied")
    await db.commit()
    return UniverseResponse.model_validate(universe)


@router.delete("/universes/{universe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_universe(
    db: DbSession,
    current_user: CurrentUser,
    universe_id: str,
) -> None:
    """Delete a custom universe."""
    service = UniverseService(db)
    deleted = await service.delete(current_user.id, universe_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Universe not found or access denied")
    await db.commit()


@router.get("/universes/{universe_id}/symbols")
async def get_universe_symbols(
    db: DbSession,
    current_user: CurrentUser,
    universe_id: str,
) -> dict:
    """Get resolved symbols for a universe."""
    service = UniverseService(db)
    universe = await service.get_by_id(universe_id)
    if not universe:
        raise HTTPException(status_code=404, detail="Universe not found")
    if universe.user_id and universe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    symbols = await service.resolve_symbols(universe)
    return {
        "universe_id": universe_id,
        "name": universe.name,
        "symbols": symbols,
        "count": len(symbols),
    }
