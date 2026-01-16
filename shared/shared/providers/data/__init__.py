"""Data providers for market data.

This module provides a unified interface for fetching market data from
various sources (Yahoo Finance, NSE, Fyers, etc.).

Usage:
    from shared.providers.data import get_data_provider, DataProviderFactory

    # Get the default provider (based on configuration)
    provider = get_data_provider()

    # Get a specific provider
    yahoo = get_data_provider("yahoo")
    nse = get_data_provider("nse")
    fyers = get_data_provider("fyers")

    # Use the provider
    quote = await provider.get_quote("RELIANCE")
    history = await provider.get_historical("RELIANCE", period="1mo")
"""

from .base import DataProvider
from .factory import (
    DataProviderFactory,
    check_data_provider_health,
    get_data_provider,
    set_config_getter,
    set_default_market,
    set_default_provider,
    set_market_getter,
)
from .fyers import FyersDataProvider
from .nse import NSEDataProvider
from .rate_limiter import RateLimiter, nse_rate_limiter, yahoo_rate_limiter
from .yahoo import YahooDataProvider

# Register providers
DataProviderFactory.register("yahoo", YahooDataProvider)
DataProviderFactory.register("nse", NSEDataProvider)
DataProviderFactory.register("fyers", FyersDataProvider)

__all__ = [
    # Base classes
    "DataProvider",
    # Factory
    "DataProviderFactory",
    "check_data_provider_health",
    "get_data_provider",
    "set_config_getter",
    "set_default_market",
    "set_default_provider",
    "set_market_getter",
    # Providers
    "FyersDataProvider",
    "NSEDataProvider",
    "YahooDataProvider",
    # Rate limiting
    "RateLimiter",
    "nse_rate_limiter",
    "yahoo_rate_limiter",
]
