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

