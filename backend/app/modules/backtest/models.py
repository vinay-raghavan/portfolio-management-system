"""Database models for backtesting module."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BacktestStatus(str, Enum):
    """Status of a backtest run."""

    PENDING = "PENDING"  # Backtest queued for execution
    RUNNING = "RUNNING"  # Backtest currently executing
    COMPLETED = "COMPLETED"  # Backtest finished successfully
    FAILED = "FAILED"  # Backtest failed with error
    CANCELLED = "CANCELLED"  # Backtest was cancelled


class TradeType(str, Enum):
    """Type of trade in a backtest."""

    ENTRY = "ENTRY"
    EXIT = "EXIT"


class TradeSide(str, Enum):
    """Side of a trade."""

    LONG = "LONG"
    SHORT = "SHORT"


class BacktestResult(Base):
    """Backtest result model.

    Stores the overall results of a backtest run including performance metrics.
    """

    __tablename__ = "backtest_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Backtest configuration
    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    strategy_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BacktestStatus.PENDING.value
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Performance metrics
    final_capital: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    total_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )  # As percentage
    annualized_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    sortino_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    calmar_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # Trade statistics
    total_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winning_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    losing_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    profit_factor: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    avg_win: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    avg_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    avg_trade: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    largest_win: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    largest_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    # Equity curve data (stored as JSON for chart rendering)
    equity_curve: Mapped[list | None] = mapped_column(JSON, nullable=True)
    drawdown_curve: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    trades: Mapped[list["BacktestTrade"]] = relationship(
        "BacktestTrade", back_populates="backtest", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_backtest_results_user_id", "user_id"),
        Index("ix_backtest_results_strategy", "strategy_name"),
        Index("ix_backtest_results_status", "status"),
        Index("ix_backtest_results_created_at", "created_at"),
    )


class BacktestTrade(Base):
    """Individual trade within a backtest."""

    __tablename__ = "backtest_trades"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    backtest_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("backtest_results.id", ondelete="CASCADE"), nullable=False
    )

    # Trade details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # LONG or SHORT
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    exit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Trade results
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    is_winner: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Additional info
    signal_indicators: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # SL, TP, SIGNAL, etc.

    # Relationship
    backtest: Mapped["BacktestResult"] = relationship("BacktestResult", back_populates="trades")

    __table_args__ = (
        Index("ix_backtest_trades_backtest_id", "backtest_id"),
        Index("ix_backtest_trades_entry_date", "entry_date"),
    )
