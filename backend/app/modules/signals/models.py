"""Signal database models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class SignalType(str, Enum):
    """Signal type enum."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStatus(str, Enum):
    """Signal status enum."""

    PENDING = "PENDING"  # Signal is awaiting action
    ACTIVE = "ACTIVE"  # Signal is still valid
    EXPIRED = "EXPIRED"  # Signal has expired
    EXECUTED = "EXECUTED"  # Signal was acted upon
    CANCELLED = "CANCELLED"  # Signal was manually cancelled


class Signal(Base):
    """Trading signal model.

    Stores generated trading signals from various strategies.
    Can be linked to orders when the signal is executed.
    """

    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Signal identification
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    signal_type: Mapped[SignalType] = mapped_column(
        SQLEnum(SignalType, name="signaltype", create_type=False), nullable=False
    )
    status: Mapped[SignalStatus] = mapped_column(
        SQLEnum(SignalStatus, name="signalstatus", create_type=False),
        nullable=False,
        default=SignalStatus.PENDING,
    )

    # Signal quality metrics
    strength: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)  # 0.0000 to 1.0000
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)  # 0.0000 to 1.0000

    # Strategy that generated this signal
    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")

    # Price levels
    price_at_signal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    # Risk/Reward
    risk_reward_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Supporting indicator data (stored as JSON)
    indicators: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Notes/reasoning for the signal
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution tracking
    is_executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    executed_order_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_signals_user_status", "user_id", "status"),
        Index("ix_signals_user_symbol", "user_id", "symbol"),
        Index("ix_signals_user_generated", "user_id", "generated_at"),
        Index("ix_signals_strategy", "strategy_name", "generated_at"),
        Index("ix_signals_active", "status", "expires_at"),  # For expiration cleanup
    )

    def __repr__(self) -> str:
        return f"<Signal {self.signal_type} {self.symbol} ({self.strategy_name}) strength={self.strength}>"
