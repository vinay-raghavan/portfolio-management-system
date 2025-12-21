"""Pydantic schemas for risk management module."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RiskLimitsResponse(BaseModel):
    """Schema for risk limits response."""

    id: str
    user_id: str
    max_position_size: Decimal
    max_position_pct: Decimal
    max_positions: int
    max_daily_loss: Decimal
    max_daily_loss_pct: Decimal
    max_order_value: Decimal
    max_orders_per_day: int
    allow_intraday: bool
    allow_short_selling: bool

    model_config = {"from_attributes": True}


class RiskLimitsUpdate(BaseModel):
    """Schema for updating risk limits."""

    max_position_size: Decimal | None = Field(None, gt=0)
    max_position_pct: Decimal | None = Field(None, gt=0, le=100)
    max_positions: int | None = Field(None, gt=0)
    max_daily_loss: Decimal | None = Field(None, gt=0)
    max_daily_loss_pct: Decimal | None = Field(None, gt=0, le=100)
    max_order_value: Decimal | None = Field(None, gt=0)
    max_orders_per_day: int | None = Field(None, gt=0)
    allow_intraday: bool | None = None
    allow_short_selling: bool | None = None


class DailyRiskMetricsResponse(BaseModel):
    """Schema for daily risk metrics response."""

    id: str
    user_id: str
    date: datetime
    orders_count: int
    trades_count: int
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_traded_value: Decimal
    daily_loss_limit_breached: bool
    position_limit_breached: bool

    model_config = {"from_attributes": True}


class RiskCheckResult(BaseModel):
    """Result of a risk check."""

    passed: bool
    checks: list[dict]
    warnings: list[str] = []
    blocked_reason: str | None = None


class RiskSummary(BaseModel):
    """Summary of current risk status."""

    daily_pnl: Decimal
    daily_pnl_pct: Decimal
    daily_loss_remaining: Decimal
    orders_today: int
    orders_remaining: int
    positions_count: int
    positions_remaining: int
    largest_position_pct: Decimal
    is_trading_blocked: bool
    block_reason: str | None = None

