"""Strategy executor for algo trading.

This module handles the execution of trading strategies, including:
- Fetching market data
- Running strategy to generate signals
- Applying position sizing
- Validating with risk service
- Placing orders via broker
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import (
    AlgoOrder,
    ExecutionStatus,
    PositionSizingMethod,
    StrategyExecution,
    StrategyStatus,
    UserStrategy,
)
from app.modules.algo.notifications import AlgoNotificationService
from app.modules.risk.service import RiskService
from app.modules.signals.models import Signal, SignalStatus, SignalType
from app.modules.signals.strategies.base import BaseStrategy, SignalData
from app.modules.signals.strategies.registry import StrategyRegistry
from app.providers.broker.base import Broker
from app.providers.data.base import DataProvider
from app.providers.schemas import OrderRequest, OrderResponse, OrderSide, OrderType, ProductType

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


class StrategyExecutor:
    """Executes trading strategies and places orders.

    This class orchestrates the full algo trading pipeline:
    1. Load strategy and configuration
    2. Fetch market data for universe symbols
    3. Run strategy to generate signals
    4. Apply position sizing
    5. Validate with risk service
    6. Place orders via broker
    7. Log execution results
    """

    def __init__(
        self,
        db: AsyncSession,
        broker: Broker,
        data_provider: DataProvider,
    ):
        """Initialize the executor.

        Args:
            db: Database session
            broker: Broker provider for order execution
            data_provider: Data provider for market data
        """
        self.db = db
        self.broker = broker
        self.data_provider = data_provider
        self.risk_service = RiskService(db)
        self.notification_service = AlgoNotificationService()

    async def execute(
        self,
        user_strategy: UserStrategy,
        symbols_override: list[str] | None = None,
    ) -> ExecutionResult:
        """Execute a user's trading strategy.

        Args:
            user_strategy: The strategy configuration to execute
            symbols_override: Optional list of symbols to override the universe

        Returns:
            ExecutionResult with details of the execution
        """
        start_time = time.time()

        # Create execution record
        execution = StrategyExecution(
            strategy_id=user_strategy.id,
            user_id=user_strategy.user_id,
            status=ExecutionStatus.RUNNING,
        )
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)

        result = ExecutionResult(
            execution_id=execution.id,
            status=ExecutionStatus.RUNNING,
        )

        try:
            # Get strategy from registry
            strategy = StrategyRegistry.get_strategy(
                user_strategy.strategy_name,
                user_strategy.strategy_params,
            )
            if not strategy:
                raise ValueError(f"Strategy '{user_strategy.strategy_name}' not found in registry")

            # Get symbols to analyze
            symbols = await self._get_symbols(user_strategy, symbols_override)
            if not symbols:
                result.status = ExecutionStatus.NO_SIGNAL
                result.error_message = "No symbols in universe"
                await self._finalize_execution(execution, result, start_time)
                return result

            result.symbols_analyzed = len(symbols)

            # Fetch market data and run strategy for each symbol
            all_signals: list[tuple[str, SignalData]] = []
            for symbol in symbols:
                try:
                    signals = await self._analyze_symbol(strategy, symbol, user_strategy.timeframe)
                    for signal in signals:
                        all_signals.append((symbol, signal))
                except Exception as e:
                    logger.warning(f"Error analyzing {symbol}: {e}")
                    continue

            result.signals_generated = len(all_signals)

            if not all_signals:
                result.status = ExecutionStatus.NO_SIGNAL
                await self._finalize_execution(execution, result, start_time)
                return result

            # Process signals and place orders
            for symbol, signal in all_signals:
                order_result = await self._process_signal(
                    user_strategy=user_strategy,
                    execution=execution,
                    signal=signal,
                )
                if order_result:
                    result.signals_data.append(self._signal_to_dict(signal))
                    result.orders_data.append(order_result)
                    result.orders_placed += 1
                    if order_result.get("status") == "FILLED":
                        result.orders_filled += 1
                    elif order_result.get("status") in ["REJECTED", "CANCELLED"]:
                        result.orders_rejected += 1

            result.status = ExecutionStatus.COMPLETED
            await self._finalize_execution(execution, result, start_time)

        except Exception as e:
            logger.exception(f"Strategy execution failed: {e}")
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            await self._finalize_execution(execution, result, start_time)

        return result

    async def _get_symbols(
        self,
        user_strategy: UserStrategy,
        symbols_override: list[str] | None = None,
    ) -> list[str]:
        """Get the list of symbols to analyze."""
        if symbols_override:
            return symbols_override

        if user_strategy.custom_symbols:
            return user_strategy.custom_symbols

        if user_strategy.universe:
            return user_strategy.universe.symbols or []

        return []

    async def _analyze_symbol(
        self,
        strategy: BaseStrategy,
        symbol: str,
        timeframe: str,
    ) -> list[SignalData]:
        """Fetch data and run strategy for a symbol."""
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
            logger.debug(f"Insufficient data for {symbol}: {len(ohlcv_data) if ohlcv_data else 0} bars")
            return []

        # Convert to DataFrame
        df = pd.DataFrame([
            {
                "Open": float(bar.open),
                "High": float(bar.high),
                "Low": float(bar.low),
                "Close": float(bar.close),
                "Volume": bar.volume,
            }
            for bar in ohlcv_data
        ])
        df.index = pd.to_datetime([bar.timestamp for bar in ohlcv_data])

        # Run strategy
        signals = strategy.generate_signals(df, symbol)
        return signals

    async def _process_signal(
        self,
        user_strategy: UserStrategy,
        execution: StrategyExecution,
        signal: SignalData,
    ) -> dict | None:
        """Process a signal: size, validate, and place order."""
        user_id = user_strategy.user_id

        # Calculate position size
        quantity = await self._calculate_position_size(user_strategy, signal)
        if quantity <= 0:
            logger.debug(f"Position size is 0 for {signal.symbol}, skipping")
            return None

        # Run risk check
        price = signal.entry_price or signal.price_at_signal
        risk_check = await self.risk_service.check_order_risk(
            user_id=user_id,
            symbol=signal.symbol,
            side="BUY" if signal.signal_type == SignalType.BUY else "SELL",
            quantity=Decimal(quantity),
            price=price,
        )

        if not risk_check.passed:
            logger.warning(f"Risk check failed for {signal.symbol}: {risk_check.blocked_reason}")
            execution.status = ExecutionStatus.RISK_BLOCKED
            return {
                "symbol": signal.symbol,
                "status": "RISK_BLOCKED",
                "reason": risk_check.blocked_reason,
            }

        # Create order request
        side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL
        order_request = OrderRequest(
            symbol=signal.symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            product_type=ProductType.DELIVERY,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )

        # Place order
        try:
            order_response = await self.broker.place_order(user_id, order_request)

            # Create algo order record
            algo_order = AlgoOrder(
                execution_id=execution.id,
                order_id=order_response.order_id,
                user_id=user_id,
                strategy_id=user_strategy.id,
                symbol=signal.symbol,
                side=side.value,
                quantity=quantity,
                order_type=order_request.order_type.value,
                price=order_response.filled_price,
                signal_type=signal.signal_type.value,
                signal_strength=signal.strength,
                sizing_method=user_strategy.position_sizing_method.value,
                calculated_quantity=quantity,
            )
            self.db.add(algo_order)

            # Update strategy stats
            user_strategy.total_trades += 1
            user_strategy.last_run_at = datetime.now(UTC)

            return {
                "order_id": order_response.order_id,
                "symbol": signal.symbol,
                "side": side.value,
                "quantity": quantity,
                "status": order_response.status.value,
                "filled_price": float(order_response.filled_price) if order_response.filled_price else None,
            }

        except Exception as e:
            logger.error(f"Order placement failed for {signal.symbol}: {e}")
            return {
                "symbol": signal.symbol,
                "status": "ERROR",
                "reason": str(e),
            }

    async def _calculate_position_size(
        self,
        user_strategy: UserStrategy,
        signal: SignalData,
    ) -> int:
        """Calculate position size based on strategy config."""
        method = user_strategy.position_sizing_method
        price = signal.entry_price or signal.price_at_signal

        if method == PositionSizingMethod.FIXED_QUANTITY:
            return user_strategy.fixed_quantity or 1

        if method == PositionSizingMethod.FIXED_AMOUNT:
            amount = user_strategy.fixed_amount or Decimal("10000")
            return max(1, int(amount / price))

        if method == PositionSizingMethod.PERCENT_OF_PORTFOLIO:
            funds = await self.broker.get_funds(user_strategy.user_id)
            portfolio_value = funds.total_balance
            target_value = portfolio_value * (user_strategy.portfolio_percent / 100)
            return max(1, int(target_value / price))

        if method == PositionSizingMethod.RISK_BASED:
            if not signal.stop_loss:
                # Fallback to percent of portfolio
                funds = await self.broker.get_funds(user_strategy.user_id)
                return max(1, int((funds.total_balance * Decimal("0.05")) / price))

            funds = await self.broker.get_funds(user_strategy.user_id)
            risk_amount = funds.total_balance * (user_strategy.risk_per_trade_percent / 100)
            risk_per_share = abs(price - signal.stop_loss)
            if risk_per_share <= 0:
                return 1
            return max(1, int(risk_amount / risk_per_share))

        # Default: fixed quantity
        return 1

    async def _finalize_execution(
        self,
        execution: StrategyExecution,
        result: ExecutionResult,
        start_time: float,
    ) -> None:
        """Finalize execution record."""
        duration_ms = int((time.time() - start_time) * 1000)
        result.duration_ms = duration_ms

        execution.status = result.status
        execution.completed_at = datetime.now(UTC)
        execution.duration_ms = duration_ms
        execution.symbols_analyzed = result.symbols_analyzed
        execution.signals_generated = result.signals_generated
        execution.orders_placed = result.orders_placed
        execution.orders_filled = result.orders_filled
        execution.orders_rejected = result.orders_rejected
        execution.signals_data = result.signals_data
        execution.orders_data = result.orders_data
        execution.error_message = result.error_message

        await self.db.flush()

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

