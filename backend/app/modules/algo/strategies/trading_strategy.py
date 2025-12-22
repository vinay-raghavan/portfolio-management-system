"""Trading strategy base class for algo trading execution.

This extends the BaseStrategy with additional methods needed for
automated order execution.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from app.modules.algo.models import PositionSizingMethod
from app.modules.signals.models import SignalType
from app.modules.signals.strategies.base import BaseStrategy, SignalData
from app.providers.schemas import OrderRequest, OrderSide, OrderType, ProductType


class EntryReason(str, Enum):
    """Reason for entering a trade."""

    SIGNAL = "SIGNAL"
    MANUAL = "MANUAL"
    REBALANCE = "REBALANCE"


class ExitReason(str, Enum):
    """Reason for exiting a trade."""

    SIGNAL = "SIGNAL"  # Opposite signal received
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"
    TIME_EXIT = "TIME_EXIT"  # End of day / session
    MANUAL = "MANUAL"
    KILL_SWITCH = "KILL_SWITCH"


@dataclass
class TradingStrategyConfig:
    """Configuration for a trading strategy instance."""

    # Position sizing
    sizing_method: PositionSizingMethod = PositionSizingMethod.PERCENT_OF_PORTFOLIO
    fixed_quantity: int | None = None
    fixed_amount: Decimal | None = None
    portfolio_percent: Decimal = Decimal("5.0")  # 5% of portfolio
    risk_per_trade_percent: Decimal = Decimal("2.0")  # 2% risk per trade
    max_position_value: Decimal | None = None

    # Risk management
    use_stop_loss: bool = True
    use_take_profit: bool = True
    trailing_stop: bool = False
    trailing_stop_percent: Decimal | None = None

    # Trade filtering
    min_signal_strength: Decimal = Decimal("0.5")
    min_confidence: Decimal = Decimal("0.5")

    # Order settings
    product_type: ProductType = ProductType.DELIVERY
    order_type: OrderType = OrderType.MARKET

    # Universe
    symbols: list[str] = field(default_factory=list)


class TradingStrategy(BaseStrategy):
    """Extended strategy class for algo trading execution.

    This class extends BaseStrategy with methods for:
    - Converting signals to orders
    - Position sizing
    - Entry/exit decision making
    - Trade filtering
    """

    # Additional metadata for trading strategies
    supports_short: bool = False  # Whether strategy can short
    min_data_points: int = 50  # Minimum data points needed

    def __init__(self, config: TradingStrategyConfig | None = None):
        """Initialize with optional trading config."""
        self.config = config or TradingStrategyConfig()

    def should_enter(self, signal: SignalData) -> bool:
        """Determine if we should enter a position based on signal.

        Args:
            signal: The signal to evaluate

        Returns:
            True if entry conditions are met
        """
        # Skip HOLD signals
        if signal.signal_type == SignalType.HOLD:
            return False

        # Check signal quality
        if signal.strength < self.config.min_signal_strength:
            return False

        if signal.confidence < self.config.min_confidence:
            return False

        # For SELL signals, check if shorting is supported
        if signal.signal_type == SignalType.SELL and not self.supports_short:
            return False

        return True

    def should_exit(
        self,
        current_price: Decimal,
        entry_price: Decimal,
        stop_loss: Decimal | None,
        take_profit: Decimal | None,
        signal: SignalData | None = None,
    ) -> tuple[bool, ExitReason | None]:
        """Determine if we should exit an existing position.

        Args:
            current_price: Current market price
            entry_price: Position entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            signal: Optional new signal (opposite signal = exit)

        Returns:
            Tuple of (should_exit, reason)
        """
        # Check stop loss
        if stop_loss and current_price <= stop_loss:
            return True, ExitReason.STOP_LOSS

        # Check take profit
        if take_profit and current_price >= take_profit:
            return True, ExitReason.TAKE_PROFIT

        # Check for opposite signal
        if signal and signal.signal_type == SignalType.SELL:
            return True, ExitReason.SIGNAL

        return False, None

    def create_order_request(
        self,
        signal: SignalData,
        quantity: int,
    ) -> OrderRequest:
        """Create an order request from a signal.

        Args:
            signal: The signal to convert
            quantity: Position size (from position sizer)

        Returns:
            OrderRequest ready to send to broker
        """
        side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL

        return OrderRequest(
            symbol=signal.symbol,
            side=side,
            order_type=self.config.order_type,
            quantity=quantity,
            price=signal.entry_price if self.config.order_type == OrderType.LIMIT else None,
            product_type=self.config.product_type,
            stop_loss=signal.stop_loss if self.config.use_stop_loss else None,
            take_profit=signal.take_profit if self.config.use_take_profit else None,
        )

    def filter_signals(self, signals: list[SignalData]) -> list[SignalData]:
        """Filter signals based on trading config criteria.

        Args:
            signals: List of raw signals from generate_signals()

        Returns:
            Filtered list of actionable signals
        """
        filtered = []
        for signal in signals:
            if self.should_enter(signal):
                filtered.append(signal)
        return filtered
