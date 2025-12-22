"""Trading/Order database models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import String, DateTime, Numeric, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class OrderSide(str, Enum):
    """Order side enum."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type enum."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"  # Stop Loss Limit
    STOP_LOSS_MARKET = "SL-M"  # Stop Loss Market
    TAKE_PROFIT = "TAKE_PROFIT"
    GTT = "GTT"  # Good Till Triggered


class OrderStatus(str, Enum):
    """Order status enum."""

    PENDING = "PENDING"
    OPEN = "OPEN"  # Active limit/SL order waiting to trigger
    TRIGGERED = "TRIGGERED"  # GTT/SL triggered, awaiting execution
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    AMO_PENDING = "AMO_PENDING"  # After Market Order - queued for next session


class Order(Base):
    """Order model for paper trading."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False, default="MARKET")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    trigger_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)  # For SL/SL-M/GTT orders
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"))
    filled_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # GTT specific fields
    valid_till: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # For GTT orders
    parent_order_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)  # For SL/TP linked orders

    # AMO (After Market Order) fields
    is_amo: Mapped[bool] = mapped_column(nullable=False, default=False)  # True if this is an after-market order
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # When AMO should execute

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # When SL/GTT was triggered

    __table_args__ = (
        Index("ix_orders_user_status", "user_id", "status"),
        Index("ix_orders_user_created", "user_id", "created_at"),
        Index("ix_orders_open_trigger", "status", "trigger_price"),  # For efficient SL/GTT monitoring
    )

    def __repr__(self) -> str:
        return f"<Order {self.side} {self.quantity} {self.symbol} @ {self.price} [{self.status}]>"

