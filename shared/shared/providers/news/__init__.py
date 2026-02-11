"""News providers for market news and sentiment analysis.

This module provides a unified interface for fetching market news from
various sources (Yahoo Finance, Google News RSS, Finnhub, etc.).

Usage:
    from shared.providers.news import get_news_provider, NewsProviderFactory

    # Get the default provider (based on configuration)
    provider = get_news_provider()

    # Get a specific provider
    yahoo = get_news_provider("yahoo")
    google = get_news_provider("google_rss")

    # Use the provider
    news = await provider.get_company_news("AAPL")
    market_news = await provider.get_market_news()
"""

from .base import BaseNewsProvider
from .factory import NewsProviderFactory, get_news_provider, set_default_news_provider

__all__ = [
    # Base classes
    "BaseNewsProvider",
    # Factory
    "NewsProviderFactory",
    "get_news_provider",
    "set_default_news_provider",
]

