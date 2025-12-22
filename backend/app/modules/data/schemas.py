"""Pydantic schemas for market data module."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

# Custom type that serializes Decimal as float for JSON
DecimalAsFloat = Annotated[Decimal, PlainSerializer(lambda v: float(v) if v is not None else None, return_type=float)]


class StockQuote(BaseModel):
    """Schema for stock quote."""

    symbol: str
    price: DecimalAsFloat
    open: DecimalAsFloat | None = None
    high: DecimalAsFloat | None = None
    low: DecimalAsFloat | None = None
    close: DecimalAsFloat | None = None
    volume: int | None = None
    change: DecimalAsFloat | None = None
    change_pct: DecimalAsFloat | None = None
    timestamp: datetime | None = None


class StockInfo(BaseModel):
    """Schema for stock information."""

    symbol: str
    name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: DecimalAsFloat | None = None
    pe_ratio: DecimalAsFloat | None = None
    dividend_yield: DecimalAsFloat | None = None
    fifty_two_week_high: DecimalAsFloat | None = None
    fifty_two_week_low: DecimalAsFloat | None = None


class HistoricalDataPoint(BaseModel):
    """Schema for historical data point."""

    date: datetime
    open: DecimalAsFloat
    high: DecimalAsFloat
    low: DecimalAsFloat
    close: DecimalAsFloat
    volume: int


class HistoricalDataResponse(BaseModel):
    """Schema for historical data response."""

    symbol: str
    interval: str
    data: list[HistoricalDataPoint]


class SearchResult(BaseModel):
    """Schema for stock search result."""

    symbol: str
    name: str
    exchange: str | None = None
    type: str | None = None


class IndexConstituent(BaseModel):
    """Schema for index constituent stock."""

    symbol: str
    name: str | None = None
    industry: str | None = None
    isin: str | None = None
    series: str = "EQ"
    is_fno: bool = False
    last_price: DecimalAsFloat | None = None
    change: DecimalAsFloat | None = None
    change_pct: DecimalAsFloat | None = None
    open: DecimalAsFloat | None = None
    high: DecimalAsFloat | None = None
    low: DecimalAsFloat | None = None
    previous_close: DecimalAsFloat | None = None
    volume: int | None = None
    year_high: DecimalAsFloat | None = None
    year_low: DecimalAsFloat | None = None


class IndexConstituentsResponse(BaseModel):
    """Schema for index constituents response."""

    index: str
    count: int
    constituents: list[IndexConstituent]
