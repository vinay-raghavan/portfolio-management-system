"""Screener database models."""

from datetime import datetime, time
from enum import Enum as PyEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.algo.models import UserStrategy

# Use JSONB for PostgreSQL (production), JSON for SQLite (testing)
# This allows tests to run with SQLite while production uses PostgreSQL's optimized JSONB
JSONType = JSONB().with_variant(JSON(), "sqlite")


class RunFrequency(str, PyEnum):
    """Frequency for scheduled screener runs."""

    DAILY = "daily"
    HOURLY = "hourly"
    MANUAL = "manual"


class CustomScreener(Base):
    """User-defined custom screener configuration.

    Supports both manual screener runs and auto-trade integration.
    When linked to auto-trade, the screener runs on schedule and
    feeds results into the auto-trade pipeline.
    """

    __tablename__ = "custom_screeners"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    universe: Mapped[str] = mapped_column(String(50), nullable=False, default="nifty500")
    filters: Mapped[dict] = mapped_column(JSONType, nullable=False)
    min_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    top_n: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ========== Auto-Trade Integration Fields ==========
    # Enable/disable auto-trade for this screener
    is_auto_trade_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Scheduling configuration
    run_frequency: Mapped[str] = mapped_column(
        String(20), default=RunFrequency.MANUAL.value, nullable=False
    )
    run_time: Mapped[time | None] = mapped_column(
        Time, nullable=True, default=None
    )  # For daily runs, e.g., 09:20

    # Run tracking
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Strategy inference - automatically determined based on filters
    inferred_strategy_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Link to strategy template for auto-trade execution params
    strategy_template_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("user_strategies.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    runs: Mapped[list["ScreenerRun"]] = relationship(
        "ScreenerRun", back_populates="custom_screener", cascade="all, delete-orphan"
    )
    strategy_template: Mapped["UserStrategy | None"] = relationship(
        "UserStrategy", foreign_keys=[strategy_template_id]
    )

    __table_args__ = (
        Index("ix_custom_screeners_user", "user_id"),
        Index("ix_custom_screeners_name", "user_id", "name"),
        Index("ix_custom_screeners_auto_trade", "is_auto_trade_enabled", "run_frequency"),
    )

    def __repr__(self) -> str:
        return f"<CustomScreener {self.name}>"

    @property
    def is_scheduled(self) -> bool:
        """Check if screener has scheduled runs."""
        return self.run_frequency in (RunFrequency.DAILY.value, RunFrequency.HOURLY.value)


class ScreenerRun(Base):
    """Record of a screener execution."""

    __tablename__ = "screener_runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    custom_screener_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("custom_screeners.id", ondelete="SET NULL"),
        nullable=True,
    )
    preset: Mapped[str | None] = mapped_column(String(50), nullable=True)
    universe: Mapped[str] = mapped_column(String(50), nullable=False)
    filters: Mapped[dict] = mapped_column(JSONType, nullable=False)
    min_score: Mapped[float] = mapped_column(Float, nullable=False)
    top_n: Mapped[int] = mapped_column(Integer, nullable=False)
    total_screened: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    custom_screener: Mapped["CustomScreener | None"] = relationship(
        "CustomScreener", back_populates="runs"
    )
    results: Mapped[list["ScreenerResultRecord"]] = relationship(
        "ScreenerResultRecord", back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_screener_runs_user", "user_id"),
        Index("ix_screener_runs_executed", "executed_at"),
    )

    def __repr__(self) -> str:
        return f"<ScreenerRun {self.id[:8]}>"


class ScreenerResultRecord(Base):
    """Individual stock result from a screener run."""

    __tablename__ = "screener_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("screener_runs.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    filter_scores: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    reasons: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    extra_data: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)

    # Relationships
    run: Mapped["ScreenerRun"] = relationship("ScreenerRun", back_populates="results")

    __table_args__ = (
        Index("ix_screener_results_run", "run_id"),
        Index("ix_screener_results_symbol", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<ScreenerResultRecord {self.symbol} rank={self.rank}>"


class DailyRecommendation(Base):
    """Daily stock recommendations generated by scheduled screeners.

    Categories:
    - momentum: Top momentum stocks
    - breakout: Potential breakout candidates
    - pullback: Pullback opportunities (value entry)
    - sector: Strong sector leaders
    """

    __tablename__ = "daily_recommendations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)

    # Price data at recommendation time
    price_at_rec: Mapped[float] = mapped_column(Float, nullable=False)

    # Performance tracking fields (updated later)
    price_1d: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_1w: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_1m: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_1d: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_1w: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_1m: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Screener data
    filter_scores: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    reasons: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    extra_data: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)

    # Multi-factor scoring fields (Section 2.6.11)
    technical_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    fundamental_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -100 to +100
    combined_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # Weighted avg 0-100
    signal_direction: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # long/short/neutral
    confidence_level: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # high/medium/low/skip
    recommended_strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position_size_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.25-1.0
    skip_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_daily_recommendations_date", "date"),
        Index("ix_daily_recommendations_date_category", "date", "category"),
        Index("ix_daily_recommendations_symbol", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<DailyRecommendation {self.symbol} {self.category}>"


class ScreenerAlert(Base):
    """Alert configuration for screener-based notifications.

    Allows users to set up alerts when:
    - New symbols match a screener
    - Symbols no longer match a screener
    - A specific symbol's score changes significantly
    """

    __tablename__ = "screener_alerts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    custom_screener_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("custom_screeners.id", ondelete="CASCADE"),
        nullable=True,
    )
    # For preset screeners (when custom_screener_id is None)
    preset: Mapped[str | None] = mapped_column(String(50), nullable=True)
    universe: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Alert configuration
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    alert_on_new_symbols: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_removed_symbols: Mapped[bool] = mapped_column(Boolean, default=False)
    min_score_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_symbol: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # Alert for specific symbol

    # State
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_symbols: Mapped[list | None] = mapped_column(
        JSONType, nullable=True
    )  # Symbols from last run

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    custom_screener: Mapped["CustomScreener | None"] = relationship("CustomScreener")

    __table_args__ = (
        Index("ix_screener_alerts_user", "user_id"),
        Index("ix_screener_alerts_enabled", "enabled"),
    )

    def __repr__(self) -> str:
        return f"<ScreenerAlert {self.name}>"
