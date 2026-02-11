"""Research database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class ResearchNote(Base):
    """User research notes for stocks.

    Allows users to save personal research notes, ratings, and target prices
    for individual stocks they are researching.
    """

    __tablename__ = "research_notes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Rating: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    rating: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Target price for the stock
    target_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Tags for categorization (e.g., "value", "growth", "dividend")
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(50)), nullable=True, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_research_notes_user", "user_id"),
        Index("ix_research_notes_symbol", "symbol"),
        Index("ix_research_notes_user_symbol", "user_id", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<ResearchNote {self.symbol}: {self.title}>"

