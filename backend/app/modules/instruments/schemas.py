"""Pydantic schemas for instruments module."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class Exchange(str, Enum):
    """Supported exchanges."""

    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"  # NSE F&O
    BFO = "BFO"  # BSE F&O
    MCX = "MCX"  # Commodity


class Segment(str, Enum):
    """Market segments."""

    EQ = "EQ"  # Equity
    FO = "FO"  # Futures & Options
    CD = "CD"  # Currency Derivatives
    COM = "COM"  # Commodity


class InstrumentType(str, Enum):
    """Instrument types."""

    EQ = "EQ"  # Equity
    FUT = "FUT"  # Futures
    OPT = "OPT"  # Options
    IDX = "IDX"  # Index


class InstrumentCreate(BaseModel):
    """Schema for creating an instrument."""

    symbol: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    exchange: str = Field(min_length=2, max_length=10)
    segment: str = Field(default="EQ", max_length=10)
    token: str | None = None
    isin: str | None = Field(default=None, max_length=12)
    lot_size: int = Field(default=1, ge=1)
    tick_size: Decimal = Field(default=Decimal("0.05"))
    expiry: date | None = None
    strike: Decimal | None = None
    option_type: str | None = Field(default=None, max_length=2)
    underlying: str | None = None
    instrument_type: str = Field(default="EQ", max_length=10)
    series: str | None = None
    is_active: bool = True
    is_tradeable: bool = True
    sector: str | None = None
    industry: str | None = None


class InstrumentResponse(BaseModel):
    """Schema for instrument response."""

    id: str
    symbol: str
    name: str
    exchange: str
    segment: str
    token: str | None
    isin: str | None
    lot_size: int
    tick_size: Decimal
    expiry: date | None
    strike: Decimal | None
    option_type: str | None
    underlying: str | None
    instrument_type: str
    series: str | None
    is_active: bool
    is_tradeable: bool
    sector: str | None
    industry: str | None
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime | None

    model_config = {"from_attributes": True}


class InstrumentSearchParams(BaseModel):
    """Query parameters for instrument search."""

    query: str | None = Field(default=None, description="Search query for symbol or name")
    exchange: str | None = Field(default=None, description="Filter by exchange")
    segment: str | None = Field(default=None, description="Filter by segment (EQ, FO, etc.)")
    instrument_type: str | None = Field(default=None, description="Filter by type (EQ, FUT, OPT)")
    is_active: bool | None = Field(default=True, description="Filter by active status")
    underlying: str | None = Field(
        default=None, description="Filter by underlying (for derivatives)"
    )
    expiry_from: date | None = Field(default=None, description="Filter expiry from date")
    expiry_to: date | None = Field(default=None, description="Filter expiry to date")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Results offset")


class InstrumentSearchResponse(BaseModel):
    """Response for instrument search."""

    total: int
    results: list[InstrumentResponse]


class InstrumentBulkCreate(BaseModel):
    """Schema for bulk instrument creation."""

    instruments: list[InstrumentCreate]


class InstrumentBulkResponse(BaseModel):
    """Response for bulk operations."""

    created: int
    updated: int
    failed: int
    errors: list[str] = []
