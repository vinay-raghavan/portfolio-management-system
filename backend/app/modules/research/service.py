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

    async def get_market_news(self, category: str | None = None, limit: int = 10) -> NewsResponse:
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
            "current_price": float(quote.price) if quote else None,
            "price_change": float(quote.change) if quote and quote.change else None,
            "price_change_pct": float(quote.change_pct)
            if quote and quote.change_pct
            else None,
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

        Fetches NIFTY 500 constituents from NSE and aggregates by sector/industry.
        Calculates average daily and weekly change per sector.

        Returns:
            List of sector dicts with performance data
        """
        try:
            from shared.providers.data.nse import NSEDataProvider
            from shared.providers.data.yahoo import YahooDataProvider

            nse = NSEDataProvider()
            constituents = await nse.get_index_constituents("NIFTY 500")

            if not constituents:
                logger.warning("No constituents returned from NSE, using fallback")
                return self._get_fallback_sectors()

            # Group stocks by industry/sector
            sectors: dict[str, list[dict]] = {}
            for stock in constituents:
                sector = stock.get("industry") or stock.get("sector") or "Other"
                if sector not in sectors:
                    sectors[sector] = []
                sectors[sector].append(stock)

            # Calculate metrics per sector
            sector_data = []
            yahoo = YahooDataProvider()

            for sector_name, stocks in sectors.items():
                # Skip empty sector names (like the index itself)
                if not sector_name or sector_name == "Other":
                    continue

                # Get daily changes (change_pct from NSE provider)
                changes = [
                    s.get("change_pct", 0)
                    for s in stocks
                    if s.get("change_pct") is not None
                ]

                if not changes:
                    continue

                avg_change = sum(changes) / len(changes)

                # Find top gainer and loser
                sorted_stocks = sorted(
                    stocks,
                    key=lambda s: s.get("change_pct", 0) or 0,
                    reverse=True,
                )
                top_gainer = sorted_stocks[0].get("symbol") if sorted_stocks else None
                top_loser = sorted_stocks[-1].get("symbol") if sorted_stocks else None

                # Calculate weekly change using top 3 stocks (by volume/liquidity)
                weekly_change = await self._calculate_sector_weekly_change(
                    yahoo, stocks[:3]
                )

                sector_data.append({
                    "sector": sector_name,
                    "change_1d": round(avg_change, 2),
                    "change_1w": weekly_change,
                    "change_1m": None,
                    "change_3m": None,
                    "change_1y": None,
                    "stock_count": len(stocks),
                    "top_gainer": top_gainer,
                    "top_loser": top_loser,
                })

            # Sort by daily change (best performing first)
            sector_data.sort(key=lambda x: x.get("change_1d") or 0, reverse=True)

            logger.info(f"Fetched {len(sector_data)} sectors from NSE NIFTY 500")
            return sector_data

        except Exception as e:
            logger.error(f"Error fetching sector data from NSE: {e}")
            return self._get_fallback_sectors()

    async def _calculate_sector_weekly_change(
        self,
        yahoo: "YahooDataProvider",
        stocks: list[dict],
    ) -> float | None:
        """Calculate average weekly change for a sector using sample stocks.

        Args:
            yahoo: Yahoo data provider instance
            stocks: List of stock dicts with 'symbol' key

        Returns:
            Average weekly change percentage or None if unavailable
        """
        if not stocks:
            return None

        weekly_changes = []
        for stock in stocks[:3]:  # Limit to 3 stocks per sector
            symbol = stock.get("symbol")
            if not symbol:
                continue

            try:
                # Get 5-day historical data
                history = await yahoo.get_historical(symbol, period="5d", interval="1d")
                if history and len(history) >= 2:
                    # Calculate change from first to last close
                    first_close = float(history[0].close)
                    last_close = float(history[-1].close)
                    if first_close > 0:
                        change = ((last_close - first_close) / first_close) * 100
                        weekly_changes.append(change)
            except Exception as e:
                logger.debug(f"Error fetching weekly data for {symbol}: {e}")
                continue

        if weekly_changes:
            return round(sum(weekly_changes) / len(weekly_changes), 2)
        return None

    def _get_fallback_sectors(self) -> list[dict]:
        """Return fallback sector list when NSE data is unavailable."""
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

        Fetches NIFTY 500 constituents and filters by sector/industry.

        Args:
            sector: Sector name
            limit: Maximum number of stocks

        Returns:
            Dict with sector stocks and count
        """
        try:
            from shared.providers.data.nse import NSEDataProvider

            nse = NSEDataProvider()
            constituents = await nse.get_index_constituents("NIFTY 500")

            if not constituents:
                logger.warning(f"No constituents for sector {sector}")
                return {"sector": sector, "stocks": [], "total_count": 0}

            # Filter stocks by sector/industry (case-insensitive match)
            sector_lower = sector.lower()
            sector_stocks = [
                s for s in constituents
                if (s.get("industry") or s.get("sector") or "").lower() == sector_lower
            ]

            # Sort by daily change (best performers first)
            sector_stocks.sort(
                key=lambda s: s.get("change_pct", 0) or 0,
                reverse=True,
            )

            # Map to expected format
            stocks = []
            for s in sector_stocks[:limit]:
                stocks.append({
                    "symbol": s.get("symbol", ""),
                    "name": s.get("name") or s.get("symbol"),
                    "current_price": s.get("last_price"),
                    "price_change_pct": s.get("change_pct"),
                    "market_cap": None,  # Not available from index constituents
                    "pe_ratio": None,
                    "pb_ratio": None,
                    "dividend_yield": None,
                    "roe": None,
                    "revenue_growth": None,
                })

            logger.info(f"Found {len(stocks)} stocks in sector {sector}")
            return {
                "sector": sector,
                "stocks": stocks,
                "total_count": len(sector_stocks),
            }

        except Exception as e:
            logger.error(f"Error fetching sector stocks for {sector}: {e}")
            return {"sector": sector, "stocks": [], "total_count": 0}
