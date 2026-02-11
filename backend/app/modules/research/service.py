"""Research module service layer."""

import logging

from shared.providers.data.base import DataProvider
from shared.providers.data.yahoo import YahooDataProvider
from shared.providers.news import BaseNewsProvider, get_news_provider
from shared.providers.schemas import (
    DividendData,
    FinancialData,
    FundamentalData,
    NewsResponse,
)

logger = logging.getLogger(__name__)


class ResearchService:
    """Service for research operations including fundamental data and news."""

    def __init__(
        self,
        provider: DataProvider | None = None,
        news_provider: BaseNewsProvider | None = None,
    ):
        """Initialize research service.

        Args:
            provider: Data provider to use. Defaults to YahooDataProvider.
            news_provider: News provider to use. Defaults to factory default.
        """
        self.provider = provider or YahooDataProvider()
        self.news_provider = news_provider or get_news_provider()

    async def get_fundamentals(self, symbol: str) -> FundamentalData | None:
        """Get fundamental analysis data for a stock.

        Args:
            symbol: Stock symbol

        Returns:
            FundamentalData with valuation ratios and metrics
        """
        return await self.provider.get_fundamentals(symbol)

    async def get_financials(self, symbol: str) -> FinancialData | None:
        """Get financial statements for a stock.

        Args:
            symbol: Stock symbol

        Returns:
            FinancialData with quarterly/annual statements
        """
        return await self.provider.get_financials(symbol)

    async def get_dividends(self, symbol: str) -> DividendData | None:
        """Get dividend history and metrics for a stock.

        Args:
            symbol: Stock symbol

        Returns:
            DividendData with dividend history
        """
        return await self.provider.get_dividends(symbol)

    async def get_news(self, symbol: str, limit: int = 10) -> NewsResponse:
        """Get news articles for a stock with sentiment analysis.

        Args:
            symbol: Stock symbol
            limit: Maximum number of articles

        Returns:
            NewsResponse with articles and sentiment stats
        """
        return await self.news_provider.get_company_news(symbol, limit=limit)

    async def get_market_news(
        self, category: str | None = None, limit: int = 10
    ) -> NewsResponse:
        """Get general market news.

        Args:
            category: Optional category filter
            limit: Maximum number of articles

        Returns:
            NewsResponse with market news articles
        """
        return await self.news_provider.get_market_news(category=category, limit=limit)

    async def get_full_research(
        self,
        symbol: str,
        news_limit: int = 5,
    ) -> dict:
        """Get complete research data for a stock.

        Combines fundamentals, dividends, and news into a single response.

        Args:
            symbol: Stock symbol
            news_limit: Maximum number of news articles

        Returns:
            Dict with fundamentals, dividends, news, and quote data
        """
        import asyncio

        # Fetch all data concurrently
        fundamentals_task = self.get_fundamentals(symbol)
        dividends_task = self.get_dividends(symbol)
        news_task = self.get_news(symbol, limit=news_limit)
        quote_task = self.provider.get_quote(symbol)

        fundamentals, dividends, news, quote = await asyncio.gather(
            fundamentals_task,
            dividends_task,
            news_task,
            quote_task,
            return_exceptions=True,
        )

        # Handle exceptions gracefully
        if isinstance(fundamentals, Exception):
            logger.warning(f"Error fetching fundamentals for {symbol}: {fundamentals}")
            fundamentals = None
        if isinstance(dividends, Exception):
            logger.warning(f"Error fetching dividends for {symbol}: {dividends}")
            dividends = None
        if isinstance(news, Exception):
            logger.warning(f"Error fetching news for {symbol}: {news}")
            news = None
        if isinstance(quote, Exception):
            logger.warning(f"Error fetching quote for {symbol}: {quote}")
            quote = None

        return {
            "symbol": symbol,
            "name": fundamentals.symbol if fundamentals else None,
            "sector": fundamentals.sector if fundamentals else None,
            "industry": fundamentals.industry if fundamentals else None,
            "current_price": float(quote.last_price) if quote else None,
            "price_change": float(quote.change) if quote and quote.change else None,
            "price_change_pct": float(quote.change_percent) if quote and quote.change_percent else None,
            "fundamentals": fundamentals,
            "dividends": dividends,
            "news": news,
        }

    async def get_peers(self, symbol: str, limit: int = 10) -> dict:
        """Get peer stocks for comparison.

        Finds stocks in the same industry/sector and fetches their metrics.

        Args:
            symbol: Stock symbol
            limit: Maximum number of peers

        Returns:
            Dict with peer stocks and sector averages
        """
        # First get the target stock's sector/industry
        fundamentals = await self.get_fundamentals(symbol)

        if not fundamentals:
            return {
                "symbol": symbol,
                "sector": None,
                "industry": None,
                "peers": [],
            }

        # For now, return empty peers - would need a stock universe to search
        # In production, this would query a database of stocks by sector/industry
        logger.info(
            f"Peer lookup for {symbol} in sector={fundamentals.sector}, "
            f"industry={fundamentals.industry} - requires stock universe"
        )

        return {
            "symbol": symbol,
            "sector": fundamentals.sector,
            "industry": fundamentals.industry,
            "peers": [],
            "sector_avg_pe": None,
            "sector_avg_pb": None,
            "sector_avg_dividend_yield": None,
        }

    async def get_sectors(self) -> list[dict]:
        """Get all sectors with performance data.

        Returns performance metrics for each sector. Currently returns a
        predefined list of sectors - in production this would aggregate
        from a stock universe database.

        Returns:
            List of sector dicts with performance data
        """
        # Standard sectors (GICS sectors)
        sectors = [
            "Technology",
            "Healthcare",
            "Financials",
            "Consumer Discretionary",
            "Communication Services",
            "Industrials",
            "Consumer Staples",
            "Energy",
            "Utilities",
            "Real Estate",
            "Materials",
        ]

        # Return sectors with placeholder performance data
        # In production, this would calculate from actual stock data
        logger.info("get_sectors() - returning predefined sector list (no stock universe)")

        return [
            {
                "sector": sector,
                "change_1d": None,
                "change_1w": None,
                "change_1m": None,
                "change_3m": None,
                "change_1y": None,
                "stock_count": 0,
                "top_gainer": None,
                "top_loser": None,
            }
            for sector in sectors
        ]

    async def get_sector_stocks(
        self,
        sector: str,
        limit: int = 20,
    ) -> dict:
        """Get stocks within a specific sector.

        Returns stocks belonging to the specified sector with their metrics.
        Currently a stub - requires a stock universe database to implement.

        Args:
            sector: Sector name
            limit: Maximum number of stocks

        Returns:
            Dict with sector stocks and count
        """
        logger.info(f"get_sector_stocks({sector}) - requires stock universe database")

        return {
            "sector": sector,
            "stocks": [],
            "total_count": 0,
        }

