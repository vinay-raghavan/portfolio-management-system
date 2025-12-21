"""Factory for creating data provider instances."""

import logging
from functools import lru_cache
from typing import Type

from app.core.config import settings
from app.providers.data.base import DataProvider
from app.providers.data.yahoo import YahooDataProvider
from app.providers.symbols import Exchange

logger = logging.getLogger(__name__)


class DataProviderFactory:
    """Factory for creating and managing data provider instances.

    Supports runtime selection of data providers based on configuration.
    """

    # Registry of available providers
    _providers: dict[str, Type[DataProvider]] = {
        "yahoo": YahooDataProvider,
        # "nse": NSEDataProvider,  # TODO: Phase 1, Week 2
        # "angelone": AngelOneDataProvider,  # TODO: Phase 2
    }

    @classmethod
    def register(cls, name: str, provider_class: Type[DataProvider]) -> None:
        """Register a new data provider.

        Args:
            name: Provider identifier
            provider_class: Provider class implementing DataProvider interface
        """
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered data provider: {name}")

    @classmethod
    def get_provider(cls, name: str | None = None) -> DataProvider:
        """Get a data provider instance.

        Args:
            name: Provider name (defaults to settings.DATA_PROVIDER)

        Returns:
            DataProvider instance

        Raises:
            ValueError: If provider is not registered
        """
        provider_name = (name or settings.DATA_PROVIDER).lower()

        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown data provider: {provider_name}. Available: {available}"
            )

        provider_class = cls._providers[provider_name]

        # Configure based on settings
        if provider_name == "yahoo":
            default_exchange = Exchange.NSE if settings.DEFAULT_MARKET == "IN" else Exchange.NYSE
            return provider_class(default_exchange=default_exchange)

        return provider_class()

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())


@lru_cache
def get_data_provider() -> DataProvider:
    """Get the configured data provider (cached singleton).

    Returns:
        DataProvider instance based on settings.DATA_PROVIDER
    """
    return DataProviderFactory.get_provider()

