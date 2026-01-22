"""API routes for algo trading."""

import logging
from decimal import Decimal
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
    ClosePositionRequest,
    ClosePositionResponse,
    ExecutionHistoryResponse,
    KillSwitchResponse,
    KillSwitchToggle,
    PnLByStrategyResponse,
    PnLHistoryResponse,
    PnLSummary,
    PositionResponse,
    SquareOffStrategyRequest,
    SquareOffStrategyResponse,
    StrategyCreate,
    StrategyResponse,
    StrategyUpdate,
    UniverseCreate,
    UniverseResponse,
    UniverseUpdate,
    UnrealizedPnLResponse,
)
from app.modules.algo.service import AlgoService
from app.modules.algo.universe_service import (
    DYNAMIC_UNIVERSES,
    PREDEFINED_UNIVERSES,
    UniverseService,
)
from app.modules.portfolio.schemas import (
    ProfitBookingRules,
    TrailingStopConfig,
    TrailingStopUpdate,
)
from app.providers.data import NSEDataProvider

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
    """List all strategies for the current user with recent execution details."""
    service = AlgoService(db)
    strategies = await service.get_user_strategies(
        current_user.id, status_filter, load_recent_executions=True
    )
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
    """Get a specific strategy with recent execution details."""
    service = AlgoService(db)
    strategy = await service.get_strategy(current_user.id, strategy_id, load_recent_executions=True)
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
    from app.core.celery_client import celery_client

    service = AlgoService(db)
    strategy = await service.get_strategy(current_user.id, strategy_id, load_universe=True)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Get symbols from strategy if not overridden
    strategy_symbols = symbols
    if not strategy_symbols:
        if strategy.custom_symbols:
            strategy_symbols = strategy.custom_symbols
        elif strategy.universe:
            strategy_symbols = strategy.universe.symbols
        else:
            strategy_symbols = []

    # Queue the execution using send_task
    # The trading engine will fetch the strategy from the database
    task = celery_client.send_task(
        "worker.tasks.algo.execute_strategy",
        kwargs={"strategy_id": strategy_id},
    )
    return {
        "task_id": task.id,
        "status": "queued",
        "strategy_id": strategy_id,
        "symbols_count": len(strategy_symbols) if strategy_symbols else 0,
    }


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
        triggered_at=state.triggered_at,
        daily_loss=state.daily_loss,
        consecutive_losses=state.consecutive_losses,
        max_daily_loss=strategy.max_daily_loss,
        max_consecutive_losses=strategy.max_consecutive_losses,
        current_drawdown_percent=Decimal("0"),  # TODO: Calculate from positions
        max_drawdown_percent=strategy.max_drawdown_percent,
        daily_profit=state.daily_profit,
        max_daily_profit=strategy.max_daily_profit,
        overall_profit=state.overall_profit,
        overall_profit_target=strategy.overall_profit_target,
        profit_cutoff_triggered=state.profit_cutoff_triggered,
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


# ============== Position Exit Endpoints ==============


@router.post(
    "/strategies/{strategy_id}/positions/{symbol}/close",
    response_model=ClosePositionResponse,
)
async def close_position(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
    symbol: str,
    data: ClosePositionRequest | None = None,
) -> ClosePositionResponse:
    """Close a specific position within a strategy.

    Closes all or part of an open position for a specific symbol.
    If no exit price is provided, fetches current market price.
    If no quantity is provided, closes the entire position.
    """
    from app.providers.data import YahooDataProvider

    service = AlgoService(db)

    # Verify strategy exists and belongs to user
    strategy = await service.get_strategy(current_user.id, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Check if position exists
    position = await service.get_open_position(current_user.id, strategy_id, symbol)
    if not position:
        raise HTTPException(
            status_code=404,
            detail=f"No open position found for {symbol} in this strategy",
        )

    # Get exit price
    exit_price = data.exit_price if data and data.exit_price else None
    quantity = data.quantity if data else None

    if not exit_price:
        # Fetch current market price
        data_provider = YahooDataProvider()
        try:
            quote = await data_provider.get_quote(symbol)
            if quote and quote.price:
                exit_price = Decimal(str(quote.price))
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not fetch current price for {symbol}. Please provide exit_price.",
                )
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Could not fetch current price for {symbol}. Please provide exit_price.",
            )

    result = await service.close_position(
        user_id=current_user.id,
        strategy_id=strategy_id,
        symbol=symbol,
        exit_price=exit_price,
        quantity=quantity,
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to close position",
        )

    await db.commit()
    logger.info(
        f"User {current_user.id} closed position {symbol} in strategy {strategy_id}: "
        f"qty={result.closed_quantity}, pnl={result.realized_pnl}"
    )

    return result


@router.post(
    "/strategies/{strategy_id}/square-off",
    response_model=SquareOffStrategyResponse,
)
async def square_off_strategy(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str,
    data: SquareOffStrategyRequest | None = None,
) -> SquareOffStrategyResponse:
    """Square off all open positions for a specific strategy.

    Closes all open positions for the specified strategy.
    Optionally provide exit prices for each symbol; missing symbols will use market price.
    This does NOT affect other strategies or disable the strategy.
    """
    from app.providers.data import YahooDataProvider

    service = AlgoService(db)

    # Verify strategy exists and belongs to user
    strategy = await service.get_strategy(current_user.id, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Get all open/partial positions to fetch prices
    all_positions = await service.get_positions(current_user.id, strategy_id)
    positions = [p for p in all_positions if p.status in ("OPEN", "PARTIAL")]

    if not positions:
        return SquareOffStrategyResponse(
            strategy_id=strategy_id,
            strategy_name=strategy.name,
            positions_closed=0,
            total_realized_pnl=Decimal("0"),
            closed_positions=[],
            message="No open positions to close",
        )

    # Build exit prices dict
    exit_prices: dict[str, Decimal] = {}
    if data and data.exit_prices:
        exit_prices = data.exit_prices

    # Fetch current prices for positions without provided exit price
    symbols_needing_price = [p.symbol for p in positions if p.symbol not in exit_prices]
    if symbols_needing_price:
        data_provider = YahooDataProvider()
        for symbol in symbols_needing_price:
            try:
                quote = await data_provider.get_quote(symbol)
                if quote and quote.price:
                    exit_prices[symbol] = Decimal(str(quote.price))
                else:
                    # Fall back to entry price if we can't get current price
                    pos = next((p for p in positions if p.symbol == symbol), None)
                    if pos:
                        exit_prices[symbol] = pos.entry_price
            except Exception as e:
                logger.warning(f"Could not fetch price for {symbol}: {e}")
                # Fall back to entry price
                pos = next((p for p in positions if p.symbol == symbol), None)
                if pos:
                    exit_prices[symbol] = pos.entry_price

    result = await service.square_off_strategy(
        user_id=current_user.id,
        strategy_id=strategy_id,
        exit_prices=exit_prices,
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to square off strategy",
        )

    await db.commit()
    logger.info(
        f"User {current_user.id} squared off strategy {strategy_id}: "
        f"{result.positions_closed} positions, total P&L={result.total_realized_pnl}"
    )

    return result


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


# ============== P&L Endpoints ==============


@router.get("/positions", response_model=list[PositionResponse])
async def list_positions(
    db: DbSession,
    current_user: CurrentUser,
    strategy_id: str | None = Query(default=None, description="Filter by strategy ID"),
    status: str | None = Query(
        default=None, description="Filter by status (OPEN, CLOSED, PARTIAL)"
    ),
) -> list[PositionResponse]:
    """List all algo positions for the current user.

    Optionally filter by strategy ID and/or position status.
    Returns unrealized P&L for open positions.
    """
    from app.providers.data import YahooDataProvider

    service = AlgoService(db)

    # First get positions without prices to know which symbols we need
    positions_raw = await service.get_positions(current_user.id, strategy_id, status)

    # Filter for open/partial positions that need current prices
    open_symbols = list(
        {
            p.symbol
            for p in positions_raw
            if p.status in ("OPEN", "PARTIAL") and p.remaining_quantity > 0
        }
    )

    # Fetch current prices for open positions
    current_prices: dict[str, Decimal] = {}
    if open_symbols:
        data_provider = YahooDataProvider()
        for symbol in open_symbols:
            try:
                quote = await data_provider.get_quote(symbol)
                if quote and quote.price:
                    current_prices[symbol] = quote.price
            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")

    # Re-fetch with current prices to calculate unrealized P&L
    if current_prices:
        return await service.get_positions(current_user.id, strategy_id, status, current_prices)

    return positions_raw


@router.get("/pnl/summary", response_model=PnLSummary)
async def get_pnl_summary(
    db: DbSession,
    current_user: CurrentUser,
) -> PnLSummary:
    """Get overall P&L summary for the current user's algo trading.

    Returns aggregated metrics including:
    - Total realized and unrealized P&L
    - Win rate and trade counts
    - Best/worst trade performance
    """
    from app.providers.data import YahooDataProvider

    service = AlgoService(db)

    # First get open/partial positions to know which symbols we need prices for
    # We pass None for status and filter manually to get both OPEN and PARTIAL
    all_positions = await service.get_positions(current_user.id)
    positions = [p for p in all_positions if p.status in ("OPEN", "PARTIAL")]

    # Fetch current prices for open positions to calculate unrealized P&L
    current_prices: dict[str, Decimal] = {}
    if positions:
        symbols = list({p.symbol for p in positions})
        data_provider = YahooDataProvider()
        for symbol in symbols:
            try:
                quote = await data_provider.get_quote(symbol)
                if quote and quote.price:
                    current_prices[symbol] = quote.price
            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")

    return await service.get_pnl_summary(current_user.id, current_prices)


@router.get("/pnl/by-strategy", response_model=PnLByStrategyResponse)
async def get_pnl_by_strategy(
    db: DbSession,
    current_user: CurrentUser,
) -> PnLByStrategyResponse:
    """Get P&L breakdown by strategy.

    Returns P&L metrics for each strategy including:
    - Realized and unrealized P&L per strategy
    - Win rate and trade counts per strategy
    - Open/closed position counts
    """
    from app.providers.data import YahooDataProvider

    service = AlgoService(db)

    # First get open/partial positions to know which symbols we need prices for
    all_positions = await service.get_positions(current_user.id)
    positions = [p for p in all_positions if p.status in ("OPEN", "PARTIAL")]

    # Fetch current prices for open/partial positions to calculate unrealized P&L
    current_prices: dict[str, Decimal] = {}
    if positions:
        symbols = list({p.symbol for p in positions})
        data_provider = YahooDataProvider()
        for symbol in symbols:
            try:
                quote = await data_provider.get_quote(symbol)
                if quote and quote.price:
                    current_prices[symbol] = quote.price
            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")

    return await service.get_pnl_by_strategy(current_user.id, current_prices)


@router.get("/pnl/history", response_model=PnLHistoryResponse)
async def get_pnl_history(
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to include"),
) -> PnLHistoryResponse:
    """Get P&L history over time.

    Returns daily P&L breakdown including:
    - Realized P&L per day
    - Cumulative P&L over time
    - Trade counts per day
    - Profitable vs losing days summary
    """
    service = AlgoService(db)
    return await service.get_pnl_history(current_user.id, days)


@router.get("/pnl/unrealized", response_model=UnrealizedPnLResponse)
async def get_unrealized_pnl(
    db: DbSession,
    current_user: CurrentUser,
) -> UnrealizedPnLResponse:
    """Get unrealized P&L for all open positions.

    Fetches current market prices and calculates unrealized P&L
    for each open position. Returns:
    - Per-position unrealized P&L
    - Total unrealized P&L
    - Entry value vs current value
    """
    from app.providers.data import YahooDataProvider

    service = AlgoService(db)

    # First get the positions to know which symbols we need prices for
    # Get both OPEN and PARTIAL positions
    all_positions = await service.get_positions(current_user.id)
    positions = [p for p in all_positions if p.status in ("OPEN", "PARTIAL")]

    if not positions:
        return UnrealizedPnLResponse(
            positions=[],
            total_unrealized_pnl=Decimal("0"),
            total_entry_value=Decimal("0"),
            total_current_value=Decimal("0"),
            positions_count=0,
        )

    # Get current prices for all symbols
    symbols = list({p.symbol for p in positions})
    current_prices: dict[str, Decimal] = {}

    data_provider = YahooDataProvider()
    for symbol in symbols:
        try:
            quote = await data_provider.get_quote(symbol)
            if quote and quote.price:
                current_prices[symbol] = quote.price
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")

    return await service.get_unrealized_pnl(current_user.id, current_prices)


# ============== Profit Booking Endpoints ==============


@router.get("/positions/{position_id}/profit-booking", response_model=ProfitBookingRules | None)
async def get_algo_profit_booking_rules(
    db: DbSession,
    current_user: CurrentUser,
    position_id: str,
) -> ProfitBookingRules | None:
    """Get profit booking rules for an algo position."""
    service = AlgoService(db)
    rules = await service.get_profit_booking_rules(current_user.id, position_id)
    return rules


@router.patch("/positions/{position_id}/profit-booking", response_model=ProfitBookingRules)
async def update_algo_profit_booking_rules(
    db: DbSession,
    current_user: CurrentUser,
    position_id: str,
    rules: ProfitBookingRules,
) -> ProfitBookingRules:
    """Set or update profit booking rules for an algo position."""
    service = AlgoService(db)
    updated_rules = await service.update_profit_booking_rules(current_user.id, position_id, rules)
    if updated_rules is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found",
        )
    await db.commit()
    return updated_rules


# ============== Trailing Stop Endpoints ==============


@router.get("/positions/{position_id}/trailing-stop", response_model=TrailingStopConfig | None)
async def get_algo_trailing_stop_config(
    db: DbSession,
    current_user: CurrentUser,
    position_id: str,
) -> TrailingStopConfig | None:
    """Get trailing stop configuration for an algo position."""
    service = AlgoService(db)
    config = await service.get_trailing_stop_config(current_user.id, position_id)
    return config


@router.patch("/positions/{position_id}/trailing-stop", response_model=TrailingStopConfig)
async def update_algo_trailing_stop(
    db: DbSession,
    current_user: CurrentUser,
    position_id: str,
    config: TrailingStopUpdate,
) -> TrailingStopConfig:
    """Set or update trailing stop configuration for an algo position."""
    service = AlgoService(db)
    try:
        updated_config = await service.update_trailing_stop(current_user.id, position_id, config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    if updated_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found",
        )
    await db.commit()
    return updated_config
