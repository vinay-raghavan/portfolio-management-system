"""Research API routes."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, OptionalUser, RedisClient
from app.modules.data.service import get_user_research_data_provider
from app.modules.research.digest_service import DigestService
from app.modules.research.notes_service import ResearchNoteService
from app.modules.research.recommendation_service import RecommendationService
from app.modules.research.schemas import (
    DailyDigestResponse,
    DigestListResponse,
    DividendRecordResponse,
    DividendsResponse,
    FundamentalsResponse,
    NewsArticleResponse,
    NewsResponse,
    PeerComparisonResponse,
    PeerStock,
    RecommendationsResponse,
    RecommendationStock,
    ResearchNoteCreate,
    ResearchNoteListResponse,
    ResearchNoteResponse,
    ResearchNoteUpdate,
    SectorListResponse,
    SectorPerformance,
    SectorStocksResponse,
    StockResearchResponse,
    UniverseResearchResponse,
    UniverseStock,
)
from app.modules.research.service import ResearchService

router = APIRouter()


# =============================================================================
# Helper Functions for Type Conversion
# =============================================================================


def _convert_dividends(dividends: Any) -> DividendsResponse | None:
    """Convert shared DividendData to research DividendsResponse."""
    if dividends is None:
        return None
    return DividendsResponse(
        symbol=dividends.symbol,
        dividend_yield=dividends.dividend_yield,
        dividend_rate=dividends.dividend_rate,
        payout_ratio=dividends.payout_ratio,
        ex_dividend_date=dividends.ex_dividend_date,
        five_year_avg_yield=dividends.five_year_avg_yield,
        dividend_growth_rate=dividends.dividend_growth_rate,
        history=[
            DividendRecordResponse(
                ex_date=d.ex_date,
                payment_date=d.payment_date,
                amount=d.amount,
                currency=d.currency,
            )
            for d in dividends.history
        ],
        last_updated=dividends.last_updated,
    )


def _convert_news(news: Any) -> NewsResponse | None:
    """Convert shared NewsResponse to research NewsResponse."""
    if news is None:
        return None
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
                sentiment=a.sentiment.value if hasattr(a.sentiment, "value") else str(a.sentiment),
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


# =============================================================================
# Fundamentals Endpoint
# =============================================================================


@router.get("/{symbol}/fundamentals", response_model=FundamentalsResponse)
async def get_fundamentals(
    symbol: str,
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
) -> FundamentalsResponse:
    """Get fundamental analysis data for a stock.

    Includes valuation ratios (P/E, P/B, P/S, PEG), earnings metrics,
    revenue, profitability margins, returns (ROE, ROA), and balance sheet metrics.

    Uses the user's preferred research data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    provider = None
    if current_user:
        provider = await get_user_research_data_provider(db, current_user.id)

    service = ResearchService(provider=provider, redis=redis)
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
    redis: RedisClient,
    current_user: OptionalUser,
) -> DividendsResponse:
    """Get dividend history and metrics for a stock.

    Includes current yield, dividend rate, payout ratio, ex-dividend date,
    5-year average yield, dividend growth rate, and historical dividend records.

    Uses the user's preferred research data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    provider = None
    if current_user:
        provider = await get_user_research_data_provider(db, current_user.id)

    service = ResearchService(provider=provider, redis=redis)
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


# =============================================================================
# Market News Endpoint (must be before /{symbol}/news to avoid route collision)
# =============================================================================


@router.get("/market/news", response_model=NewsResponse)
async def get_market_news(
    db: DbSession,
    redis: RedisClient,
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
        provider = await get_user_research_data_provider(db, current_user.id)

    service = ResearchService(provider=provider, redis=redis)
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


# =============================================================================
# Stock News Endpoint
# =============================================================================


@router.get("/{symbol}/news", response_model=NewsResponse)
async def get_news(
    symbol: str,
    db: DbSession,
    redis: RedisClient,
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
        provider = await get_user_research_data_provider(db, current_user.id)

    service = ResearchService(provider=provider, redis=redis)
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


@router.get("/{symbol}/peers", response_model=PeerComparisonResponse)
async def get_peers(
    symbol: str,
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
    limit: int = Query(default=10, ge=1, le=20, description="Maximum number of peers"),
) -> PeerComparisonResponse:
    """Get peer stocks for comparison.

    Finds stocks in the same industry/sector and returns comparative metrics.

    Args:
        symbol: Stock symbol (e.g., "AAPL", "MSFT")
        limit: Maximum number of peer stocks to return (1-20, default 10)

    Returns:
        Peer stocks with comparative metrics and sector averages.
    """
    provider = None
    if current_user:
        provider = await get_user_research_data_provider(db, current_user.id)

    service = ResearchService(provider=provider, redis=redis)
    data = await service.get_peers(symbol, limit=limit)

    return PeerComparisonResponse(
        symbol=data["symbol"],
        sector=data.get("sector"),
        industry=data.get("industry"),
        peers=[
            PeerStock(
                symbol=p.get("symbol", ""),
                name=p.get("name"),
                current_price=p.get("current_price"),
                price_change_pct=p.get("price_change_pct"),
                market_cap=p.get("market_cap"),
                pe_ratio=p.get("pe_ratio"),
                pb_ratio=p.get("pb_ratio"),
                dividend_yield=p.get("dividend_yield"),
                roe=p.get("roe"),
                revenue_growth=p.get("revenue_growth"),
            )
            for p in data.get("peers", [])
        ],
        sector_avg_pe=data.get("sector_avg_pe"),
        sector_avg_pb=data.get("sector_avg_pb"),
        sector_avg_dividend_yield=data.get("sector_avg_dividend_yield"),
        last_updated=datetime.now(UTC),
    )


# =============================================================================
# Sector Endpoints
# =============================================================================


@router.get("/sectors", response_model=SectorListResponse)
async def get_sectors(
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
) -> SectorListResponse:
    """Get all sectors with performance metrics.

    Returns a list of all sectors with their daily/weekly/monthly performance,
    stock count, and top gainers/losers.

    Note: Currently returns a predefined sector list. Performance data
    requires a stock universe database to calculate.
    """
    provider = None
    if current_user:
        provider = await get_user_research_data_provider(db, current_user.id)

    service = ResearchService(provider=provider, redis=redis)
    sectors_data = await service.get_sectors()

    return SectorListResponse(
        sectors=[
            SectorPerformance(
                sector=s["sector"],
                change_1d=s.get("change_1d"),
                change_1w=s.get("change_1w"),
                change_1m=s.get("change_1m"),
                change_3m=s.get("change_3m"),
                change_1y=s.get("change_1y"),
                stock_count=s.get("stock_count", 0),
                top_gainer=s.get("top_gainer"),
                top_loser=s.get("top_loser"),
            )
            for s in sectors_data
        ],
        last_updated=datetime.now(UTC),
    )


@router.get("/sectors/{sector}", response_model=SectorStocksResponse)
async def get_sector_stocks(
    sector: str,
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
    limit: int = Query(default=20, ge=1, le=50, description="Maximum number of stocks"),
) -> SectorStocksResponse:
    """Get stocks within a specific sector.

    Returns stocks belonging to the specified sector with their metrics
    including price, market cap, P/E ratio, and performance.

    Note: Currently a stub - requires a stock universe database to implement.

    Args:
        sector: Sector name (e.g., "Technology", "Healthcare")
        limit: Maximum number of stocks to return (1-50, default 20)
    """
    provider = None
    if current_user:
        provider = await get_user_research_data_provider(db, current_user.id)

    service = ResearchService(provider=provider, redis=redis)
    data = await service.get_sector_stocks(sector, limit=limit)

    return SectorStocksResponse(
        sector=data["sector"],
        stocks=[
            PeerStock(
                symbol=s.get("symbol", ""),
                name=s.get("name"),
                current_price=s.get("current_price"),
                price_change_pct=s.get("price_change_pct"),
                market_cap=s.get("market_cap"),
                pe_ratio=s.get("pe_ratio"),
                pb_ratio=s.get("pb_ratio"),
                dividend_yield=s.get("dividend_yield"),
                roe=s.get("roe"),
                revenue_growth=s.get("revenue_growth"),
            )
            for s in data.get("stocks", [])
        ],
        total_count=data.get("total_count", 0),
        last_updated=datetime.now(UTC),
    )


# =============================================================================
# Research Notes Endpoints
# =============================================================================


@router.get("/notes", response_model=ResearchNoteListResponse)
async def get_research_notes(
    db: DbSession,
    current_user: CurrentUser,
    symbol: str | None = Query(default=None, description="Filter by symbol"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of notes"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> ResearchNoteListResponse:
    """Get research notes for the current user.

    Optionally filter by stock symbol. Requires authentication.

    Args:
        symbol: Optional symbol to filter notes by
        limit: Maximum number of notes to return (1-100, default 50)
        offset: Offset for pagination (default 0)
    """
    service = ResearchNoteService(db)
    notes, total_count = await service.get_notes(
        user_id=current_user.id,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )

    return ResearchNoteListResponse(
        notes=[
            ResearchNoteResponse(
                id=n.id,
                symbol=n.symbol,
                title=n.title,
                content=n.content,
                rating=n.rating,
                target_price=float(n.target_price) if n.target_price else None,
                tags=n.tags,
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in notes
        ],
        total_count=total_count,
    )


@router.post("/notes", response_model=ResearchNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_research_note(
    data: ResearchNoteCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ResearchNoteResponse:
    """Create a new research note.

    Saves personal research notes, ratings, and target prices for a stock.
    Requires authentication.
    """
    service = ResearchNoteService(db)
    note = await service.create_note(user_id=current_user.id, data=data)

    return ResearchNoteResponse(
        id=note.id,
        symbol=note.symbol,
        title=note.title,
        content=note.content,
        rating=note.rating,
        target_price=float(note.target_price) if note.target_price else None,
        tags=note.tags,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get("/notes/{note_id}", response_model=ResearchNoteResponse)
async def get_research_note(
    note_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> ResearchNoteResponse:
    """Get a specific research note by ID.

    Requires authentication. Users can only access their own notes.
    """
    service = ResearchNoteService(db)
    note = await service.get_note(user_id=current_user.id, note_id=note_id)

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research note not found: {note_id}",
        )

    return ResearchNoteResponse(
        id=note.id,
        symbol=note.symbol,
        title=note.title,
        content=note.content,
        rating=note.rating,
        target_price=float(note.target_price) if note.target_price else None,
        tags=note.tags,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.patch("/notes/{note_id}", response_model=ResearchNoteResponse)
async def update_research_note(
    note_id: str,
    data: ResearchNoteUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ResearchNoteResponse:
    """Update a research note.

    Partial update - only provided fields will be updated.
    Requires authentication. Users can only update their own notes.
    """
    service = ResearchNoteService(db)
    note = await service.update_note(user_id=current_user.id, note_id=note_id, data=data)

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research note not found: {note_id}",
        )

    return ResearchNoteResponse(
        id=note.id,
        symbol=note.symbol,
        title=note.title,
        content=note.content,
        rating=note.rating,
        target_price=float(note.target_price) if note.target_price else None,
        tags=note.tags,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research_note(
    note_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete a research note.

    Permanently deletes the note. Requires authentication.
    Users can only delete their own notes.
    """
    service = ResearchNoteService(db)
    deleted = await service.delete_note(user_id=current_user.id, note_id=note_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research note not found: {note_id}",
        )


# =============================================================================
# Daily Digest Endpoints
# =============================================================================


@router.get("/digest", response_model=DigestListResponse)
async def get_digests(
    db: DbSession,
    limit: int = Query(10, ge=1, le=50, description="Number of digests to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> DigestListResponse:
    """Get list of available daily digests.

    Returns paginated list of daily market digests ordered by date (newest first).
    Each digest contains market summary, top movers, sector performance, etc.
    """
    service = DigestService(db)
    digests, total = await service.get_digests(limit=limit, offset=offset)

    return DigestListResponse(
        digests=[service.digest_to_response(d) for d in digests],
        total_count=total,
    )


@router.get("/digest/latest", response_model=DailyDigestResponse | None)
async def get_latest_digest(
    db: DbSession,
) -> DailyDigestResponse | None:
    """Get the most recent daily digest.

    Returns the latest generated digest, or null if no digests exist.
    """
    service = DigestService(db)
    digest = await service.get_latest_digest()

    if not digest:
        return None

    return service.digest_to_response(digest)


@router.get("/digest/{date}", response_model=DailyDigestResponse)
async def get_digest_by_date(
    date: str,
    db: DbSession,
) -> DailyDigestResponse:
    """Get daily digest for a specific date.

    Args:
        date: Date in YYYY-MM-DD format

    Returns:
        Daily digest for the specified date

    Raises:
        404: If no digest exists for the specified date
    """
    from datetime import date as date_type

    try:
        target_date = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {date}. Expected YYYY-MM-DD",
        )

    service = DigestService(db)
    digest = await service.get_digest_by_date(target_date)

    if not digest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No digest found for date: {date}",
        )

    return service.digest_to_response(digest)


@router.post("/digest/generate", response_model=DailyDigestResponse)
async def generate_digest(
    db: DbSession,
    current_user: CurrentUser,
    date: str | None = Query(None, description="Date in YYYY-MM-DD format. Defaults to today."),
) -> DailyDigestResponse:
    """Generate a daily digest.

    This endpoint is typically called by the Celery worker at market close,
    but can be triggered manually by authenticated users.

    Args:
        date: Optional date to generate digest for. Defaults to today.

    Returns:
        The generated daily digest

    Raises:
        409: If a digest already exists for the specified date
    """
    from datetime import date as date_type

    target_date = None
    if date:
        try:
            target_date = date_type.fromisoformat(date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {date}. Expected YYYY-MM-DD",
            )

    service = DigestService(db)

    # Check if digest already exists
    existing = await service.get_digest_by_date(target_date or date_type.today())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Digest already exists for date: {target_date or date_type.today()}",
        )

    digest = await service.generate_digest(target_date)
    return service.digest_to_response(digest)


# =============================================================================
# Recommendations Endpoints
# =============================================================================


@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
    category: str | None = Query(
        None, description="Filter by category: quality, value, growth, dividend"
    ),
    limit: int = Query(20, ge=1, le=50, description="Maximum recommendations"),
) -> RecommendationsResponse:
    """Get daily stock recommendations combining fundamental + technical analysis.

    Returns stocks ranked by combined score (60% fundamental, 40% technical).
    Categories include: quality, value, growth, dividend, momentum, breakout.

    Uses the user's selected research data provider setting (default: Yahoo).
    """
    from app.modules.algo.universe_service import PREDEFINED_UNIVERSES

    # Use user's research data provider setting if authenticated
    provider = None
    if current_user:
        provider = await get_user_research_data_provider(db, current_user.id)

    service = RecommendationService(db, provider=provider, redis=redis)

    # Get NIFTY50 stocks for recommendations (can be expanded)
    symbols = PREDEFINED_UNIVERSES.get("NIFTY50", {}).get("symbols", [])[:20]

    recommendations = await service.generate_recommendations(
        symbols=symbols,
        limit=limit,
    )

    # Filter by category if specified
    if category:
        recommendations = [r for r in recommendations if r.get("category") == category]

    # Convert to response format
    rec_stocks = [
        RecommendationStock(
            symbol=r["symbol"],
            name=r.get("name"),
            sector=r.get("sector"),
            industry=r.get("industry"),
            current_price=r.get("current_price"),
            price_change_pct=r.get("price_change_pct"),
            fundamental_score=r.get("fundamental_score", 0),
            technical_score=r.get("technical_score", 0),
            combined_score=r.get("combined_score", 0),
            category=r.get("category", "quality"),
            pe_ratio=r.get("pe_ratio"),
            pb_ratio=r.get("pb_ratio"),
            roe=r.get("roe"),
            debt_to_equity=r.get("debt_to_equity"),
            dividend_yield=r.get("dividend_yield"),
            eps_growth=r.get("eps_growth"),
            rsi=r.get("rsi"),
            above_200ma=r.get("above_200ma"),
            volume_ratio=r.get("volume_ratio"),
            pct_from_52w_high=r.get("pct_from_52w_high"),
            thesis=r.get("thesis"),
            reasons=r.get("reasons", []),
        )
        for r in recommendations
    ]

    # Calculate category breakdown
    by_category: dict[str, int] = {}
    for r in rec_stocks:
        by_category[r.category] = by_category.get(r.category, 0) + 1

    # Calculate averages
    avg_fund = (
        sum(r.fundamental_score for r in rec_stocks) / len(rec_stocks) if rec_stocks else None
    )
    avg_tech = sum(r.technical_score for r in rec_stocks) / len(rec_stocks) if rec_stocks else None

    return RecommendationsResponse(
        date=datetime.now(UTC),
        recommendations=rec_stocks,
        total_count=len(rec_stocks),
        by_category=by_category,
        avg_fundamental_score=avg_fund,
        avg_technical_score=avg_tech,
    )


# =============================================================================
# Universe Research Endpoints
# =============================================================================


@router.get("/universe/{universe_name}", response_model=UniverseResearchResponse)
async def get_universe_research(
    universe_name: str,
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
    max_pe: float | None = Query(None, description="Maximum P/E ratio"),
    min_roe: float | None = Query(None, description="Minimum ROE %"),
    max_debt: float | None = Query(None, description="Maximum Debt/Equity"),
    min_dividend: float | None = Query(None, description="Minimum dividend yield %"),
    sector: str | None = Query(None, description="Filter by sector"),
    limit: int = Query(50, ge=1, le=100, description="Maximum stocks"),
) -> UniverseResearchResponse:
    """Get fundamental research data for a stock universe.

    Supported universes: NIFTY50, NIFTY100, NIFTY500, FO_STOCKS, etc.
    Returns stocks with fundamental metrics, sorted by quality score.
    """
    from app.modules.algo.universe_service import PREDEFINED_UNIVERSES
    from app.modules.screener.filters import FundamentalCriteria

    # Use research data provider for fundamental research
    provider = None
    if current_user:
        provider = await get_user_research_data_provider(db, current_user.id)

    service = RecommendationService(db, provider=provider, redis=redis)

    # Resolve universe
    universe_upper = universe_name.upper().replace(" ", "")
    if universe_upper in PREDEFINED_UNIVERSES:
        symbols = PREDEFINED_UNIVERSES[universe_upper]["symbols"]
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Universe not found: {universe_name}. Available: NIFTY50, NIFTY100, etc.",
        )

    # Build criteria if filters provided
    criteria = None
    if any([max_pe, min_roe, max_debt, min_dividend, sector]):
        criteria = FundamentalCriteria(
            max_pe=max_pe,
            min_roe=min_roe,
            max_debt_to_equity=max_debt,
            min_dividend_yield=min_dividend,
            sectors=[sector] if sector else None,
        )

    # Get fundamental data
    stocks_data = await service.get_universe_fundamentals(
        symbols=symbols[:limit],
        criteria=criteria,
    )

    # Convert to response format
    stocks = [
        UniverseStock(
            symbol=s["symbol"],
            name=s.get("name"),
            sector=s.get("sector"),
            industry=s.get("industry"),
            current_price=s.get("current_price"),
            price_change_pct=s.get("price_change_pct"),
            market_cap=s.get("market_cap"),
            pe_ratio=s.get("pe_ratio"),
            pb_ratio=s.get("pb_ratio"),
            ps_ratio=s.get("ps_ratio"),
            roe=s.get("roe"),
            roa=s.get("roa"),
            profit_margin=s.get("profit_margin"),
            debt_to_equity=s.get("debt_to_equity"),
            current_ratio=s.get("current_ratio"),
            dividend_yield=s.get("dividend_yield"),
            eps_growth=s.get("eps_growth"),
            revenue_growth=s.get("revenue_growth"),
            fundamental_score=s.get("fundamental_score"),
        )
        for s in stocks_data
    ]

    # Calculate sector breakdown
    by_sector: dict[str, int] = {}
    for s in stocks:
        if s.sector:
            by_sector[s.sector] = by_sector.get(s.sector, 0) + 1

    filters_applied = {}
    if max_pe:
        filters_applied["max_pe"] = max_pe
    if min_roe:
        filters_applied["min_roe"] = min_roe
    if max_debt:
        filters_applied["max_debt_to_equity"] = max_debt
    if min_dividend:
        filters_applied["min_dividend_yield"] = min_dividend
    if sector:
        filters_applied["sector"] = sector

    return UniverseResearchResponse(
        universe=universe_name,
        stocks=stocks,
        total_count=len(stocks),
        by_sector=by_sector,
        filters_applied=filters_applied if filters_applied else None,
        last_updated=datetime.now(UTC),
    )


# =============================================================================
# Full Research Endpoint (Catch-All - Must Be Last)
# =============================================================================


@router.get("/{symbol}", response_model=StockResearchResponse)
async def get_stock_research(
    symbol: str,
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
    news_limit: int = Query(5, ge=1, le=20, description="Number of news articles to include"),
) -> StockResearchResponse:
    """Get comprehensive research data for a stock.

    Combines fundamental analysis, dividend data, and recent news with sentiment
    into a single response. This is the primary endpoint for stock research.

    Uses the user's preferred data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.

    Note: This route is defined last because it matches any path segment.
    More specific routes like /sectors, /digest, etc. are defined above.
    """
    provider = None
    if current_user:
        provider = await get_user_research_data_provider(db, current_user.id)

    service = ResearchService(provider=provider, redis=redis)
    data = await service.get_full_research(symbol, news_limit=news_limit)

    # Convert shared module types to research response types
    dividends_response = _convert_dividends(data.get("dividends"))
    news_response = _convert_news(data.get("news"))

    return StockResearchResponse(
        symbol=data["symbol"],
        name=data.get("name"),
        sector=data.get("sector"),
        industry=data.get("industry"),
        current_price=data.get("current_price"),
        price_change=data.get("price_change"),
        price_change_pct=data.get("price_change_pct"),
        fundamentals=data.get("fundamentals"),
        dividends=dividends_response,
        news=news_response,
        last_updated=datetime.now(UTC),
    )
