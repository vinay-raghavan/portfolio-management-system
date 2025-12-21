"""Instrument API routes."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.modules.instruments.schemas import (
    InstrumentCreate,
    InstrumentResponse,
    InstrumentSearchParams,
    InstrumentSearchResponse,
)
from app.modules.instruments.service import InstrumentService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", response_model=InstrumentSearchResponse)
async def search_instruments(
    query: str | None = Query(default=None, description="Search query"),
    exchange: str | None = Query(default=None, description="Filter by exchange (NSE, BSE)"),
    segment: str | None = Query(default=None, description="Filter by segment (EQ, FO)"),
    instrument_type: str | None = Query(default=None, description="Filter by type (EQ, FUT, OPT)"),
    is_active: bool | None = Query(default=True, description="Filter by active status"),
    underlying: str | None = Query(default=None, description="Filter by underlying"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> InstrumentSearchResponse:
    """Search instruments with filters.
    
    Examples:
    - Search by symbol: /search?query=RELIANCE
    - Filter by exchange: /search?exchange=NSE
    - Filter F&O: /search?segment=FO&underlying=NIFTY
    """
    service = InstrumentService(db)
    params = InstrumentSearchParams(
        query=query,
        exchange=exchange,
        segment=segment,
        instrument_type=instrument_type,
        is_active=is_active,
        underlying=underlying,
        limit=limit,
        offset=offset,
    )
    results, total = await service.search(params)
    
    return InstrumentSearchResponse(
        total=total,
        results=[InstrumentResponse.model_validate(i) for i in results],
    )


@router.get("/{instrument_id}", response_model=InstrumentResponse)
async def get_instrument(
    instrument_id: str,
    db: AsyncSession = Depends(get_db),
) -> InstrumentResponse:
    """Get instrument by ID."""
    service = InstrumentService(db)
    instrument = await service.get_by_id(instrument_id)
    
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument not found: {instrument_id}",
        )
    
    return InstrumentResponse.model_validate(instrument)


@router.get("/symbol/{symbol}", response_model=InstrumentResponse)
async def get_instrument_by_symbol(
    symbol: str,
    exchange: str | None = Query(default=None, description="Exchange (NSE, BSE)"),
    db: AsyncSession = Depends(get_db),
) -> InstrumentResponse:
    """Get instrument by symbol.
    
    If exchange is not specified, returns the first match.
    """
    service = InstrumentService(db)
    instrument = await service.get_by_symbol(symbol, exchange)
    
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument not found: {symbol}",
        )
    
    return InstrumentResponse.model_validate(instrument)


@router.get("/indices/", response_model=list[InstrumentResponse])
async def get_indices(
    exchange: str = Query(default="NSE", description="Exchange"),
    db: AsyncSession = Depends(get_db),
) -> list[InstrumentResponse]:
    """Get all index instruments."""
    service = InstrumentService(db)
    instruments = await service.get_indices(exchange)
    return [InstrumentResponse.model_validate(i) for i in instruments]


@router.get("/fo/underlyings", response_model=list[str])
async def get_fo_underlyings(
    exchange: str = Query(default="NSE", description="Exchange"),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get unique F&O underlyings."""
    service = InstrumentService(db)
    return await service.get_fo_underlyings(exchange)


@router.get("/fo/expiries/{underlying}", response_model=list[str])
async def get_expiry_dates(
    underlying: str,
    exchange: str = Query(default="NSE", description="Exchange"),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get available expiry dates for an F&O underlying."""
    service = InstrumentService(db)
    dates = await service.get_expiry_dates(underlying, exchange)
    return [d.isoformat() for d in dates]


@router.post("/sync/pending", response_model=dict)
async def sync_pending_instruments(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Process pending instrument syncs from Redis.

    This endpoint picks up instruments stored by Celery tasks and
    syncs them to the database using bulk upsert.
    """
    redis = await get_redis()
    service = InstrumentService(db)

    # Keys for pending syncs
    pending_keys = [
        "instruments:nse:equity:pending",
        "instruments:nse:indices:pending",
    ]

    results = {}

    for key in pending_keys:
        try:
            data = await redis.get(key)
            if not data:
                continue

            instruments_data = json.loads(data)

            # Convert to InstrumentCreate objects
            instrument_creates = []
            for inst_data in instruments_data:
                try:
                    instrument_creates.append(InstrumentCreate(**inst_data))
                except Exception as e:
                    logger.warning(f"Invalid instrument data for {inst_data.get('symbol')}: {e}")

            # Use bulk upsert
            if instrument_creates:
                bulk_result = await service.upsert_bulk(instrument_creates)
                results[key] = {
                    "created": bulk_result.created,
                    "updated": bulk_result.updated,
                    "failed": bulk_result.failed,
                }

            # Delete processed key
            await redis.delete(key)

        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            results[key] = {"error": str(e)}

    total_created = sum(r.get("created", 0) for r in results.values() if isinstance(r, dict))
    total_updated = sum(r.get("updated", 0) for r in results.values() if isinstance(r, dict))

    return {
        "status": "success",
        "total_created": total_created,
        "total_updated": total_updated,
        "details": results,
    }

