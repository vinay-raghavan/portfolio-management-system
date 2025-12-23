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

from engine.algo.notifications import AlgoNotificationService
from engine.algo.safety import SafetyService
from engine.models.algo import ExecutionStatus, PositionSizingMethod
from engine.models.signals import SignalData, SignalType
from engine.providers.broker.base import Broker
from engine.providers.data.base import DataProvider
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
    position_sizing_method: PositionSizingMethod = PositionSizingMethod.FIXED_QUANTITY
    fixed_quantity: int = 1
    fixed_amount: Decimal = Decimal("10000")
    portfolio_percent: Decimal = Decimal("5.0")
    risk_per_trade_percent: Decimal = Decimal("2.0")


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
        self.safety_service = safety_service or SafetyService()
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
        start_time = time.time()
        execution_id = f"exec_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{config.id}"

        result = ExecutionResult(
            execution_id=execution_id,
            status=ExecutionStatus.RUNNING,
        )

        try:
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

            # Get symbols to analyze
            symbols = symbols_override or config.symbols
            if not symbols:
                result.status = ExecutionStatus.NO_SIGNAL
                result.error_message = "No symbols to analyze"
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

            result.symbols_analyzed = len(symbols)

            # Fetch market data and run strategy for each symbol
            all_signals: list[tuple[str, SignalData]] = []
            for symbol in symbols:
                try:
                    signals = await self._analyze_symbol(strategy, symbol, config.timeframe)
                    for signal in signals:
                        all_signals.append((symbol, signal))
                except Exception as e:
                    logger.warning(f"Error analyzing {symbol}: {e}")
                    continue

            result.signals_generated = len(all_signals)

            if not all_signals:
                result.status = ExecutionStatus.NO_SIGNAL
                result.duration_ms = int((time.time() - start_time) * 1000)
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
            result.duration_ms = int((time.time() - start_time) * 1000)

        except Exception as e:
            logger.exception(f"Strategy execution failed: {e}")
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.duration_ms = int((time.time() - start_time) * 1000)

            await self.notification_service.notify_strategy_error(
                user_id=config.user_id,
                strategy_name=config.name,
                strategy_id=config.id,
                error=str(e),
            )

        return result

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
            logger.debug(
                f"Insufficient data for {symbol}: {len(ohlcv_data) if ohlcv_data else 0} bars"
            )
            return []

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
        return signals

    async def _process_signal(
        self,
        config: StrategyConfig,
        signal: SignalData,
    ) -> dict | None:
        """Process a signal: size, validate, and place order."""
        # Calculate position size
        quantity = self._calculate_position_size(config, signal)
        if quantity <= 0:
            logger.debug(f"Position size is 0 for {signal.symbol}, skipping")
            return None

        # Run safety check
        price = signal.entry_price or signal.price_at_signal
        side = "BUY" if signal.signal_type == SignalType.BUY else "SELL"

        safety_check = self.safety_service.check_order(
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            price=price,
        )

        if not safety_check.passed:
            logger.warning(f"Safety check failed for {signal.symbol}: {safety_check.reason}")
            return {
                "symbol": signal.symbol,
                "status": "SAFETY_BLOCKED",
                "reason": safety_check.reason,
            }

        # Create order request
        order_side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL
        order_request = OrderRequest(
            symbol=signal.symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            product_type=ProductType.DELIVERY,
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

    def _calculate_position_size(
        self,
        config: StrategyConfig,
        signal: SignalData,
    ) -> int:
        """Calculate position size based on strategy config."""
        method = config.position_sizing_method
        price = signal.entry_price or signal.price_at_signal

        if method == PositionSizingMethod.FIXED_QUANTITY:
            return config.fixed_quantity or 1

        if method == PositionSizingMethod.FIXED_AMOUNT:
            amount = config.fixed_amount or Decimal("10000")
            return max(1, int(amount / price))

        # Default: fixed quantity
        return 1

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
