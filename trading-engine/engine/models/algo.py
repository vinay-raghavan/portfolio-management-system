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

from engine.core.database import Base


class User(Base):
    """Minimal User model for foreign key references.

    This is a read-only model that mirrors the backend's User table.
    The trading engine only needs this for foreign key relationships.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class StrategyStatus(str, Enum):
    """Strategy status enum."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"
    KILLED = "KILLED"


class ScheduleType(str, Enum):
    """Schedule type for strategy execution."""

    INTERVAL = "INTERVAL"
    CRON = "CRON"
    MARKET_OPEN = "MARKET_OPEN"
    MARKET_CLOSE = "MARKET_CLOSE"
    CONTINUOUS = "CONTINUOUS"


class PositionSizingMethod(str, Enum):
    """Position sizing method enum."""

    FIXED_QUANTITY = "FIXED_QUANTITY"
    FIXED_AMOUNT = "FIXED_AMOUNT"
    PERCENT_OF_PORTFOLIO = "PERCENT_OF_PORTFOLIO"
    RISK_BASED = "RISK_BASED"
    VOLATILITY_ADJUSTED = "VOLATILITY_ADJUSTED"


class ExecutionStatus(str, Enum):
    """Execution status enum."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NO_SIGNAL = "NO_SIGNAL"
    RISK_BLOCKED = "RISK_BLOCKED"
    SKIPPED = "SKIPPED"


class UserStrategy(Base):
    """User's configured strategy for algo trading."""

    __tablename__ = "user_strategies"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False)

    status: Mapped[StrategyStatus] = mapped_column(
        SQLEnum(StrategyStatus, name="strategystatus", create_type=False),
        nullable=False,
        default=StrategyStatus.DISABLED,
    )
    is_paper_trading: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    strategy_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    schedule_type: Mapped[ScheduleType] = mapped_column(
        SQLEnum(ScheduleType, name="scheduletype", create_type=False),
        nullable=False,
        default=ScheduleType.MARKET_OPEN,
    )
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cron_expression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")

    universe_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("universes.id", ondelete="SET NULL"), nullable=True
    )
    custom_symbols: Mapped[list | None] = mapped_column(JSON, nullable=True)

    position_sizing_method: Mapped[PositionSizingMethod] = mapped_column(
        SQLEnum(PositionSizingMethod, name="positionsizingmethod", create_type=False),
        nullable=False,
        default=PositionSizingMethod.PERCENT_OF_PORTFOLIO,
    )
    fixed_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    portfolio_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("5.00")
    )
    risk_per_trade_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("2.00")
    )
    max_position_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    max_daily_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_daily_loss: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("5000.00")
    )
    max_open_positions: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    max_consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_drawdown_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("10.00")
    )

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    consecutive_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

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


class StrategyExecution(Base):
    """Record of a strategy execution."""

    __tablename__ = "strategy_executions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("user_strategies.id", ondelete="CASCADE"), nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus, name="executionstatus", create_type=False),
        nullable=False,
        default=ExecutionStatus.RUNNING,
    )

    symbols_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signals_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_placed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_filled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    signals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    orders: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_log: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    strategy: Mapped["UserStrategy"] = relationship("UserStrategy", back_populates="executions")

    __table_args__ = (
        Index("ix_strategy_executions_strategy_started", "strategy_id", "started_at"),
        Index("ix_strategy_executions_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<StrategyExecution {self.id[:8]} [{self.status}]>"


class Universe(Base):
    """Stock universe for strategy screening."""

    __tablename__ = "universes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    symbols: Mapped[list | None] = mapped_column(JSON, nullable=True)
    filter_criteria: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    strategies: Mapped[list["UserStrategy"]] = relationship("UserStrategy", back_populates="universe")

    __table_args__ = (Index("ix_universes_user", "user_id"),)

    def __repr__(self) -> str:
        return f"<Universe {self.name} ({len(self.symbols or [])} symbols)>"

