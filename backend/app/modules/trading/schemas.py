"""Pydantic schemas for trading module."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field
from shared.providers.schemas import ProductType


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
    AMO_PENDING = "AMO_PENDING"  # After Market Order - queued for next session


class OrderCreate(BaseModel):
    """Schema for creating an order."""

    symbol: str = Field(min_length=1, max_length=20)
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(None, gt=0)
    stop_loss: Decimal | None = Field(None, gt=0)
    take_profit: Decimal | None = Field(None, gt=0)
    product_type: ProductType = Field(
        default=ProductType.DELIVERY,
        description="Product type: DELIVERY (CNC), INTRADAY (MIS), or MARGIN (MTF)",
    )
    notes: str | None = None
    is_amo: bool = Field(
        default=False,
        description="After Market Order - if True, order will be queued for next market open",
    )


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
    is_amo: bool = False
    scheduled_for: datetime | None = None

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Schema for order list response."""

    orders: list[OrderResponse]
    total_count: int
    page: int
    page_size: int


# ============== Order Template Schemas ==============


class OrderTemplateCreate(BaseModel):
    """Schema for creating an order template."""

    name: str = Field(min_length=1, max_length=100)
    symbol: str = Field(min_length=1, max_length=20)
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: int | None = Field(None, gt=0)
    quantity_pct: Decimal | None = Field(None, gt=0, le=100)
    stop_loss_pct: Decimal | None = Field(None, gt=0, le=100)
    take_profit_pct: Decimal | None = Field(None, gt=0, le=1000)
    is_favorite: bool = False


class OrderTemplateUpdate(BaseModel):
    """Schema for updating an order template."""

    name: str | None = Field(None, min_length=1, max_length=100)
    symbol: str | None = Field(None, min_length=1, max_length=20)
    side: OrderSide | None = None
    order_type: OrderType | None = None
    quantity: int | None = Field(None, gt=0)
    quantity_pct: Decimal | None = Field(None, gt=0, le=100)
    stop_loss_pct: Decimal | None = Field(None, gt=0, le=100)
    take_profit_pct: Decimal | None = Field(None, gt=0, le=1000)
    is_favorite: bool | None = None


class OrderTemplateResponse(BaseModel):
    """Schema for order template response."""

    id: str
    name: str
    symbol: str
    side: str
    order_type: str
    quantity: int | None
    quantity_pct: Decimal | None
    stop_loss_pct: Decimal | None
    take_profit_pct: Decimal | None
    is_favorite: bool
    use_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderTemplateListResponse(BaseModel):
    """Schema for order template list response."""

    templates: list[OrderTemplateResponse]
    total_count: int


class OrderFromTemplateCreate(BaseModel):
    """Schema for creating an order from a template."""

    current_price: Decimal = Field(gt=0, description="Current market price for calculating SL/TP")
    quantity_override: int | None = Field(None, gt=0, description="Override template quantity")
    confirm: bool = Field(default=True, description="Execute immediately if True")
