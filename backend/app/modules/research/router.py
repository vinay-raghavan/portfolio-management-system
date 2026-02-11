"""Research API routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession, OptionalUser
from app.modules.data.service import get_user_data_provider
from app.modules.research.schemas import (
    DividendsResponse,
    FundamentalsResponse,
    NewsArticleResponse,
    NewsResponse,
    PeerComparisonResponse,
    PeerStock,
    StockResearchResponse,
)
from app.modules.research.service import ResearchService

router = APIRouter()


# =============================================================================
# Full Research Endpoint
# =============================================================================


@router.get("/{symbol}", response_model=StockResearchResponse)
async def get_stock_research(
    symbol: str,
    db: DbSession,
    current_user: OptionalUser,
    news_limit: int = Query(5, ge=1, le=20, description="Number of news articles to include"),
) -> StockResearchResponse:
    """Get comprehensive research data for a stock.

    Combines fundamental analysis, dividend data, and recent news with sentiment
    into a single response. This is the primary endpoint for stock research.

    Uses the user's preferred data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = ResearchService(provider=provider)
    data = await service.get_full_research(symbol, news_limit=news_limit)

    return StockResearchResponse(
        symbol=data["symbol"],
        name=data.get("name"),
        sector=data.get("sector"),
        industry=data.get("industry"),
        current_price=data.get("current_price"),
        price_change=data.get("price_change"),
        price_change_pct=data.get("price_change_pct"),
        fundamentals=data.get("fundamentals"),
        dividends=data.get("dividends"),
        news=data.get("news"),
        last_updated=datetime.now(UTC),
    )


# =============================================================================
# Fundamentals Endpoint
# =============================================================================


@router.get("/{symbol}/fundamentals", response_model=FundamentalsResponse)
async def get_fundamentals(
    symbol: str,
    db: DbSession,
    current_user: OptionalUser,
) -> FundamentalsResponse:
    """Get fundamental analysis data for a stock.

    Includes valuation ratios (P/E, P/B, P/S, PEG), earnings metrics,
    revenue, profitability margins, returns (ROE, ROA), and balance sheet metrics.

    Uses the user's preferred data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = ResearchService(provider=provider)
    fundamentals = await service.get_fundamentals(symbol)

    if fundamentals is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not get fundamentals for symbol: {symbol}",
        )

    return FundamentalsResponse(
        symbol=fundamentals.symbol,
        pe_ratio=fundamentals.pe_ratio,
        forward_pe=fundamentals.forward_pe,
        pb_ratio=fundamentals.pb_ratio,
        ps_ratio=fundamentals.ps_ratio,
        peg_ratio=fundamentals.peg_ratio,
        eps=fundamentals.eps,
        eps_forward=fundamentals.eps_forward,
        eps_growth_yoy=fundamentals.eps_growth_yoy,
        revenue=fundamentals.revenue,
        revenue_growth_yoy=fundamentals.revenue_growth_yoy,
        profit_margin=fundamentals.profit_margin,
        operating_margin=fundamentals.operating_margin,
        gross_margin=fundamentals.gross_margin,
        roe=fundamentals.roe,
        roa=fundamentals.roa,
        dividend_yield=fundamentals.dividend_yield,
        dividend_rate=fundamentals.dividend_rate,
        payout_ratio=fundamentals.payout_ratio,
        market_cap=fundamentals.market_cap,
        enterprise_value=fundamentals.enterprise_value,
        book_value=fundamentals.book_value,
        debt_to_equity=fundamentals.debt_to_equity,
        current_ratio=fundamentals.current_ratio,
        beta=fundamentals.beta,
        sector=fundamentals.sector,
        industry=fundamentals.industry,
        last_updated=fundamentals.last_updated,
    )


@router.get("/{symbol}/dividends", response_model=DividendsResponse)
async def get_dividends(
    symbol: str,
    db: DbSession,
    current_user: OptionalUser,
) -> DividendsResponse:
    """Get dividend history and metrics for a stock.

    Includes current yield, dividend rate, payout ratio, ex-dividend date,
    5-year average yield, dividend growth rate, and historical dividend records.

    Uses the user's preferred data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = ResearchService(provider=provider)
    dividends = await service.get_dividends(symbol)

    if dividends is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not get dividend data for symbol: {symbol}",
        )

    return DividendsResponse(
        symbol=dividends.symbol,
        dividend_yield=dividends.dividend_yield,
        dividend_rate=dividends.dividend_rate,
        payout_ratio=dividends.payout_ratio,
        ex_dividend_date=dividends.ex_dividend_date,
        five_year_avg_yield=dividends.five_year_avg_yield,
        dividend_growth_rate=dividends.dividend_growth_rate,
        history=[
            {
                "ex_date": d.ex_date,
                "payment_date": d.payment_date,
                "amount": d.amount,
                "currency": d.currency,
            }
            for d in dividends.history
        ],
        last_updated=dividends.last_updated,
    )


@router.get("/{symbol}/news", response_model=NewsResponse)
async def get_news(
    symbol: str,
    db: DbSession,
    current_user: OptionalUser,
    limit: int = Query(default=10, ge=1, le=50),
) -> NewsResponse:
    """Get news articles for a stock with sentiment analysis.

    Fetches recent news articles related to the stock symbol and analyzes
    their sentiment (positive, negative, neutral).

    Args:
        symbol: Stock symbol (e.g., "AAPL", "MSFT")
        limit: Maximum number of articles to return (1-50, default 10)

    Returns:
        News articles with sentiment scores and aggregate statistics.
    """
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = ResearchService(provider=provider)
    news = await service.get_news(symbol, limit=limit)

    return NewsResponse(
        symbol=news.symbol,
        articles=[
            NewsArticleResponse(
                title=a.title,
                url=a.url,
                source=a.source,
                published_at=a.published_at,
                summary=a.summary,
                thumbnail_url=a.thumbnail_url,
                related_symbols=a.related_symbols,
                sentiment=a.sentiment.value,
                sentiment_score=a.sentiment_score,
            )
            for a in news.articles
        ],
        total_count=news.total_count,
        average_sentiment=news.average_sentiment,
        positive_count=news.positive_count,
        negative_count=news.negative_count,
        neutral_count=news.neutral_count,
        last_updated=news.last_updated,
    )


@router.get("/market/news", response_model=NewsResponse)
async def get_market_news(
    db: DbSession,
    current_user: OptionalUser,
    category: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
) -> NewsResponse:
    """Get general market news with sentiment analysis.

    Fetches recent market-wide news articles and analyzes their sentiment.

    Args:
        category: Optional category filter (e.g., "technology", "finance")
        limit: Maximum number of articles to return (1-50, default 10)

    Returns:
        Market news articles with sentiment scores and aggregate statistics.
    """
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = ResearchService(provider=provider)
    news = await service.get_market_news(category=category, limit=limit)

    return NewsResponse(
        symbol=None,
        articles=[
            NewsArticleResponse(
                title=a.title,
                url=a.url,
                source=a.source,
                published_at=a.published_at,
                summary=a.summary,
                thumbnail_url=a.thumbnail_url,
                related_symbols=a.related_symbols,
                sentiment=a.sentiment.value,
                sentiment_score=a.sentiment_score,
            )
            for a in news.articles
        ],
        total_count=news.total_count,
        average_sentiment=news.average_sentiment,
        positive_count=news.positive_count,
        negative_count=news.negative_count,
        neutral_count=news.neutral_count,
        last_updated=news.last_updated,
    )

