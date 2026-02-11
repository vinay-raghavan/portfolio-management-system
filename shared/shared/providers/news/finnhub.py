"""Finnhub news provider stub.

This is a placeholder implementation for the Finnhub API news provider.
Finnhub offers a generous free tier (60 calls/min) with official API support.

To use this provider:
1. Get a free API key from https://finnhub.io/
2. Set FINNHUB_API_KEY environment variable
3. Register the provider: NewsProviderFactory.register("finnhub", FinnhubNewsProvider)

API Endpoints (to be implemented):
- /api/v1/news?category=general - Market news
- /api/v1/company-news?symbol=AAPL - Company-specific news
- /api/v1/stock/social-sentiment?symbol=GME - Social media sentiment (premium)
"""

import logging
from datetime import UTC, datetime

from ..schemas import NewsArticle, NewsResponse
from .base import BaseNewsProvider
from .sentiment import KeywordSentimentAnalyzer

logger = logging.getLogger(__name__)


class FinnhubNewsProvider(BaseNewsProvider):
    """News provider stub for Finnhub API.

    Requires FINNHUB_API_KEY to be set.
    See https://finnhub.io/docs/api for API documentation.

    Features available with free tier:
    - Company news (60 calls/min)
    - Market news (60 calls/min)
    - Basic sentiment

    Premium features:
    - Social media sentiment
    - Company filings
    - Analyst recommendations
    """

    name = "finnhub"

    def __init__(self, api_key: str | None = None, timeout: float = 10.0):
        """Initialize Finnhub news provider.

        Args:
            api_key: Finnhub API key (or set FINNHUB_API_KEY env var)
            timeout: HTTP request timeout in seconds
        """
        import os

        self._api_key = api_key or os.getenv("FINNHUB_API_KEY")
        self._base_url = "https://finnhub.io/api/v1"
        self._timeout = timeout
        self._sentiment_analyzer = KeywordSentimentAnalyzer()

        if not self._api_key:
            logger.warning(
                "FinnhubNewsProvider initialized without API key. "
                "Set FINNHUB_API_KEY environment variable to use this provider."
            )

    def analyze_sentiment(self, article: NewsArticle) -> NewsArticle:
        """Analyze sentiment using keyword-based analyzer."""
        return self._sentiment_analyzer.analyze(article)

    async def get_company_news(
        self,
        symbol: str,
        limit: int = 10,
    ) -> NewsResponse:
        """Get news articles for a specific company/stock.

        STUB: Returns empty response. Implement with actual Finnhub API.

        API endpoint: GET /api/v1/company-news
        Parameters: symbol, from, to

        Args:
            symbol: Stock symbol (e.g., "AAPL", "MSFT")
            limit: Maximum number of articles to return

        Returns:
            NewsResponse with list of NewsArticle objects
        """
        if not self._api_key:
            logger.warning("Cannot fetch Finnhub news: API key not configured")
            return NewsResponse(
                symbol=symbol,
                articles=[],
                total_count=0,
                last_updated=datetime.now(UTC),
            )

        # TODO: Implement actual Finnhub API call
        # url = f"{self._base_url}/company-news"
        # params = {
        #     "symbol": symbol,
        #     "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        #     "to": datetime.now().strftime("%Y-%m-%d"),
        #     "token": self._api_key,
        # }
        # response = await httpx.get(url, params=params)
        # ...

        logger.info(f"FinnhubNewsProvider.get_company_news({symbol}) - STUB, not implemented")
        return NewsResponse(
            symbol=symbol,
            articles=[],
            total_count=0,
            last_updated=datetime.now(UTC),
        )

    async def get_market_news(
        self,
        category: str | None = None,
        limit: int = 10,
    ) -> NewsResponse:
        """Get general market news.

        STUB: Returns empty response. Implement with actual Finnhub API.

        API endpoint: GET /api/v1/news
        Parameters: category (general, forex, crypto, merger)

        Args:
            category: News category (general, forex, crypto, merger)
            limit: Maximum number of articles to return

        Returns:
            NewsResponse with list of NewsArticle objects
        """
        if not self._api_key:
            logger.warning("Cannot fetch Finnhub market news: API key not configured")
            return NewsResponse(articles=[], total_count=0)

        # TODO: Implement actual Finnhub API call
        # url = f"{self._base_url}/news"
        # params = {
        #     "category": category or "general",
        #     "token": self._api_key,
        # }
        # response = await httpx.get(url, params=params)
        # ...

        logger.info(f"FinnhubNewsProvider.get_market_news({category}) - STUB, not implemented")
        return NewsResponse(
            articles=[],
            total_count=0,
            last_updated=datetime.now(UTC),
        )

