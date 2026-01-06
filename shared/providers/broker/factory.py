"""Factory for creating broker instances."""

import logging
from functools import lru_cache
from typing import Callable

from .base import Broker

logger = logging.getLogger(__name__)


# Configuration function type - allows services to provide their own config
ConfigGetter = Callable[[], str]

# Default broker type
_default_broker_type: str = "paper"
_config_getter: ConfigGetter | None = None


def set_default_broker_type(broker_type: str) -> None:
    """Set the default broker type.

    Args:
        broker_type: Default broker type to use
    """
    global _default_broker_type
    _default_broker_type = broker_type.lower()


def set_config_getter(getter: ConfigGetter) -> None:
    """Set a config getter function for retrieving broker type.

    This allows services to provide their own configuration without
    the shared package depending on service-specific config modules.

    Args:
        getter: Function that returns the broker type string
    """
    global _config_getter
    _config_getter = getter


def _get_broker_type() -> str:
    """Get the current broker type from config or default."""
    if _config_getter is not None:
        try:
            return _config_getter().lower()
        except Exception:
            pass
    return _default_broker_type


class BrokerFactory:
    """Factory for creating and managing broker instances.

    Supports runtime selection of brokers based on configuration.
    """

    # Registry of available brokers
    _brokers: dict[str, type[Broker]] = {}

    # Singleton instances
    _instances: dict[str, Broker] = {}

    @classmethod
    def register(cls, name: str, broker_class: type[Broker]) -> None:
        """Register a new broker.

        Args:
            name: Broker identifier
            broker_class: Broker class implementing Broker interface
        """
        cls._brokers[name.lower()] = broker_class
        logger.info(f"Registered broker: {name}")

    @classmethod
    def get_broker(cls, name: str | None = None) -> Broker:
        """Get a broker instance.

        Args:
            name: Broker name (defaults to configured broker type)

        Returns:
            Broker instance

        Raises:
            ValueError: If broker is not registered
        """
        broker_name = (name or _get_broker_type()).lower()

        if broker_name not in cls._brokers:
            available = ", ".join(cls._brokers.keys())
            raise ValueError(f"Unknown broker: {broker_name}. Available: {available}")

        # Return existing instance if available
        if broker_name in cls._instances:
            return cls._instances[broker_name]

        # Create new instance
        broker_class = cls._brokers[broker_name]
        instance = broker_class()
        cls._instances[broker_name] = instance

        return instance

    @classmethod
    def list_brokers(cls) -> list[str]:
        """List all registered broker names."""
        return list(cls._brokers.keys())

    @classmethod
    def is_paper_trading(cls, name: str | None = None) -> bool:
        """Check if current broker is paper trading."""
        broker_name = name or _get_broker_type()
        return broker_name.lower() == "paper"

    @classmethod
    async def connect_all(cls) -> None:
        """Connect all instantiated brokers."""
        for name, broker in cls._instances.items():
            if not await broker.is_connected():
                logger.info(f"Connecting broker: {name}")
                await broker.connect()

    @classmethod
    async def disconnect_all(cls) -> None:
        """Disconnect all instantiated brokers."""
        for name, broker in cls._instances.items():
            if await broker.is_connected():
                logger.info(f"Disconnecting broker: {name}")
                await broker.disconnect()

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all broker instances (for testing)."""
        cls._instances.clear()


@lru_cache
def get_broker(name: str | None = None) -> Broker:
    """Get a broker instance (cached singleton).

    Args:
        name: Broker name (defaults to configured broker type)

    Returns:
        Broker instance
    """
    return BrokerFactory.get_broker(name)


# Register default brokers when module loads
def _register_default_brokers() -> None:
    """Register default broker implementations."""
    from .paper import PaperBroker

    BrokerFactory.register("paper", PaperBroker)


_register_default_brokers()

