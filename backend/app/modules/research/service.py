"""Research module service layer."""

import logging

from shared.providers.data.base import DataProvider
from shared.providers.data.yahoo import YahooDataProvider
from shared.providers.schemas import DividendData, FinancialData, FundamentalData

logger = logging.getLogger(__name__)


class ResearchService:
    """Service for research operations including fundamental data."""

    def __init__(self, provider: DataProvider | None = None):
        """Initialize research service.

        Args:
            provider: Data provider to use. Defaults to YahooDataProvider.
        """
        self.provider = provider or YahooDataProvider()

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

