"""Pydantic schemas for research module."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

# Custom type that serializes Decimal as float for JSON
DecimalAsFloat = Annotated[
    Decimal, PlainSerializer(lambda x: float(x) if x is not None else None, return_type=float)
]


class ResearchNoteCreate(BaseModel):
    """Schema for creating a research note."""

    symbol: str
    title: str
    content: str
    rating: str | None = None  # BUY, HOLD, SELL, STRONG_BUY, STRONG_SELL
    target_price: DecimalAsFloat | None = None
    tags: list[str] = []


class ResearchNoteUpdate(BaseModel):
    """Schema for updating a research note."""

    title: str | None = None
    content: str | None = None
    rating: str | None = None
    target_price: DecimalAsFloat | None = None
    tags: list[str] | None = None


class ResearchNoteResponse(BaseModel):
    """Schema for research note response."""

    id: int
    user_id: int
    symbol: str
    title: str
    content: str
    rating: str | None = None
    target_price: DecimalAsFloat | None = None
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FundamentalsResponse(BaseModel):
    """Response schema for fundamental data (wraps shared schema)."""

    symbol: str
    # Valuation
    pe_ratio: float | None = None
    forward_pe: float | None = None
    pb_ratio: float | None = None
    ps_ratio: float | None = None
    peg_ratio: float | None = None
    # Earnings
    eps: float | None = None
    eps_forward: float | None = None
    eps_growth_yoy: float | None = None
    # Revenue
    revenue: float | None = None
    revenue_growth_yoy: float | None = None
    # Profitability
    profit_margin: float | None = None
    operating_margin: float | None = None
    gross_margin: float | None = None
    # Returns
    roe: float | None = None
    roa: float | None = None
    # Dividends
    dividend_yield: float | None = None
    dividend_rate: float | None = None
    payout_ratio: float | None = None
    # Balance sheet
    market_cap: float | None = None
    enterprise_value: float | None = None
    book_value: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    # Other
    beta: float | None = None
    sector: str | None = None
    industry: str | None = None
    last_updated: datetime | None = None


class DividendRecordResponse(BaseModel):
    """Schema for a single dividend record."""

    ex_date: datetime
    payment_date: datetime | None = None
    amount: float
    currency: str | None = None


class DividendsResponse(BaseModel):
    """Response schema for dividend data."""

    symbol: str
    dividend_yield: float | None = None
    dividend_rate: float | None = None
    payout_ratio: float | None = None
    ex_dividend_date: datetime | None = None
    five_year_avg_yield: float | None = None
    dividend_growth_rate: float | None = None
    history: list[DividendRecordResponse] = []
    last_updated: datetime | None = None

