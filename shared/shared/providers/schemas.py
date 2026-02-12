"""Common schemas for broker and data providers."""

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
    """Product type for orders (Indian markets terminology).

    Three main product types with their rules:
    - DELIVERY (CNC): Full payment required, no shorting, hold indefinitely
    - INTRADAY (MIS): Margin required (20-40%), shorting allowed, must square off same day
    - MARGIN (MTF): Margin required (25-50%) + interest, leveraged buying only, no shorting
    """

    DELIVERY = "DELIVERY"  # CNC - Cash and Carry
    INTRADAY = "INTRADAY"  # MIS - Margin Intraday Square-off
    MARGIN = "MARGIN"  # MTF - Margin Trading Facility
    CNC = "CNC"  # Alias for DELIVERY
    MIS = "MIS"  # Alias for INTRADAY
    MTF = "MTF"  # Alias for MARGIN

    # Margin percentages (configurable defaults)
    @classmethod
    def get_margin_percent(cls, product_type: "ProductType") -> float:
        """Get the margin percentage required for a product type.

        Returns:
            Margin percentage as decimal (e.g., 0.25 = 25%)
        """
        # Normalize aliases
        normalized = cls.normalize(product_type)

        margins = {
            cls.DELIVERY: 1.0,  # 100% - full payment
            cls.INTRADAY: 0.25,  # 25% margin for MIS
            cls.MARGIN: 0.50,  # 50% margin for MTF
        }
        return margins.get(normalized, 1.0)

    @classmethod
    def allows_short_selling(cls, product_type: "ProductType") -> bool:
        """Check if short selling is allowed for this product type."""
        normalized = cls.normalize(product_type)
        return normalized == cls.INTRADAY

    @classmethod
    def requires_square_off(cls, product_type: "ProductType") -> bool:
        """Check if positions must be squared off same day."""
        normalized = cls.normalize(product_type)
        return normalized == cls.INTRADAY

    @classmethod
    def normalize(cls, product_type: "ProductType") -> "ProductType":
        """Normalize alias values to canonical product type."""
        if product_type in (cls.CNC, cls.DELIVERY):
            return cls.DELIVERY
        elif product_type in (cls.MIS, cls.INTRADAY):
            return cls.INTRADAY
        elif product_type in (cls.MTF, cls.MARGIN):
            return cls.MARGIN
        return product_type


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
    """OHLCV candlestick data point."""

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
    tag: str | None = None  # Optional tag for tracking


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
    pnl: Decimal | None = None  # Alias for unrealized_pnl
    pnl_percent: Decimal | None = None
    product_type: ProductType = ProductType.DELIVERY

    @property
    def market_value(self) -> Decimal:
        """Calculate current market value."""
        if self.current_price is None:
            return self.quantity * self.avg_cost
        return self.quantity * self.current_price


class Funds(BaseModel):
    """Account funds/balance."""

    available_cash: Decimal
    used_margin: Decimal = Decimal("0")
    total_balance: Decimal
    collateral: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")

    @property
    def available_margin(self) -> Decimal:
        """Calculate available margin."""
        return self.available_cash + self.collateral - self.used_margin

    @property
    def net_pnl(self) -> Decimal:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl


# =============================================================================
# Research Module Schemas
# =============================================================================


class FundamentalData(BaseModel):
    """Fundamental analysis data for a stock.

    Contains key financial ratios and metrics used for fundamental analysis.
    """

    symbol: str
    # Valuation ratios
    pe_ratio: float | None = None  # Price to Earnings
    forward_pe: float | None = None  # Forward P/E
    pb_ratio: float | None = None  # Price to Book
    ps_ratio: float | None = None  # Price to Sales
    peg_ratio: float | None = None  # Price/Earnings to Growth
    # Earnings
    eps: float | None = None  # Earnings Per Share (TTM)
    eps_forward: float | None = None  # Forward EPS
    eps_growth_yoy: float | None = None  # YoY EPS growth %
    # Revenue
    revenue: float | None = None  # Total Revenue (TTM)
    revenue_per_share: float | None = None
    revenue_growth_yoy: float | None = None  # YoY Revenue growth %
    # Profitability
    profit_margin: float | None = None  # Net Profit Margin %
    operating_margin: float | None = None  # Operating Margin %
    gross_margin: float | None = None  # Gross Margin %
    # Returns
    roe: float | None = None  # Return on Equity %
    roa: float | None = None  # Return on Assets %
    roic: float | None = None  # Return on Invested Capital %
    # Dividends
    dividend_yield: float | None = None  # Annual Dividend Yield %
    dividend_rate: float | None = None  # Annual Dividend Rate
    payout_ratio: float | None = None  # Dividend Payout Ratio %
    # Balance sheet
    market_cap: float | None = None
    enterprise_value: float | None = None
    book_value: float | None = None  # Book Value Per Share
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None
    # Other
    beta: float | None = None
    shares_outstanding: float | None = None
    float_shares: float | None = None
    # Classification
    sector: str | None = None
    industry: str | None = None
    # Metadata
    currency: str | None = None
    fiscal_year_end: str | None = None
    last_updated: datetime | None = None


class FinancialStatement(BaseModel):
    """A single financial statement entry (income statement, balance sheet, cash flow)."""

    period: str  # e.g., "2024-Q4", "2024-FY"
    period_end_date: datetime | None = None
    currency: str | None = None
    # Income Statement items
    total_revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    ebitda: float | None = None
    # Balance Sheet items
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None
    total_debt: float | None = None
    cash_and_equivalents: float | None = None
    # Cash Flow items
    operating_cash_flow: float | None = None
    capital_expenditure: float | None = None
    free_cash_flow: float | None = None


class FinancialData(BaseModel):
    """Financial statements data for a stock.

    Contains historical income statement, balance sheet, and cash flow data.
    """

    symbol: str
    statements: list[FinancialStatement] = []
    currency: str | None = None
    last_updated: datetime | None = None


class DividendRecord(BaseModel):
    """A single dividend payment record."""

    ex_date: datetime
    payment_date: datetime | None = None
    record_date: datetime | None = None
    declaration_date: datetime | None = None
    amount: float
    currency: str | None = None


class DividendData(BaseModel):
    """Dividend history and metrics for a stock."""

    symbol: str
    # Current dividend info
    dividend_yield: float | None = None  # Annual yield %
    dividend_rate: float | None = None  # Annual dividend rate
    payout_ratio: float | None = None  # % of earnings paid as dividends
    ex_dividend_date: datetime | None = None
    # Dividend history
    history: list[DividendRecord] = []
    # Dividend growth
    five_year_avg_yield: float | None = None
    dividend_growth_rate: float | None = None  # 5-year CAGR
    consecutive_years: int | None = None  # Years of consecutive dividends
    last_updated: datetime | None = None


# =============================================================================
# News Schemas (Section 1.11.3 - News Integration)
# =============================================================================


class SentimentScore(str, Enum):
    """News sentiment classification."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class NewsArticle(BaseModel):
    """Individual news article with metadata and sentiment."""

    title: str
    url: str
    source: str  # e.g., "Yahoo Finance", "Reuters", "Finnhub"
    published_at: datetime
    summary: str | None = None
    thumbnail_url: str | None = None
    # Related symbols (for multi-symbol news)
    related_symbols: list[str] = []
    # Sentiment analysis
    sentiment: SentimentScore = SentimentScore.NEUTRAL
    sentiment_score: float = 0.0  # -1.0 (negative) to 1.0 (positive)
    # Provider metadata
    provider: str = "unknown"  # Provider that fetched this article
    article_id: str | None = None  # Unique ID from provider


class NewsResponse(BaseModel):
    """Collection of news articles for a symbol or topic."""

    symbol: str | None = None  # None for general market news
    articles: list[NewsArticle] = []
    total_count: int = 0
    # Aggregate sentiment
    average_sentiment: float = 0.0  # Average sentiment score
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    last_updated: datetime | None = None
