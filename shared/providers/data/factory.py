"""Factory for creating data provider instances."""

import logging
from collections.abc import Callable
from functools import lru_cache

from ..symbols import Exchange
from .base import DataProvider

logger = logging.getLogger(__name__)


# Configuration function types
ConfigGetter = Callable[[], str]
MarketGetter = Callable[[], str]

# Default configuration
_default_provider: str = "yahoo"
_default_market: str = "IN"
_config_getter: ConfigGetter | None = None
_market_getter: MarketGetter | None = None


def set_default_provider(provider: str) -> None:
    """Set the default data provider.

    Args:
        provider: Default provider name (e.g., "yahoo", "nse")
    """
    global _default_provider
    _default_provider = provider.lower()


def set_default_market(market: str) -> None:
    """Set the default market.

    Args:
        market: Default market code (e.g., "IN", "US")
    """
    global _default_market
    _default_market = market.upper()


def set_config_getter(getter: ConfigGetter) -> None:
    """Set a config getter function for retrieving provider name.

    Args:
        getter: Function that returns the provider name string
    """
    global _config_getter
    _config_getter = getter


def set_market_getter(getter: MarketGetter) -> None:
    """Set a market getter function for retrieving default market.

    Args:
        getter: Function that returns the market code string
    """
    global _market_getter
    _market_getter = getter


def _get_provider_name() -> str:
    """Get the current provider name from config or default."""
    if _config_getter is not None:
        try:
            return _config_getter().lower()
        except Exception:
            pass
    return _default_provider


def _get_default_market() -> str:
    """Get the default market from config or default."""
    if _market_getter is not None:
        try:
            return _market_getter().upper()
        except Exception:
            pass
    return _default_market


class DataProviderFactory:
    """Factory for creating and managing data provider instances.

    Supports runtime selection of data providers based on configuration.
    """

    # Registry of available providers
    _providers: dict[str, type[DataProvider]] = {}

    # Singleton instances
    _instances: dict[str, DataProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[DataProvider]) -> None:
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
            name: Provider name (defaults to configured provider)

        Returns:
            DataProvider instance

        Raises:
            ValueError: If provider is not registered
        """
        provider_name = (name or _get_provider_name()).lower()

        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unknown data provider: {provider_name}. Available: {available}")

        # Return existing instance if available
        if provider_name in cls._instances:
            return cls._instances[provider_name]

        # Create new instance with appropriate configuration
        provider_class = cls._providers[provider_name]
        instance = cls._create_instance(provider_name, provider_class)
        cls._instances[provider_name] = instance

        return instance

    @classmethod
    def _create_instance(cls, name: str, provider_class: type[DataProvider]) -> DataProvider:
        """Create a provider instance with appropriate configuration."""
        if name == "yahoo":
            default_market = _get_default_market()
            default_exchange = Exchange.NSE if default_market == "IN" else Exchange.NYSE
            return provider_class(default_exchange=default_exchange)
        return provider_class()

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all provider instances (for testing)."""
        cls._instances.clear()


@lru_cache
def get_data_provider(name: str | None = None) -> DataProvider:
    """Get a data provider instance (cached singleton).

    Args:
        name: Provider name (defaults to configured provider)

    Returns:
        DataProvider instance
    """
    return DataProviderFactory.get_provider(name)
