"""Market data API routes."""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from datetime import datetime

from app.modules.data.schemas import (
    StockQuote,
    StockInfo,
    HistoricalDataResponse,
    SearchResult,
    IndexConstituentsResponse,
)
from app.modules.data.service import MarketDataService
from app.core.config import settings

router = APIRouter()


class MarketStatus(BaseModel):
    """Market status response."""

    is_open: bool
    status: str
    market: str
    timestamp: datetime | None = None
    next_open: datetime | None = None


@router.get("/market/status", response_model=MarketStatus)
async def get_market_status() -> MarketStatus:
    """Get current market status (open/closed)."""
    service = MarketDataService()
    status_info = await service.get_market_status()
    return MarketStatus(**status_info)


@router.get("/index/{index_name}/constituents", response_model=IndexConstituentsResponse)
async def get_index_constituents(index_name: str) -> IndexConstituentsResponse:
    """Get constituents of a Nifty index with their current quotes.

    Available indices:
    - NIFTY 50, NIFTY 100, NIFTY 200, NIFTY 500
    - NIFTY BANK, NIFTY IT, NIFTY NEXT 50
    - NIFTY MIDCAP 50, NIFTY MIDCAP 100
    - And other NSE indices

    Note: This endpoint is only available when using the NSE data provider.
    """
    service = MarketDataService()
    result = await service.get_index_constituents(index_name)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Index constituents not found for: {index_name}. Make sure you're using the NSE data provider.",
        )

    return result


@router.get("/{symbol}/quote", response_model=StockQuote)
async def get_stock_quote(symbol: str) -> StockQuote:
    """Get current quote for a stock symbol."""
    service = MarketDataService()
    quote = await service.get_quote(symbol)

    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote not found for symbol: {symbol}",
        )

    return quote


@router.get("/{symbol}/info", response_model=StockInfo)
async def get_stock_info(symbol: str) -> StockInfo:
    """Get detailed information for a stock symbol."""
    service = MarketDataService()
    info = await service.get_stock_info(symbol)

    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Info not found for symbol: {symbol}",
        )

    return info


@router.get("/{symbol}/history", response_model=HistoricalDataResponse)
async def get_historical_data(
    symbol: str,
    period: str = Query("1mo", pattern="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$"),
    interval: str = Query("1d", pattern="^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$"),
) -> HistoricalDataResponse:
    """Get historical price data for a stock symbol."""
    service = MarketDataService()
    data = await service.get_historical_data(symbol, period, interval)

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historical data not found for symbol: {symbol}",
        )

    return data


@router.get("/search", response_model=list[SearchResult])
async def search_stocks(q: str = Query(min_length=1, max_length=50)) -> list[SearchResult]:
    """Search for stock symbols."""
    service = MarketDataService()
    results = await service.search_symbols(q)
    return [SearchResult(**r) for r in results]

