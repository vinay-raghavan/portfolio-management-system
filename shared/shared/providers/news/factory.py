"""Factory for creating news provider instances."""

import logging
from typing import Callable

from .base import BaseNewsProvider

logger = logging.getLogger(__name__)

# Default provider name
_default_provider = "yahoo"

# Optional config getter for reading provider from settings
_config_getter: Callable[[], str] | None = None


class NewsProviderFactory:
    """Factory for creating news provider instances.

    Supports registration of custom providers and fallback chains.
    """

    _providers: dict[str, type[BaseNewsProvider]] = {}
    _instances: dict[str, BaseNewsProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[BaseNewsProvider]) -> None:
        """Register a news provider class.

        Args:
            name: Provider name (e.g., "yahoo", "google_rss", "finnhub")
            provider_class: Provider class to register
        """
        cls._providers[name] = provider_class
        logger.debug(f"Registered news provider: {name}")

    @classmethod
    def get(cls, name: str | None = None) -> BaseNewsProvider:
        """Get a news provider instance.

        Args:
            name: Provider name, or None for default

        Returns:
            News provider instance

        Raises:
            ValueError: If provider not found
        """
        if name is None:
            # Try config getter first, then use default
            if _config_getter:
                try:
                    name = _config_getter()
                except Exception:
                    name = _default_provider
            else:
                name = _default_provider

        # Return cached instance if available
        if name in cls._instances:
            return cls._instances[name]

        # Create new instance
        if name not in cls._providers:
            available = list(cls._providers.keys())
            raise ValueError(f"Unknown news provider: {name}. Available: {available}")

        provider = cls._providers[name]()
        cls._instances[name] = provider
        logger.info(f"Created news provider instance: {name}")
        return provider

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached provider instances."""
        cls._instances.clear()


def get_news_provider(name: str | None = None) -> BaseNewsProvider:
    """Get a news provider instance.

    Convenience function wrapping NewsProviderFactory.get().

    Args:
        name: Provider name, or None for default

    Returns:
        News provider instance
    """
    return NewsProviderFactory.get(name)


def set_default_news_provider(name: str) -> None:
    """Set the default news provider.

    Args:
        name: Provider name to use as default
    """
    global _default_provider
    _default_provider = name
    logger.info(f"Default news provider set to: {name}")


def set_config_getter(getter: Callable[[], str]) -> None:
    """Set a function to get the news provider name from config.

    Args:
        getter: Function that returns the provider name
    """
    global _config_getter
    _config_getter = getter

