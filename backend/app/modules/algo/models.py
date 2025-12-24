"""Database models for algo trading module."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class StrategyStatus(str, Enum):
    """Strategy status enum."""

    ACTIVE = "ACTIVE"  # Running on schedule
    PAUSED = "PAUSED"  # Temporarily paused
    DISABLED = "DISABLED"  # Manually disabled
    ERROR = "ERROR"  # Stopped due to error
    KILLED = "KILLED"  # Stopped by kill switch


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

    # Universe (symbols to trade)
    universe_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("universes.id", ondelete="SET NULL"), nullable=True
    )
    custom_symbols: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # Override universe with custom list

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

    # Tracking
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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

    __table_args__ = (
        Index("ix_user_strategies_user_status", "user_id", "status"),
        Index("ix_user_strategies_next_run", "status", "next_run_at"),
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
    order_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
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
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    realized_pnl_percent: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))
    is_winner: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Risk management
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_algo_positions_strategy_status", "strategy_id", "status"),
        Index("ix_algo_positions_user_symbol", "user_id", "symbol", "status"),
        Index("ix_algo_positions_open", "status", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<AlgoPosition {self.side.value} {self.entry_quantity} {self.symbol} @ {self.entry_price} [{self.status.value}]>"
