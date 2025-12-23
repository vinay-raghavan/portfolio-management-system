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
from app.modules.algo.universe_service import (
    DYNAMIC_UNIVERSES,
    PREDEFINED_UNIVERSES,
    UniverseService,
)
from app.providers.data.nse import NSEDataProvider

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
    from celery import current_app

    service = AlgoService(db)
    strategy = await service.get_strategy(current_user.id, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Queue the execution using send_task (avoids circular import)
    task = current_app.send_task(
        "worker.tasks.algo.execute_strategy",
        args=[strategy_id, symbols],
    )
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


@router.get("/universes/definitions/available")
async def get_available_universe_definitions(
    current_user: CurrentUser,
) -> dict:
    """Get all available universe definitions (static + dynamic).

    Returns a list of all pre-defined universes that can be created,
    including both static (hardcoded symbols) and dynamic (fetched from NSE).
    """
    return {
        "universes": UniverseService.get_available_universes(),
        "dynamic_indices": list(DYNAMIC_UNIVERSES.keys()),
    }


@router.post("/universes/refresh/{universe_key}")
async def refresh_dynamic_universe(
    db: DbSession,
    current_user: CurrentUser,
    universe_key: str,
) -> UniverseResponse:
    """Refresh a dynamic universe by fetching latest constituents from NSE.

    Args:
        universe_key: Key of the dynamic universe (e.g., "NIFTY500", "NIFTY100")

    Returns:
        Updated universe with fresh symbols
    """
    if universe_key not in DYNAMIC_UNIVERSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown dynamic universe: {universe_key}. Available: {list(DYNAMIC_UNIVERSES.keys())}",
        )

    service = UniverseService(db)

    # Create NSE provider and fetch
    nse_provider = NSEDataProvider()
    try:
        universe = await service.create_or_update_dynamic_universe(universe_key, nse_provider)
        if not universe:
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch universe {universe_key} from NSE"
            )
        await db.commit()
        return UniverseResponse.model_validate(universe)
    finally:
        await nse_provider.close()


@router.post("/universes/refresh-all")
async def refresh_all_dynamic_universes(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Refresh all dynamic universes from NSE.

    This fetches the latest constituents for all dynamic indices:
    - Nifty 500, Nifty 100, Nifty 200
    - Nifty Midcap 50/100/150
    - Nifty Smallcap 50/100/250

    Returns:
        Summary of refresh operation
    """
    service = UniverseService(db)

    nse_provider = NSEDataProvider()
    try:
        count = await service.seed_dynamic_universes(nse_provider)

        # Also refresh All NSE and F&O universes
        await service.create_all_nse_universe()
        await service.create_fo_universe()

        await db.commit()

        return {
            "message": f"Successfully refreshed {count} dynamic universes",
            "refreshed_count": count,
            "dynamic_universes": list(DYNAMIC_UNIVERSES.keys()),
        }
    finally:
        await nse_provider.close()


@router.post("/universes/seed-all")
async def seed_all_universes(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Seed all predefined system universes and optionally refresh dynamic ones.

    This seeds:
    - All predefined static universes (Nifty 50, Bank Nifty, sectoral indices, etc.)
    - All dynamic universes from NSE (Nifty 500, Nifty 100, etc.)
    - All NSE stocks universe
    - F&O stocks universe

    Returns:
        Summary of seed operation
    """
    service = UniverseService(db)

    # Seed predefined static universes
    predefined_count = await service.seed_predefined_universes()

    # Seed dynamic universes from NSE
    nse_provider = NSEDataProvider()
    try:
        dynamic_count = await service.seed_dynamic_universes(nse_provider)

        # Also create All NSE and F&O universes
        await service.create_all_nse_universe()
        await service.create_fo_universe()

        await db.commit()

        return {
            "message": f"Successfully seeded {predefined_count} predefined + {dynamic_count} dynamic universes",
            "predefined_count": predefined_count,
            "dynamic_count": dynamic_count,
            "predefined_universes": list(PREDEFINED_UNIVERSES.keys()),
            "dynamic_universes": list(DYNAMIC_UNIVERSES.keys()),
        }
    finally:
        await nse_provider.close()


@router.get("/universes/index/{index_name}/constituents")
async def get_index_constituents(
    current_user: CurrentUser,
    index_name: str,
) -> dict:
    """Fetch current constituents of an NSE index directly.

    This is a live fetch from NSE, not from the database.

    Args:
        index_name: NSE index name (e.g., "NIFTY 500", "NIFTY BANK")

    Returns:
        Index constituents with basic quote data
    """
    nse_provider = NSEDataProvider()
    try:
        constituents = await nse_provider.get_index_constituents(index_name)
        if not constituents:
            raise HTTPException(
                status_code=404, detail=f"No constituents found for index: {index_name}"
            )

        return {
            "index": index_name,
            "count": len(constituents),
            "constituents": constituents,
        }
    finally:
        await nse_provider.close()
