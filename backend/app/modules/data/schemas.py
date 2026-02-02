"""Pydantic schemas for market data module."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class StockQuote(BaseModel):
    """Schema for stock quote."""

    symbol: str
    price: Decimal
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: int | None = None
    change: Decimal | None = None
    change_pct: Decimal | None = None
    timestamp: datetime | None = None


class StockInfo(BaseModel):
    """Schema for stock information."""

    symbol: str
    name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: Decimal | None = None
    pe_ratio: Decimal | None = None
    dividend_yield: Decimal | None = None
    fifty_two_week_high: Decimal | None = None
    fifty_two_week_low: Decimal | None = None


class HistoricalDataPoint(BaseModel):
    """Schema for historical data point."""

    date: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
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

