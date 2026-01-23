"""Screener API routes."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.modules.algo.universe_service import (
    DYNAMIC_UNIVERSES,
    PREDEFINED_UNIVERSES,
    UniverseService,
)
from app.modules.screener.schemas import (
    CustomScreenerCreate,
    CustomScreenerListResponse,
    CustomScreenerResponse,
    CustomScreenerUpdate,
    FilterConfig,
    ScreenerPresetRunRequest,
    ScreenerPresetsResponse,
    ScreenerRunRequest,
    ScreenerRunResponse,
)
from app.modules.screener.service import ScreenerService
from shared.providers.data import NSEDataProvider

logger = logging.getLogger(__name__)

router = APIRouter()


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

    # Create data provider
    nse_provider = NSEDataProvider()
    try:
        service = ScreenerService(db)
        result = await service.run_screener(
            user_id=current_user.id,
            symbols=symbols,
            filters=data.filters,
            universe=data.universe,
            min_score=data.min_score,
            top_n=data.top_n,
            data_provider=nse_provider,
        )
        await db.commit()
        return result
    finally:
        await nse_provider.close()


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

    nse_provider = NSEDataProvider()
    try:
        service = ScreenerService(db)
        result = await service.run_screener(
            user_id=current_user.id,
            symbols=symbols,
            filters=preset.filters,
            universe=data.universe,
            min_score=data.min_score,
            top_n=data.top_n,
            data_provider=nse_provider,
            preset=data.preset.value,
        )
        await db.commit()
        return result
    finally:
        await nse_provider.close()


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
    return CustomScreenerListResponse(
        screeners=[_screener_to_response(s) for s in screeners]
    )


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
    service = ScreenerService(db)
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
    nse_provider = NSEDataProvider()
    try:
        result = await service.run_screener(
            user_id=current_user.id,
            symbols=symbols,
            filters=filters,
            universe=screener.universe,
            min_score=screener.min_score,
            top_n=screener.top_n,
            data_provider=nse_provider,
            custom_screener_id=screener.id,
        )
        await db.commit()
        return result
    finally:
        await nse_provider.close()


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
        nse_provider = NSEDataProvider()
        try:
            universe_svc = UniverseService(db)
            nse_index = DYNAMIC_UNIVERSES[universe_upper]["nse_index"]
            return await universe_svc.fetch_index_symbols(nse_index, nse_provider)
        finally:
            await nse_provider.close()

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

