"""Pydantic schemas for signals module."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

from app.modules.signals.models import SignalStatus, SignalType

# Custom type that serializes Decimal as float for JSON
DecimalAsFloat = Annotated[
    Decimal, PlainSerializer(lambda x: float(x) if x is not None else None, return_type=float)
]


class SignalBase(BaseModel):
    """Base schema for Signal."""

    symbol: str = Field(..., min_length=1, max_length=20)
    signal_type: SignalType
    strength: DecimalAsFloat = Field(..., ge=0, le=1)
    confidence: DecimalAsFloat = Field(..., ge=0, le=1)
    strategy_name: str = Field(..., min_length=1, max_length=50)
    timeframe: str = Field(default="1d", max_length=10)
    price_at_signal: DecimalAsFloat
    entry_price: DecimalAsFloat | None = None
    stop_loss: DecimalAsFloat | None = None
    take_profit: DecimalAsFloat | None = None
    risk_reward_ratio: DecimalAsFloat | None = None
    indicators: dict | None = None
    notes: str | None = None
    expires_at: datetime | None = None


class SignalCreate(SignalBase):
    """Schema for creating a new signal."""

    pass


class SignalUpdate(BaseModel):
    """Schema for updating a signal."""

    status: SignalStatus | None = None
    is_executed: bool | None = None
    executed_order_id: str | None = None
    executed_at: datetime | None = None
    notes: str | None = None


class SignalResponse(SignalBase):
    """Schema for signal response."""

    id: str
    user_id: str
    status: SignalStatus
    is_executed: bool
    executed_order_id: str | None = None
    generated_at: datetime
    executed_at: datetime | None = None

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    """Schema for listing signals."""

    signals: list[SignalResponse]
    total: int
    page: int
    page_size: int


class SignalGenerateRequest(BaseModel):
    """Schema for signal generation request."""

    symbols: list[str] = Field(..., min_length=1, max_length=50)
    strategy_name: str | None = None  # None means run all strategies
    timeframe: str = Field(default="1d")


class SignalGenerateResponse(BaseModel):
    """Schema for signal generation response."""

    signals_generated: int
    signals: list[SignalResponse]


class StrategyInfo(BaseModel):
    """Schema for strategy information."""

    name: str
    description: str
    default_timeframe: str
    parameters: dict


class StrategyListResponse(BaseModel):
    """Schema for listing available strategies."""

    strategies: list[StrategyInfo]


class SignalExecuteRequest(BaseModel):
    """Schema for executing a signal (converting to order)."""

    quantity: int = Field(..., gt=0)
    order_type: str = Field(default="MARKET")  # MARKET or LIMIT
    price: DecimalAsFloat | None = None  # Required for LIMIT orders


class SignalExecuteResponse(BaseModel):
    """Schema for signal execution response."""

    signal_id: str
    order_id: str
    message: str

