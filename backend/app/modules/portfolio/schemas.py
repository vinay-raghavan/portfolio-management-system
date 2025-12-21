"""Pydantic schemas for portfolio module."""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ProductType(str, Enum):
    """Product type for positions."""

    DELIVERY = "DELIVERY"
    INTRADAY = "INTRADAY"


class PositionResponse(BaseModel):
    """Schema for position response."""

    id: str
    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    product_type: str = "DELIVERY"
    realized_pnl: Decimal = Decimal("0")
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None

    model_config = {"from_attributes": True}


# ============== Funds Schemas ==============


class FundsResponse(BaseModel):
    """Schema for user funds response."""

    id: str
    user_id: str
    cash_balance: Decimal
    margin_used: Decimal
    collateral: Decimal
    available_cash: Decimal
    total_balance: Decimal
    available_margin: Decimal

    model_config = {"from_attributes": True}


class FundsUpdate(BaseModel):
    """Schema for updating funds (admin or deposit/withdraw)."""

    amount: Decimal = Field(..., description="Amount to add (positive) or withdraw (negative)")
    reason: str = Field(..., max_length=100, description="Reason for adjustment")


class FundsSummary(BaseModel):
    """Schema for funds summary in portfolio view."""

    cash_balance: Decimal
    margin_used: Decimal
    available_margin: Decimal
    collateral: Decimal


# ============== Daily P&L Schemas ==============


class DailyPnLResponse(BaseModel):
    """Schema for daily P&L response."""

    id: str
    date: date
    total_value: Decimal
    total_cost: Decimal
    total_pnl: Decimal
    cash_balance: Decimal
    day_pnl: Decimal
    trades_count: int

    model_config = {"from_attributes": True}


class DailyPnLHistory(BaseModel):
    """Schema for daily P&L history response."""

    records: list[DailyPnLResponse]
    total_count: int
    period_pnl: Decimal
    period_return_pct: Decimal


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

