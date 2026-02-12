"""Research database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base

# Use JSONB for PostgreSQL (production), JSON for SQLite (testing)
# This allows tests to run with SQLite while production uses PostgreSQL's optimized JSONB
JSONType = JSONB().with_variant(JSON(), "sqlite")


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
    # Using JSON instead of ARRAY for SQLite compatibility in tests
    tags: Mapped[list[str] | None] = mapped_column(JSONType, nullable=True, default=list)

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


class DailyDigest(Base):
    """Daily market intelligence digest.

    Generated automatically at market close with:
    - Market summary (index performance)
    - Top gainers and losers
    - Sector performance
    - Volume leaders
    - Breakout candidates
    - News highlights
    """

    __tablename__ = "daily_digests"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Date of the digest (unique per day)
    digest_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, unique=True
    )

    # Market Summary - JSON with index performance
    # {"NIFTY50": {"close": 22000, "change": 0.5}, "BANKNIFTY": {...}, "SENSEX": {...}}
    market_summary: Mapped[dict | None] = mapped_column(JSONType, nullable=True, default=dict)

    # Top Gainers - JSON array with symbol, name, change_pct, reason
    top_gainers: Mapped[list | None] = mapped_column(JSONType, nullable=True, default=list)

    # Top Losers - JSON array with symbol, name, change_pct, reason
    top_losers: Mapped[list | None] = mapped_column(JSONType, nullable=True, default=list)

    # Sector Performance - JSON object with sector -> performance data
    sector_performance: Mapped[dict | None] = mapped_column(JSONType, nullable=True, default=dict)

    # Volume Leaders - JSON array with unusual volume activity
    volume_leaders: Mapped[list | None] = mapped_column(JSONType, nullable=True, default=list)

    # Breakout Candidates - JSON array from breakout screener
    breakout_candidates: Mapped[list | None] = mapped_column(JSONType, nullable=True, default=list)

    # News Highlights - JSON array of top market-moving news
    news_highlights: Mapped[list | None] = mapped_column(JSONType, nullable=True, default=list)

    # Overall market sentiment score (-1.0 to 1.0)
    market_sentiment: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_daily_digests_date", "digest_date"),)

    def __repr__(self) -> str:
        return f"<DailyDigest {self.digest_date.date()}>"
