"""Market data service using provider abstraction."""

from decimal import Decimal
import logging

from app.providers.data.factory import get_data_provider
from app.providers.data.base import DataProvider
from app.modules.data.schemas import (
    StockQuote,
    StockInfo,
    HistoricalDataPoint,
    HistoricalDataResponse,
)

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching market data using configurable data providers.

    This service acts as a bridge between the API layer and the data provider
    abstraction. It converts provider schemas to module-specific schemas.
    """

    def __init__(self, provider: DataProvider | None = None):
        """Initialize with optional custom provider.

        Args:
            provider: Data provider instance. If None, uses default from config.
        """
        self._provider = provider or get_data_provider()

    async def get_current_price(self, symbol: str) -> Decimal | None:
        """Get current price for a symbol."""
        price = await self._provider.get_current_price(symbol)
        if price is not None:
            return Decimal(str(price))
        return None

    async def get_quote(self, symbol: str) -> StockQuote | None:
        """Get full quote for a symbol."""
        quote = await self._provider.get_quote(symbol)
        if quote is None:
            return None

        return StockQuote(
            symbol=quote.symbol,
            price=quote.price,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            close=quote.close,
            volume=quote.volume,
            change=quote.change,
            change_pct=quote.change_percent,
            timestamp=quote.timestamp,
        )

    async def get_stock_info(self, symbol: str) -> StockInfo | None:
        """Get detailed stock information."""
        info = await self._provider.get_instrument_info(symbol)
        if info is None:
            return None

        return StockInfo(
            symbol=info.symbol,
            name=info.name,
            exchange=info.exchange,
            sector=info.sector,
            industry=info.industry,
        )

    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> HistoricalDataResponse | None:
        """Get historical price data."""
        ohlcv_list = await self._provider.get_historical(symbol, period, interval)
        if not ohlcv_list:
            return None

        data_points = [
            HistoricalDataPoint(
                date=ohlcv.timestamp,
                open=ohlcv.open,
                high=ohlcv.high,
                low=ohlcv.low,
                close=ohlcv.close,
                volume=ohlcv.volume,
            )
            for ohlcv in ohlcv_list
        ]

        return HistoricalDataResponse(
            symbol=symbol.upper(),
            interval=interval,
            data=data_points,
        )

    async def search_symbols(self, query: str) -> list[dict]:
        """Search for symbols by name or ticker."""
        results = await self._provider.search_symbols(query)
        return [
            {
                "symbol": r.symbol,
                "name": r.name,
                "exchange": r.exchange,
                "type": r.instrument_type,
            }
            for r in results
        ]

