"""Screener API routes."""

import logging
from datetime import UTC

from fastapi import APIRouter, HTTPException, status
from shared.providers.data import get_data_provider

from app.api.deps import CurrentUser, DbSession, InternalOrCurrentUser
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
    CreateSmartStrategyRequest,
    CreateSmartStrategyResponse,
    CreateStrategyFromScreenerRequest,
    CreateStrategyFromScreenerResponse,
    CreateUniverseFromScreenerRequest,
    CreateUniverseFromScreenerResponse,
    CustomScreenerCreate,
    CustomScreenerListResponse,
    CustomScreenerResponse,
    CustomScreenerUpdate,
    DailyRecommendationsResponse,
    FilterAnalysisResponse,
    FilterConfig,
    InferStrategyRequest,
    InferStrategyResponse,
    LinkAutoTradeRequest,
    OverallPerformanceStats,
    RecommendationCategory,
    RecommendationItem,
    RunAutoTradeScreenerResponse,
    RunScheduledScreenersRequest,
    RunScheduledScreenersResponse,
    ScreenerAlertCreate,
    ScreenerAlertListResponse,
    ScreenerAlertResponse,
    ScreenerAlertUpdate,
    ScreenerPresetRunRequest,
    ScreenerPresetsResponse,
    ScreenerRunRequest,
    ScreenerRunResponse,
    StoreRecommendationsRequest,
    StrategyInferenceResponse,
    StrategyRecommendationResponse,
    UnlinkAutoTradeResponse,
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
    current_user: InternalOrCurrentUser,
) -> ScreenerRunResponse:
    """Run a preset screener on a universe of stocks.

    Supports both user authentication (JWT) and internal service calls (X-Internal-Key).
    """
    from app.modules.screener.service import apply_strictness_to_filters

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

    # Apply strictness level to filter parameters
    adjusted_filters = apply_strictness_to_filters(preset.filters, data.strictness)

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
        filters=adjusted_filters,
        universe=data.universe,
        min_score=data.min_score,
        top_n=data.top_n,
        data_provider=provider,
        preset=f"{data.preset.value}:{data.strictness.value}",
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
# Custom Screener Auto-Trade Endpoints
# =============================================================================


@router.post("/custom/{screener_id}/link-auto-trade", response_model=CustomScreenerResponse)
async def link_auto_trade(
    screener_id: str,
    data: LinkAutoTradeRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomScreenerResponse:
    """Link a custom screener to auto-trade configuration.

    This enables automated trading based on the screener results.
    The screener will run on the specified schedule and create trades.
    """
    from datetime import time

    from app.modules.algo.strategy_inference import StrategyInferenceEngine

    service = ScreenerService(db)
    screener = await service.get_custom_screener(current_user.id, screener_id)
    if not screener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom screener not found",
        )

    # Parse run_time
    run_time_obj = None
    if data.run_time:
        h, m = map(int, data.run_time.split(":"))
        run_time_obj = time(hour=h, minute=m)

    # Infer strategy type from filters
    filters = [FilterConfig(**f) for f in screener.filters]
    inference_engine = StrategyInferenceEngine()
    inference_result = inference_engine.infer(filters)
    inferred_type = inference_result.recommended_strategy.strategy_type

    # Update screener with auto-trade settings
    screener.is_auto_trade_enabled = True
    screener.run_frequency = data.run_frequency.value
    screener.run_time = run_time_obj
    screener.strategy_template_id = data.strategy_template_id
    screener.inferred_strategy_type = inferred_type

    await db.commit()
    await db.refresh(screener)

    return _screener_to_response(screener)


@router.post("/custom/{screener_id}/unlink-auto-trade", response_model=UnlinkAutoTradeResponse)
async def unlink_auto_trade(
    screener_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> UnlinkAutoTradeResponse:
    """Unlink a custom screener from auto-trade.

    This disables automated trading for the screener.
    """
    service = ScreenerService(db)
    screener = await service.get_custom_screener(current_user.id, screener_id)
    if not screener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom screener not found",
        )

    # Disable auto-trade
    screener.is_auto_trade_enabled = False

    await db.commit()

    return UnlinkAutoTradeResponse(
        id=screener.id,
        name=screener.name,
        is_auto_trade_enabled=False,
        message="Auto-trade has been disabled for this screener",
    )


@router.get("/custom/{screener_id}/infer-strategy", response_model=StrategyInferenceResponse)
async def infer_strategy_from_screener(
    screener_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> StrategyInferenceResponse:
    """Infer the optimal strategy type from a screener's filters.

    This analyzes the screener's filter configuration and recommends
    the best algo strategy type (e.g., trend_following, mean_reversion).
    """
    from app.modules.algo.strategy_inference import StrategyInferenceEngine

    service = ScreenerService(db)
    screener = await service.get_custom_screener(current_user.id, screener_id)
    if not screener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom screener not found",
        )

    # Run strategy inference
    filters = [FilterConfig(**f) for f in screener.filters]
    inference_engine = StrategyInferenceEngine()
    result = inference_engine.infer(filters)

    return StrategyInferenceResponse(
        screener_id=screener.id,
        screener_name=screener.name,
        inferred_strategy_type=result.recommended_strategy.strategy_type,
        confidence=result.recommended_strategy.confidence,
        reasoning=result.recommended_strategy.reasoning,
        suggested_params=result.recommended_strategy.suggested_params,
    )


@router.post("/custom/run-scheduled", response_model=RunScheduledScreenersResponse)
async def run_scheduled_screeners(
    data: RunScheduledScreenersRequest,
    db: DbSession,
    internal_user: InternalOrCurrentUser,
) -> RunScheduledScreenersResponse:
    """Run all scheduled custom screeners with the given frequency.

    This endpoint is called by the Celery beat scheduler:
    - Daily at 9:20 AM IST for frequency='daily'
    - Hourly during market hours for frequency='hourly'

    For each screener with matching frequency and auto-trade enabled:
    1. Run the screener against its configured universe
    2. Apply multi-factor scoring (if configured)
    3. Create pending trades or auto-execute (based on config)
    4. Update last_run_at and next_run_at timestamps
    """
    service = ScreenerService(db)
    frequency = data.frequency.value

    # Get all screeners due to run with this frequency
    screeners = await service.get_screeners_by_frequency(frequency)

    results = []
    errors = []
    auto_trades_triggered = 0
    screeners_succeeded = 0

    for screener in screeners:
        try:
            # Skip if not enabled for auto-trade
            if not screener.is_auto_trade_enabled:
                continue

            # Run the screener
            run_result = await service.run_custom_screener_for_auto_trade(
                user_id=screener.user_id,
                screener_id=str(screener.id),
            )

            if run_result.get("status") == "success":
                screeners_succeeded += 1
                auto_trades_triggered += run_result.get("trades_created", 0)
                auto_trades_triggered += run_result.get("pending_trades_created", 0)

            results.append(
                {
                    "screener_id": str(screener.id),
                    "screener_name": screener.name,
                    "user_id": str(screener.user_id),
                    "status": run_result.get("status", "error"),
                    "passed_count": run_result.get("passed_count", 0),
                    "trades_created": run_result.get("trades_created", 0),
                }
            )

        except Exception as e:
            logger.exception(f"Error running scheduled screener {screener.id}: {e}")
            errors.append(f"Screener {screener.id}: {str(e)}")
            results.append(
                {
                    "screener_id": str(screener.id),
                    "screener_name": screener.name,
                    "status": "error",
                    "error": str(e),
                }
            )

    return RunScheduledScreenersResponse(
        status="completed" if screeners_succeeded > 0 else "no_screeners",
        frequency=frequency,
        screeners_processed=len(results),
        screeners_succeeded=screeners_succeeded,
        screeners_failed=len(errors),
        auto_trades_triggered=auto_trades_triggered,
        results=results,
        errors=errors,
    )


@router.post(
    "/custom/{screener_id}/run-auto-trade",
    response_model=RunAutoTradeScreenerResponse,
)
async def run_screener_auto_trade(
    screener_id: str,
    db: DbSession,
    current_user: InternalOrCurrentUser,
) -> RunAutoTradeScreenerResponse:
    """Run a specific custom screener and trigger auto-trade.

    This endpoint can be called:
    - By the scheduled Celery task for a specific screener
    - Manually by the user to trigger an immediate run

    The screener must have auto-trade enabled. Results flow through
    the auto-trade pipeline based on the user's confirmation mode:
    - AUTO: Strategies are created and activated immediately
    - NOTIFY: Pending trades are created for user approval
    """
    service = ScreenerService(db)

    # Get the screener
    screener = await service.get_custom_screener(str(current_user.id), screener_id)
    if not screener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom screener not found",
        )

    if not screener.is_auto_trade_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-trade is not enabled for this screener",
        )

    # Cache the name before calling the service (session may be released inside)
    screener_name = screener.name

    # Run the screener for auto-trade
    result = await service.run_custom_screener_for_auto_trade(
        user_id=str(current_user.id),
        screener_id=screener_id,
    )

    return RunAutoTradeScreenerResponse(
        status=result.get("status", "success"),
        screener_id=screener_id,
        screener_name=screener_name,
        passed_count=result.get("passed_count", 0),
        total_screened=result.get("total_screened", 0),
        trades_created=result.get("trades_created", 0),
        pending_trades_created=result.get("pending_trades_created", 0),
        results=result.get("results", []),
        message=result.get("message"),
    )


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
    current_user: InternalOrCurrentUser,
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
                metadata=r.extra_data or {},
                return_1d=r.return_1d,
                return_1w=r.return_1w,
                return_1m=r.return_1m,
                # Multi-factor scoring fields
                technical_score=r.technical_score,
                fundamental_score=r.fundamental_score,
                sentiment_score=r.sentiment_score,
                combined_score=r.combined_score,
                signal_direction=r.signal_direction,
                confidence_level=r.confidence_level,
                recommended_strategy=r.recommended_strategy,
                position_size_multiplier=r.position_size_multiplier,
                skip_reason=r.skip_reason,
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
    data: StoreRecommendationsRequest,
) -> dict:
    """Internal endpoint to store daily recommendations.

    Called by the Celery task to persist recommendations.
    Accepts JSON body with date, category, and results.

    Enriches recommendations with multi-factor scoring:
    - Technical score (from screener data)
    - Fundamental score (from RecommendationService)
    - Sentiment score (from news analysis)
    - Combined score, direction, confidence, and strategy recommendation
    """
    from datetime import datetime

    from app.modules.algo.multi_factor_scorer import MultiFactorScorer
    from app.modules.screener.models import DailyRecommendation

    # Parse date
    try:
        rec_date = datetime.fromisoformat(data.date).replace(tzinfo=UTC)
    except ValueError:
        rec_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    # Delete existing recommendations for this date/category (replace on re-run)
    from sqlalchemy import delete, func

    await db.execute(
        delete(DailyRecommendation).where(
            func.date(DailyRecommendation.date) == func.date(rec_date),
            DailyRecommendation.category == data.category,
        )
    )

    # Fetch current prices for all symbols to populate price_at_rec
    symbols = [r.get("symbol", "") for r in data.results if r.get("symbol")]
    price_map: dict[str, float] = {}

    if symbols:
        provider = get_data_provider("yahoo")
        for symbol in symbols:
            try:
                quote = await provider.get_quote(symbol)
                if quote and quote.price:
                    price_map[symbol] = float(quote.price)
            except Exception:
                pass  # nosec B110 - Price will default to 0.0 if fetch fails

    # Prepare technical and fundamental data for multi-factor scoring
    technical_data: dict[str, dict] = {}
    fundamental_data: dict[str, dict] = {}

    for result in data.results:
        symbol = result.get("symbol", "")
        if symbol:
            # Technical data from screener result
            technical_data[symbol] = {
                "score": result.get("score", 50.0),
                "momentum_score": result.get("filter_scores", {}).get("momentum", 0),
                "volume_ratio": result.get("metadata", {}).get("volume_ratio", 1.0),
                "breakout_score": result.get("filter_scores", {}).get("breakout", 0),
                "ma_position": result.get("metadata", {}).get("ma_position", "unknown"),
            }
            # Fundamental data will be fetched by scorer if not provided
            fund_score = result.get("metadata", {}).get("fundamental_score")
            if fund_score is not None:
                fundamental_data[symbol] = {
                    "fundamental_score": fund_score,
                    "reasons": result.get("metadata", {}).get("fundamental_reasons", []),
                }

    # Calculate multi-factor scores
    scorer = MultiFactorScorer(db)
    multi_factor_scores: dict[str, dict] = {}

    try:
        scores = await scorer.score_symbols(
            symbols=symbols,
            category=data.category,
            technical_data=technical_data,
            fundamental_data=fundamental_data,
        )
        for score in scores:
            multi_factor_scores[score.symbol] = score.to_dict()
    except Exception as e:
        logger.warning(f"Multi-factor scoring failed: {e}. Storing without scores.")

    # Store new recommendations with multi-factor data
    stored_count = 0
    for i, result in enumerate(data.results):
        symbol = result.get("symbol", "")
        # Use fetched price, or fallback to metadata, or 0.0
        price_at_rec = price_map.get(symbol, result.get("metadata", {}).get("current_price", 0.0))

        # Get multi-factor score data if available
        mf_data = multi_factor_scores.get(symbol, {})

        rec = DailyRecommendation(
            date=rec_date,
            category=data.category,
            symbol=symbol,
            rank=i + 1,
            score=result.get("score", 0.0),
            price_at_rec=price_at_rec,
            filter_scores=result.get("filter_scores", {}),
            reasons=mf_data.get("reasons", result.get("reasons", [])),
            extra_data=result.get("metadata", {}),
            # Multi-factor scoring fields
            technical_score=mf_data.get("technical_score"),
            fundamental_score=mf_data.get("fundamental_score"),
            sentiment_score=mf_data.get("sentiment_score"),
            combined_score=mf_data.get("combined_score"),
            signal_direction=mf_data.get("direction"),
            confidence_level=mf_data.get("confidence"),
            recommended_strategy=mf_data.get("recommended_strategy"),
            position_size_multiplier=mf_data.get("position_size_multiplier"),
            skip_reason=mf_data.get("skip_reason"),
        )
        db.add(rec)
        stored_count += 1

    await db.commit()

    return {
        "status": "success",
        "date": data.date,
        "category": data.category,
        "stored_count": stored_count,
        "multi_factor_scored": len(multi_factor_scores),
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

    # Get recommendations that need 1-week update (7+ days old, missing return_1w)
    one_week_ago = today - timedelta(days=7)
    result = await db.execute(
        select(DailyRecommendation).where(
            and_(
                DailyRecommendation.date <= dt.combine(one_week_ago, time.min),
                DailyRecommendation.return_1w == None,  # noqa: E711
            )
        )
    )
    recs_1w = result.scalars().all()

    # Get recommendations that need 1-month update (30+ days old, missing return_1m)
    one_month_ago = today - timedelta(days=30)
    result = await db.execute(
        select(DailyRecommendation).where(
            and_(
                DailyRecommendation.date <= dt.combine(one_month_ago, time.min),
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
        if rec.symbol in price_map and rec.price_at_rec and rec.price_at_rec > 0:
            current_price = price_map[rec.symbol]
            rec.price_1d = current_price
            rec.return_1d = ((current_price - rec.price_at_rec) / rec.price_at_rec) * 100
            updated_1d += 1
        elif rec.symbol in price_map:
            # Can't calculate return without valid price_at_rec, but record current price
            rec.price_1d = price_map[rec.symbol]
            errors.append(f"{rec.symbol}: Missing price_at_rec for 1d return")

    # Update 1-week returns
    for rec in recs_1w:
        if rec.symbol in price_map and rec.price_at_rec and rec.price_at_rec > 0:
            current_price = price_map[rec.symbol]
            rec.price_1w = current_price
            rec.return_1w = ((current_price - rec.price_at_rec) / rec.price_at_rec) * 100
            updated_1w += 1
        elif rec.symbol in price_map:
            rec.price_1w = price_map[rec.symbol]
            errors.append(f"{rec.symbol}: Missing price_at_rec for 1w return")

    # Update 1-month returns
    for rec in recs_1m:
        if rec.symbol in price_map and rec.price_at_rec and rec.price_at_rec > 0:
            current_price = price_map[rec.symbol]
            rec.price_1m = current_price
            rec.return_1m = ((current_price - rec.price_at_rec) / rec.price_at_rec) * 100
            updated_1m += 1
        elif rec.symbol in price_map:
            rec.price_1m = price_map[rec.symbol]
            errors.append(f"{rec.symbol}: Missing price_at_rec for 1m return")

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
    # Format run_time as HH:MM string if it exists
    run_time_str = None
    if screener.run_time:
        run_time_str = screener.run_time.strftime("%H:%M")

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
        # Auto-trade fields
        is_auto_trade_enabled=screener.is_auto_trade_enabled or False,
        run_frequency=screener.run_frequency or "manual",
        run_time=run_time_str,
        last_run_at=screener.last_run_at,
        next_run_at=screener.next_run_at,
        inferred_strategy_type=screener.inferred_strategy_type,
        strategy_template_id=screener.strategy_template_id,
    )


async def _resolve_universe(universe: str, db: DbSession) -> list[str]:
    """Resolve a universe identifier to a list of symbols.

    First checks the database for a universe by name (same as algo trading),
    then falls back to predefined universes for backward compatibility.
    """
    from sqlalchemy import select

    from app.modules.algo.models import Universe

    # First, try to find universe by name in the database (same as algo trading)
    result = await db.execute(select(Universe).where(Universe.name == universe))
    db_universe = result.scalar_one_or_none()
    if db_universe and db_universe.symbols:
        logger.info(
            f"Resolved universe '{universe}' from database with {len(db_universe.symbols)} symbols"
        )
        return db_universe.symbols

    # Fallback: Check predefined static universes by key (uppercase)
    universe_upper = universe.upper().replace(" ", "")  # "Nifty 50" -> "NIFTY50"
    if universe_upper in PREDEFINED_UNIVERSES:
        return PREDEFINED_UNIVERSES[universe_upper]["symbols"]

    # For dynamic universes (e.g., NIFTY500), fallback to NIFTY50
    if universe_upper in DYNAMIC_UNIVERSES:
        logger.warning(f"Dynamic universe {universe_upper} requested, falling back to NIFTY50")
        return PREDEFINED_UNIVERSES["NIFTY50"]["symbols"]

    # Handle special cases
    if universe_upper in ("ALL_NSE", "ALL", "ALLNSE"):
        universe_svc = UniverseService(db)
        return await universe_svc.get_all_nse_stocks()

    if universe_upper in ("FO_STOCKS", "FOSTOCKS", "F&OSTOCKS"):
        universe_svc = UniverseService(db)
        return await universe_svc.get_fo_stocks()

    # Try to find by UUID (custom universe ID)
    result = await db.execute(select(Universe).where(Universe.id == universe))
    custom_universe = result.scalar_one_or_none()
    if custom_universe and custom_universe.symbols:
        return custom_universe.symbols

    logger.warning(f"Universe '{universe}' not found, returning empty list")
    return []


# ============== Screener Alert Endpoints ==============


@router.post("/alerts", response_model=ScreenerAlertResponse)
async def create_screener_alert(
    data: ScreenerAlertCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ScreenerAlertResponse:
    """Create a new screener alert."""
    from sqlalchemy import select

    from app.modules.screener.models import CustomScreener, ScreenerAlert

    # Validate that either custom_screener_id or preset is provided
    if not data.custom_screener_id and not data.preset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either custom_screener_id or preset must be provided",
        )

    # If custom_screener_id, validate it exists and belongs to user
    custom_screener_name = None
    if data.custom_screener_id:
        result = await db.execute(
            select(CustomScreener).where(
                CustomScreener.id == data.custom_screener_id,
                CustomScreener.user_id == str(current_user.id),
            )
        )
        custom_screener = result.scalar_one_or_none()
        if not custom_screener:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom screener not found",
            )
        custom_screener_name = custom_screener.name

    alert = ScreenerAlert(
        user_id=str(current_user.id),
        name=data.name,
        custom_screener_id=data.custom_screener_id,
        preset=data.preset,
        universe=data.universe,
        alert_on_new_symbols=data.alert_on_new_symbols,
        alert_on_removed_symbols=data.alert_on_removed_symbols,
        min_score_threshold=data.min_score_threshold,
        target_symbol=data.target_symbol,
        enabled=data.enabled,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return ScreenerAlertResponse(
        id=alert.id,
        name=alert.name,
        custom_screener_id=alert.custom_screener_id,
        custom_screener_name=custom_screener_name,
        preset=alert.preset,
        universe=alert.universe,
        alert_on_new_symbols=alert.alert_on_new_symbols,
        alert_on_removed_symbols=alert.alert_on_removed_symbols,
        min_score_threshold=alert.min_score_threshold,
        target_symbol=alert.target_symbol,
        enabled=alert.enabled,
        last_run_at=alert.last_run_at,
        last_symbols=alert.last_symbols,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


@router.get("/alerts", response_model=ScreenerAlertListResponse)
async def list_screener_alerts(
    db: DbSession,
    current_user: CurrentUser,
) -> ScreenerAlertListResponse:
    """List all screener alerts for the current user."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.modules.screener.models import ScreenerAlert

    result = await db.execute(
        select(ScreenerAlert)
        .options(selectinload(ScreenerAlert.custom_screener))
        .where(ScreenerAlert.user_id == str(current_user.id))
        .order_by(ScreenerAlert.created_at.desc())
    )
    alerts = result.scalars().all()

    return ScreenerAlertListResponse(
        alerts=[
            ScreenerAlertResponse(
                id=a.id,
                name=a.name,
                custom_screener_id=a.custom_screener_id,
                custom_screener_name=a.custom_screener.name if a.custom_screener else None,
                preset=a.preset,
                universe=a.universe,
                alert_on_new_symbols=a.alert_on_new_symbols,
                alert_on_removed_symbols=a.alert_on_removed_symbols,
                min_score_threshold=a.min_score_threshold,
                target_symbol=a.target_symbol,
                enabled=a.enabled,
                last_run_at=a.last_run_at,
                last_symbols=a.last_symbols,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in alerts
        ]
    )


@router.get("/alerts/{alert_id}", response_model=ScreenerAlertResponse)
async def get_screener_alert(
    alert_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> ScreenerAlertResponse:
    """Get a specific screener alert."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.modules.screener.models import ScreenerAlert

    result = await db.execute(
        select(ScreenerAlert)
        .options(selectinload(ScreenerAlert.custom_screener))
        .where(
            ScreenerAlert.id == alert_id,
            ScreenerAlert.user_id == str(current_user.id),
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return ScreenerAlertResponse(
        id=alert.id,
        name=alert.name,
        custom_screener_id=alert.custom_screener_id,
        custom_screener_name=alert.custom_screener.name if alert.custom_screener else None,
        preset=alert.preset,
        universe=alert.universe,
        alert_on_new_symbols=alert.alert_on_new_symbols,
        alert_on_removed_symbols=alert.alert_on_removed_symbols,
        min_score_threshold=alert.min_score_threshold,
        target_symbol=alert.target_symbol,
        enabled=alert.enabled,
        last_run_at=alert.last_run_at,
        last_symbols=alert.last_symbols,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


@router.put("/alerts/{alert_id}", response_model=ScreenerAlertResponse)
async def update_screener_alert(
    alert_id: str,
    data: ScreenerAlertUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ScreenerAlertResponse:
    """Update a screener alert."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.modules.screener.models import ScreenerAlert

    result = await db.execute(
        select(ScreenerAlert)
        .options(selectinload(ScreenerAlert.custom_screener))
        .where(
            ScreenerAlert.id == alert_id,
            ScreenerAlert.user_id == str(current_user.id),
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    # Update fields
    if data.name is not None:
        alert.name = data.name
    if data.alert_on_new_symbols is not None:
        alert.alert_on_new_symbols = data.alert_on_new_symbols
    if data.alert_on_removed_symbols is not None:
        alert.alert_on_removed_symbols = data.alert_on_removed_symbols
    if data.min_score_threshold is not None:
        alert.min_score_threshold = data.min_score_threshold
    if data.target_symbol is not None:
        alert.target_symbol = data.target_symbol
    if data.enabled is not None:
        alert.enabled = data.enabled

    await db.commit()
    await db.refresh(alert)

    return ScreenerAlertResponse(
        id=alert.id,
        name=alert.name,
        custom_screener_id=alert.custom_screener_id,
        custom_screener_name=alert.custom_screener.name if alert.custom_screener else None,
        preset=alert.preset,
        universe=alert.universe,
        alert_on_new_symbols=alert.alert_on_new_symbols,
        alert_on_removed_symbols=alert.alert_on_removed_symbols,
        min_score_threshold=alert.min_score_threshold,
        target_symbol=alert.target_symbol,
        enabled=alert.enabled,
        last_run_at=alert.last_run_at,
        last_symbols=alert.last_symbols,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


@router.delete("/alerts/{alert_id}")
async def delete_screener_alert(
    alert_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Delete a screener alert."""
    from sqlalchemy import select

    from app.modules.screener.models import ScreenerAlert

    result = await db.execute(
        select(ScreenerAlert).where(
            ScreenerAlert.id == alert_id,
            ScreenerAlert.user_id == str(current_user.id),
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    await db.delete(alert)
    await db.commit()

    return {"status": "success", "deleted_id": alert_id}


@router.post("/alerts/process")
async def process_screener_alerts(
    db: DbSession,
) -> dict:
    """Process all enabled screener alerts (internal endpoint).

    Called by Celery task to:
    1. Run the screener for each enabled alert
    2. Compare with last_symbols to find new/removed symbols
    3. Update last_symbols and last_run_at

    Returns counts of alerts processed and notifications triggered.
    """
    from datetime import datetime

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.modules.screener.models import ScreenerAlert

    # Get all enabled alerts
    result = await db.execute(
        select(ScreenerAlert)
        .options(selectinload(ScreenerAlert.custom_screener))
        .where(ScreenerAlert.enabled == True)  # noqa: E712
    )
    alerts = result.scalars().all()

    if not alerts:
        return {
            "status": "success",
            "alerts_processed": 0,
            "notifications_sent": 0,
            "message": "No enabled alerts",
        }

    redis = await get_redis()
    service = ScreenerService(db, redis)

    alerts_processed = 0
    notifications_sent = 0
    errors: list[str] = []

    try:
        for alert in alerts:
            try:
                # Determine screener configuration
                if alert.custom_screener_id and alert.custom_screener:
                    # Custom screener
                    screener = alert.custom_screener
                    universe = screener.universe
                    filters = [FilterConfig(**f) for f in (screener.filters or [])]
                    min_score = screener.min_score
                    top_n = screener.top_n
                elif alert.preset:
                    # Preset screener
                    preset_config = ScreenerService.get_preset_filters(alert.preset, "moderate")
                    if not preset_config:
                        errors.append(f"Alert {alert.id}: Invalid preset {alert.preset}")
                        continue
                    universe = alert.universe or "nifty500"
                    filters = preset_config
                    min_score = 50.0
                    top_n = 50
                else:
                    errors.append(f"Alert {alert.id}: No screener configuration")
                    continue

                # Resolve universe symbols
                symbols = await _resolve_universe(universe, db)
                if not symbols:
                    errors.append(f"Alert {alert.id}: Empty universe {universe}")
                    continue

                # Run the screener
                run_result = await service.run_screener(
                    symbols=symbols,
                    filters=filters,
                    min_score=min_score,
                    top_n=top_n,
                    user_id=alert.user_id,
                    use_cache=False,  # Fresh results for alerts
                )

                # Get current matching symbols (above threshold if set)
                current_symbols = []
                for r in run_result.results:
                    if not r.passed:
                        continue
                    if alert.min_score_threshold and r.score < alert.min_score_threshold:
                        continue
                    if alert.target_symbol and r.symbol != alert.target_symbol:
                        continue
                    current_symbols.append(r.symbol)

                # Compare with last run
                last_symbols = set(alert.last_symbols or [])
                current_set = set(current_symbols)

                new_symbols = current_set - last_symbols
                removed_symbols = last_symbols - current_set

                # Check if notifications should be sent
                should_notify = False
                notification_data = {
                    "alert_id": alert.id,
                    "alert_name": alert.name,
                    "new_symbols": list(new_symbols) if alert.alert_on_new_symbols else [],
                    "removed_symbols": (
                        list(removed_symbols) if alert.alert_on_removed_symbols else []
                    ),
                }

                if alert.alert_on_new_symbols and new_symbols:
                    should_notify = True
                if alert.alert_on_removed_symbols and removed_symbols:
                    should_notify = True

                if should_notify:
                    # TODO: Send notification (email, push, etc.)
                    # For now, just log it
                    logger.info(f"Alert triggered: {notification_data}")
                    notifications_sent += 1

                # Update alert state
                alert.last_symbols = current_symbols
                alert.last_run_at = datetime.now(UTC)
                alerts_processed += 1

            except Exception as e:
                logger.exception(f"Error processing alert {alert.id}: {e}")
                errors.append(f"Alert {alert.id}: {str(e)}")

        await db.commit()

    finally:
        if redis:
            await redis.close()

    result_data = {
        "status": "success",
        "alerts_processed": alerts_processed,
        "notifications_sent": notifications_sent,
    }
    if errors:
        result_data["errors"] = errors

    return result_data


# ============== Create Strategy from Screener ==============


@router.post("/create-strategy", response_model=CreateStrategyFromScreenerResponse)
async def create_strategy_from_screener(
    data: CreateStrategyFromScreenerRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> CreateStrategyFromScreenerResponse:
    """Create an algo strategy from screener results.

    This creates a new universe from the screener results and links it to a new strategy.
    If is_dynamic_universe is True, the universe can be refreshed by re-running the screener.
    """
    from app.modules.algo.models import UserStrategy
    from app.modules.algo.schemas import UniverseCreate

    universe_svc = UniverseService(db)

    # Build filter_criteria for dynamic universes
    filter_criteria = None
    if data.is_dynamic_universe and data.screener_config:
        filter_criteria = {
            "source": "screener",
            "screener_config": data.screener_config,
        }

    # Create the universe
    universe_name = f"{data.name} Universe"
    universe_data = UniverseCreate(
        name=universe_name,
        description=f"Screener-based universe for strategy '{data.name}'",
        symbols=data.symbols,
        filter_criteria=filter_criteria,
        is_dynamic=data.is_dynamic_universe,
    )
    universe = await universe_svc.create(str(current_user.id), universe_data)

    # Create the strategy
    strategy = UserStrategy(
        user_id=str(current_user.id),
        name=data.name,
        description=data.description
        or f"Strategy created from screener with {len(data.symbols)} symbols",
        strategy_type=data.strategy_type,
        universe_id=universe.id,
        is_active=False,  # User needs to configure and activate
        strategy_config={
            "source": "screener",
            "screener_config": data.screener_config,
            "initial_symbols": data.symbols,
        },
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)

    return CreateStrategyFromScreenerResponse(
        strategy_id=strategy.id,
        strategy_name=strategy.name,
        universe_id=universe.id,
        universe_name=universe.name,
        symbol_count=len(data.symbols),
        is_dynamic=data.is_dynamic_universe,
        created_at=strategy.created_at,
    )


# ============== Strategy Inference ==============


@router.post("/infer-strategy", response_model=InferStrategyResponse)
async def infer_strategy(
    data: InferStrategyRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> InferStrategyResponse:
    """Infer optimal strategy type and parameters from screener filters.

    Analyzes the filter configuration to recommend the best strategy type
    and derive optimal parameters from filter thresholds.
    """
    from app.modules.algo.strategy_inference import inference_engine
    from app.modules.screener.models import CustomScreener
    from app.modules.screener.service import PRESET_DEFINITIONS

    filters = data.filters

    # If screener_run_id provided, get filters from the screener config
    if data.screener_run_id and not filters:
        screener = await db.get(CustomScreener, data.screener_run_id)
        if not screener:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Screener run {data.screener_run_id} not found",
            )
        # Convert stored filter config to FilterConfig objects
        filters = [FilterConfig(**f) for f in screener.filters]

    # If preset provided, get filters from preset definition
    if data.preset and not filters:
        preset_info = PRESET_DEFINITIONS.get(data.preset)
        if preset_info:
            filters = preset_info.filters

    if not filters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filters provided for inference",
        )

    # Run inference
    result = inference_engine.infer(filters)

    return InferStrategyResponse(
        recommended_strategy=StrategyRecommendationResponse(
            strategy_type=result.recommended_strategy.strategy_type,
            strategy_name=result.recommended_strategy.strategy_name,
            description=result.recommended_strategy.description,
            suggested_params=result.recommended_strategy.suggested_params,
            confidence=result.recommended_strategy.confidence,
            reasoning=result.recommended_strategy.reasoning,
        ),
        alternative_strategies=[
            StrategyRecommendationResponse(
                strategy_type=alt.strategy_type,
                strategy_name=alt.strategy_name,
                description=alt.description,
                suggested_params=alt.suggested_params,
                confidence=alt.confidence,
                reasoning=alt.reasoning,
            )
            for alt in result.alternative_strategies
        ],
        filter_analysis=FilterAnalysisResponse(
            primary_intent=result.filter_analysis.primary_intent.value,
            secondary_intent=(
                result.filter_analysis.secondary_intent.value
                if result.filter_analysis.secondary_intent
                else None
            ),
            risk_profile=result.filter_analysis.risk_profile.value,
            detected_patterns=result.filter_analysis.detected_patterns,
        ),
    )


@router.post("/create-smart-strategy", response_model=CreateSmartStrategyResponse)
async def create_smart_strategy(
    data: CreateSmartStrategyRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> CreateSmartStrategyResponse:
    """Create a strategy with auto-inferred parameters from screener filters.

    This combines strategy inference with strategy creation:
    1. Infers optimal strategy type and parameters from filters
    2. Applies any user overrides
    3. Creates universe and strategy
    """
    from app.modules.algo.models import StrategyStatus, UserStrategy
    from app.modules.algo.schemas import UniverseCreate
    from app.modules.algo.strategy_inference import inference_engine
    from app.modules.screener.models import CustomScreener
    from app.modules.screener.service import PRESET_DEFINITIONS

    universe_svc = UniverseService(db)

    filters = data.filters

    # If screener_run_id provided, get filters from the screener config
    if data.screener_run_id and not filters:
        screener = await db.get(CustomScreener, data.screener_run_id)
        if screener:
            filters = [FilterConfig(**f) for f in screener.filters]

    # If preset provided, get filters from preset definition
    if data.preset and not filters:
        preset_info = PRESET_DEFINITIONS.get(data.preset)
        if preset_info:
            filters = preset_info.filters

    # Run inference to get recommended strategy
    if filters:
        result = inference_engine.infer(filters)
        inferred_type = result.recommended_strategy.strategy_type
        inferred_params = result.recommended_strategy.suggested_params.copy()
        inference_reasoning = result.recommended_strategy.reasoning
    else:
        # Fallback if no filters
        inferred_type = "vwap_momentum"
        inferred_params = {}
        inference_reasoning = ["No filters provided - using default strategy"]

    # Apply overrides
    final_strategy_type = data.strategy_type_override or inferred_type
    params_overridden = []

    if data.strategy_params_override:
        for key, value in data.strategy_params_override.items():
            if key in inferred_params and inferred_params[key] != value:
                params_overridden.append(key)
            inferred_params[key] = value

    # Build filter_criteria for dynamic universes
    filter_criteria = None
    if data.is_dynamic_universe and data.screener_config:
        filter_criteria = {
            "source": "screener",
            "screener_config": data.screener_config,
        }

    # Create the universe
    universe_name = f"{data.name} Universe"
    universe_data = UniverseCreate(
        name=universe_name,
        description=f"Smart strategy universe for '{data.name}'",
        symbols=data.symbols,
        filter_criteria=filter_criteria,
        is_dynamic=data.is_dynamic_universe,
    )
    universe = await universe_svc.create(str(current_user.id), universe_data)

    # Create the strategy with inferred config
    strategy = UserStrategy(
        user_id=str(current_user.id),
        name=data.name,
        description=data.description or f"Smart strategy with {len(data.symbols)} symbols",
        strategy_name=final_strategy_type,
        universe_id=universe.id,
        status=StrategyStatus.DISABLED,
        position_sizing_method=data.position_sizing_method,
        portfolio_percent=data.position_size_value,
        strategy_params={
            "source": "smart_screener",
            "product_type": data.product_type,
            "inferred_params": inferred_params,
            "filters_used": [f.model_dump() for f in filters] if filters else [],
            "initial_symbols": data.symbols,
        },
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)

    return CreateSmartStrategyResponse(
        strategy_id=strategy.id,
        strategy_name=strategy.name,
        universe_id=universe.id,
        universe_name=universe.name,
        symbol_count=len(data.symbols),
        is_dynamic=data.is_dynamic_universe,
        created_at=strategy.created_at,
        inferred_strategy_type=inferred_type,
        inferred_params=inferred_params,
        params_overridden=params_overridden,
        inference_reasoning=inference_reasoning,
    )
