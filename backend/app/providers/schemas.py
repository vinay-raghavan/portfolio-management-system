"""Common schemas for providers."""

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
    GTT = "GTT"  # Good Till Triggered


class OrderStatus(str, Enum):
    """Order status enum."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    TRIGGERED = "TRIGGERED"  # GTT/SL has been triggered
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ProductType(str, Enum):
    """Product type for Indian markets."""

    DELIVERY = "DELIVERY"  # CNC - Cash and Carry
    INTRADAY = "INTRADAY"  # MIS - Margin Intraday Square-off
    MARGIN = "MARGIN"  # For F&O


class MarketSession(str, Enum):
    """Market session type."""

    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    POST_MARKET = "POST_MARKET"
    CLOSED = "CLOSED"


class Quote(BaseModel):
    """Real-time quote data with extended hours support."""

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
    """OHLCV candlestick data."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class InstrumentInfo(BaseModel):
    """Detailed instrument information."""

    symbol: str
    name: str
    exchange: str
    instrument_type: str = "EQ"  # EQ, FUT, OPT, IDX
    sector: str | None = None
    industry: str | None = None
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.05")
    isin: str | None = None
    token: str | None = None  # Exchange-specific token
    expiry: datetime | None = None  # For F&O


class SearchResult(BaseModel):
    """Symbol search result."""

    symbol: str
    name: str
    exchange: str
    instrument_type: str = "EQ"


class OrderRequest(BaseModel):
    """Order placement request."""

    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Decimal | None = None  # Required for LIMIT orders
    trigger_price: Decimal | None = None  # Required for SL/GTT orders
    product_type: ProductType = ProductType.DELIVERY
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    valid_till: datetime | None = None  # For GTT orders (default: 1 year)


class OrderResponse(BaseModel):
    """Order placement response."""

    order_id: str
    status: OrderStatus
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    filled_quantity: int = 0
    price: Decimal | None = None
    filled_price: Decimal | None = None
    fees: Decimal = Decimal("0")
    message: str | None = None
    placed_at: datetime | None = None
    filled_at: datetime | None = None


class Position(BaseModel):
    """Trading position."""

    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    current_price: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    realized_pnl: Decimal = Decimal("0")
    product_type: ProductType = ProductType.DELIVERY


class Funds(BaseModel):
    """Account funds/balance."""

    available_cash: Decimal
    used_margin: Decimal = Decimal("0")
    total_balance: Decimal
    collateral: Decimal = Decimal("0")

    @property
    def available_margin(self) -> Decimal:
        """Calculate available margin."""
        return self.available_cash + self.collateral - self.used_margin
