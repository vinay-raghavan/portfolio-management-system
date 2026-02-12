"""Yahoo Finance news provider implementation."""

import logging
from datetime import UTC, datetime

import yfinance as yf

from ..schemas import NewsArticle, NewsResponse
from .base import BaseNewsProvider
from .sentiment import KeywordSentimentAnalyzer

logger = logging.getLogger(__name__)


class YahooNewsProvider(BaseNewsProvider):
    """News provider using Yahoo Finance (yfinance).

    Uses yfinance's built-in news functionality to fetch company
    and market news. This is free but unofficial and may be rate-limited.
    """

    name = "yahoo"

    def __init__(self):
        """Initialize Yahoo news provider with sentiment analyzer."""
        self._sentiment_analyzer = KeywordSentimentAnalyzer()

    def analyze_sentiment(self, article: NewsArticle) -> NewsArticle:
        """Analyze sentiment using keyword-based analyzer.

        Overrides base class to use KeywordSentimentAnalyzer.

        Args:
            article: NewsArticle to analyze

        Returns:
            Same NewsArticle with updated sentiment fields
        """
        return self._sentiment_analyzer.analyze(article)

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
        try:
            ticker = yf.Ticker(symbol)
            news_list = ticker.news or []

            articles = []
            for item in news_list:
                article = self._parse_yahoo_news_item(item, symbol)
                if article:
                    # Apply sentiment analysis
                    article = self.analyze_sentiment(article)
                    articles.append(article)

            # Sort articles by published date (newest first)
            articles.sort(
                key=lambda a: a.published_at
                if a.published_at
                else datetime.min.replace(tzinfo=UTC),
                reverse=True,
            )

            # Take only the top `limit` newest articles
            articles = articles[:limit]

            response = NewsResponse(
                symbol=symbol,
                articles=articles,
                last_updated=datetime.now(UTC),
            )
            return self.aggregate_sentiment(response)

        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
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
        """Get general market news for Indian markets.

        Uses Indian index tickers and major stocks to aggregate market-wide news.

        Args:
            category: Optional category filter (not used for Yahoo)
            limit: Maximum number of articles to return

        Returns:
            NewsResponse with list of NewsArticle objects
        """
        try:
            # Use Indian indices and major stocks for Indian market news
            # ^NSEI = Nifty 50, ^NSEBANK = Bank Nifty
            # Major Indian stocks with .NS suffix for NSE
            tickers = [
                "^NSEI",  # Nifty 50 Index
                "^NSEBANK",  # Bank Nifty Index
                "RELIANCE.NS",  # Reliance Industries
                "TCS.NS",  # TCS
                "HDFCBANK.NS",  # HDFC Bank
                "INFY.NS",  # Infosys
                "ICICIBANK.NS",  # ICICI Bank
                "HINDUNILVR.NS",  # Hindustan Unilever
                "SBIN.NS",  # State Bank of India
                "BHARTIARTL.NS",  # Bharti Airtel
            ]
            seen_urls: set[str] = set()
            articles = []
            # Collect more articles than needed so we can sort and pick newest
            max_articles_to_collect = limit * 5  # Collect 5x to have good selection

            for ticker_symbol in tickers:
                if len(articles) >= max_articles_to_collect:
                    break

                try:
                    ticker = yf.Ticker(ticker_symbol)
                    news_list = ticker.news or []

                    for item in news_list:
                        if len(articles) >= max_articles_to_collect:
                            break

                        # Extract URL for deduplication (handle both old and new formats)
                        url = self._extract_url_for_dedup(item)
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)

                        article = self._parse_yahoo_news_item(item)
                        if article:
                            article = self.analyze_sentiment(article)
                            articles.append(article)
                except Exception as e:
                    logger.debug(f"Error fetching news for {ticker_symbol}: {e}")
                    continue

            # Sort articles by published date (newest first)
            articles.sort(
                key=lambda a: a.published_at
                if a.published_at
                else datetime.min.replace(tzinfo=UTC),
                reverse=True,
            )

            # Take only the top `limit` newest articles
            articles = articles[:limit]

            response = NewsResponse(
                symbol=None,
                articles=articles,
                last_updated=datetime.now(UTC),
            )
            return self.aggregate_sentiment(response)

        except Exception as e:
            logger.error(f"Error fetching market news: {e}")
            return NewsResponse(articles=[], total_count=0)

    def _extract_url_for_dedup(self, item: dict) -> str:
        """Extract URL from news item for deduplication.

        Handles both old format (link key) and new format (nested content).

        Args:
            item: Raw news item from yfinance

        Returns:
            URL string or unique identifier for deduplication
        """
        # Old format: direct link key
        if "link" in item:
            return item.get("link", "")

        # New format: nested in content
        if "content" in item and isinstance(item.get("content"), dict):
            content = item["content"]
            # Try canonicalUrl first, then clickThroughUrl
            if canonical := content.get("canonicalUrl"):
                return canonical.get("url", "")
            if click_through := content.get("clickThroughUrl"):
                return click_through.get("url", "")
            # Fallback to article ID
            if article_id := content.get("id"):
                return f"id:{article_id}"

        # Fallback: use title as unique identifier
        title = item.get("title", "") or item.get("content", {}).get("title", "")
        return f"title:{title}"

    def _parse_yahoo_news_item(
        self,
        item: dict,
        symbol: str | None = None,
    ) -> NewsArticle | None:
        """Parse a Yahoo Finance news item into NewsArticle.

        Handles both old format (flat structure) and new format (nested content).

        Args:
            item: Raw news item from yfinance
            symbol: Optional symbol to add to related_symbols

        Returns:
            NewsArticle or None if parsing fails
        """
        try:
            # Check if new format (has 'content' key with nested data)
            if "content" in item and isinstance(item.get("content"), dict):
                return self._parse_new_format(item, symbol)
            else:
                return self._parse_old_format(item, symbol)
        except Exception as e:
            logger.warning(f"Error parsing Yahoo news item: {e}")
            return None

    def _parse_old_format(
        self,
        item: dict,
        symbol: str | None = None,
    ) -> NewsArticle | None:
        """Parse old Yahoo Finance news format (flat structure)."""
        # Extract publish time
        pub_time = item.get("providerPublishTime", 0)
        published_at = datetime.fromtimestamp(pub_time, tz=UTC)

        # Extract related symbols
        related = []
        if symbol:
            related.append(symbol)
        related_tickers = item.get("relatedTickers", [])
        related.extend(related_tickers)

        return NewsArticle(
            title=item.get("title", ""),
            url=item.get("link", ""),
            source=item.get("publisher", "Yahoo Finance"),
            published_at=published_at,
            summary=item.get("summary"),
            thumbnail_url=item.get("thumbnail", {}).get("resolutions", [{}])[0].get("url"),
            related_symbols=list(set(related)),  # Deduplicate
            provider="yahoo",
            article_id=item.get("uuid"),
        )

    def _parse_new_format(
        self,
        item: dict,
        symbol: str | None = None,
    ) -> NewsArticle | None:
        """Parse new Yahoo Finance news format (nested content structure)."""
        content = item.get("content", {})

        # Extract publish time from ISO date string
        pub_date_str = content.get("pubDate", "")
        if pub_date_str:
            # Parse ISO format: "2026-02-11T21:06:23Z"
            published_at = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
        else:
            published_at = datetime.now(UTC)

        # Extract URL from canonicalUrl or clickThroughUrl
        url = ""
        if canonical := content.get("canonicalUrl"):
            url = canonical.get("url", "")
        elif click_through := content.get("clickThroughUrl"):
            url = click_through.get("url", "")

        # Extract source from provider
        source = "Yahoo Finance"
        if provider := content.get("provider"):
            source = provider.get("displayName", source)

        # Extract thumbnail
        thumbnail_url = None
        if thumbnail := content.get("thumbnail"):
            resolutions = thumbnail.get("resolutions", [])
            if resolutions:
                thumbnail_url = resolutions[0].get("url")

        # Extract related symbols
        related = []
        if symbol:
            related.append(symbol)

        return NewsArticle(
            title=content.get("title", ""),
            url=url,
            source=source,
            published_at=published_at,
            summary=content.get("summary"),
            thumbnail_url=thumbnail_url,
            related_symbols=list(set(related)),
            provider="yahoo",
            article_id=content.get("id"),
        )
