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


@router.post("/sync/nifty/{index_name}", response_model=dict)
async def sync_nifty_index_constituents(
    index_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Sync constituents of a Nifty index to the instruments table.

    This fetches stocks from NSE directly and stores them with industry data.

    Available indices:
    - NIFTY50, NIFTY100, NIFTY200, NIFTY500
    - BANKNIFTY, NIFTYIT, NIFTYNEXT50
    - NIFTYMIDCAP50, NIFTYMIDCAP100

    Example: POST /api/v1/instruments/sync/nifty/NIFTY500
    """
    from app.providers.data.nse import NSEDataProvider
    from decimal import Decimal

    try:
        # Use NSE provider to fetch constituents
        nse_provider = NSEDataProvider()
        constituents = await nse_provider.get_index_constituents(index_name)

        if not constituents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No constituents found for index: {index_name}",
            )

        # Convert to InstrumentCreate objects
        service = InstrumentService(db)
        instrument_creates = []

        for c in constituents:
            try:
                instrument_creates.append(
                    InstrumentCreate(
                        symbol=c["symbol"],
                        name=c.get("name") or c["symbol"],
                        exchange="NSE",
                        segment="EQ",
                        instrument_type="EQ",
                        series=c.get("series", "EQ"),
                        isin=c.get("isin"),
                        lot_size=1,
                        tick_size=Decimal("0.05"),
                        is_active=True,
                        is_tradeable=True,
                        industry=c.get("industry"),
                    )
                )
            except Exception as e:
                logger.warning(f"Error creating instrument for {c.get('symbol')}: {e}")

        # Bulk upsert
        if instrument_creates:
            result = await service.upsert_bulk(instrument_creates)
            await db.commit()

            return {
                "status": "success",
                "index": index_name.upper(),
                "total_constituents": len(constituents),
                "created": result.created,
                "updated": result.updated,
                "failed": result.failed,
                "errors": result.errors[:5] if result.errors else [],
            }

        return {
            "status": "error",
            "message": "No valid instruments to sync",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing index {index_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing index constituents: {str(e)}",
        )


@router.post("/sync/nse/all", response_model=dict)
async def sync_all_nse_stocks(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Sync ALL NSE listed stocks from the official equity master CSV.

    This fetches ~2200+ stocks from NSE's official equity list.
    Note: This does not include industry data. Use /sync/nifty/NIFTY500 first
    to get industry data for major stocks.

    Example: POST /api/v1/instruments/sync/nse/all
    """
    import csv
    import io
    import httpx
    from decimal import Decimal

    NSE_EQUITY_CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

    try:
        # Download equity CSV from NSE
        async with httpx.AsyncClient(timeout=60.0) as client:
            # First visit NSE homepage to get cookies
            await client.get(
                "https://www.nseindia.com/",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )

            # Download CSV
            response = await client.get(
                NSE_EQUITY_CSV_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/csv,application/csv,text/plain,*/*",
                    "Referer": "https://www.nseindia.com/",
                },
            )
            response.raise_for_status()

        # Parse CSV
        content = response.text
        reader = csv.DictReader(io.StringIO(content))

        # Get existing instruments to preserve industry data
        from sqlalchemy import select
        from app.modules.instruments.models import Instrument

        service = InstrumentService(db)
        existing_result = await db.execute(
            select(Instrument.symbol, Instrument.industry).where(Instrument.exchange == "NSE")
        )
        existing_industries = {row[0]: row[1] for row in existing_result.fetchall()}

        instrument_creates = []
        for row in reader:
            try:
                symbol = row.get("SYMBOL", "").strip()
                if not symbol:
                    continue

                # Preserve existing industry data if available
                industry = existing_industries.get(symbol)

                # CSV columns have spaces in names, try both variants
                series = (row.get(" SERIES") or row.get("SERIES") or "EQ").strip()
                isin = (row.get(" ISIN NUMBER") or row.get("ISIN NUMBER") or "").strip()

                instrument_creates.append(
                    InstrumentCreate(
                        symbol=symbol,
                        name=row.get("NAME OF COMPANY", "").strip() or symbol,
                        exchange="NSE",
                        segment="EQ",
                        instrument_type="EQ",
                        series=series or "EQ",
                        isin=isin or None,
                        lot_size=1,
                        tick_size=Decimal("0.05"),
                        is_active=True,
                        is_tradeable=True,
                        industry=industry,  # Preserve if we have it
                    )
                )
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")

        # Bulk upsert
        if instrument_creates:
            result = await service.upsert_bulk(instrument_creates)
            await db.commit()

            return {
                "status": "success",
                "source": "NSE Equity Master CSV",
                "total_parsed": len(instrument_creates),
                "created": result.created,
                "updated": result.updated,
                "failed": result.failed,
                "errors": result.errors[:5] if result.errors else [],
            }

        return {
            "status": "error",
            "message": "No instruments found in CSV",
        }

    except Exception as e:
        logger.error(f"Error syncing NSE equity master: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing NSE stocks: {str(e)}",
        )