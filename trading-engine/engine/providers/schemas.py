"""Schemas for broker and data providers."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class OrderSide(str, Enum):
    """Order side enum."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type enum."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"
    GTT = "GTT"


class OrderStatus(str, Enum):
    """Order status enum."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ProductType(str, Enum):
    """Product type for orders."""

    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"
    CNC = "CNC"
    MIS = "MIS"


class OrderRequest(BaseModel):
    """Request to place an order."""

    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    product_type: ProductType = ProductType.DELIVERY
    valid_till: datetime | None = None
    tag: str | None = None


class OrderResponse(BaseModel):
    """Response from order placement."""

    order_id: str
    status: OrderStatus
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    filled_quantity: int = 0
    price: Decimal | None = None
    filled_price: Decimal | None = None
    fees: Decimal | None = None
    message: str | None = None
    placed_at: datetime | None = None
    filled_at: datetime | None = None


class Position(BaseModel):
    """Current position in a symbol."""

    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    current_price: Decimal
    pnl: Decimal | None = None
    pnl_percent: Decimal | None = None

    @property
    def market_value(self) -> Decimal:
        """Calculate current market value."""
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> Decimal:
        """Calculate unrealized P&L."""
        return (self.current_price - self.avg_cost) * self.quantity


class Funds(BaseModel):
    """Account funds/balance."""

    available_cash: Decimal
    used_margin: Decimal
    total_balance: Decimal
    collateral: Decimal = Decimal("0")


class MarketSession(str, Enum):
    """Market session type."""

    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    POST_MARKET = "POST_MARKET"
    CLOSED = "CLOSED"


class Quote(BaseModel):
    """Real-time quote for a symbol with extended hours support."""

    symbol: str
    price: Decimal
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    previous_close: Decimal | None = None
    volume: int | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    timestamp: datetime | None = None

    # Extended hours (pre-market) data
    pre_market_price: Decimal | None = None
    pre_market_change: Decimal | None = None
    pre_market_change_percent: Decimal | None = None
    pre_market_time: datetime | None = None

    # Extended hours (post-market/after-hours) data
    post_market_price: Decimal | None = None
    post_market_change: Decimal | None = None
    post_market_change_percent: Decimal | None = None
    post_market_time: datetime | None = None

    # Current market session
    market_session: MarketSession | None = None


class OHLCV(BaseModel):
    """OHLCV data point."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class SearchResult(BaseModel):
    """Symbol search result."""

    symbol: str
    name: str
    exchange: str
    instrument_type: str = "EQ"


class InstrumentInfo(BaseModel):
    """Detailed instrument information."""

    symbol: str
    name: str
    exchange: str
    instrument_type: str = "EQ"
    sector: str | None = None
    industry: str | None = None
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.05")
    isin: str | None = None
    token: str | None = None
