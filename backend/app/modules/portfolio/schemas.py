"""Pydantic schemas for portfolio module."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PositionResponse(BaseModel):
    """Schema for position response."""

    id: str
    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None

    model_config = {"from_attributes": True}


class TradeResponse(BaseModel):
    """Schema for trade response."""

    id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fees: Decimal
    total_value: Decimal | None = None
    executed_at: datetime

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    """Schema for portfolio summary."""

    total_value: Decimal
    total_cost: Decimal
    total_pnl: Decimal
    total_pnl_pct: Decimal
    cash_balance: Decimal
    positions_count: int
    day_change: Decimal | None = None
    day_change_pct: Decimal | None = None


class PortfolioResponse(BaseModel):
    """Schema for full portfolio response."""

    summary: PortfolioSummary
    positions: list[PositionResponse]


class TradeHistoryResponse(BaseModel):
    """Schema for trade history response."""

    trades: list[TradeResponse]
    total_count: int
    page: int
    page_size: int

