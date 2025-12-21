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
    IndexConstituent,
    IndexConstituentsResponse,
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

    async def get_market_status(self) -> dict:
        """Get current market status.

        Returns:
            Dict with market status information.
        """
        from datetime import datetime
        from app.core.config import settings

        # Check if provider has market status method
        if hasattr(self._provider, "get_market_status"):
            status = await self._provider.get_market_status()
            status["market"] = settings.DEFAULT_MARKET
            return status

        # Fallback for providers without market status
        is_open = await self._provider.is_market_open()
        result = {
            "is_open": is_open,
            "status": "open" if is_open else "closed",
            "market": settings.DEFAULT_MARKET,
            "timestamp": datetime.now().isoformat(),
        }

        # Add next open time if provider supports it
        if hasattr(self._provider, "get_next_market_open"):
            result["next_open"] = self._provider.get_next_market_open().isoformat()

        return result

    async def get_index_constituents(self, index: str) -> IndexConstituentsResponse | None:
        """Get constituents of an index.

        Args:
            index: Index name (e.g., "NIFTY 50", "NIFTY 500")

        Returns:
            IndexConstituentsResponse with list of constituent stocks
        """
        # Check if provider supports index constituents
        if not hasattr(self._provider, "get_index_constituents"):
            logger.warning(f"Provider {type(self._provider).__name__} does not support index constituents")
            return None

        constituents_data = await self._provider.get_index_constituents(index)
        if not constituents_data:
            return None

        constituents = [
            IndexConstituent(
                symbol=c["symbol"],
                name=c.get("name"),
                industry=c.get("industry"),
                isin=c.get("isin"),
                series=c.get("series", "EQ"),
                is_fno=c.get("is_fno", False),
                last_price=c.get("last_price"),
                change=c.get("change"),
                change_pct=c.get("change_pct"),
                open=c.get("open"),
                high=c.get("high"),
                low=c.get("low"),
                previous_close=c.get("previous_close"),
                volume=c.get("volume"),
                year_high=c.get("year_high"),
                year_low=c.get("year_low"),
            )
            for c in constituents_data
        ]

        return IndexConstituentsResponse(
            index=index.upper(),
            count=len(constituents),
            constituents=constituents,
        )
