"""Google News RSS feed provider implementation."""

import logging
import re
import urllib.parse
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from ..schemas import NewsArticle, NewsResponse
from .base import BaseNewsProvider
from .sentiment import KeywordSentimentAnalyzer

logger = logging.getLogger(__name__)

# Google News RSS feed URLs
GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss"
GOOGLE_NEWS_SEARCH = f"{GOOGLE_NEWS_RSS_BASE}/search"
GOOGLE_NEWS_TOPICS = f"{GOOGLE_NEWS_RSS_BASE}/topics"


class GoogleNewsRSSProvider(BaseNewsProvider):
    """News provider using Google News RSS feeds.

    Free, no API key required. Uses RSS feeds from news.google.com.
    Good as a fallback provider when Yahoo Finance news is unavailable.
    """

    name = "google_rss"

    def __init__(self, timeout: float = 10.0):
        """Initialize Google News RSS provider.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self._sentiment_analyzer = KeywordSentimentAnalyzer()
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    def analyze_sentiment(self, article: NewsArticle) -> NewsArticle:
        """Analyze sentiment using keyword-based analyzer."""
        return self._sentiment_analyzer.analyze(article)

    async def get_company_news(
        self,
        symbol: str,
        limit: int = 10,
    ) -> NewsResponse:
        """Get news articles for a specific company/stock.

        Searches Google News for the stock symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "MSFT")
            limit: Maximum number of articles to return

        Returns:
            NewsResponse with list of NewsArticle objects
        """
        try:
            # Search for stock symbol + "stock" to get relevant news
            query = urllib.parse.quote(f"{symbol} stock")
            url = f"{GOOGLE_NEWS_SEARCH}?q={query}&hl=en-US&gl=US&ceid=US:en"

            articles = await self._fetch_rss_feed(url, limit)

            # Add symbol to related symbols
            for article in articles:
                if symbol not in article.related_symbols:
                    article.related_symbols.append(symbol)
                article = self.analyze_sentiment(article)

            response = NewsResponse(
                symbol=symbol,
                articles=articles,
                last_updated=datetime.now(UTC),
            )
            return self.aggregate_sentiment(response)

        except Exception as e:
            logger.error(f"Error fetching Google News for {symbol}: {e}")
            return NewsResponse(symbol=symbol, articles=[], total_count=0)

    async def get_market_news(
        self,
        category: str | None = None,
        limit: int = 10,
    ) -> NewsResponse:
        """Get general market news from Google News Business section.

        Args:
            category: Not used for Google RSS (always fetches business news)
            limit: Maximum number of articles to return

        Returns:
            NewsResponse with list of NewsArticle objects
        """
        try:
            # Business/Finance topic
            url = f"{GOOGLE_NEWS_TOPICS}/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"

            articles = await self._fetch_rss_feed(url, limit)

            for article in articles:
                article = self.analyze_sentiment(article)

            response = NewsResponse(
                symbol=None,
                articles=articles,
                last_updated=datetime.now(UTC),
            )
            return self.aggregate_sentiment(response)

        except Exception as e:
            logger.error(f"Error fetching Google market news: {e}")
            return NewsResponse(articles=[], total_count=0)

    async def _fetch_rss_feed(self, url: str, limit: int) -> list[NewsArticle]:
        """Fetch and parse RSS feed.

        Args:
            url: RSS feed URL
            limit: Maximum number of articles

        Returns:
            List of NewsArticle objects
        """
        try:
            response = await self._client.get(url)
            response.raise_for_status()

            return self._parse_rss_xml(response.text, limit)

        except Exception as e:
            logger.warning(f"Error fetching RSS feed: {e}")
            return []

    def _parse_rss_xml(self, xml_content: str, limit: int) -> list[NewsArticle]:
        """Parse RSS XML content into NewsArticle objects.

        Uses regex for simple XML parsing (no external XML library needed).
        """
        articles = []

        # Extract items from RSS
        items = re.findall(r"<item>(.*?)</item>", xml_content, re.DOTALL)

        for item in items[:limit]:
            try:
                title_match = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
                link_match = re.search(r"<link>(.*?)</link>", item, re.DOTALL)
                pub_date_match = re.search(r"<pubDate>(.*?)</pubDate>", item, re.DOTALL)
                source_match = re.search(r"<source[^>]*>(.*?)</source>", item, re.DOTALL)

                if not title_match or not link_match:
                    continue

                # Parse title (remove CDATA wrapper if present)
                title = title_match.group(1).strip()
                title = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", title)

                # Parse link
                link = link_match.group(1).strip()

                # Parse publish date
                published_at = datetime.now(UTC)
                if pub_date_match:
                    try:
                        date_str = pub_date_match.group(1).strip()
                        published_at = parsedate_to_datetime(date_str)
                    except Exception:
                        pass

                # Parse source
                source = "Google News"
                if source_match:
                    source = source_match.group(1).strip()

                articles.append(
                    NewsArticle(
                        title=title,
                        url=link,
                        source=source,
                        published_at=published_at,
                        summary=None,  # RSS feeds don't usually have summaries
                        provider="google_rss",
                        related_symbols=[],
                    )
                )

            except Exception as e:
                logger.warning(f"Error parsing RSS item: {e}")
                continue

        return articles

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
