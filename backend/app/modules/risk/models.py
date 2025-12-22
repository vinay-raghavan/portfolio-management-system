"""Risk management database models."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import String, DateTime, Numeric, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class RiskLimits(Base):
    """User-specific risk limits configuration.
    
    Defines trading limits for position sizes, daily losses, etc.
    """

    __tablename__ = "risk_limits"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        unique=True,
        index=True
    )
    
    # Position limits
    max_position_size: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("100000")  # ₹1 Lakh default
    )
    max_position_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("20")  # 20% of portfolio
    )
    max_positions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20  # Max 20 open positions
    )

    # Sector concentration limits
    max_sector_concentration: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("40")  # Max 40% in one sector
    )

    # Daily loss limits
    max_daily_loss: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("50000")  # ₹50K default
    )
    max_daily_loss_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("5")  # 5% of portfolio
    )

    # Intraday limits
    max_intraday_exposure: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("500000")  # ₹5 Lakh default intraday exposure
    )

    # Order limits
    max_order_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("50000")  # ₹50K per order
    )
    max_orders_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50  # Max 50 orders per day
    )

    # Feature flags
    allow_intraday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_short_selling: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_square_off_intraday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # Auto square-off at 3:15 PM
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<RiskLimits user={self.user_id}>"


class DailyRiskMetrics(Base):
    """Daily risk metrics tracking.
    
    Tracks daily trading activity for risk limit enforcement.
    """

    __tablename__ = "daily_risk_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    
    # Daily metrics
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trades_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    total_traded_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    
    # Risk breach flags
    daily_loss_limit_breached: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    position_limit_breached: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # Unique constraint on user_id and date
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<DailyRiskMetrics user={self.user_id} date={self.date}>"

