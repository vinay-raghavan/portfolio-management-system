"""Data provider abstraction layer.

This module re-exports from the shared package for backward compatibility.
"""

from shared.providers.data import (
    DataProvider,
    DataProviderFactory,
    NSEDataProvider,
    YahooDataProvider,
    get_data_provider,
)

__all__ = [
    "DataProvider",
    "YahooDataProvider",
    "NSEDataProvider",
    "DataProviderFactory",
    "get_data_provider",
]
