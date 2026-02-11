"""Yahoo Finance news provider implementation."""

import logging
from datetime import UTC, datetime

import yfinance as yf

from ..schemas import NewsArticle, NewsResponse, SentimentScore
from .base import BaseNewsProvider

logger = logging.getLogger(__name__)


class YahooNewsProvider(BaseNewsProvider):
    """News provider using Yahoo Finance (yfinance).

    Uses yfinance's built-in news functionality to fetch company
    and market news. This is free but unofficial and may be rate-limited.
    """

    name = "yahoo"

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
            for item in news_list[:limit]:
                article = self._parse_yahoo_news_item(item, symbol)
                if article:
                    # Apply sentiment analysis
                    article = self.analyze_sentiment(article)
                    articles.append(article)

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
        """Get general market news.

        Uses major index tickers to aggregate market-wide news.

        Args:
            category: Optional category filter (not used for Yahoo)
            limit: Maximum number of articles to return

        Returns:
            NewsResponse with list of NewsArticle objects
        """
        try:
            # Use major indices to get market news
            tickers = ["^GSPC", "^DJI", "^IXIC"]  # S&P 500, Dow Jones, NASDAQ
            seen_urls: set[str] = set()
            articles = []

            for ticker_symbol in tickers:
                if len(articles) >= limit:
                    break

                ticker = yf.Ticker(ticker_symbol)
                news_list = ticker.news or []

                for item in news_list:
                    if len(articles) >= limit:
                        break

                    # Skip duplicates by URL
                    url = item.get("link", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    article = self._parse_yahoo_news_item(item)
                    if article:
                        article = self.analyze_sentiment(article)
                        articles.append(article)

            response = NewsResponse(
                symbol=None,
                articles=articles,
                last_updated=datetime.now(UTC),
            )
            return self.aggregate_sentiment(response)

        except Exception as e:
            logger.error(f"Error fetching market news: {e}")
            return NewsResponse(articles=[], total_count=0)

    def _parse_yahoo_news_item(
        self,
        item: dict,
        symbol: str | None = None,
    ) -> NewsArticle | None:
        """Parse a Yahoo Finance news item into NewsArticle.

        Args:
            item: Raw news item from yfinance
            symbol: Optional symbol to add to related_symbols

        Returns:
            NewsArticle or None if parsing fails
        """
        try:
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
        except Exception as e:
            logger.warning(f"Error parsing Yahoo news item: {e}")
            return None

