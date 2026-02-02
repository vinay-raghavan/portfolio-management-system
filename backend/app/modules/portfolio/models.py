"""Portfolio database models."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ProductType(str, Enum):
    """Product type for positions."""

    DELIVERY = "DELIVERY"  # CNC - Cash and Carry (overnight holding)
    INTRADAY = "INTRADAY"  # MIS - Margin Intraday Square-off


class Portfolio(Base):
    """Portfolio model for organizing positions into separate portfolios."""

    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Portfolio-level settings
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    positions: Mapped[list["Position"]] = relationship(
        "Position", back_populates="portfolio", cascade="all, delete-orphan"
    )
    trades: Mapped[list["Trade"]] = relationship(
        "Trade", back_populates="portfolio", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_portfolios_user", "user_id"),
        Index("ix_portfolios_user_default", "user_id", "is_default"),
    )

    def __repr__(self) -> str:
        return f"<Portfolio {self.name} (user={self.user_id})>"


class Position(Base):
    """Portfolio position model."""

    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    portfolio_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    # New fields for enhanced position tracking
    product_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default=ProductType.DELIVERY.value
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )

    # Position-level stop loss and take profit
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

    # Profit booking rules (percentage-based)
    profit_booking_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Sector classification for concentration tracking
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    portfolio: Mapped["Portfolio | None"] = relationship("Portfolio", back_populates="positions")

    __table_args__ = (
        Index("ix_positions_portfolio_symbol", "portfolio_id", "symbol", unique=True),
        Index("ix_positions_user_symbol", "user_id", "symbol"),
        Index("ix_positions_user_product", "user_id", "product_type"),
        Index("ix_positions_user_sector", "user_id", "sector"),
    )

    def __repr__(self) -> str:
        return f"<Position {self.symbol}: {self.quantity} ({self.product_type})>"


class UserFunds(Base):
    """User funds/balance model for paper trading.

    Tracks virtual cash balance, margin usage, and collateral.
    """

    __tablename__ = "user_funds"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Cash available for trading
    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )

    # Margin blocked for open positions/orders
    margin_used: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )

    # Stock collateral value (for margin trading - future use)
    collateral: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def available_cash(self) -> Decimal:
        """Calculate available cash (balance - margin used)."""
        return self.cash_balance - self.margin_used

    @property
    def total_balance(self) -> Decimal:
        """Calculate total balance including collateral."""
        return self.cash_balance + self.collateral

    @property
    def available_margin(self) -> Decimal:
        """Calculate available margin for new positions."""
        return self.cash_balance + self.collateral - self.margin_used

    def __repr__(self) -> str:
        return f"<UserFunds user={self.user_id} cash={self.cash_balance}>"


class DailyPnL(Base):
    """Daily P&L snapshot for tracking performance over time.

    Captures end-of-day portfolio state for historical analysis.
    """

    __tablename__ = "daily_pnl"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Date of the snapshot
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Portfolio values at end of day
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    # Cash balance at end of day
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    # Daily change
    day_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))

    # Number of trades executed that day
    trades_count: Mapped[int] = mapped_column(nullable=False, default=0)

    # Snapshot of positions as JSON for historical reference
    positions_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_daily_pnl_user_date", "user_id", "date", unique=True),)


class Trade(Base):
    """Trade history model."""

    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    portfolio_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY or SELL
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    portfolio: Mapped["Portfolio | None"] = relationship("Portfolio", back_populates="trades")

    __table_args__ = (
        Index("ix_trades_user_executed", "user_id", "executed_at"),
        Index("ix_trades_portfolio_executed", "portfolio_id", "executed_at"),
    )

    def __repr__(self) -> str:
        return f"<Trade {self.side} {self.quantity} {self.symbol} @ {self.price}>"


class CostLot(Base):
    """Cost lot for FIFO average price tracking.

    Each buy creates a new lot. Sells consume lots in FIFO order.
    """

    __tablename__ = "cost_lots"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    portfolio_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Original purchase details
    original_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    # Reference to the buy trade that created this lot
    trade_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("trades.id", ondelete="SET NULL"), nullable=True
    )

    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_cost_lots_user_symbol", "user_id", "symbol"),
        Index("ix_cost_lots_portfolio_symbol", "portfolio_id", "symbol"),
        Index("ix_cost_lots_fifo", "user_id", "symbol", "purchased_at"),  # For FIFO ordering
    )

    def __repr__(self) -> str:
        return f"<CostLot {self.symbol}: {self.remaining_quantity}/{self.original_quantity} @ {self.purchase_price}>"
