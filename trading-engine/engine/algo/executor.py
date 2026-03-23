"""Strategy executor for algo trading.

This module handles the execution of trading strategies, including:
- Fetching market data
- Running strategy to generate signals
- Applying position sizing
- Validating with risk service
- Placing orders via broker
- Persisting execution results to database
"""

import logging
import time as time_module
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from decimal import Decimal
from uuid import uuid4

import pandas as pd
from shared.utils.time_window import TimeWindowValidator

from engine.algo.notifications import AlgoNotificationService
from engine.algo.position_tracker import PnLStats, PositionTracker
from engine.algo.safety import SafetyService
from engine.core.database import get_db_context
from engine.models.algo import (
    AlgoOrder,
    ExecutionStatus,
    Order,
    PositionSizingMethod,
    SignalDirection,
    StrategyExecution,
    StrategyProductType,
)
from engine.models.signals import SignalData, SignalIntent, SignalType
from engine.providers.broker import Broker
from engine.providers.data import DataProvider
from engine.providers.schemas import OrderRequest, OrderSide, OrderType, ProductType
from engine.strategies.base import BaseStrategy
from engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a strategy execution run."""

    execution_id: str
    status: ExecutionStatus
    symbols_analyzed: int = 0
    signals_generated: int = 0
    orders_placed: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    signals_data: list = field(default_factory=list)
    orders_data: list = field(default_factory=list)
    error_message: str | None = None
    duration_ms: int = 0
    # P&L tracking from position tracker
    pnl_stats: PnLStats = field(default_factory=PnLStats)


@dataclass
class StrategyConfig:
    """Configuration for strategy execution."""

    id: str
    user_id: str
    name: str
    strategy_name: str
    strategy_params: dict = field(default_factory=dict)
    timeframe: str = "1d"
    symbols: list[str] = field(default_factory=list)
    # Exit-only symbols: only SELL signals are allowed, no new BUY positions
    exit_only_symbols: list[str] = field(default_factory=list)
    position_sizing_method: PositionSizingMethod = PositionSizingMethod.FIXED_QUANTITY
    fixed_quantity: int = 1
    fixed_amount: Decimal = Decimal("10000")
    portfolio_percent: Decimal = Decimal("5.0")
    risk_per_trade_percent: Decimal = Decimal("2.0")
    max_open_positions: int = 5
    product_type: ProductType = ProductType.DELIVERY
    # Signal direction (LONG/SHORT/BOTH)
    signal_direction: SignalDirection = SignalDirection.LONG
    # Trading time window fields
    trading_start_time: time | None = None
    trading_end_time: time | None = None
    trading_timezone: str = "Asia/Kolkata"
    active_trading_days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])


class StrategyExecutor:
    """Executes trading strategies and places orders.

    This class orchestrates the full algo trading pipeline:
    1. Load strategy and configuration
    2. Fetch market data for universe symbols
    3. Run strategy to generate signals
    4. Apply position sizing
    5. Validate with safety service
    6. Place orders via broker
    7. Log execution results
    """

    def __init__(
        self,
        broker: Broker,
        data_provider: DataProvider,
        safety_service: SafetyService | None = None,
    ):
        """Initialize the executor.

        Args:
            broker: Broker provider for order execution
            data_provider: Data provider for market data
            safety_service: Optional safety service for risk checks
        """
        self.broker = broker
        self.data_provider = data_provider
        # Initialize safety service with broker for funds validation
        self.safety_service = safety_service or SafetyService(broker=broker)
        self.notification_service = AlgoNotificationService()

    async def execute(
        self,
        config: StrategyConfig,
        symbols_override: list[str] | None = None,
    ) -> ExecutionResult:
        """Execute a trading strategy.

        Args:
            config: The strategy configuration to execute
            symbols_override: Optional list of symbols to override

        Returns:
            ExecutionResult with details of the execution
        """
        start_time = time_module.time()
        execution_id = f"exec_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{config.id}"

        result = ExecutionResult(
            execution_id=execution_id,
            status=ExecutionStatus.RUNNING,
        )

        try:
            # Check time window BEFORE executing (skip if outside trading window)
            if config.trading_start_time or config.trading_end_time:
                validator = TimeWindowValidator()
                is_valid, reason = validator.is_within_window(
                    start_time=config.trading_start_time,
                    end_time=config.trading_end_time,
                    timezone=config.trading_timezone,
                    active_days=config.active_trading_days,
                )

                if not is_valid:
                    logger.info(
                        f"Strategy '{config.name}' skipped: Outside trading window - {reason}"
                    )
                    result.status = ExecutionStatus.SKIPPED
                    result.error_message = f"Outside trading window: {reason}"
                    result.duration_ms = int((time_module.time() - start_time) * 1000)
                    return result

            # Notify strategy started
            await self.notification_service.notify_strategy_started(
                user_id=config.user_id,
                strategy_name=config.name,
                strategy_id=config.id,
            )

            # Get strategy from registry
            strategy = StrategyRegistry.get_strategy(
                config.strategy_name,
                config.strategy_params,
            )
            if not strategy:
                raise ValueError(f"Strategy '{config.strategy_name}' not found in registry")

            # Get symbols to analyze: active symbols + exit-only symbols
            active_symbols = symbols_override or config.symbols
            exit_only_symbols = set(config.exit_only_symbols or [])
            all_symbols = list(set(active_symbols) | exit_only_symbols)

            if not all_symbols:
                result.status = ExecutionStatus.NO_SIGNAL
                result.error_message = "No symbols to analyze"
                result.duration_ms = int((time_module.time() - start_time) * 1000)
                return result

            result.symbols_analyzed = len(all_symbols)

            # Fetch market data and run strategy for each symbol
            all_signals: list[tuple[str, SignalData]] = []
            symbol_prices: dict[str, Decimal] = {}
            for symbol in all_symbols:
                try:
                    signals, current_price = await self._analyze_symbol(
                        strategy, symbol, config.timeframe
                    )
                    if current_price:
                        symbol_prices[symbol] = current_price

                    # Filter signals based on exit-only status
                    for signal in signals:
                        if symbol in exit_only_symbols:
                            # Exit-only: only allow SELL signals (to close positions)
                            if signal.signal_type == SignalType.SELL:
                                all_signals.append((symbol, signal))
                                logger.debug(f"Exit-only symbol {symbol}: allowing SELL signal")
                            else:
                                logger.debug(f"Exit-only symbol {symbol}: blocking BUY signal")
                        else:
                            # Active symbol: allow all signals
                            all_signals.append((symbol, signal))
                except Exception as e:
                    logger.warning(f"Error analyzing {symbol}: {e}")
                    continue

            result.signals_generated = len(all_signals)

            # Check open positions for stop-loss/take-profit exits
            await self._check_exit_conditions(config, symbol_prices, result)

            if not all_signals:
                result.status = ExecutionStatus.NO_SIGNAL
                result.duration_ms = int((time_module.time() - start_time) * 1000)
                return result

            # Process signals and place orders
            for symbol, signal in all_signals:
                order_result = await self._process_signal(config, signal)
                if order_result:
                    result.signals_data.append(self._signal_to_dict(signal))
                    result.orders_data.append(order_result)
                    result.orders_placed += 1
                    if order_result.get("status") == "FILLED":
                        result.orders_filled += 1
                    elif order_result.get("status") in ["REJECTED", "CANCELLED"]:
                        result.orders_rejected += 1

            result.status = ExecutionStatus.COMPLETED
            result.duration_ms = int((time_module.time() - start_time) * 1000)

        except Exception as e:
            logger.exception(f"Strategy execution failed: {e}")
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.duration_ms = int((time_module.time() - start_time) * 1000)

            await self.notification_service.notify_strategy_error(
                user_id=config.user_id,
                strategy_name=config.name,
                strategy_id=config.id,
                error=str(e),
            )

        # Persist execution results to database
        await self._persist_execution(config, result, start_time)

        return result

    async def _analyze_symbol(
        self,
        strategy: BaseStrategy,
        symbol: str,
        timeframe: str,
    ) -> tuple[list[SignalData], Decimal | None]:
        """Fetch data and run strategy for a symbol.

        Returns:
            Tuple of (signals, current_price)
        """
        # Map timeframe to data provider interval
        interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "1d": "1d"}
        interval = interval_map.get(timeframe, "1d")

        # Determine period based on timeframe
        period_map = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "1mo", "1d": "6mo"}
        period = period_map.get(timeframe, "6mo")

        # Fetch historical data
        ohlcv_data = await self.data_provider.get_historical(
            symbol=symbol,
            period=period,
            interval=interval,
        )

        if not ohlcv_data or len(ohlcv_data) < 20:
            logger.debug(
                f"Insufficient data for {symbol}: {len(ohlcv_data) if ohlcv_data else 0} bars"
            )
            return [], None

        # Get current price from latest bar
        current_price = Decimal(str(ohlcv_data[-1].close))

        # Convert to DataFrame
        df = pd.DataFrame(
            [
                {
                    "Open": float(bar.open),
                    "High": float(bar.high),
                    "Low": float(bar.low),
                    "Close": float(bar.close),
                    "Volume": bar.volume,
                }
                for bar in ohlcv_data
            ]
        )
        df.index = pd.to_datetime([bar.timestamp for bar in ohlcv_data])

        # Run strategy
        signals = strategy.generate_signals(df, symbol)
        return signals, current_price

    async def _process_signal(
        self,
        config: StrategyConfig,
        signal: SignalData,
    ) -> dict | None:
        """Process a signal: size, validate, and place order."""
        open_position_side = await self._get_open_position_side(
            strategy_id=config.id,
            user_id=config.user_id,
            symbol=signal.symbol,
        )

        # Check if signal direction is allowed by strategy configuration
        if config.signal_direction == SignalDirection.LONG:
            # LONG only: block SHORT signals
            if signal.intent in (SignalIntent.OPEN_SHORT, SignalIntent.CLOSE_SHORT):
                logger.debug(
                    f"Blocking {signal.intent} signal for {signal.symbol}: strategy is LONG only"
                )
                return None

            # Fallback guard for strategies that don't set intent:
            # allow SELL only when it closes an existing LONG position.
            if signal.intent is None and signal.signal_type == SignalType.SELL:
                if open_position_side != "LONG":
                    logger.debug(
                        f"Blocking SELL signal for {signal.symbol}: LONG strategy has no LONG "
                        "position to close (would open short)"
                    )
                    return None
        elif config.signal_direction == SignalDirection.SHORT:
            # SHORT only: block LONG signals
            if signal.intent in (SignalIntent.OPEN_LONG, SignalIntent.CLOSE_LONG):
                logger.debug(
                    f"Blocking {signal.intent} signal for {signal.symbol}: strategy is SHORT only"
                )
                return None

            # Fallback guard for strategies that don't set intent:
            # allow BUY only when it closes an existing SHORT position.
            if signal.intent is None and signal.signal_type == SignalType.BUY:
                if open_position_side != "SHORT":
                    logger.debug(
                        f"Blocking BUY signal for {signal.symbol}: SHORT strategy has no SHORT "
                        "position to close (would open long)"
                    )
                    return None
        # BOTH: allow all signals

        # Check if signal intent is compatible with product type
        if signal.intent == SignalIntent.OPEN_SHORT:
            # Short selling requires INTRADAY or SLB product type
            if config.product_type not in (
                StrategyProductType.INTRADAY,
                StrategyProductType.SLB,
            ):
                logger.warning(
                    f"Cannot open SHORT for {signal.symbol}: "
                    f"{config.product_type.value} does not allow short selling. "
                    f"Use INTRADAY or SLB product type."
                )
                return {
                    "symbol": signal.symbol,
                    "status": "BLOCKED",
                    "reason": (
                        f"Short selling not allowed with {config.product_type.value}. "
                        f"Switch to INTRADAY or SLB product type."
                    ),
                }

        # Block new INTRADAY entries after square-off time (3:10 PM IST)
        # This prevents positions from being opened that won't get squared off
        if config.product_type == StrategyProductType.INTRADAY:
            if open_position_side is None:  # Only for new entries, not exits
                from datetime import time as dt_time

                import pytz

                ist = pytz.timezone("Asia/Kolkata")
                now_ist = datetime.now(ist)
                intraday_entry_cutoff = dt_time(15, 10)  # 3:10 PM IST (same as square-off)

                if now_ist.time() >= intraday_entry_cutoff:
                    logger.warning(
                        f"Blocking INTRADAY entry for {signal.symbol}: "
                        f"past entry cutoff time {intraday_entry_cutoff} IST"
                    )
                    return {
                        "symbol": signal.symbol,
                        "status": "BLOCKED",
                        "reason": "INTRADAY entries blocked after 3:10 PM IST",
                    }

        # Enforce strategy-level max open positions before opening a new symbol position.
        if open_position_side is None:
            open_positions_count = await self._get_open_positions_count(
                strategy_id=config.id, user_id=config.user_id
            )
            if open_positions_count >= config.max_open_positions:
                logger.warning(
                    f"Max open positions reached for strategy {config.id}: "
                    f"{open_positions_count}/{config.max_open_positions}"
                )
                return {
                    "symbol": signal.symbol,
                    "status": "RISK_BLOCKED",
                    "reason": (
                        f"Max open positions reached: "
                        f"{open_positions_count}/{config.max_open_positions}"
                    ),
                }

        # Calculate position size (async to fetch funds for percent-based sizing)
        quantity = await self._calculate_position_size(config, signal)
        if quantity <= 0:
            logger.debug(f"Position size is 0 for {signal.symbol}, skipping")
            return None

        # Get existing position quantity for product type validation
        existing_position_qty = Decimal("0")
        try:
            positions = await self.broker.get_positions(config.user_id)
            for pos in positions:
                if pos.symbol.upper() == signal.symbol.upper():
                    existing_position_qty = pos.quantity
                    break
        except Exception as e:
            logger.warning(f"Could not get existing position for {signal.symbol}: {e}")

        # Run safety check (with funds/margin validation based on product type)
        price = signal.entry_price or signal.price_at_signal
        side = "BUY" if signal.signal_type == SignalType.BUY else "SELL"

        safety_check = await self.safety_service.check_order_with_funds(
            user_id=config.user_id,
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            price=price,
            product_type=config.product_type.value,
            existing_position_qty=existing_position_qty,
        )

        if not safety_check.passed:
            logger.warning(f"Safety check failed for {signal.symbol}: {safety_check.reason}")
            return {
                "symbol": signal.symbol,
                "status": "SAFETY_BLOCKED",
                "reason": safety_check.reason,
            }

        # Create order request with strategy's product type
        order_side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL
        order_request = OrderRequest(
            symbol=signal.symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            product_type=config.product_type,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )

        # Place order
        try:
            order_response = await self.broker.place_order(config.user_id, order_request)

            return {
                "order_id": order_response.order_id,
                "symbol": signal.symbol,
                "side": order_side.value,
                "quantity": quantity,
                "status": order_response.status.value,
                "filled_price": float(order_response.filled_price)
                if order_response.filled_price
                else None,
            }

        except Exception as e:
            logger.error(f"Order placement failed for {signal.symbol}: {e}")
            return {
                "symbol": signal.symbol,
                "status": "ERROR",
                "reason": str(e),
            }

    async def _get_open_position_side(
        self,
        strategy_id: str,
        user_id: str,
        symbol: str,
    ) -> str | None:
        """Get open position side for a strategy/symbol from internal position tracker."""
        try:
            async with get_db_context() as db:
                tracker = PositionTracker(db)
                position = await tracker.get_open_position(strategy_id, user_id, symbol)
                return position.side.value if position else None
        except Exception as e:
            logger.warning(
                f"Failed to fetch open position side for {symbol} in strategy {strategy_id}: {e}"
            )
            return None

    async def _get_open_positions_count(
        self,
        strategy_id: str,
        user_id: str,
    ) -> int:
        """Count open+partial positions for strategy-level position cap enforcement."""
        try:
            async with get_db_context() as db:
                tracker = PositionTracker(db)
                open_positions = await tracker.get_all_open_positions(
                    strategy_id=strategy_id,
                    user_id=user_id,
                    include_partial=True,
                )
                return len(open_positions)
        except Exception as e:
            logger.warning(
                f"Failed to count open positions for strategy {strategy_id}, "
                f"defaulting to safe block: {e}"
            )
            # Fail-safe: return a high number to avoid unintentionally opening new risk.
            return 10_000

    async def _calculate_position_size(
        self,
        config: StrategyConfig,
        signal: SignalData,
    ) -> int:
        """Calculate position size based on strategy config.

        For percentage-based methods (PERCENT_OF_PORTFOLIO, RISK_BASED),
        fetches actual portfolio value from the broker.

        Args:
            config: Strategy configuration with sizing method
            signal: Signal data with price information

        Returns:
            Position size as integer quantity
        """
        method = config.position_sizing_method
        price = signal.entry_price or signal.price_at_signal

        if method == PositionSizingMethod.FIXED_QUANTITY:
            return config.fixed_quantity or 1

        if method == PositionSizingMethod.FIXED_AMOUNT:
            amount = config.fixed_amount or Decimal("10000")
            return max(1, int(amount / price))

        if method == PositionSizingMethod.PERCENT_OF_PORTFOLIO:
            # Fetch actual portfolio value from broker
            try:
                funds = await self.broker.get_funds(config.user_id)
                portfolio_value = funds.total_balance
                pct = config.portfolio_percent or Decimal("5.0")
                amount_to_invest = portfolio_value * (pct / Decimal("100"))
                quantity = int(amount_to_invest / price)
                logger.debug(
                    f"PERCENT_OF_PORTFOLIO sizing: {pct}% of {portfolio_value} = "
                    f"{amount_to_invest}, qty={quantity} @ {price}"
                )
                return max(1, quantity) if quantity > 0 else 0
            except Exception as e:
                logger.warning(f"Failed to get portfolio value: {e}, using fixed amount")
                return max(1, int((config.fixed_amount or Decimal("10000")) / price))

        if method == PositionSizingMethod.RISK_BASED:
            # Risk-based sizing: risk_amount = portfolio_value * risk_percent
            # quantity = risk_amount / (entry_price - stop_loss)
            try:
                funds = await self.broker.get_funds(config.user_id)
                portfolio_value = funds.total_balance
                risk_pct = config.risk_per_trade_percent or Decimal("2.0")
                risk_amount = portfolio_value * (risk_pct / Decimal("100"))

                # Calculate risk per share (entry - stop_loss)
                stop_loss = signal.stop_loss
                if stop_loss and price > stop_loss:
                    risk_per_share = price - stop_loss
                    quantity = int(risk_amount / risk_per_share)
                    logger.debug(
                        f"RISK_BASED sizing: {risk_pct}% risk = {risk_amount}, "
                        f"risk/share={risk_per_share}, qty={quantity}"
                    )
                    return max(1, quantity) if quantity > 0 else 0
                else:
                    # No stop loss defined, fall back to portfolio percent
                    pct = config.portfolio_percent or Decimal("5.0")
                    amount = portfolio_value * (pct / Decimal("100"))
                    return max(1, int(amount / price))
            except Exception as e:
                logger.warning(f"Failed risk-based sizing: {e}, using fixed amount")
                return max(1, int((config.fixed_amount or Decimal("10000")) / price))

        # Default: fixed quantity
        return 1

    async def _check_exit_conditions(
        self,
        config: StrategyConfig,
        symbol_prices: dict[str, Decimal],
        result: ExecutionResult,
    ) -> None:
        """Check open positions for stop-loss/take-profit exits.

        If any positions hit their SL/TP, places exit orders and updates funds.
        """
        if not symbol_prices:
            return

        try:
            async with get_db_context() as db:
                position_tracker = PositionTracker(db)
                closed_positions, pnl_stats = await position_tracker.check_stop_loss_take_profit(
                    strategy_id=config.id,
                    user_id=config.user_id,
                    current_prices=symbol_prices,
                )

                if closed_positions:
                    logger.info(
                        f"Auto-closed {len(closed_positions)} positions due to SL/TP: "
                        f"pnl={pnl_stats.total_pnl}, winners={pnl_stats.winning_trades}"
                    )

                    # Update funds for closed positions (credit sale proceeds)
                    # This ensures realized P&L reflects in user funds
                    # Pass product_type to ensure proper margin release for INTRADAY/MARGIN
                    await self._update_funds_for_closed_positions(
                        config.user_id, closed_positions, db, config.product_type
                    )

                    # Add exit orders to result
                    for pos in closed_positions:
                        exit_order = {
                            "symbol": pos.symbol,
                            "side": "SELL" if pos.side == "LONG" else "BUY",
                            "quantity": pos.quantity,
                            "status": "FILLED",
                            "filled_price": float(pos.exit_price) if pos.exit_price else None,
                            "exit_type": "stop_loss" if not pos.is_winner else "take_profit",
                        }
                        result.orders_data.append(exit_order)
                        result.orders_placed += 1
                        result.orders_filled += 1

                    # Update P&L stats on result
                    if result.pnl_stats:
                        result.pnl_stats.trades_closed += pnl_stats.trades_closed
                        result.pnl_stats.winning_trades += pnl_stats.winning_trades
                        result.pnl_stats.losing_trades += pnl_stats.losing_trades
                        result.pnl_stats.total_pnl += pnl_stats.total_pnl
                    else:
                        result.pnl_stats = pnl_stats

                await db.commit()

        except Exception as e:
            logger.warning(f"Error checking exit conditions: {e}")

    async def _update_funds_for_closed_positions(
        self,
        user_id: str,
        closed_positions: list,
        db,
        product_type: ProductType = ProductType.DELIVERY,
    ) -> None:
        """Update user funds after positions are closed.

        Uses recalculate_funds() to derive all values from positions,
        ensuring funds are always in sync with actual position state.

        Args:
            user_id: The user ID
            closed_positions: List of PositionResult objects (for logging only)
            db: Database session
            product_type: Product type (unused, kept for API compatibility)
        """
        from shared.providers.funds import DatabaseFundsProvider

        from engine.models import AlgoPosition, UserFunds

        try:
            # Create a funds provider
            funds_provider = DatabaseFundsProvider(
                db=db,
                user_funds_model=UserFunds,
                initial_balance=Decimal("0"),
                algo_position_model=AlgoPosition,
            )

            # Log the positions being closed
            total_realized_pnl = Decimal("0")
            for pos in closed_positions:
                if pos.realized_pnl:
                    total_realized_pnl += Decimal(str(pos.realized_pnl))
                logger.debug(
                    f"Closed position {pos.symbol}: side={pos.side}, "
                    f"qty={pos.quantity}, pnl={pos.realized_pnl}"
                )

            # Recalculate funds from positions (single source of truth)
            await funds_provider.recalculate_funds(user_id)

            if total_realized_pnl != Decimal("0"):
                logger.info(
                    f"Positions closed for user {user_id[:8]}...: "
                    f"total_pnl=₹{total_realized_pnl:.2f}"
                )

        except Exception as e:
            logger.warning(f"Failed to recalculate funds: {e}")

    def _signal_to_dict(self, signal: SignalData) -> dict:
        """Convert SignalData to dictionary."""
        return {
            "symbol": signal.symbol,
            "signal_type": signal.signal_type.value,
            "strength": float(signal.strength),
            "confidence": float(signal.confidence),
            "price_at_signal": float(signal.price_at_signal),
            "entry_price": float(signal.entry_price) if signal.entry_price else None,
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
            "take_profit": float(signal.take_profit) if signal.take_profit else None,
        }

    async def _persist_execution(
        self,
        config: StrategyConfig,
        result: ExecutionResult,
        start_time: float,
    ) -> None:
        """Persist execution results to the database.

        Creates a StrategyExecution record, AlgoOrder records for each order,
        and tracks positions with P&L calculation.
        """
        try:
            async with get_db_context() as db:
                # Initialize position tracker for P&L calculation
                position_tracker = PositionTracker(db)
                aggregated_pnl = PnLStats()

                # Create execution record
                execution_id = str(uuid4())
                execution = StrategyExecution(
                    id=execution_id,
                    strategy_id=config.id,
                    user_id=config.user_id,
                    started_at=datetime.fromtimestamp(start_time, tz=UTC),
                    completed_at=datetime.now(UTC),
                    duration_ms=result.duration_ms,
                    status=result.status,
                    symbols_analyzed=result.symbols_analyzed,
                    signals_generated=result.signals_generated,
                    orders_placed=result.orders_placed,
                    orders_filled=result.orders_filled,
                    orders_rejected=result.orders_rejected,
                    signals_data=result.signals_data,
                    orders_data=result.orders_data,
                    error_message=result.error_message,
                )
                db.add(execution)

                # Create Order and AlgoOrder records for each order
                for i, order_data in enumerate(result.orders_data):
                    signal_data = result.signals_data[i] if i < len(result.signals_data) else {}

                    # Create Order record in the orders table
                    order_id = str(uuid4())
                    filled_price = order_data.get("filled_price")
                    order_status = order_data.get("status", "PENDING")

                    order = Order(
                        id=order_id,
                        user_id=config.user_id,
                        symbol=order_data.get("symbol", ""),
                        side=order_data.get("side", "BUY"),
                        order_type="MARKET",
                        quantity=Decimal(str(order_data.get("quantity", 0))),
                        price=Decimal(str(filled_price)) if filled_price else None,
                        status=order_status,
                        filled_quantity=Decimal(str(order_data.get("quantity", 0)))
                        if order_status == "FILLED"
                        else Decimal("0"),
                        filled_price=Decimal(str(filled_price)) if filled_price else None,
                        filled_at=datetime.now(UTC) if order_status == "FILLED" else None,
                        notes=f"Algo order from strategy {config.name}",
                    )
                    db.add(order)
                    # Flush to ensure Order is persisted before AlgoOrder (FK constraint)
                    await db.flush()

                    # Create AlgoOrder record linking to the Order
                    order_qty = order_data.get("quantity", 0)
                    order_value = (
                        Decimal(str(filled_price)) * order_qty if filled_price else Decimal("0")
                    )
                    algo_order = AlgoOrder(
                        id=str(uuid4()),
                        execution_id=execution_id,
                        order_id=order_id,
                        user_id=config.user_id,
                        strategy_id=config.id,
                        symbol=order_data.get("symbol", ""),
                        side=order_data.get("side", "BUY"),
                        quantity=order_qty,
                        order_type="MARKET",
                        price=Decimal(str(filled_price)) if filled_price else None,
                        order_status=order_status,
                        filled_quantity=order_qty if order_status == "FILLED" else 0,
                        filled_price=Decimal(str(filled_price)) if filled_price else None,
                        order_value=order_value,
                        filled_at=datetime.now(UTC) if order_status == "FILLED" else None,
                        signal_type=signal_data.get("signal_type"),
                        signal_strength=Decimal(str(signal_data.get("strength", 0)))
                        if signal_data.get("strength")
                        else None,
                        sizing_method=config.position_sizing_method.value,
                        calculated_quantity=order_qty,
                    )
                    db.add(algo_order)

                    # Track position and calculate P&L for filled orders
                    if order_status == "FILLED" and filled_price:
                        try:
                            position_result, pnl_stats = await position_tracker.process_order_fill(
                                strategy_id=config.id,
                                user_id=config.user_id,
                                symbol=order_data.get("symbol", ""),
                                side=order_data.get("side", "BUY"),
                                quantity=order_data.get("quantity", 0),
                                fill_price=Decimal(str(filled_price)),
                                order_id=order_id,
                            )
                            # Aggregate P&L stats
                            aggregated_pnl.trades_closed += pnl_stats.trades_closed
                            aggregated_pnl.winning_trades += pnl_stats.winning_trades
                            aggregated_pnl.losing_trades += pnl_stats.losing_trades
                            aggregated_pnl.total_pnl += pnl_stats.total_pnl
                            if pnl_stats.consecutive_losses > 0:
                                aggregated_pnl.consecutive_losses += pnl_stats.consecutive_losses

                            # Import funds provider (used for both opening and closing)
                            from shared.providers.funds import DatabaseFundsProvider

                            from engine.models import AlgoPosition, UserFunds

                            funds_provider = DatabaseFundsProvider(
                                db=db,
                                user_funds_model=UserFunds,
                                initial_balance=Decimal("0"),
                                algo_position_model=AlgoPosition,
                            )

                            # Recalculate funds from positions (single source of truth)
                            # This handles both opening new positions and closing existing ones
                            await funds_provider.recalculate_funds(config.user_id)

                            if pnl_stats.trades_closed > 0:
                                logger.info(
                                    f"Position closed {order_data.get('symbol')}: "
                                    f"pnl={pnl_stats.total_pnl:.2f}"
                                )
                            else:
                                logger.info(
                                    f"Position opened {order_data.get('symbol')}: "
                                    f"side={order_data.get('side')}, qty={order_data.get('quantity')}"
                                )
                        except Exception as e:
                            logger.warning(
                                f"Position tracking failed for {order_data.get('symbol')}: {e}"
                            )

                await db.commit()

                # Update the result with P&L stats
                result.pnl_stats = aggregated_pnl

                logger.info(
                    f"Persisted execution {execution_id} with {len(result.orders_data)} orders, "
                    f"pnl={aggregated_pnl.total_pnl}, closed={aggregated_pnl.trades_closed}"
                )

        except Exception as e:
            logger.error(f"Failed to persist execution results: {e}")
