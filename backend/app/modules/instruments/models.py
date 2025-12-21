"""Instrument database models."""

from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import String, DateTime, Date, Numeric, Integer, Boolean, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Instrument(Base):
    """Tradeable instrument model.
    
    Stores information about all tradeable securities including:
    - Equity stocks (NSE, BSE)
    - Futures & Options (F&O)
    - Indices
    """

    __tablename__ = "instruments"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    
    # Basic identification
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Exchange information
    exchange: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # NSE, BSE
    segment: Mapped[str] = mapped_column(String(10), nullable=False, default="EQ")  # EQ, FO, CD, COM
    
    # Exchange-specific identifiers
    token: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)  # Exchange token
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)  # ISIN code
    
    # Trading parameters
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tick_size: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.05"))
    
    # F&O specific fields
    expiry: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    strike: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    option_type: Mapped[str | None] = mapped_column(String(2), nullable=True)  # CE, PE
    underlying: Mapped[str | None] = mapped_column(String(50), nullable=True)  # For derivatives
    
    # Classification
    instrument_type: Mapped[str] = mapped_column(String(10), nullable=False, default="EQ")  # EQ, FUT, OPT, IDX
    series: Mapped[str | None] = mapped_column(String(10), nullable=True)  # EQ, BE, BL, etc.
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_tradeable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Additional metadata
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # Composite unique constraint for exchange + symbol + expiry (for derivatives)
        Index("ix_instruments_exchange_symbol", "exchange", "symbol"),
        Index("ix_instruments_segment_exchange", "segment", "exchange"),
        Index("ix_instruments_underlying_expiry", "underlying", "expiry"),
        # Note: For full-text search, enable pg_trgm extension and create index manually:
        # CREATE EXTENSION IF NOT EXISTS pg_trgm;
        # CREATE INDEX ix_instruments_name_trgm ON instruments USING gin (name gin_trgm_ops);
    )

    def __repr__(self) -> str:
        return f"<Instrument {self.exchange}:{self.symbol}>"

