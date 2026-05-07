"""Database models for algo trading module."""

from datetime import datetime, time
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.screener.models import CustomScreener


class StrategyStatus(str, Enum):
    """Strategy status enum."""

    ACTIVE = "ACTIVE"  # Running on schedule
    PAUSED = "PAUSED"  # Temporarily paused
    DISABLED = "DISABLED"  # Manually disabled
    ERROR = "ERROR"  # Stopped due to error
    KILLED = "KILLED"  # Stopped by kill switch


class ProfitCutoffAction(str, Enum):
    """Action to take when profit cutoff is reached."""

    PAUSE_STRATEGY = "PAUSE_STRATEGY"  # Pause strategy for the day/overall
    CLOSE_POSITIONS_AND_PAUSE = "CLOSE_POSITIONS_AND_PAUSE"  # Close positions and pause
    CLOSE_POSITIONS_AND_CONTINUE = (
        "CLOSE_POSITIONS_AND_CONTINUE"  # Close positions, reset, keep trading
    )
    NOTIFY_ONLY = "NOTIFY_ONLY"  # Only send notification, continue trading


class ScheduleType(str, Enum):
    """Schedule type for strategy execution."""

    INTERVAL = "INTERVAL"  # Run every N seconds/minutes
    CRON = "CRON"  # Cron expression
    MARKET_OPEN = "MARKET_OPEN"  # Run at market open
    MARKET_CLOSE = "MARKET_CLOSE"  # Run before market close
    CONTINUOUS = "CONTINUOUS"  # Run continuously during market hours


class PositionSizingMethod(str, Enum):
    """Position sizing method enum."""

    FIXED_QUANTITY = "FIXED_QUANTITY"  # Fixed number of shares
    FIXED_AMOUNT = "FIXED_AMOUNT"  # Fixed rupee amount
    PERCENT_OF_PORTFOLIO = "PERCENT_OF_PORTFOLIO"  # Percentage of portfolio
    RISK_BASED = "RISK_BASED"  # Based on stop loss and risk per trade
    VOLATILITY_ADJUSTED = "VOLATILITY_ADJUSTED"  # ATR-based sizing


class ExecutionStatus(str, Enum):
    """Execution status enum."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_SIGNAL = "NO_SIGNAL"
    RISK_BLOCKED = "RISK_BLOCKED"
    SKIPPED = "SKIPPED"


class StrategyProductType(str, Enum):
    """Product type for strategy orders (matches broker terminology).

    Rules:
    - DELIVERY (CNC): Full payment required, no shorting, hold indefinitely
    - INTRADAY (MIS): Margin required (25%), shorting allowed, must square off same day
    - MARGIN (MTF): Margin required (50%), no shorting, leveraged buying with interest
    - SLB: Securities Lending & Borrowing, multi-day shorting with borrowing fee
    """

    DELIVERY = "DELIVERY"  # CNC - Cash and Carry (no leverage, no shorting)
    INTRADAY = "INTRADAY"  # MIS - Margin Intraday Square-off (leverage + shorting)
    MARGIN = "MARGIN"  # MTF - Margin Trading Facility (leverage, no shorting)
    SLB = "SLB"  # Securities Lending & Borrowing (multi-day short selling)


class SignalDirection(str, Enum):
    """Direction of signals the strategy will generate.

    - LONG: Only generate BUY signals (go long)
    - SHORT: Only generate SELL signals to open short positions (requires INTRADAY/SLB)
    - BOTH: Generate both LONG and SHORT signals based on market conditions
    """

    LONG = "LONG"  # Only long positions (default, safest)
    SHORT = "SHORT"  # Only short positions (requires INTRADAY or SLB)
    BOTH = "BOTH"  # Both directions (requires INTRADAY or SLB)


class PortfolioSafetyThresholdType(str, Enum):
    """Threshold type for portfolio-level safety trigger."""

    PERCENT = "PERCENT"
    AMOUNT = "AMOUNT"


class PortfolioSafetyActionMode(str, Enum):
    """Action mode when portfolio safety threshold is breached."""

    PAUSE_ONLY = "PAUSE_ONLY"
    PAUSE_AND_SQUARE_OFF = "PAUSE_AND_SQUARE_OFF"


class PortfolioSafetyConfig(Base):
    """User-level portfolio safety guardrail configuration."""

    __tablename__ = "portfolio_safety_configs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Guardrail configuration
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    threshold_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PortfolioSafetyThresholdType.PERCENT.value,
    )
    threshold_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("5.00"),
    )
    action_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=PortfolioSafetyActionMode.PAUSE_ONLY.value,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<PortfolioSafetyConfig user={self.user_id} enabled={self.enabled} "
            f"type={self.threshold_type} value={self.threshold_value}>"
        )


class UserStrategy(Base):
    """User's configured strategy for algo trading.

    Stores the strategy configuration, schedule, and trading parameters.
    """

    __tablename__ = "user_strategies"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Strategy identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # References StrategyRegistry

    # Status
    status: Mapped[StrategyStatus] = mapped_column(
        SQLEnum(StrategyStatus, name="strategystatus", create_type=False),
        nullable=False,
        default=StrategyStatus.DISABLED,
    )
    is_paper_trading: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Product type for orders (CNC/MIS/MTF)
    product_type: Mapped[StrategyProductType] = mapped_column(
        SQLEnum(StrategyProductType, name="strategyproducttype", create_type=False),
        nullable=False,
        default=StrategyProductType.DELIVERY,
    )

    # Signal direction (LONG/SHORT/BOTH)
    signal_direction: Mapped[SignalDirection] = mapped_column(
        SQLEnum(SignalDirection, name="signaldirection", create_type=False),
        nullable=False,
        default=SignalDirection.LONG,
    )

    # Strategy parameters (stored as JSON for flexibility)
    strategy_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Schedule configuration
    schedule_type: Mapped[ScheduleType] = mapped_column(
        SQLEnum(ScheduleType, name="scheduletype", create_type=False),
        nullable=False,
        default=ScheduleType.MARKET_OPEN,
    )
    interval_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # For INTERVAL type
    cron_expression: Mapped[str | None] = mapped_column(String(100), nullable=True)  # For CRON type
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")

    # Trading time window (optional restriction on when strategy can execute)
    trading_start_time: Mapped[time | None] = mapped_column(Time, nullable=True)  # e.g., 09:45:00
    trading_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)  # e.g., 15:15:00
    trading_timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Asia/Kolkata"
    )  # IANA timezone
    active_trading_days: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=[0, 1, 2, 3, 4]
    )  # Monday=0, Sunday=6

    # Universe (symbols to trade)
    universe_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("universes.id", ondelete="SET NULL"), nullable=True
    )
    custom_symbols: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # Override universe with custom list

    # Exit-only symbols: symbols with open positions that should only be exited, not entered
    # Used when screener updates remove symbols that still have open positions
    exit_only_symbols: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Position sizing
    position_sizing_method: Mapped[PositionSizingMethod] = mapped_column(
        SQLEnum(PositionSizingMethod, name="positionsizingmethod", create_type=False),
        nullable=False,
        default=PositionSizingMethod.PERCENT_OF_PORTFOLIO,
    )
    fixed_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    portfolio_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("5.00")
    )  # 5%
    risk_per_trade_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("2.00")
    )  # 2%
    max_position_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Risk controls per strategy
    max_daily_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_daily_loss: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("5000.00")
    )
    max_open_positions: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    cooldown_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )  # Min time between trades

    # Circuit breaker settings
    max_consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_drawdown_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("10.00")
    )
    # Max unrealized loss (absolute value) - triggers circuit breaker when open positions are down
    max_unrealized_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Profit cutoff settings
    max_daily_profit: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True, default=None
    )  # Stop trading for the day after this profit (e.g., ₹20,000)
    overall_profit_target: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True, default=None
    )  # Optional: lifetime target for the strategy
    profit_cutoff_action: Mapped[ProfitCutoffAction] = mapped_column(
        SQLEnum(ProfitCutoffAction, name="profitcutoffaction", create_type=False),
        nullable=False,
        default=ProfitCutoffAction.PAUSE_STRATEGY,
    )

    # Strategy-level default fixed stop loss / take profit (applied to positions)
    default_stop_loss_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Fixed stop loss percentage as decimal (e.g., 0.02 = 2%)
    default_take_profit_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Fixed take profit percentage as decimal (e.g., 0.04 = 4%)

    # Strategy-level default trailing stop settings (applied to positions unless overridden)
    default_trailing_stop_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    default_trailing_stop_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Default trailing stop percentage (e.g., 0.05 = 5%)

    # Strategy-level default profit booking rules (applied to positions unless overridden)
    default_profit_booking_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Strategy-level default profit lock setting
    # When enabled, uses first profit_booking_rule threshold to lock stop at profit level
    default_profit_lock_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Tracking
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Screener linking - for strategies created via auto-trade
    # When linked, screener master settings override on each auto-trade run
    linked_screener_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("custom_screeners.id", ondelete="SET NULL"),
        nullable=True,
    )
    sync_from_screener: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )  # If False, strategy settings are independent

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    universe: Mapped["Universe | None"] = relationship("Universe", back_populates="strategies")
    executions: Mapped[list["StrategyExecution"]] = relationship(
        "StrategyExecution", back_populates="strategy", cascade="all, delete-orphan"
    )
    linked_screener: Mapped["CustomScreener | None"] = relationship(
        "CustomScreener",
        foreign_keys=[linked_screener_id],
        back_populates="linked_strategies",
    )

    __table_args__ = (
        Index("ix_user_strategies_user_status", "user_id", "status"),
        Index("ix_user_strategies_next_run", "status", "next_run_at"),
        Index("ix_user_strategies_linked_screener", "linked_screener_id"),
    )

    def __repr__(self) -> str:
        return f"<UserStrategy {self.name} ({self.strategy_name}) [{self.status}]>"


class Universe(Base):
    """Universe of symbols for strategy trading.

    Predefined or custom groups of symbols that strategies can trade.
    """

    __tablename__ = "universes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )  # NULL for system universes

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Static symbols list
    symbols: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Dynamic filter criteria (for dynamic universes)
    filter_criteria: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    strategies: Mapped[list["UserStrategy"]] = relationship(
        "UserStrategy", back_populates="universe"
    )

    __table_args__ = (Index("ix_universes_user", "user_id"),)

    def __repr__(self) -> str:
        return f"<Universe {self.name} ({len(self.symbols or [])} symbols)>"


class StrategyExecution(Base):
    """Log of strategy execution runs.

    Records each time a strategy is run, signals generated, and orders placed.
    """

    __tablename__ = "strategy_executions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("user_strategies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Execution status
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus, name="executionstatus", create_type=False),
        nullable=False,
        default=ExecutionStatus.RUNNING,
    )

    # Execution timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Results
    symbols_analyzed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signals_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_placed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_filled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # P&L tracking for this execution
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    total_order_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    positions_opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    positions_closed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Details stored as JSON
    signals_data: Mapped[list | None] = mapped_column(JSON, nullable=True)
    orders_data: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_log: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Relationships
    strategy: Mapped["UserStrategy"] = relationship("UserStrategy", back_populates="executions")
    algo_orders: Mapped[list["AlgoOrder"]] = relationship(
        "AlgoOrder", back_populates="execution", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_strategy_executions_strategy", "strategy_id", "started_at"),
        Index("ix_strategy_executions_user", "user_id", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<StrategyExecution {self.strategy_id} [{self.status}] signals={self.signals_generated}>"


class AlgoOrder(Base):
    """Orders placed by algo trading strategies.

    Links orders to strategy executions for tracking.
    """

    __tablename__ = "algo_orders"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    execution_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("strategy_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    signal_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("signals.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("user_strategies.id", ondelete="CASCADE"), nullable=False
    )

    # Order details snapshot
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    # Filled/execution details
    order_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    filled_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filled_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    order_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Signal info
    signal_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    signal_strength: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    # Position sizing info
    sizing_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    calculated_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    execution: Mapped["StrategyExecution"] = relationship(
        "StrategyExecution", back_populates="algo_orders"
    )

    __table_args__ = (
        Index("ix_algo_orders_execution", "execution_id"),
        Index("ix_algo_orders_strategy", "strategy_id", "created_at"),
        Index("ix_algo_orders_user", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AlgoOrder {self.side} {self.quantity} {self.symbol}>"


class PositionSide(str, Enum):
    """Position side enum."""

    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(str, Enum):
    """Position status enum."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"


class AlgoPosition(Base):
    """Track open positions for algo strategies.

    This tracks positions opened by algo strategies to calculate P&L.
    When a BUY signal opens a position, we track entry price.
    When a SELL signal closes it, we calculate realized P&L.
    """

    __tablename__ = "algo_positions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("user_strategies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[PositionSide] = mapped_column(
        SQLEnum(PositionSide, name="positionside", create_type=False),
        nullable=False,
        default=PositionSide.LONG,
    )
    status: Mapped[PositionStatus] = mapped_column(
        SQLEnum(PositionStatus, name="positionstatus", create_type=False),
        nullable=False,
        default=PositionStatus.OPEN,
    )

    # Product type at time of position opening (to ensure correct margin handling on close)
    product_type: Mapped[StrategyProductType | None] = mapped_column(
        SQLEnum(StrategyProductType, name="strategyproducttype", create_type=False),
        nullable=True,  # Nullable for backward compatibility with existing positions
    )

    # Entry details
    entry_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    entry_order_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Exit details (filled when position is closed)
    exit_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    exit_order_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Remaining quantity for partial closes
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # P&L calculation
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    realized_pnl_percent: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0")
    )
    is_winner: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Risk management
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    # Trailing stop loss fields
    trailing_stop_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trailing_stop_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # Percentage distance from high/low price (e.g., 0.05 = 5%)
    trailing_stop_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )  # Current calculated trailing stop price
    highest_price_since_entry: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )  # Track highest price for LONG positions
    lowest_price_since_entry: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )  # Track lowest price for SHORT positions

    # Profit booking rules
    profit_booking_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Profit lock stop loss fields
    # Uses first profit_booking_rule threshold to lock stop at profit level
    profit_lock_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    profit_lock_activated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Whether profit threshold has been reached
    profit_lock_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )  # The locked profit price level (effective stop)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_algo_positions_strategy_status", "strategy_id", "status"),
        Index("ix_algo_positions_user_symbol", "user_id", "symbol", "status"),
        Index("ix_algo_positions_open", "status", "symbol"),
    )

    # Relationship to SLB position (if opened via SLB)
    slb_position = relationship("SLBPosition", back_populates="algo_position", uselist=False)

    def __repr__(self) -> str:
        return f"<AlgoPosition {self.side.value} {self.entry_quantity} {self.symbol} @ {self.entry_price} [{self.status.value}]>"


class CircuitBreakerState(Base):
    """Persisted circuit breaker state for a strategy.

    Stores the current state of the circuit breaker for recovery after restarts.
    The primary source of truth during operation is Redis for low latency.
    This table is synced periodically and on triggers for persistence.
    """

    __tablename__ = "circuit_breaker_states"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("user_strategies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One state per strategy
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Circuit breaker status
    is_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trigger_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Daily tracking (resets at midnight)
    daily_loss: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    daily_profit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Overall profit tracking (persists across days)
    overall_profit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    profit_cutoff_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Tracking date for daily reset detection
    tracking_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Sync timestamps
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<CircuitBreakerState strategy={self.strategy_id} triggered={self.is_triggered}>"


class CircuitBreakerHistory(Base):
    """Historical record of circuit breaker events.

    Records each time a circuit breaker is triggered or reset for audit trail.
    """

    __tablename__ = "circuit_breaker_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("user_strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Event details
    event_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # TRIGGERED, RESET, DAILY_RESET
    trigger_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # State at time of event
    daily_loss: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    daily_profit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overall_profit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )

    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_cb_history_strategy_event", "strategy_id", "event_at"),)

    def __repr__(self) -> str:
        return f"<CircuitBreakerHistory {self.event_type} strategy={self.strategy_id} at={self.event_at}>"


# =============================================================================
# Auto-Trade Configuration Models
# =============================================================================


class ConfirmationMode(str, Enum):
    """Confirmation mode for auto-trade execution."""

    AUTO = "auto"  # Execute immediately without confirmation
    NOTIFY = "notify"  # Create pending, notify user, await confirmation
    DISABLED = "disabled"  # Don't auto-trade this category


class ScreenerSourceType(str, Enum):
    """Source type for auto-trade screener."""

    PRESET = "preset"  # Use daily preset recommendations
    CUSTOM = "custom"  # Use saved custom screener


class PendingTradeStatus(str, Enum):
    """Status of a pending auto-trade."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


class StrategyTemplate(Base):
    """Reusable strategy configurations for auto-trade.

    Users can create templates with predefined position sizing, risk limits,
    and trading windows to quickly apply to auto-trade generated strategies.
    """

    __tablename__ = "strategy_templates"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Template info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Strategy execution params
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    strategy_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Position sizing
    position_sizing_method: Mapped[PositionSizingMethod] = mapped_column(
        SQLEnum(PositionSizingMethod, name="positionsizingmethod", create_type=False),
        nullable=False,
        default=PositionSizingMethod.PERCENT_OF_PORTFOLIO,
    )
    position_size_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("5.00")
    )
    max_position_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Risk limits
    stop_loss_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("2.00")
    )
    take_profit_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("4.00")
    )
    max_daily_loss: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("5000.00")
    )
    max_consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Product type
    product_type: Mapped[StrategyProductType] = mapped_column(
        SQLEnum(StrategyProductType, name="strategyproducttype", create_type=False),
        nullable=False,
        default=StrategyProductType.DELIVERY,
    )

    # Trading window (restrict execution to specific hours)
    trading_start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trading_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Default template flag
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_strategy_templates_user", "user_id"),)

    def __repr__(self) -> str:
        return f"<StrategyTemplate {self.name} user={self.user_id}>"


class AutoTradeConfig(Base):
    """Configuration for automatic trade execution from screener recommendations.

    Users configure how recommendations from each category (momentum, breakout, etc.)
    should be handled: auto-execute, notify for approval, or disabled.
    """

    __tablename__ = "auto_trade_configs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Category (momentum, breakout, value, sector) or custom
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # Enabled and confirmation mode
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmation_mode: Mapped[ConfirmationMode] = mapped_column(
        SQLEnum(
            ConfirmationMode,
            name="confirmationmode",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ConfirmationMode.NOTIFY,
    )

    # Link to strategy template for execution params
    strategy_template_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("strategy_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Daily limits for this category
    max_positions_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_capital_per_day: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("50000.00")
    )

    # Auto-expiry for pending trades
    expiry_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    # Multi-factor weights (0-100, converted to 0-1 for calculations)
    weight_technical: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    weight_fundamental: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    weight_sentiment: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    # Minimum confidence to auto-trade
    min_confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")

    # Screener source selection (from Section 2.6.12.5)
    screener_source_type: Mapped[ScreenerSourceType] = mapped_column(
        SQLEnum(
            ScreenerSourceType,
            name="screenersourcetype",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ScreenerSourceType.PRESET,
    )

    # If PRESET: which category (momentum, breakout, value, sector)
    preset_category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # If CUSTOM: which saved screener
    saved_screener_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("custom_screeners.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Schedule settings for when to run the screener
    run_time: Mapped[str | None] = mapped_column(
        String(5), nullable=True, default="09:20"
    )  # HH:MM format, e.g., "09:20" for 9:20 AM IST

    # Product type for created strategies (DELIVERY, INTRADAY, MARGIN, SLB)
    product_type: Mapped[StrategyProductType] = mapped_column(
        SQLEnum(
            StrategyProductType,
            name="strategyproducttype",
            create_type=False,  # Already exists from user_strategies
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=StrategyProductType.INTRADAY,
    )

    # Signal direction for created strategies (LONG, SHORT, BOTH)
    signal_direction: Mapped[SignalDirection] = mapped_column(
        SQLEnum(
            SignalDirection,
            name="signaldirection",
            create_type=False,  # Already exists from user_strategies
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SignalDirection.LONG,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    strategy_template = relationship("StrategyTemplate", foreign_keys=[strategy_template_id])

    __table_args__ = (
        Index("ix_auto_trade_configs_user", "user_id"),
        Index("ix_auto_trade_configs_category", "user_id", "category", unique=True),
    )

    @property
    def weights_normalized(self) -> dict[str, float]:
        """Return weights as decimals (0-1) for calculations."""
        return {
            "technical": self.weight_technical / 100,
            "fundamental": self.weight_fundamental / 100,
            "sentiment": self.weight_sentiment / 100,
        }

    def __repr__(self) -> str:
        return f"<AutoTradeConfig {self.category} user={self.user_id} enabled={self.enabled}>"


class PendingAutoTrade(Base):
    """Queue for pending auto-trade executions awaiting user confirmation.

    When confirmation_mode is NOTIFY, recommendations are queued here
    for user approval before execution.
    """

    __tablename__ = "pending_auto_trades"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    auto_trade_config_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("auto_trade_configs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Source recommendation
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    recommendation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbols: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Multi-factor scores (optional, if scoring was applied)
    scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Inferred strategy details
    recommended_strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    suggested_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[PendingTradeStatus] = mapped_column(
        SQLEnum(
            PendingTradeStatus,
            name="pendingtradestatus",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=PendingTradeStatus.PENDING,
    )

    # If executed, link to created strategy
    created_strategy_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("user_strategies.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timing
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    auto_trade_config = relationship("AutoTradeConfig", foreign_keys=[auto_trade_config_id])
    created_strategy = relationship("UserStrategy", foreign_keys=[created_strategy_id])

    __table_args__ = (
        Index("ix_pending_auto_trades_user", "user_id"),
        Index("ix_pending_auto_trades_status", "status"),
        Index("ix_pending_auto_trades_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<PendingAutoTrade {self.id} status={self.status} category={self.category}>"


class SLBPositionStatus(str, Enum):
    """Status of an SLB borrowing position."""

    ACTIVE = "ACTIVE"  # Securities borrowed and short position active
    RETURNED = "RETURNED"  # Securities returned to lender, position closed
    DEFAULTED = "DEFAULTED"  # Failed to return by due date (penalty applies)


class SLBPosition(Base):
    """Track Securities Lending & Borrowing positions.

    When a user opens a short position using SLB:
    1. Securities are borrowed from the market via SLB mechanism
    2. Borrowed securities are sold to open the short
    3. Daily borrowing fee accrues based on borrow_rate
    4. When closing, securities are bought back and returned to lender

    This model tracks the SLB-specific details separate from the AlgoPosition
    to handle borrowing fees, return dates, and SLB lifecycle.
    """

    __tablename__ = "slb_positions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    algo_position_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("algo_positions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Borrowing details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    borrow_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    return_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,  # Must return by this date
    )

    # Fee details (annualized rate, converted to daily)
    borrow_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,  # Annualized rate, e.g., 0.05 = 5%
    )
    daily_fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,  # Daily fee amount in currency
    )
    total_fee_accrued: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )

    # Status tracking
    status: Mapped[SLBPositionStatus] = mapped_column(
        SQLEnum(SLBPositionStatus, name="slbpositionstatus", create_type=False),
        nullable=False,
        default=SLBPositionStatus.ACTIVE,
    )

    # Broker reference for SLB position
    broker_slb_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="slb_positions")
    algo_position = relationship("AlgoPosition", back_populates="slb_position")

    __table_args__ = (
        Index("ix_slb_positions_user", "user_id"),
        Index("ix_slb_positions_symbol", "symbol"),
        Index("ix_slb_positions_status", "status"),
        Index("ix_slb_positions_return_date", "return_date"),
    )

    def __repr__(self) -> str:
        return f"<SLBPosition {self.symbol} qty={self.quantity} status={self.status}>"
