"""Screener API routes."""

import logging
from datetime import UTC

from fastapi import APIRouter, HTTPException, status
from shared.providers.data import get_data_provider

from app.api.deps import CurrentUser, DbSession
from app.core.celery_client import celery_client
from app.core.redis import get_redis
from app.modules.algo.universe_service import (
    DYNAMIC_UNIVERSES,
    PREDEFINED_UNIVERSES,
    UniverseService,
)
from app.modules.data.service import get_user_data_provider
from app.modules.screener.schemas import (
    CategoryPerformanceStats,
    CategoryRecommendations,
    CreateUniverseFromScreenerRequest,
    CreateUniverseFromScreenerResponse,
    CustomScreenerCreate,
    CustomScreenerListResponse,
    CustomScreenerResponse,
    CustomScreenerUpdate,
    DailyRecommendationsResponse,
    FilterConfig,
    OverallPerformanceStats,
    RecommendationCategory,
    RecommendationItem,
    ScreenerPresetRunRequest,
    ScreenerPresetsResponse,
    ScreenerRunRequest,
    ScreenerRunResponse,
    UpdateReturnsResponse,
)
from app.modules.screener.service import ScreenerService

logger = logging.getLogger(__name__)

router = APIRouter()

# Threshold for async execution (large universes)
ASYNC_UNIVERSE_THRESHOLD = 500


@router.get("/presets", response_model=ScreenerPresetsResponse)
async def get_presets(current_user: CurrentUser) -> ScreenerPresetsResponse:
    """Get all available preset screeners."""
    presets = ScreenerService.get_preset_definitions()
    return ScreenerPresetsResponse(presets=presets)


@router.post("/run", response_model=ScreenerRunResponse)
async def run_screener(
    data: ScreenerRunRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ScreenerRunResponse:
    """Run a custom screener on a universe of stocks."""
    # Resolve universe to symbols
    symbols = await _resolve_universe(data.universe, db)
    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No symbols found for universe: {data.universe}",
        )

    # Get Redis client for caching
    redis = await get_redis()

    # Get user's preferred data provider (Yahoo, Fyers, or NSE)
    provider = await get_user_data_provider(db, current_user.id)
    if provider is None:
        # Default to Yahoo if no user preference
        provider = get_data_provider("yahoo")

    service = ScreenerService(db, redis=redis)
    result = await service.run_screener(
        user_id=current_user.id,
        symbols=symbols,
        filters=data.filters,
        universe=data.universe,
        min_score=data.min_score,
        top_n=data.top_n,
        data_provider=provider,
    )
    await db.commit()
    return result


@router.post("/run/async")
async def run_screener_async(
    data: ScreenerRunRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Queue a screener to run asynchronously for large universes.

    Returns a task_id that can be used to check the status.
    """
    # Validate universe exists
    symbols = await _resolve_universe(data.universe, db)
    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No symbols found for universe: {data.universe}",
        )

    # Queue the task
    task = celery_client.send_task(
        "worker.tasks.screener.run_screener_async",
        args=[
            current_user.id,
            data.universe,
            [f.model_dump() for f in data.filters],
            data.min_score,
            data.top_n,
            None,  # preset
        ],
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "universe": data.universe,
        "symbol_count": len(symbols),
        "message": f"Screener queued for {len(symbols)} symbols",
    }


@router.post("/run/preset", response_model=ScreenerRunResponse)
async def run_preset_screener(
    data: ScreenerPresetRunRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ScreenerRunResponse:
    """Run a preset screener on a universe of stocks."""
    preset = ScreenerService.get_preset(data.preset)
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset not found: {data.preset}",
        )

    symbols = await _resolve_universe(data.universe, db)
    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No symbols found for universe: {data.universe}",
        )

    # Get Redis client for caching
    redis = await get_redis()

    # Get user's preferred data provider (Yahoo, Fyers, or NSE)
    provider = await get_user_data_provider(db, current_user.id)
    if provider is None:
        provider = get_data_provider("yahoo")

    service = ScreenerService(db, redis=redis)
    result = await service.run_screener(
        user_id=current_user.id,
        symbols=symbols,
        filters=preset.filters,
        universe=data.universe,
        min_score=data.min_score,
        top_n=data.top_n,
        data_provider=provider,
        preset=data.preset.value,
    )
    await db.commit()
    return result


@router.get("/results/{run_id}", response_model=ScreenerRunResponse)
async def get_screener_results(
    run_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> ScreenerRunResponse:
    """Get cached results from a previous screener run."""
    service = ScreenerService(db)
    run = await service.get_screener_run(current_user.id, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screener run not found",
        )

    from app.modules.screener.schemas import ScreenerResultItem

    return ScreenerRunResponse(
        run_id=run.id,
        status="completed",
        universe=run.universe,
        total_screened=run.total_screened,
        passed_count=run.passed_count,
        min_score=run.min_score,
        results=[
            ScreenerResultItem(
                symbol=r.symbol,
                rank=r.rank,
                score=r.score,
                passed=r.passed,
                filter_scores=r.filter_scores,
                reasons=r.reasons,
                metadata=r.metadata,
            )
            for r in sorted(run.results, key=lambda x: x.rank)
        ],
        executed_at=run.executed_at,
        duration_ms=run.duration_ms,
    )


@router.get("/custom", response_model=CustomScreenerListResponse)
async def get_custom_screeners(
    db: DbSession,
    current_user: CurrentUser,
) -> CustomScreenerListResponse:
    """Get all custom screeners for the current user."""
    service = ScreenerService(db)
    screeners = await service.get_custom_screeners(current_user.id)
    return CustomScreenerListResponse(screeners=[_screener_to_response(s) for s in screeners])


@router.post("/custom", response_model=CustomScreenerResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_screener(
    data: CustomScreenerCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomScreenerResponse:
    """Create a new custom screener configuration."""
    service = ScreenerService(db)
    screener = await service.create_custom_screener(current_user.id, data)
    await db.commit()
    return _screener_to_response(screener)


@router.get("/custom/{screener_id}", response_model=CustomScreenerResponse)
async def get_custom_screener(
    screener_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomScreenerResponse:
    """Get a specific custom screener."""
    service = ScreenerService(db)
    screener = await service.get_custom_screener(current_user.id, screener_id)
    if not screener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom screener not found",
        )
    return _screener_to_response(screener)


@router.patch("/custom/{screener_id}", response_model=CustomScreenerResponse)
async def update_custom_screener(
    screener_id: str,
    data: CustomScreenerUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomScreenerResponse:
    """Update a custom screener configuration."""
    service = ScreenerService(db)
    screener = await service.update_custom_screener(current_user.id, screener_id, data)
    if not screener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom screener not found",
        )
    await db.commit()
    return _screener_to_response(screener)


@router.delete("/custom/{screener_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_screener(
    screener_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete a custom screener."""
    service = ScreenerService(db)
    deleted = await service.delete_custom_screener(current_user.id, screener_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom screener not found",
        )
    await db.commit()


@router.post("/custom/{screener_id}/run", response_model=ScreenerRunResponse)
async def run_custom_screener(
    screener_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> ScreenerRunResponse:
    """Run a saved custom screener."""
    redis = await get_redis()
    service = ScreenerService(db, redis=redis)
    screener = await service.get_custom_screener(current_user.id, screener_id)
    if not screener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom screener not found",
        )

    symbols = await _resolve_universe(screener.universe, db)
    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No symbols found for universe: {screener.universe}",
        )

    filters = [FilterConfig(**f) for f in screener.filters]

    # Get user's preferred data provider (Yahoo, Fyers, or NSE)
    provider = await get_user_data_provider(db, current_user.id)
    if provider is None:
        provider = get_data_provider("yahoo")

    result = await service.run_screener(
        user_id=current_user.id,
        symbols=symbols,
        filters=filters,
        universe=screener.universe,
        min_score=screener.min_score,
        top_n=screener.top_n,
        data_provider=provider,
        custom_screener_id=screener.id,
    )
    await db.commit()
    return result


# =============================================================================
# Recommendations Endpoints
# =============================================================================


# Category metadata for display
CATEGORY_METADATA = {
    RecommendationCategory.MOMENTUM: {
        "title": "Top Momentum",
        "description": "Stocks with strong upward momentum and volume",
    },
    RecommendationCategory.BREAKOUT: {
        "title": "Potential Breakouts",
        "description": "Stocks breaking out of consolidation patterns",
    },
    RecommendationCategory.PULLBACK: {
        "title": "Pullback Opportunities",
        "description": "Strong stocks with temporary pullbacks",
    },
    RecommendationCategory.SECTOR: {
        "title": "Strong Sectors",
        "description": "Leaders in the strongest performing sectors",
    },
}


@router.get("/recommendations", response_model=DailyRecommendationsResponse)
async def get_recommendations(
    db: DbSession,
    current_user: CurrentUser,
    date: str | None = None,
) -> DailyRecommendationsResponse:
    """Get daily stock recommendations.

    Returns recommendations across all categories (momentum, breakout, pullback, sector).
    By default returns today's recommendations.
    """
    from datetime import datetime

    from sqlalchemy import func, select

    from app.modules.screener.models import DailyRecommendation

    # Parse date or use today
    if date:
        try:
            target_date = datetime.fromisoformat(date).replace(tzinfo=UTC)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use ISO format: YYYY-MM-DD",
            )
    else:
        target_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    # Get the most recent recommendation date up to target_date
    latest_date_result = await db.execute(
        select(func.max(DailyRecommendation.date)).where(DailyRecommendation.date <= target_date)
    )
    latest_date = latest_date_result.scalar_one_or_none()

    if not latest_date:
        return DailyRecommendationsResponse(
            date=target_date,
            generated_at=target_date,
            categories=[],
        )

    # Fetch all recommendations for that date
    result = await db.execute(
        select(DailyRecommendation)
        .where(func.date(DailyRecommendation.date) == func.date(latest_date))
        .order_by(DailyRecommendation.category, DailyRecommendation.rank)
    )
    recommendations = list(result.scalars().all())

    # Group by category
    categories_data: dict[str, list[DailyRecommendation]] = {}
    for rec in recommendations:
        if rec.category not in categories_data:
            categories_data[rec.category] = []
        categories_data[rec.category].append(rec)

    # Build response
    categories = []
    for cat_str, recs in categories_data.items():
        try:
            cat_enum = RecommendationCategory(cat_str)
        except ValueError:
            continue  # Skip unknown categories

        metadata = CATEGORY_METADATA.get(cat_enum, {"title": cat_str, "description": ""})

        items = [
            RecommendationItem(
                symbol=r.symbol,
                rank=r.rank,
                score=r.score,
                price_at_rec=r.price_at_rec,
                filter_scores=r.filter_scores or {},
                reasons=r.reasons or [],
                metadata=r.metadata or {},
                return_1d=r.return_1d,
                return_1w=r.return_1w,
                return_1m=r.return_1m,
            )
            for r in recs
        ]

        categories.append(
            CategoryRecommendations(
                category=cat_enum,
                title=metadata["title"],
                description=metadata["description"],
                recommendations=items,
            )
        )

    return DailyRecommendationsResponse(
        date=latest_date,
        generated_at=recommendations[0].created_at if recommendations else latest_date,
        categories=categories,
    )


@router.post("/recommendations/store")
async def store_recommendations(
    db: DbSession,
    date: str,
    category: str,
    results: list[dict],
) -> dict:
    """Internal endpoint to store daily recommendations.

    Called by the Celery task to persist recommendations.
    Requires internal API key authentication.
    """
    from datetime import datetime

    from app.modules.screener.models import DailyRecommendation

    # Parse date
    try:
        rec_date = datetime.fromisoformat(date).replace(tzinfo=UTC)
    except ValueError:
        rec_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    # Delete existing recommendations for this date/category (replace on re-run)
    from sqlalchemy import delete, func

    await db.execute(
        delete(DailyRecommendation).where(
            func.date(DailyRecommendation.date) == func.date(rec_date),
            DailyRecommendation.category == category,
        )
    )

    # Store new recommendations
    stored_count = 0
    for i, result in enumerate(results):
        rec = DailyRecommendation(
            date=rec_date,
            category=category,
            symbol=result.get("symbol", ""),
            rank=i + 1,
            score=result.get("score", 0.0),
            price_at_rec=result.get("metadata", {}).get("current_price", 0.0),
            filter_scores=result.get("filter_scores", {}),
            reasons=result.get("reasons", []),
            extra_data=result.get("metadata", {}),
        )
        db.add(rec)
        stored_count += 1

    await db.commit()

    return {
        "status": "success",
        "date": date,
        "category": category,
        "stored_count": stored_count,
    }


# ============== Screener → Algo Integration ==============


@router.post("/create-universe", response_model=CreateUniverseFromScreenerResponse)
async def create_universe_from_screener(
    data: CreateUniverseFromScreenerRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> CreateUniverseFromScreenerResponse:
    """Create a trading universe from screener results.

    This allows users to save screener results as a universe that can be used
    in algo strategies. If is_dynamic is True, the universe can be refreshed
    by re-running the screener configuration.
    """
    from app.modules.algo.schemas import UniverseCreate

    universe_svc = UniverseService(db)

    # Build filter_criteria for dynamic universes
    filter_criteria = None
    if data.is_dynamic and data.screener_config:
        filter_criteria = {
            "source": "screener",
            "screener_config": data.screener_config,
        }

    # Create the universe
    universe_data = UniverseCreate(
        name=data.name,
        description=data.description or f"Created from screener with {len(data.symbols)} symbols",
        symbols=data.symbols,
        filter_criteria=filter_criteria,
        is_dynamic=data.is_dynamic,
    )

    universe = await universe_svc.create(str(current_user.id), universe_data)

    return CreateUniverseFromScreenerResponse(
        id=universe.id,
        name=universe.name,
        description=universe.description,
        symbol_count=len(data.symbols),
        is_dynamic=data.is_dynamic,
        created_at=universe.created_at,
    )


@router.post("/refresh-universe/{universe_id}")
async def refresh_screener_universe(
    universe_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Refresh a screener-based dynamic universe by re-running the screener.

    Only works for universes created from screeners with is_dynamic=True.
    """
    from sqlalchemy import select

    from app.modules.algo.models import Universe

    # Get the universe
    result = await db.execute(
        select(Universe).where(
            Universe.id == universe_id,
            Universe.user_id == str(current_user.id),
        )
    )
    universe = result.scalar_one_or_none()

    if not universe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Universe not found",
        )

    if not universe.is_dynamic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Universe is not dynamic and cannot be refreshed",
        )

    filter_criteria = universe.filter_criteria or {}
    if filter_criteria.get("source") != "screener":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Universe was not created from a screener",
        )

    screener_config = filter_criteria.get("screener_config")
    if not screener_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Screener configuration not found in universe",
        )

    # Re-run the screener
    redis = await get_redis()
    service = ScreenerService(db, redis)

    # Get user's preferred data provider (Yahoo, Fyers, or NSE)
    provider = await get_user_data_provider(db, current_user.id)
    if provider is None:
        provider = get_data_provider("yahoo")

    try:
        # Resolve the universe symbols
        universe_name = screener_config.get("universe", "NIFTY500")
        symbols = await _resolve_universe(universe_name, db)

        if not symbols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not resolve universe: {universe_name}",
            )

        # Convert filter configs
        filters = [FilterConfig(**f) for f in screener_config.get("filters", [])]

        # Run the screener
        run_result = await service.run_screener(
            symbols=symbols,
            filters=filters,
            min_score=screener_config.get("min_score", 0.5),
            top_n=screener_config.get("top_n"),
            user_id=str(current_user.id),
            use_cache=False,  # Force fresh results
            data_provider=provider,
        )

        # Update universe symbols
        new_symbols = [r.symbol for r in run_result.results if r.passed]
        old_count = len(universe.symbols or [])
        universe.symbols = new_symbols

        await db.commit()

        return {
            "status": "success",
            "universe_id": universe_id,
            "old_symbol_count": old_count,
            "new_symbol_count": len(new_symbols),
            "symbols_added": [s for s in new_symbols if s not in (universe.symbols or [])],
            "symbols_removed": [s for s in (universe.symbols or []) if s not in new_symbols],
        }

    finally:
        if redis:
            await redis.close()


# ============== Performance Tracking Endpoints ==============


@router.post("/recommendations/update-returns", response_model=UpdateReturnsResponse)
async def update_recommendation_returns(
    db: DbSession,
) -> UpdateReturnsResponse:
    """Update return metrics for past recommendations (internal endpoint).

    Called by Celery task after market close to:
    - Update 1-day returns for yesterday's recommendations
    - Update 1-week returns for 1-week-old recommendations
    - Update 1-month returns for 1-month-old recommendations
    """
    from datetime import date, time, timedelta
    from datetime import datetime as dt

    from sqlalchemy import and_, select

    from app.modules.screener.models import DailyRecommendation

    today = date.today()
    updated_1d = 0
    updated_1w = 0
    updated_1m = 0
    errors: list[str] = []

    # Get recommendations that need 1-day update (from yesterday)
    yesterday = today - timedelta(days=1)
    result = await db.execute(
        select(DailyRecommendation).where(
            and_(
                DailyRecommendation.date >= dt.combine(yesterday, time.min),
                DailyRecommendation.date < dt.combine(today, time.min),
                DailyRecommendation.return_1d == None,  # noqa: E711
            )
        )
    )
    recs_1d = result.scalars().all()

    # Get recommendations that need 1-week update (from 7 days ago)
    one_week_ago = today - timedelta(days=7)
    result = await db.execute(
        select(DailyRecommendation).where(
            and_(
                DailyRecommendation.date >= dt.combine(one_week_ago, time.min),
                DailyRecommendation.date < dt.combine(one_week_ago + timedelta(days=1), time.min),
                DailyRecommendation.return_1w == None,  # noqa: E711
            )
        )
    )
    recs_1w = result.scalars().all()

    # Get recommendations that need 1-month update (from 30 days ago)
    one_month_ago = today - timedelta(days=30)
    result = await db.execute(
        select(DailyRecommendation).where(
            and_(
                DailyRecommendation.date >= dt.combine(one_month_ago, time.min),
                DailyRecommendation.date < dt.combine(one_month_ago + timedelta(days=1), time.min),
                DailyRecommendation.return_1m == None,  # noqa: E711
            )
        )
    )
    recs_1m = result.scalars().all()

    # Get current prices for all symbols
    symbols = set()
    for rec in recs_1d + recs_1w + recs_1m:
        symbols.add(rec.symbol)

    if not symbols:
        return UpdateReturnsResponse(status="success", updated_1d=0, updated_1w=0, updated_1m=0)

    # Fetch current prices using default Yahoo provider (background task has no user context)
    provider = get_data_provider("yahoo")
    price_map: dict[str, float] = {}
    for symbol in symbols:
        try:
            quote = await provider.get_quote(symbol)
            if quote and quote.price:
                price_map[symbol] = float(quote.price)
        except Exception as e:
            errors.append(f"{symbol}: {str(e)}")

    # Update 1-day returns
    for rec in recs_1d:
        if rec.symbol in price_map:
            current_price = price_map[rec.symbol]
            rec.price_1d = current_price
            rec.return_1d = ((current_price - rec.price_at_rec) / rec.price_at_rec) * 100
            updated_1d += 1

    # Update 1-week returns
    for rec in recs_1w:
        if rec.symbol in price_map:
            current_price = price_map[rec.symbol]
            rec.price_1w = current_price
            rec.return_1w = ((current_price - rec.price_at_rec) / rec.price_at_rec) * 100
            updated_1w += 1

    # Update 1-month returns
    for rec in recs_1m:
        if rec.symbol in price_map:
            current_price = price_map[rec.symbol]
            rec.price_1m = current_price
            rec.return_1m = ((current_price - rec.price_at_rec) / rec.price_at_rec) * 100
            updated_1m += 1

    await db.commit()

    return UpdateReturnsResponse(
        status="success",
        updated_1d=updated_1d,
        updated_1w=updated_1w,
        updated_1m=updated_1m,
        errors=errors[:10],  # Limit error list
    )


@router.get("/performance", response_model=OverallPerformanceStats)
async def get_screener_performance(
    db: DbSession,
    current_user: CurrentUser,
    days: int = 30,
) -> OverallPerformanceStats:
    """Get screener performance statistics.

    Aggregates win rates and average returns across all recommendation categories.
    """
    from datetime import datetime as dt
    from datetime import timedelta

    from sqlalchemy import select

    from app.modules.screener.models import DailyRecommendation

    cutoff_date = dt.now() - timedelta(days=days)

    # Get all recommendations in the date range
    result = await db.execute(
        select(DailyRecommendation)
        .where(DailyRecommendation.date >= cutoff_date)
        .order_by(DailyRecommendation.date.desc())
    )
    recommendations = result.scalars().all()

    if not recommendations:
        return OverallPerformanceStats(
            total_recommendations=0,
            unique_symbols=0,
            categories=[],
        )

    # Calculate overall stats
    unique_symbols = {r.symbol for r in recommendations}
    date_range_start = min(r.date for r in recommendations)
    date_range_end = max(r.date for r in recommendations)

    # Group by category
    categories_data: dict[str, list] = {}
    for rec in recommendations:
        if rec.category not in categories_data:
            categories_data[rec.category] = []
        categories_data[rec.category].append(rec)

    category_stats = []
    all_returns_1d = []
    all_returns_1w = []
    all_returns_1m = []

    for category, recs in categories_data.items():
        returns_1d = [r.return_1d for r in recs if r.return_1d is not None]
        returns_1w = [r.return_1w for r in recs if r.return_1w is not None]
        returns_1m = [r.return_1m for r in recs if r.return_1m is not None]

        all_returns_1d.extend(returns_1d)
        all_returns_1w.extend(returns_1w)
        all_returns_1m.extend(returns_1m)

        # Find best picks
        best_1d = max(recs, key=lambda r: r.return_1d or -float("inf")) if returns_1d else None
        best_1w = max(recs, key=lambda r: r.return_1w or -float("inf")) if returns_1w else None
        best_1m = max(recs, key=lambda r: r.return_1m or -float("inf")) if returns_1m else None

        stats = CategoryPerformanceStats(
            category=category,
            total_recommendations=len(recs),
            win_rate_1d=len([r for r in returns_1d if r > 0]) / len(returns_1d) * 100
            if returns_1d
            else None,
            win_rate_1w=len([r for r in returns_1w if r > 0]) / len(returns_1w) * 100
            if returns_1w
            else None,
            win_rate_1m=len([r for r in returns_1m if r > 0]) / len(returns_1m) * 100
            if returns_1m
            else None,
            avg_return_1d=sum(returns_1d) / len(returns_1d) if returns_1d else None,
            avg_return_1w=sum(returns_1w) / len(returns_1w) if returns_1w else None,
            avg_return_1m=sum(returns_1m) / len(returns_1m) if returns_1m else None,
            best_pick_1d=best_1d.symbol if best_1d and best_1d.return_1d else None,
            best_pick_1w=best_1w.symbol if best_1w and best_1w.return_1w else None,
            best_pick_1m=best_1m.symbol if best_1m and best_1m.return_1m else None,
            best_return_1d=best_1d.return_1d if best_1d else None,
            best_return_1w=best_1w.return_1w if best_1w else None,
            best_return_1m=best_1m.return_1m if best_1m else None,
        )
        category_stats.append(stats)

    return OverallPerformanceStats(
        total_recommendations=len(recommendations),
        unique_symbols=len(unique_symbols),
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        categories=category_stats,
        overall_win_rate_1d=len([r for r in all_returns_1d if r > 0]) / len(all_returns_1d) * 100
        if all_returns_1d
        else None,
        overall_win_rate_1w=len([r for r in all_returns_1w if r > 0]) / len(all_returns_1w) * 100
        if all_returns_1w
        else None,
        overall_win_rate_1m=len([r for r in all_returns_1m if r > 0]) / len(all_returns_1m) * 100
        if all_returns_1m
        else None,
        overall_avg_return_1d=sum(all_returns_1d) / len(all_returns_1d) if all_returns_1d else None,
        overall_avg_return_1w=sum(all_returns_1w) / len(all_returns_1w) if all_returns_1w else None,
        overall_avg_return_1m=sum(all_returns_1m) / len(all_returns_1m) if all_returns_1m else None,
    )


# Helper functions
def _screener_to_response(screener) -> CustomScreenerResponse:
    """Convert CustomScreener model to response."""
    return CustomScreenerResponse(
        id=screener.id,
        name=screener.name,
        description=screener.description,
        universe=screener.universe,
        filters=[FilterConfig(**f) for f in screener.filters],
        min_score=screener.min_score,
        top_n=screener.top_n,
        created_at=screener.created_at,
        updated_at=screener.updated_at,
    )


async def _resolve_universe(universe: str, db: DbSession) -> list[str]:
    """Resolve a universe identifier to a list of symbols."""
    universe_upper = universe.upper()

    # Check predefined static universes
    if universe_upper in PREDEFINED_UNIVERSES:
        return PREDEFINED_UNIVERSES[universe_upper]["symbols"]

    # Check dynamic universes
    if universe_upper in DYNAMIC_UNIVERSES:
        # NSE provider is appropriate for fetching index constituents
        nse_provider = get_data_provider("nse")
        universe_svc = UniverseService(db)
        nse_index = DYNAMIC_UNIVERSES[universe_upper]["nse_index"]
        return await universe_svc.fetch_index_symbols(nse_index, nse_provider)

    # Handle special cases
    if universe_upper in ("ALL_NSE", "ALL"):
        universe_svc = UniverseService(db)
        return await universe_svc.get_all_nse_stocks()

    if universe_upper == "FO_STOCKS":
        universe_svc = UniverseService(db)
        return await universe_svc.get_fo_stocks()

    # Try to find by UUID (custom universe)
    from sqlalchemy import select

    from app.modules.algo.models import Universe

    result = await db.execute(select(Universe).where(Universe.id == universe))
    custom_universe = result.scalar_one_or_none()
    if custom_universe:
        return custom_universe.symbols or []

    return []
