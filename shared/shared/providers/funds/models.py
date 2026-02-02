"""Shared UserFunds model for database-backed funds management.

This is a standalone model that maps to the user_funds table,
usable by both backend and trading-engine.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UserFundsModel:
    """Mixin class for UserFunds model.

    This provides the column definitions that can be used with any Base class.
    Both backend and trading-engine can create their own models using this mixin.

    Usage:
        from shared.providers.funds.models import UserFundsModel

        class UserFunds(Base, UserFundsModel):
            __tablename__ = "user_funds"
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
