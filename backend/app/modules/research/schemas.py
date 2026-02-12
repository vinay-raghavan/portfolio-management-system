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


# =============================================================================
# News Schemas
# =============================================================================


class NewsArticleResponse(BaseModel):
    """Response schema for a news article."""

    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None = None
    thumbnail_url: str | None = None
    related_symbols: list[str] = []
    sentiment: str = "neutral"  # positive, negative, neutral
    sentiment_score: float = 0.0


class NewsResponse(BaseModel):
    """Response schema for news feed."""

    symbol: str | None = None
    articles: list[NewsArticleResponse] = []
    total_count: int = 0
    average_sentiment: float = 0.0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    last_updated: datetime | None = None


# =============================================================================
# Full Research Response
# =============================================================================


class StockResearchResponse(BaseModel):
    """Complete research data for a stock symbol.

    Combines fundamentals, dividends, and news into a single response.
    """

    symbol: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None

    # Current price info
    current_price: float | None = None
    price_change: float | None = None
    price_change_pct: float | None = None

    # Fundamentals summary
    fundamentals: FundamentalsResponse | None = None

    # Dividends summary
    dividends: DividendsResponse | None = None

    # Recent news with sentiment
    news: NewsResponse | None = None

    # Timestamps
    last_updated: datetime | None = None


# =============================================================================
# Peer Comparison Schemas
# =============================================================================


class PeerStock(BaseModel):
    """A peer stock with comparative metrics."""

    symbol: str
    name: str | None = None
    current_price: float | None = None
    price_change_pct: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    dividend_yield: float | None = None
    roe: float | None = None
    revenue_growth: float | None = None


class PeerComparisonResponse(BaseModel):
    """Peer comparison for a stock."""

    symbol: str
    sector: str | None = None
    industry: str | None = None
    peers: list[PeerStock] = []
    # Sector averages for comparison
    sector_avg_pe: float | None = None
    sector_avg_pb: float | None = None
    sector_avg_dividend_yield: float | None = None
    last_updated: datetime | None = None


# =============================================================================
# Sector Performance Schemas
# =============================================================================


class SectorPerformance(BaseModel):
    """Performance data for a sector."""

    sector: str
    change_1d: float | None = None  # 1-day change %
    change_1w: float | None = None  # 1-week change %
    change_1m: float | None = None  # 1-month change %
    change_3m: float | None = None  # 3-month change %
    change_1y: float | None = None  # 1-year change %
    stock_count: int = 0
    top_gainer: str | None = None
    top_loser: str | None = None


class SectorListResponse(BaseModel):
    """List of all sectors with performance."""

    sectors: list[SectorPerformance] = []
    last_updated: datetime | None = None


class SectorStocksResponse(BaseModel):
    """Stocks within a specific sector."""

    sector: str
    stocks: list[PeerStock] = []
    total_count: int = 0
    last_updated: datetime | None = None


class ResearchNoteListResponse(BaseModel):
    """Schema for list of research notes."""

    notes: list[ResearchNoteResponse] = []
    total_count: int = 0


# =============================================================================
# Daily Digest Schemas
# =============================================================================


class IndexPerformance(BaseModel):
    """Performance data for a market index."""

    symbol: str
    name: str | None = None
    close: float | None = None
    change: float | None = None
    change_pct: float | None = None


class MarketSummary(BaseModel):
    """Market summary with major index performance."""

    indices: list[IndexPerformance] = []
    overall_trend: str | None = None  # bullish, bearish, neutral
    trading_date: datetime | None = None


class TopMover(BaseModel):
    """A top gainer or loser stock."""

    symbol: str
    name: str | None = None
    close: float | None = None
    change_pct: float
    volume: int | None = None
    reason: str | None = None  # Why it moved


class SectorDigest(BaseModel):
    """Sector performance for digest."""

    sector: str
    change_pct: float | None = None
    top_stock: str | None = None
    stock_count: int = 0


class VolumeLeader(BaseModel):
    """Stock with unusual volume activity."""

    symbol: str
    name: str | None = None
    volume: int
    avg_volume: int | None = None
    volume_ratio: float | None = None  # volume / avg_volume
    price_change_pct: float | None = None


class BreakoutCandidate(BaseModel):
    """Stock showing breakout pattern."""

    symbol: str
    name: str | None = None
    pattern: str | None = None  # e.g., "52-week high", "resistance breakout"
    current_price: float | None = None
    breakout_level: float | None = None
    strength: float | None = None  # 0-100 breakout strength score


class NewsHighlight(BaseModel):
    """Top market-moving news item."""

    title: str
    source: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    sentiment: str | None = None  # positive, negative, neutral
    related_symbols: list[str] = []


class DailyDigestResponse(BaseModel):
    """Complete daily research digest response."""

    id: str
    digest_date: datetime

    # Market Overview
    market_summary: MarketSummary | None = None

    # Top Movers
    top_gainers: list[TopMover] = []
    top_losers: list[TopMover] = []

    # Sector Analysis
    sector_performance: list[SectorDigest] = []

    # Volume Analysis
    volume_leaders: list[VolumeLeader] = []

    # Technical Signals
    breakout_candidates: list[BreakoutCandidate] = []

    # News
    news_highlights: list[NewsHighlight] = []

    # Overall sentiment
    market_sentiment: float | None = None  # -1.0 to 1.0

    created_at: datetime


class DigestListResponse(BaseModel):
    """List of available digests."""

    digests: list[DailyDigestResponse] = []
    total_count: int = 0


# =============================================================================
# Recommendation Schemas
# =============================================================================


class RecommendationStock(BaseModel):
    """A stock recommendation with combined fundamental + technical analysis."""

    symbol: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None

    # Current price info
    current_price: float | None = None
    price_change_pct: float | None = None

    # Scores (0-100)
    fundamental_score: float = 0
    technical_score: float = 0
    combined_score: float = 0

    # Strategy/category
    category: str = "quality"  # quality, momentum, value, dividend, breakout

    # Fundamental metrics
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    roe: float | None = None
    debt_to_equity: float | None = None
    dividend_yield: float | None = None
    eps_growth: float | None = None

    # Technical metrics
    rsi: float | None = None
    above_200ma: bool | None = None
    volume_ratio: float | None = None
    pct_from_52w_high: float | None = None

    # Thesis/rationale
    thesis: str | None = None
    reasons: list[str] = []


class RecommendationsResponse(BaseModel):
    """Response schema for daily recommendations."""

    date: datetime
    recommendations: list[RecommendationStock] = []
    total_count: int = 0

    # Category breakdown
    by_category: dict[str, int] = {}

    # Overall stats
    avg_fundamental_score: float | None = None
    avg_technical_score: float | None = None


# =============================================================================
# Universe Research Schemas
# =============================================================================


class UniverseStock(BaseModel):
    """A stock within a universe with fundamental metrics."""

    symbol: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None

    # Price data
    current_price: float | None = None
    price_change_pct: float | None = None
    volume: int | None = None

    # Fundamental metrics
    market_cap: float | None = None
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    ps_ratio: float | None = None
    roe: float | None = None
    roa: float | None = None
    profit_margin: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    dividend_yield: float | None = None
    eps_growth: float | None = None
    revenue_growth: float | None = None

    # Quality score (based on fundamentals)
    fundamental_score: float | None = None


class UniverseResearchResponse(BaseModel):
    """Response schema for universe research."""

    universe: str
    stocks: list[UniverseStock] = []
    total_count: int = 0

    # Sector breakdown
    by_sector: dict[str, int] = {}

    # Filter applied
    filters_applied: dict | None = None

    last_updated: datetime | None = None


class FundamentalFilterParams(BaseModel):
    """Parameters for fundamental screening."""

    max_pe: float | None = None
    min_pe: float | None = None
    max_pb: float | None = None
    min_roe: float | None = None
    min_dividend_yield: float | None = None
    max_debt_to_equity: float | None = None
    min_current_ratio: float | None = None
    min_market_cap: float | None = None
    max_market_cap: float | None = None
    sectors: list[str] | None = None
    industries: list[str] | None = None
