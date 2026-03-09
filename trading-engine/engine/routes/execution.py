"""Execution routes for strategy running."""

import logging
from datetime import time as dt_time
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis
from shared.utils.time_window import TimeWindowValidator
from sqlalchemy.ext.asyncio import AsyncSession

from engine.algo.executor import StrategyConfig, StrategyExecutor
from engine.algo.position_tracker import PnLStats, PositionResult, PositionTracker
from engine.algo.safety import AlgoKillSwitch, CircuitBreaker, PreExecutionChecker, SafetyService
from engine.algo.scheduler import StrategyScheduler
from engine.config import settings
from engine.core.database import get_db
from engine.core.locks import (
    SCHEDULED_RUN_LOCK_KEY,
    STRATEGY_LOCK_KEY,
    DistributedLock,
)
from engine.core.redis import get_redis
from engine.models.algo import (
    PositionSizingMethod,
    StrategyStatus,
    UserStrategy,
)
from engine.providers.broker import PaperBroker
from engine.providers.data import DataProvider, get_data_provider
from engine.providers.schemas import ProductType
from engine.providers.user_broker import get_user_broker
from engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


def _is_within_strategy_time_window(strategy: UserStrategy) -> tuple[bool, str]:
    """Check if current time is within the strategy's trading time window.

    Args:
        strategy: The strategy to check

    Returns:
        Tuple of (is_within_window, reason_if_not)
    """
    # If no time window is configured, always allow
    if not strategy.time_window_start and not strategy.time_window_end:
        return True, ""

    validator = TimeWindowValidator()
    return validator.is_within_window(
        start_time=strategy.time_window_start,
        end_time=strategy.time_window_end,
        timezone=strategy.trading_timezone or "Asia/Kolkata",
        active_days=strategy.active_trading_days or [0, 1, 2, 3, 4],
    )


async def _check_exit_conditions_for_strategy(
    db: AsyncSession,
    strategy: UserStrategy,
    data_provider: DataProvider,
    respect_time_window: bool = True,
) -> tuple[list[PositionResult], PnLStats]:
    """Check exit conditions (SL/TP/profit booking) for a strategy's open positions.

    This should be called even when strategy execution is blocked by max_trades,
    cooldown, etc. to ensure profit booking rules and exit conditions are still
    evaluated.

    However, if the strategy has a time window configured and respect_time_window
    is True, exit conditions will NOT be checked outside the trading window.
    This prevents positions from being closed at times the user didn't expect
    (e.g., stop loss triggered at 9:20 when strategy is set to trade 9:45-15:15).

    Args:
        db: Database session
        strategy: The strategy to check
        data_provider: Data provider to fetch current prices
        respect_time_window: If True, skip exit checks outside strategy's time window

    Returns:
        Tuple of (closed positions, aggregated PnL stats)
    """
    # Check if we should respect the strategy's time window
    if respect_time_window:
        is_within_window, reason = _is_within_strategy_time_window(strategy)
        if not is_within_window:
            logger.debug(
                f"Skipping exit check for strategy {strategy.id[:8]}...: "
                f"Outside time window - {reason}"
            )
            return [], PnLStats()

    position_tracker = PositionTracker(db)
    open_positions = await position_tracker.get_all_open_positions(
        strategy.id, strategy.user_id, include_partial=True
    )

    if not open_positions:
        return [], PnLStats()

    # Fetch current prices for open positions
    position_symbols = list({p.symbol for p in open_positions})
    current_prices: dict[str, Decimal] = {}
    for sym in position_symbols:
        try:
            quote = await data_provider.get_quote(sym)
            if quote and quote.price:
                current_prices[sym] = Decimal(str(quote.price))
        except Exception as e:
            logger.warning(f"Failed to get price for {sym}: {e}")

    if not current_prices:
        return [], PnLStats()

    # Check exit conditions
    closed_positions, pnl_stats = await position_tracker.check_stop_loss_take_profit(
        strategy_id=strategy.id,
        user_id=strategy.user_id,
        current_prices=current_prices,
    )

    if closed_positions:
        logger.info(
            f"Exit conditions triggered for strategy {strategy.id}: "
            f"{len(closed_positions)} positions closed, PnL: {pnl_stats.total_pnl}"
        )

        # Update user funds for closed positions (credit proceeds, release margin, update P&L)
        await _update_funds_for_closed_positions(
            db=db,
            user_id=strategy.user_id,
            closed_positions=closed_positions,
            product_type=strategy.product_type or ProductType.DELIVERY,
        )

    return closed_positions, pnl_stats


async def _update_funds_for_closed_positions(
    db: AsyncSession,
    user_id: str,
    closed_positions: list[PositionResult],
    product_type: ProductType = ProductType.DELIVERY,
) -> None:
    """Update user funds when positions are closed via SL/TP/trailing stop.

    This handles:
    1. Crediting sale proceeds (for LONG) or debiting buy cost (for SHORT)
    2. Releasing margin (for INTRADAY/MARGIN products)
    3. Updating cumulative realized P&L

    Args:
        db: Database session
        user_id: User ID
        closed_positions: List of PositionResult objects from closed positions
        product_type: Product type for margin handling
    """
    from shared.providers.funds import DatabaseFundsProvider

    from engine.models import AlgoPosition, UserFunds

    try:
        funds_provider = DatabaseFundsProvider(
            db=db,
            user_funds_model=UserFunds,
            initial_balance=Decimal("0"),  # Not used for updates
            algo_position_model=AlgoPosition,
        )

        total_realized_pnl = Decimal("0")

        for pos in closed_positions:
            # For LONG positions, closing means SELL (credit proceeds)
            # For SHORT positions, closing means BUY (debit cost)
            side = "SELL" if pos.side == "LONG" else "BUY"
            exit_price = pos.exit_price if pos.exit_price else Decimal("0")

            # entry_price is required for INTRADAY/MARGIN to calculate P&L correctly
            await funds_provider.update_funds_for_trade(
                user_id=user_id,
                side=side,
                quantity=Decimal(str(pos.quantity)),
                price=exit_price,
                fees=Decimal("0"),  # Fees handled separately
                product_type=product_type,
                existing_position_qty=Decimal(str(pos.quantity)),  # Closing position
                entry_price=pos.entry_price,  # Required for P&L calculation
            )
            logger.debug(
                f"Updated funds for closed position {pos.symbol}: "
                f"side={side}, qty={pos.quantity}, price={exit_price}, pnl={pos.realized_pnl}"
            )

            # Accumulate realized P&L
            if pos.realized_pnl:
                total_realized_pnl += Decimal(str(pos.realized_pnl))

        # Update cumulative realized P&L in user funds
        if total_realized_pnl != Decimal("0"):
            await funds_provider.update_realized_pnl(user_id, total_realized_pnl)
            logger.info(
                f"Updated realized P&L for user {user_id[:8]}...: "
                f"{'+' if total_realized_pnl > 0 else ''}₹{total_realized_pnl:.2f}"
            )

    except Exception as e:
        logger.warning(f"Failed to update funds for closed positions: {e}")


def _configure_broker_price_fetcher(broker, data_provider: DataProvider) -> None:
    """Configure the broker with a price fetcher using the data provider.

    This ensures the paper broker can get real market prices for order execution.
    """
    if isinstance(broker, PaperBroker) and broker._price_fetcher is None:
        import asyncio

        def sync_price_fetcher(symbol: str) -> float | None:
            """Synchronous price fetcher that wraps the async data provider."""
            try:
                # Try to get the running loop
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    # We're in an async context - use a new thread to run the coroutine
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, data_provider.get_quote(symbol))
                        quote = future.result(timeout=10)
                else:
                    # No running loop - safe to use asyncio.run
                    quote = asyncio.run(data_provider.get_quote(symbol))

                if quote and quote.price:
                    return float(quote.price)
                return None
            except Exception as e:
                logger.warning(f"Failed to fetch price for {symbol}: {e}")
                return None

        broker.set_price_fetcher(sync_price_fetcher)
        logger.info("Configured paper broker with data provider price fetcher")


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
    # Exit-only symbols: only SELL signals allowed (for closing positions)
    exit_only_symbols: list[str] = []
    position_sizing_method: str = "FIXED_QUANTITY"
    fixed_quantity: int = 1
    fixed_amount: float = 10000.0
    portfolio_percent: float = 5.0
    risk_per_trade_percent: float = 2.0
    is_paper_trading: bool = True
    product_type: str = "DELIVERY"
    # Trading time window (optional)
    trading_start_time: str | None = None  # Format: HH:MM:SS
    trading_end_time: str | None = None  # Format: HH:MM:SS
    trading_timezone: str = "Asia/Kolkata"
    active_trading_days: list[int] = [0, 1, 2, 3, 4]  # Monday=0, Sunday=6


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
    db: DbSession,
    _key: InternalKeyDep,
) -> ExecuteStrategyResponse:
    """Execute a trading strategy with full configuration.

    This endpoint is called by the backend API or Celery worker
    to execute a strategy and place orders.
    """
    try:
        # Parse time window fields from strings if provided
        start_time = None
        end_time = None
        if request.trading_start_time:
            parts = request.trading_start_time.split(":")
            start_time = dt_time(
                int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0
            )
        if request.trading_end_time:
            parts = request.trading_end_time.split(":")
            end_time = dt_time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)

        # Build strategy config
        config = StrategyConfig(
            id=request.strategy_id,
            user_id=request.user_id,
            name=request.name,
            strategy_name=request.strategy_name,
            strategy_params=request.strategy_params,
            timeframe=request.timeframe,
            symbols=request.symbols,
            exit_only_symbols=request.exit_only_symbols,
            position_sizing_method=PositionSizingMethod(request.position_sizing_method),
            fixed_quantity=request.fixed_quantity,
            fixed_amount=Decimal(str(request.fixed_amount)),
            portfolio_percent=Decimal(str(request.portfolio_percent)),
            risk_per_trade_percent=Decimal(str(request.risk_per_trade_percent)),
            product_type=ProductType.normalize(request.product_type),
            # Trading time window configuration
            trading_start_time=start_time,
            trading_end_time=end_time,
            trading_timezone=request.trading_timezone,
            active_trading_days=request.active_trading_days,
        )

        # Get broker based on paper trading mode
        # Live trading uses user's connected broker, paper trading uses global paper broker
        broker = await get_user_broker(
            db=db,
            user_id=request.user_id,
            is_paper_trading=request.is_paper_trading,
        )
        if not await broker.is_connected():
            await broker.connect()
        data_provider = get_data_provider()
        _configure_broker_price_fetcher(broker, data_provider)
        # Pass broker to SafetyService for funds validation
        safety_service = SafetyService(broker=broker)

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

    Uses a distributed lock to prevent multiple workers from running
    scheduled strategies simultaneously.
    """
    # Try to acquire global scheduled run lock (non-blocking)
    # This prevents multiple Celery workers from running scheduled strategies
    # at the same time when tasks queue up during long-running executions
    global_lock = DistributedLock(
        redis,
        SCHEDULED_RUN_LOCK_KEY,
        timeout=300,  # 5 minute lock timeout for long strategy runs
    )

    if not await global_lock.acquire(blocking=False):
        logger.info("Another worker is already running scheduled strategies, skipping")
        return {
            "status": "skipped",
            "reason": "Another worker is already processing scheduled strategies",
            "executed": 0,
            "total_due": 0,
            "results": [],
        }

    try:
        pre_checker = PreExecutionChecker(redis)
        scheduler = StrategyScheduler(db)

        # Get strategies due to run
        due_strategies = await scheduler.get_due_strategies()
        logger.info(f"Found {len(due_strategies)} strategies due for execution")

        results = []
        executed_count = 0

        for strategy in due_strategies:
            try:
                # Try to acquire per-strategy lock (non-blocking)
                # This prevents race conditions when checking cooldown
                strategy_lock = DistributedLock(
                    redis,
                    STRATEGY_LOCK_KEY.format(strategy_id=strategy.id),
                    timeout=300,  # 5 minute lock timeout
                )

                if not await strategy_lock.acquire(blocking=False):
                    logger.info(f"Strategy {strategy.id} is already being executed, skipping")
                    results.append(
                        {
                            "strategy_id": strategy.id,
                            "status": "SKIPPED",
                            "reason": "already_executing",
                            "message": "Strategy is already being executed by another process",
                        }
                    )
                    continue

                try:
                    # Always check exit conditions (SL/TP/profit booking) first,
                    # even if strategy execution is blocked. This ensures profit
                    # booking rules are evaluated regardless of max_trades limits.
                    data_provider = get_data_provider()
                    closed_positions, exit_pnl = await _check_exit_conditions_for_strategy(
                        db=db,
                        strategy=strategy,
                        data_provider=data_provider,
                    )

                    # Update strategy stats if any positions were closed
                    if closed_positions:
                        await scheduler.update_strategy_stats(
                            strategy=strategy,
                            orders_filled=len(closed_positions),
                            total_pnl_delta=float(exit_pnl.total_pnl),
                            winning_trades_delta=exit_pnl.winning_trades,
                            losing_trades_delta=exit_pnl.losing_trades,
                        )

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
                                "exit_conditions_checked": True,
                                "positions_closed": len(closed_positions),
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

                    # Get exit-only symbols (symbols waiting to close positions)
                    exit_only_symbols = strategy.exit_only_symbols or []

                    # Build strategy config
                    config = StrategyConfig(
                        id=strategy.id,
                        user_id=strategy.user_id,
                        name=strategy.name,
                        strategy_name=strategy.strategy_name,
                        strategy_params=strategy.strategy_params or {},
                        timeframe=strategy.timeframe,
                        symbols=symbols,
                        exit_only_symbols=exit_only_symbols,
                        position_sizing_method=strategy.position_sizing_method,
                        fixed_quantity=strategy.fixed_quantity,
                        fixed_amount=strategy.fixed_amount or Decimal("10000"),
                        portfolio_percent=strategy.portfolio_percent,
                        risk_per_trade_percent=strategy.risk_per_trade_percent,
                        product_type=ProductType.normalize(strategy.product_type.value),
                        # Trading time window configuration
                        trading_start_time=strategy.trading_start_time,
                        trading_end_time=strategy.trading_end_time,
                        trading_timezone=strategy.trading_timezone or "Asia/Kolkata",
                        active_trading_days=strategy.active_trading_days or [0, 1, 2, 3, 4],
                    )

                    # Get broker based on paper trading mode
                    # Live trading uses user's connected broker, paper uses global paper broker
                    broker = await get_user_broker(
                        db=db,
                        user_id=strategy.user_id,
                        is_paper_trading=strategy.is_paper_trading,
                    )
                    if not await broker.is_connected():
                        await broker.connect()
                    data_provider = get_data_provider()
                    _configure_broker_price_fetcher(broker, data_provider)
                    safety_service = SafetyService(broker=broker)

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

                    # Always update circuit breaker with execution results
                    # Get current prices for open positions to calculate unrealized P&L
                    position_tracker = PositionTracker(db)
                    open_positions = await position_tracker.get_all_open_positions(
                        strategy.id, strategy.user_id
                    )

                    unrealized_pnl = Decimal("0")
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

                    # Extract trade P&L data from execution result
                    # For circuit breaker, we pass the total realized P&L from this execution
                    # and whether the net result was a loss (for consecutive loss tracking)
                    trade_pnl = (
                        result.pnl_stats.total_pnl if result.pnl_stats.trades_closed > 0 else None
                    )
                    # Net loss if more losing trades than winning OR if total P&L is negative
                    is_loss = (
                        result.pnl_stats.total_pnl < 0
                        if result.pnl_stats.trades_closed > 0
                        else None
                    )

                    # Update circuit breaker with both realized and unrealized P&L
                    circuit_breaker = CircuitBreaker(redis)
                    cb_state = await circuit_breaker.check_and_update(
                        strategy_id=strategy.id,
                        max_daily_loss=strategy.max_daily_loss,
                        max_consecutive_losses=strategy.max_consecutive_losses,
                        trade_pnl=trade_pnl,
                        is_loss=is_loss,
                        unrealized_pnl=unrealized_pnl,
                        max_daily_profit=strategy.max_daily_profit,
                        overall_profit_target=strategy.overall_profit_target,
                        max_unrealized_loss=strategy.max_unrealized_loss,
                    )

                    # Handle circuit breaker triggers
                    if cb_state.is_triggered:
                        # Immediately persist to DB on trigger
                        from engine.algo.safety import CircuitBreakerPersistence

                        cb_persistence = CircuitBreakerPersistence(redis)
                        await cb_persistence.persist_trigger_event(
                            db=db,
                            strategy_id=strategy.id,
                            user_id=strategy.user_id,
                            event_type="TRIGGERED",
                            state=cb_state,
                        )
                        # Also sync current state to DB
                        await cb_persistence.sync_to_db(db, strategy.id, strategy.user_id)

                        if cb_state.profit_cutoff_triggered:
                            logger.info(
                                f"🎯 Profit cutoff triggered for strategy {strategy.id}: "
                                f"{cb_state.trigger_reason}"
                            )
                            # Pause the strategy based on profit_cutoff_action
                            await scheduler.disable_strategy(strategy, StrategyStatus.PAUSED)
                        else:
                            logger.warning(
                                f"⚠️ Circuit breaker triggered for strategy {strategy.id}: "
                                f"{cb_state.trigger_reason}"
                            )
                            # Disable the strategy for safety
                            await scheduler.disable_strategy(strategy, StrategyStatus.DISABLED)

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

                finally:
                    # Always release the per-strategy lock
                    await strategy_lock.release()

                # Commit after each strategy to release locks quickly
                # This prevents blocking other transactions (like UI strategy edits)
                await db.commit()

            except Exception as e:
                logger.exception(f"Error executing strategy {strategy.id}: {e}")
                # Rollback any partial changes from the failed strategy
                await db.rollback()
                results.append(
                    {
                        "strategy_id": strategy.id,
                        "status": "ERROR",
                        "error": str(e),
                    }
                )

        return {
            "status": "success",
            "executed": executed_count,
            "total_due": len(due_strategies),
            "results": results,
        }

    finally:
        # Always release the global lock
        await global_lock.release()


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

        # Get exit-only symbols (symbols waiting to close positions)
        exit_only_symbols = strategy.exit_only_symbols or []

        # Build strategy config
        config = StrategyConfig(
            id=strategy.id,
            user_id=strategy.user_id,
            name=strategy.name,
            strategy_name=strategy.strategy_name,
            strategy_params=strategy.strategy_params or {},
            timeframe=strategy.timeframe,
            symbols=symbols,
            exit_only_symbols=exit_only_symbols,
            position_sizing_method=strategy.position_sizing_method,
            fixed_quantity=strategy.fixed_quantity,
            fixed_amount=strategy.fixed_amount or Decimal("10000"),
            portfolio_percent=strategy.portfolio_percent,
            risk_per_trade_percent=strategy.risk_per_trade_percent,
            product_type=ProductType.normalize(strategy.product_type.value),
            # Trading time window configuration
            trading_start_time=strategy.trading_start_time,
            trading_end_time=strategy.trading_end_time,
            trading_timezone=strategy.trading_timezone or "Asia/Kolkata",
            active_trading_days=strategy.active_trading_days or [0, 1, 2, 3, 4],
        )

        # Get broker based on paper trading mode
        # Live trading uses user's connected broker, paper uses global paper broker
        broker = await get_user_broker(
            db=db,
            user_id=strategy.user_id,
            is_paper_trading=strategy.is_paper_trading,
        )
        if not await broker.is_connected():
            await broker.connect()
        data_provider = get_data_provider()
        _configure_broker_price_fetcher(broker, data_provider)
        safety_service = SafetyService(broker=broker)

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


@router.post("/circuit-breaker/sync-all")
async def sync_all_circuit_breakers(
    db: DbSession,
    redis: RedisDep,
    _key: InternalKeyDep,
):
    """Sync all circuit breaker states from Redis to DB.

    Called periodically by Celery beat to persist state.
    """
    from sqlalchemy import select

    from engine.algo.safety import CircuitBreakerPersistence
    from engine.models.algo import StrategyStatus, UserStrategy

    cb_persistence = CircuitBreakerPersistence(redis)

    # Get all active strategies
    result = await db.execute(
        select(UserStrategy).where(
            UserStrategy.status.in_([StrategyStatus.ACTIVE, StrategyStatus.PAUSED])
        )
    )
    strategies = result.scalars().all()

    synced = 0
    errors = 0

    for strategy in strategies:
        try:
            success = await cb_persistence.sync_to_db(db, strategy.id, strategy.user_id)
            if success:
                synced += 1
        except Exception as e:
            logger.error(f"Error syncing circuit breaker for {strategy.id}: {e}")
            errors += 1

    logger.info(f"Circuit breaker sync complete: {synced} synced, {errors} errors")
    return {"synced": synced, "errors": errors, "total": len(strategies)}


@router.post("/circuit-breaker/load-all")
async def load_all_circuit_breakers(
    db: DbSession,
    redis: RedisDep,
    _key: InternalKeyDep,
):
    """Load all circuit breaker states from DB to Redis.

    Called on startup to restore state after Redis restart.
    """
    from engine.algo.safety import CircuitBreakerPersistence

    cb_persistence = CircuitBreakerPersistence(redis)
    loaded = await cb_persistence.load_all_active_strategies(db)

    return {"loaded": len(loaded), "strategy_ids": loaded}


@router.post("/check-stop-monitors")
async def check_stop_monitors(
    db: DbSession,
    redis: RedisDep,
    _key: InternalKeyDep,
):
    """Check trailing stops and circuit breakers for all active strategies.

    Called by Celery worker every 5 minutes during market hours.
    This ensures trailing stops are checked frequently even for strategies
    with longer execution intervals.

    Unlike run_scheduled_strategies, this checks ALL active strategies
    regardless of their next_run_at time.
    """
    from engine.algo.safety import CircuitBreakerPersistence

    scheduler = StrategyScheduler(db)

    # Get ALL active strategies (not just due ones)
    active_strategies = await scheduler.get_active_strategies()

    if not active_strategies:
        return {
            "status": "no_active_strategies",
            "checked": 0,
            "positions_closed": 0,
            "circuit_breakers_triggered": 0,
        }

    data_provider = get_data_provider()
    position_tracker = PositionTracker(db)
    circuit_breaker = CircuitBreaker(redis)
    cb_persistence = CircuitBreakerPersistence(redis)

    checked = 0
    positions_closed = 0
    circuit_breakers_triggered = 0
    errors = []

    for strategy in active_strategies:
        try:
            # Check exit conditions (SL/TP/trailing stop/profit booking)
            closed_positions, pnl_stats = await _check_exit_conditions_for_strategy(
                db=db,
                strategy=strategy,
                data_provider=data_provider,
            )

            if closed_positions:
                positions_closed += len(closed_positions)
                # Update strategy stats
                await scheduler.update_strategy_stats(
                    strategy=strategy,
                    orders_filled=len(closed_positions),
                    total_pnl_delta=float(pnl_stats.total_pnl),
                    winning_trades_delta=pnl_stats.winning_trades,
                    losing_trades_delta=pnl_stats.losing_trades,
                )
                logger.info(
                    f"Stop monitor: Closed {len(closed_positions)} positions for "
                    f"strategy {strategy.id[:8]}..., P&L: {pnl_stats.total_pnl:.2f}"
                )

            # Calculate current unrealized P&L for circuit breaker check
            open_positions = await position_tracker.get_all_open_positions(
                strategy.id, strategy.user_id, include_partial=True
            )

            unrealized_pnl = Decimal("0")
            if open_positions:
                position_symbols = list({p.symbol for p in open_positions})
                current_prices: dict[str, Decimal] = {}
                for sym in position_symbols:
                    try:
                        quote = await data_provider.get_quote(sym)
                        if quote and quote.price:
                            current_prices[sym] = Decimal(str(quote.price))
                    except Exception as price_err:
                        logger.warning(f"Failed to get price for {sym}: {price_err}")

                if current_prices:
                    unrealized_pnl = await position_tracker.calculate_unrealized_pnl(
                        strategy.id, strategy.user_id, current_prices
                    )

            # Check circuit breaker (unrealized loss check)
            cb_state = await circuit_breaker.check_and_update(
                strategy_id=strategy.id,
                max_daily_loss=strategy.max_daily_loss,
                max_consecutive_losses=strategy.max_consecutive_losses,
                unrealized_pnl=unrealized_pnl,
                max_daily_profit=strategy.max_daily_profit,
                overall_profit_target=strategy.overall_profit_target,
                max_unrealized_loss=strategy.max_unrealized_loss,
            )

            if cb_state.is_triggered:
                circuit_breakers_triggered += 1
                # Persist trigger event
                await cb_persistence.persist_trigger_event(
                    db=db,
                    strategy_id=strategy.id,
                    user_id=strategy.user_id,
                    event_type="TRIGGERED",
                    state=cb_state,
                )
                await cb_persistence.sync_to_db(db, strategy.id, strategy.user_id)

                if cb_state.profit_cutoff_triggered:
                    logger.info(
                        f"🎯 Stop monitor: Profit cutoff triggered for {strategy.id[:8]}..."
                    )
                    await scheduler.disable_strategy(strategy, StrategyStatus.PAUSED)
                else:
                    logger.warning(
                        f"⚠️ Stop monitor: Circuit breaker triggered for {strategy.id[:8]}...: "
                        f"{cb_state.trigger_reason}"
                    )
                    await scheduler.disable_strategy(strategy, StrategyStatus.DISABLED)

            checked += 1

        except Exception as e:
            logger.exception(f"Stop monitor error for strategy {strategy.id}: {e}")
            # Don't expose exception details to external users
            errors.append({"strategy_id": str(strategy.id), "error": "internal_error"})

    logger.info(
        f"Stop monitor complete: checked={checked}, closed={positions_closed}, "
        f"cb_triggered={circuit_breakers_triggered}"
    )

    return {
        "status": "success",
        "checked": checked,
        "positions_closed": positions_closed,
        "circuit_breakers_triggered": circuit_breakers_triggered,
        "errors": errors if errors else None,
    }
