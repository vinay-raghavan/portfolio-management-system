"""Analysis API routes."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, OptionalUser, RedisClient
from app.modules.analysis.schemas import AnalysisResult, StockInfo, TechnicalIndicators
from app.modules.analysis.service import AnalysisService
from app.modules.data.service import get_user_data_provider

router = APIRouter()


@router.get("/{symbol}/indicators", response_model=TechnicalIndicators)
async def get_technical_indicators(
    symbol: str,
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
) -> TechnicalIndicators:
    """Get technical indicators for a stock symbol.

    Uses the user's preferred data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    # Get user-specific provider if authenticated
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = AnalysisService(provider=provider, redis=redis)
    indicators = await service.get_technical_indicators(symbol)

    if indicators is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not calculate indicators for symbol: {symbol}",
        )

    return indicators


@router.get("/{symbol}/info", response_model=StockInfo)
async def get_stock_info(
    symbol: str,
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
) -> StockInfo:
    """Get detailed stock information including fundamentals.

    Uses the user's preferred data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = AnalysisService(provider=provider, redis=redis)
    info = await service.get_stock_info(symbol)

    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not get info for symbol: {symbol}",
        )

    return info


@router.get("/{symbol}", response_model=AnalysisResult)
async def get_analysis(
    symbol: str,
    db: DbSession,
    redis: RedisClient,
    current_user: OptionalUser,
) -> AnalysisResult:
    """Get complete technical analysis for a stock symbol.

    Uses the user's preferred data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = AnalysisService(provider=provider, redis=redis)
    analysis = await service.get_analysis(symbol)

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not analyze symbol: {symbol}",
        )

    return analysis
