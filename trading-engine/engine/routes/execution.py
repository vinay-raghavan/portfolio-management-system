"""Execution routes for strategy running."""

import logging
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from engine.algo.executor import StrategyConfig, StrategyExecutor
from engine.algo.position_tracker import PositionTracker
from engine.algo.safety import AlgoKillSwitch, CircuitBreaker, PreExecutionChecker, SafetyService
from engine.algo.scheduler import StrategyScheduler
from engine.config import settings
from engine.core.database import get_db
from engine.core.redis import get_redis
from engine.models.algo import PositionSizingMethod, StrategyStatus
from engine.providers.broker.factory import get_broker
from engine.providers.data.factory import get_data_provider
from engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["execution"])

# Dependency types
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def verify_internal_key(x_internal_key: Annotated[str | None, Header()] = None) -> str:
    """Verify the internal API key."""
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )
    return x_internal_key


InternalKeyDep = Annotated[str, Depends(verify_internal_key)]


class ExecuteStrategyRequest(BaseModel):
    """Request to execute a strategy."""

    strategy_id: str
    user_id: str
    name: str
    strategy_name: str
    strategy_params: dict = {}
    timeframe: str = "1d"
    symbols: list[str] = []
    position_sizing_method: str = "FIXED_QUANTITY"
    fixed_quantity: int = 1
    fixed_amount: float = 10000.0
    portfolio_percent: float = 5.0
    risk_per_trade_percent: float = 2.0


class ExecuteStrategyResponse(BaseModel):
    """Response from strategy execution."""

    status: str
    execution_id: str | None = None
    symbols_analyzed: int = 0
    signals_generated: int = 0
    orders_placed: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    error_message: str | None = None
    duration_ms: int = 0


@router.post("/execute", response_model=ExecuteStrategyResponse)
async def execute_strategy_full(
    request: ExecuteStrategyRequest,
    _key: InternalKeyDep,
) -> ExecuteStrategyResponse:
    """Execute a trading strategy with full configuration.

    This endpoint is called by the backend API or Celery worker
    to execute a strategy and place orders.
    """
    try:
        # Build strategy config
        config = StrategyConfig(
            id=request.strategy_id,
            user_id=request.user_id,
            name=request.name,
            strategy_name=request.strategy_name,
            strategy_params=request.strategy_params,
            timeframe=request.timeframe,
            symbols=request.symbols,
            position_sizing_method=PositionSizingMethod(request.position_sizing_method),
            fixed_quantity=request.fixed_quantity,
            fixed_amount=Decimal(str(request.fixed_amount)),
            portfolio_percent=Decimal(str(request.portfolio_percent)),
            risk_per_trade_percent=Decimal(str(request.risk_per_trade_percent)),
        )

        # Get broker and data provider
        broker = get_broker()
        data_provider = get_data_provider()
        safety_service = SafetyService()

        # Execute strategy
        executor = StrategyExecutor(
            broker=broker,
            data_provider=data_provider,
            safety_service=safety_service,
        )
        result = await executor.execute(config)

        return ExecuteStrategyResponse(
            status=result.status.value,
            execution_id=result.execution_id,
            symbols_analyzed=result.symbols_analyzed,
            signals_generated=result.signals_generated,
            orders_placed=result.orders_placed,
            orders_filled=result.orders_filled,
            orders_rejected=result.orders_rejected,
            error_message=result.error_message,
            duration_ms=result.duration_ms,
        )

    except Exception as e:
        logger.exception(f"Error executing strategy: {e}")
        return ExecuteStrategyResponse(
            status="ERROR",
            error_message=str(e),
        )


@router.post("/run-scheduled")
async def run_scheduled_strategies(
    db: DbSession,
    redis: RedisDep,
    _key: InternalKeyDep,
):
    """Run all scheduled strategies that are due.

    Called by Celery worker every 30 seconds.
    This endpoint queries the database for due strategies and executes them.
    """
    pre_checker = PreExecutionChecker(redis)
    scheduler = StrategyScheduler(db)

    # Get strategies due to run
    due_strategies = await scheduler.get_due_strategies()
    logger.info(f"Found {len(due_strategies)} strategies due for execution")

    results = []
    executed_count = 0

    for strategy in due_strategies:
        try:
            # Run all pre-execution safety checks
            check_result = await pre_checker.check_all(
                user_id=strategy.user_id,
                strategy_id=strategy.id,
                cooldown_seconds=strategy.cooldown_seconds or 0,
                max_daily_trades=strategy.max_daily_trades or 0,
            )

            if not check_result.can_execute:
                logger.warning(
                    f"Strategy {strategy.id} blocked by {check_result.check_type}: "
                    f"{check_result.reason}"
                )
                results.append(
                    {
                        "strategy_id": strategy.id,
                        "status": "SKIPPED",
                        "reason": check_result.check_type,
                        "message": check_result.reason,
                    }
                )
                continue

            # Check if market is open for non-CRON strategies
            if not scheduler.is_market_hours() and strategy.schedule_type.value not in [
                "CRON",
                "MARKET_OPEN",
                "MARKET_CLOSE",
            ]:
                logger.debug(f"Market closed, skipping strategy {strategy.id}")
                results.append(
                    {
                        "strategy_id": strategy.id,
                        "status": "SKIPPED",
                        "reason": "market_closed",
                    }
                )
                continue

            # Get symbols from universe or custom list
            symbols = []
            if strategy.custom_symbols:
                symbols = strategy.custom_symbols
            elif strategy.universe:
                symbols = strategy.universe.symbols or []

            # Build strategy config
            config = StrategyConfig(
                id=strategy.id,
                user_id=strategy.user_id,
                name=strategy.name,
                strategy_name=strategy.strategy_name,
                strategy_params=strategy.strategy_params or {},
                timeframe=strategy.timeframe,
                symbols=symbols,
                position_sizing_method=strategy.position_sizing_method,
                fixed_quantity=strategy.fixed_quantity,
                fixed_amount=strategy.fixed_amount or Decimal("10000"),
                portfolio_percent=strategy.portfolio_percent,
                risk_per_trade_percent=strategy.risk_per_trade_percent,
            )

            # Execute strategy
            broker = get_broker()
            # Ensure broker is connected (initializes data provider for paper broker)
            if not await broker.is_connected():
                await broker.connect()
            data_provider = get_data_provider()
            safety_service = SafetyService()

            executor = StrategyExecutor(
                broker=broker,
                data_provider=data_provider,
                safety_service=safety_service,
            )
            result = await executor.execute(config)

            # Update next run time
            await scheduler.update_next_run(strategy)

            # Update strategy statistics with P&L from position tracker
            await scheduler.update_strategy_stats(
                strategy=strategy,
                orders_filled=result.orders_filled,
                total_pnl_delta=float(result.pnl_stats.total_pnl),
                winning_trades_delta=result.pnl_stats.winning_trades,
                losing_trades_delta=result.pnl_stats.losing_trades,
            )

            # Record trade for cooldown and daily trade tracking
            if result.orders_placed > 0:
                await pre_checker.record_trade(
                    strategy_id=strategy.id,
                    cooldown_seconds=strategy.cooldown_seconds or 0,
                )

            # Check profit cutoff with unrealized P&L
            if strategy.max_daily_profit or strategy.overall_profit_target:
                # Get current prices for open positions
                position_tracker = PositionTracker(db)
                open_positions = await position_tracker.get_all_open_positions(
                    strategy.id, strategy.user_id
                )

                if open_positions:
                    # Fetch current prices
                    position_symbols = list({p.symbol for p in open_positions})
                    current_prices: dict[str, Decimal] = {}
                    for sym in position_symbols:
                        try:
                            quote = await data_provider.get_quote(sym)
                            if quote and quote.price:
                                current_prices[sym] = quote.price
                        except Exception as price_err:
                            logger.warning(f"Failed to get price for {sym}: {price_err}")

                    # Calculate unrealized P&L
                    unrealized_pnl = await position_tracker.calculate_unrealized_pnl(
                        strategy.id, strategy.user_id, current_prices
                    )
                else:
                    unrealized_pnl = Decimal("0")

                # Check profit cutoff with circuit breaker
                circuit_breaker = CircuitBreaker(redis)
                cb_state = await circuit_breaker.check_and_update(
                    strategy_id=strategy.id,
                    max_daily_loss=strategy.max_daily_loss,
                    max_consecutive_losses=strategy.max_consecutive_losses,
                    unrealized_pnl=unrealized_pnl,
                    max_daily_profit=strategy.max_daily_profit,
                    overall_profit_target=strategy.overall_profit_target,
                )

                if cb_state.profit_cutoff_triggered:
                    logger.info(
                        f"🎯 Profit cutoff triggered for strategy {strategy.id}: "
                        f"{cb_state.trigger_reason}"
                    )
                    # Pause the strategy based on profit_cutoff_action
                    await scheduler.disable_strategy(strategy, StrategyStatus.PAUSED)
                    # TODO: Handle CLOSE_POSITIONS_AND_PAUSE action

            results.append(
                {
                    "strategy_id": strategy.id,
                    "status": result.status.value,
                    "execution_id": result.execution_id,
                    "signals_generated": result.signals_generated,
                    "orders_placed": result.orders_placed,
                }
            )
            executed_count += 1

        except Exception as e:
            logger.exception(f"Error executing strategy {strategy.id}: {e}")
            results.append(
                {
                    "strategy_id": strategy.id,
                    "status": "ERROR",
                    "error": str(e),
                }
            )

    await db.commit()

    return {
        "executed": executed_count,
        "total_due": len(due_strategies),
        "results": results,
    }


@router.post("/execute/{strategy_id}")
async def execute_strategy_by_id(
    strategy_id: str,
    db: DbSession,
    redis: RedisDep,
    _key: InternalKeyDep,
    symbols_override: list[str] | None = None,
):
    """Execute a specific strategy by ID.

    Called by the backend API for manual triggers.

    Args:
        strategy_id: The ID of the strategy to execute
        symbols_override: Optional list of symbols to override the strategy's universe
    """
    scheduler = StrategyScheduler(db)
    pre_checker = PreExecutionChecker(redis)

    # Get strategy from database
    strategy = await scheduler.get_strategy_by_id(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found",
        )

    # Run all pre-execution safety checks
    check_result = await pre_checker.check_all(
        user_id=strategy.user_id,
        strategy_id=strategy.id,
        cooldown_seconds=strategy.cooldown_seconds or 0,
        max_daily_trades=strategy.max_daily_trades or 0,
    )

    if not check_result.can_execute:
        return {
            "status": "blocked",
            "reason": check_result.check_type,
            "message": check_result.reason,
        }

    try:
        # Get symbols
        symbols = symbols_override if symbols_override else []
        if not symbols:
            if strategy.custom_symbols:
                symbols = strategy.custom_symbols
            elif strategy.universe:
                symbols = strategy.universe.symbols or []

        # Build strategy config
        config = StrategyConfig(
            id=strategy.id,
            user_id=strategy.user_id,
            name=strategy.name,
            strategy_name=strategy.strategy_name,
            strategy_params=strategy.strategy_params or {},
            timeframe=strategy.timeframe,
            symbols=symbols,
            position_sizing_method=strategy.position_sizing_method,
            fixed_quantity=strategy.fixed_quantity,
            fixed_amount=strategy.fixed_amount or Decimal("10000"),
            portfolio_percent=strategy.portfolio_percent,
            risk_per_trade_percent=strategy.risk_per_trade_percent,
        )

        # Execute strategy
        broker = get_broker()
        # Ensure broker is connected (initializes data provider for paper broker)
        is_connected = await broker.is_connected()
        print(f"DEBUG: Broker connected: {is_connected}")
        if not is_connected:
            print("DEBUG: Connecting broker...")
            await broker.connect()
            print(f"DEBUG: Broker connected after connect(): {await broker.is_connected()}")
        data_provider = get_data_provider()
        safety_service = SafetyService()

        executor = StrategyExecutor(
            broker=broker,
            data_provider=data_provider,
            safety_service=safety_service,
        )
        result = await executor.execute(config)

        # Update next run time
        await scheduler.update_next_run(strategy)

        # Update strategy statistics with P&L from position tracker
        await scheduler.update_strategy_stats(
            strategy=strategy,
            orders_filled=result.orders_filled,
            total_pnl_delta=float(result.pnl_stats.total_pnl),
            winning_trades_delta=result.pnl_stats.winning_trades,
            losing_trades_delta=result.pnl_stats.losing_trades,
        )

        # Record trade for cooldown and daily trade tracking
        if result.orders_placed > 0:
            await pre_checker.record_trade(
                strategy_id=strategy.id,
                cooldown_seconds=strategy.cooldown_seconds or 0,
            )

        await db.commit()

        return {
            "status": "success",
            "execution_id": result.execution_id,
            "execution_status": result.status.value,
            "signals_generated": result.signals_generated,
            "orders_placed": result.orders_placed,
        }

    except Exception as e:
        logger.exception(f"Error executing strategy {strategy_id}: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/strategies")
async def list_available_strategies(_key: InternalKeyDep) -> dict:
    """List all available trading strategies."""
    strategies = []
    for name in StrategyRegistry.get_names():
        strategy_class = StrategyRegistry._strategies.get(name)
        if strategy_class:
            strategies.append(
                {
                    "name": name,
                    "description": (strategy_class.__doc__ or "").split("\n")[0].strip(),
                }
            )

    return {"strategies": strategies, "count": len(strategies)}


@router.get("/kill-switch/{user_id}")
async def get_kill_switch_status(user_id: str, redis: RedisDep, _key: InternalKeyDep):
    """Get kill switch status for a user."""
    kill_switch = AlgoKillSwitch(redis)
    is_active = await kill_switch.is_active(user_id)
    return {"user_id": user_id, "is_active": is_active}


@router.post("/kill-switch/{user_id}/activate")
async def activate_kill_switch(
    user_id: str,
    redis: RedisDep,
    _key: InternalKeyDep,
    reason: str | None = None,
):
    """Activate kill switch for a user."""
    kill_switch = AlgoKillSwitch(redis)
    await kill_switch.activate(user_id, reason or "Manual activation")
    logger.warning(f"Kill switch activated for user {user_id}: {reason}")
    return {"user_id": user_id, "activated": True, "reason": reason}


@router.post("/kill-switch/{user_id}/deactivate")
async def deactivate_kill_switch(user_id: str, redis: RedisDep, _key: InternalKeyDep):
    """Deactivate kill switch for a user."""
    kill_switch = AlgoKillSwitch(redis)
    await kill_switch.deactivate(user_id)
    logger.info(f"Kill switch deactivated for user {user_id}")
    return {"user_id": user_id, "deactivated": True}


@router.get("/circuit-breaker/{strategy_id}")
async def get_circuit_breaker_status(strategy_id: str, redis: RedisDep, _key: InternalKeyDep):
    """Get circuit breaker status for a strategy."""
    from engine.algo.safety import CircuitBreaker

    circuit_breaker = CircuitBreaker(redis)
    is_triggered = await circuit_breaker.is_triggered(strategy_id)
    return {"strategy_id": strategy_id, "is_triggered": is_triggered}
