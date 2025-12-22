"""Factory for creating broker instances."""

import logging
from functools import lru_cache

from app.core.config import settings
from app.providers.broker.base import Broker
from app.providers.broker.paper import PaperBroker

logger = logging.getLogger(__name__)


class BrokerFactory:
    """Factory for creating and managing broker instances.

    Supports runtime selection of brokers based on configuration.
    """

    # Registry of available brokers
    _brokers: dict[str, type[Broker]] = {
        "paper": PaperBroker,
        # "angelone": AngelOneBroker,  # TODO: Phase 2
        # "dhan": DhanBroker,  # TODO: Phase 3
    }

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
            name: Broker name (defaults to settings.BROKER_TYPE)

        Returns:
            Broker instance

        Raises:
            ValueError: If broker is not registered
        """
        broker_name = (name or settings.BROKER_TYPE).lower()

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
    def is_paper_trading(cls) -> bool:
        """Check if current broker is paper trading."""
        return settings.BROKER_TYPE.lower() == "paper"

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


@lru_cache
def get_broker() -> Broker:
    """Get the configured broker (cached singleton).

    Returns:
        Broker instance based on settings.BROKER_TYPE
    """
    return BrokerFactory.get_broker()
