"""Abstract base class for news providers."""

from abc import ABC, abstractmethod

from ..schemas import NewsArticle, NewsResponse, SentimentScore


class BaseNewsProvider(ABC):
    """Abstract base class for news providers.

    All news providers (Yahoo, Google RSS, Finnhub, etc.) must implement this interface.
    This allows switching between news sources without changing business logic.
    """

    name: str = "base"

    @abstractmethod
    async def get_company_news(
        self,
        symbol: str,
        limit: int = 10,
    ) -> NewsResponse:
        """Get news articles for a specific company/stock.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "MSFT")
            limit: Maximum number of articles to return

        Returns:
            NewsResponse with list of NewsArticle objects
        """
        pass

    @abstractmethod
    async def get_market_news(
        self,
        category: str | None = None,
        limit: int = 10,
    ) -> NewsResponse:
        """Get general market news.

        Args:
            category: Optional category filter (e.g., "technology", "finance")
            limit: Maximum number of articles to return

        Returns:
            NewsResponse with list of NewsArticle objects
        """
        pass

    async def search_news(
        self,
        query: str,
        limit: int = 10,
    ) -> NewsResponse:
        """Search news articles by query string.

        Default implementation returns empty response (optional to implement).

        Args:
            query: Search query string
            limit: Maximum number of articles to return

        Returns:
            NewsResponse with matching articles
        """
        return NewsResponse(articles=[], total_count=0)

    def analyze_sentiment(self, article: NewsArticle) -> NewsArticle:
        """Analyze and update sentiment for a news article.

        Default implementation returns neutral sentiment.
        Override in subclass for actual sentiment analysis.

        Args:
            article: NewsArticle to analyze

        Returns:
            Same NewsArticle with updated sentiment fields
        """
        article.sentiment = SentimentScore.NEUTRAL
        article.sentiment_score = 0.0
        return article

    def aggregate_sentiment(self, response: NewsResponse) -> NewsResponse:
        """Calculate aggregate sentiment statistics for a news response.

        Args:
            response: NewsResponse with articles

        Returns:
            Same NewsResponse with updated aggregate sentiment fields
        """
        if not response.articles:
            return response

        total_score = 0.0
        positive = 0
        negative = 0
        neutral = 0

        for article in response.articles:
            total_score += article.sentiment_score
            if article.sentiment == SentimentScore.POSITIVE:
                positive += 1
            elif article.sentiment == SentimentScore.NEGATIVE:
                negative += 1
            else:
                neutral += 1

        response.average_sentiment = total_score / len(response.articles)
        response.positive_count = positive
        response.negative_count = negative
        response.neutral_count = neutral
        response.total_count = len(response.articles)

        return response

    async def health_check(self) -> bool:
        """Check if the news provider is healthy and accessible.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            response = await self.get_market_news(limit=1)
            return len(response.articles) > 0
        except Exception:
            return False
