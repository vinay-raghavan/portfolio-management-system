"""Analysis API routes."""

from fastapi import APIRouter, HTTPException, status

from app.modules.analysis.schemas import TechnicalIndicators, AnalysisResult, StockInfo
from app.modules.analysis.service import AnalysisService

router = APIRouter()


@router.get("/{symbol}/indicators", response_model=TechnicalIndicators)
async def get_technical_indicators(symbol: str) -> TechnicalIndicators:
    """Get technical indicators for a stock symbol."""
    service = AnalysisService()
    indicators = await service.get_technical_indicators(symbol)

    if indicators is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not calculate indicators for symbol: {symbol}",
        )

    return indicators


@router.get("/{symbol}/info", response_model=StockInfo)
async def get_stock_info(symbol: str) -> StockInfo:
    """Get detailed stock information including fundamentals."""
    service = AnalysisService()
    info = await service.get_stock_info(symbol)

    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not get info for symbol: {symbol}",
        )

    return info


@router.get("/{symbol}", response_model=AnalysisResult)
async def get_analysis(symbol: str) -> AnalysisResult:
    """Get complete technical analysis for a stock symbol."""
    service = AnalysisService()
    analysis = await service.get_analysis(symbol)

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not analyze symbol: {symbol}",
        )

    return analysis

