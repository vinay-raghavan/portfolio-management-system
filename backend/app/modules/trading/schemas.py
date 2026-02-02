"""Pydantic schemas for trading module."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    """Order side."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(str, Enum):
    """Order status."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderCreate(BaseModel):
    """Schema for creating an order."""

    symbol: str = Field(min_length=1, max_length=20)
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(None, gt=0)
    stop_loss: Decimal | None = Field(None, gt=0)
    take_profit: Decimal | None = Field(None, gt=0)
    notes: str | None = None


class OrderResponse(BaseModel):
    """Schema for order response."""

    id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None
    stop_loss: Decimal | None
    take_profit: Decimal | None
    status: str
    filled_quantity: Decimal
    filled_price: Decimal | None
    fees: Decimal
    notes: str | None
    created_at: datetime
    filled_at: datetime | None

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Schema for order list response."""

    orders: list[OrderResponse]
    total_count: int
    page: int
    page_size: int

