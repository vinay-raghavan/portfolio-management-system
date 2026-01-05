"""Abstract base class for data providers."""

from abc import ABC, abstractmethod
from decimal import Decimal

from app.providers.schemas import OHLCV, InstrumentInfo, MarketSession, Quote, SearchResult


class DataProvider(ABC):
    """Abstract base class for market data providers.

    All data providers (Yahoo, NSE, AngelOne, etc.) must implement this interface.
    This allows switching between data sources without changing business logic.
    """

    name: str = "base"

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for a symbol.

        Args:
            symbol: Stock symbol (e.g., "RELIANCE", "AAPL")

        Returns:
            Quote object with current price data, or None if not found
        """
        pass

    @abstractmethod
    async def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[OHLCV]:
        """Get historical OHLCV data for a symbol.

        Args:
            symbol: Stock symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)

        Returns:
            List of OHLCV data points
        """
        pass

    @abstractmethod
    async def search_symbols(self, query: str) -> list[SearchResult]:
        """Search for symbols matching a query.

        Args:
            query: Search query string

        Returns:
            List of matching symbols with basic info
        """
        pass

    @abstractmethod
    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        """Get detailed instrument information.

        Args:
            symbol: Stock symbol

        Returns:
            InstrumentInfo with details, or None if not found
        """
        pass

    async def get_current_price(self, symbol: str) -> float | None:
        """Convenience method to get just the current price.

        Args:
            symbol: Stock symbol

        Returns:
            Current price as float, or None if not available
        """
        quote = await self.get_quote(symbol)
        if quote:
            return float(quote.price)
        return None

    async def is_market_open(self) -> bool:
        """Check if the market is currently open.

        Returns:
            True if market is open, False otherwise
        """
        # Default implementation - override in subclasses for specific markets
        return True

    def get_market_session(self) -> MarketSession:
        """Get the current market session.

        Returns:
            MarketSession enum indicating current session type
        """
        # Default implementation - override in subclasses for specific markets
        return MarketSession.REGULAR

    async def get_extended_hours_quote(self, symbol: str) -> Quote | None:
        """Get quote with extended hours data (pre-market/post-market).

        This is a convenience method that returns the same data as get_quote()
        but explicitly indicates that extended hours data is expected.
        Providers that support extended hours will include pre_market_* and
        post_market_* fields in the Quote response.

        Args:
            symbol: Stock symbol

        Returns:
            Quote object with extended hours data, or None if not found
        """
        return await self.get_quote(symbol)

    async def get_effective_price(self, symbol: str) -> Decimal | None:
        """Get the most relevant current price based on market session.

        During pre-market: returns pre_market_price if available
        During regular hours: returns regular price
        During post-market: returns post_market_price if available
        When closed: returns the last available price

        Args:
            symbol: Stock symbol

        Returns:
            The most relevant current price, or None if not available
        """
        quote = await self.get_quote(symbol)
        if not quote:
            return None

        session = self.get_market_session()

        if session == MarketSession.PRE_MARKET and quote.pre_market_price:
            return quote.pre_market_price
        elif session == MarketSession.POST_MARKET and quote.post_market_price:
            return quote.post_market_price
        else:
            return quote.price

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to provider-specific format.

        Args:
            symbol: Input symbol in any format

        Returns:
            Symbol formatted for this provider
        """
        return symbol.upper().strip()
