"""Data providers package.

This module re-exports from the shared package for backward compatibility.
"""

from shared.providers.data import (
    DataProvider,
    DataProviderFactory,
    NSEDataProvider,
    YahooDataProvider,
    check_data_provider_health,
    get_data_provider,
)

__all__ = [
    "DataProvider",
    "DataProviderFactory",
    "check_data_provider_health",
    "get_data_provider",
    "YahooDataProvider",
    "NSEDataProvider",
]
