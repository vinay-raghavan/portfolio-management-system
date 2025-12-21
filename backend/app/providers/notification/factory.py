"""Factory for creating notification provider instances."""

import logging
from typing import Type

from app.providers.notification.base import NotificationProvider

logger = logging.getLogger(__name__)


class NotificationProviderFactory:
    """Factory for creating and managing notification provider instances.

    Supports multiple notification channels that can be enabled/disabled
    per user or globally.
    """

    # Registry of available providers
    _providers: dict[str, Type[NotificationProvider]] = {
        # "email": EmailNotificationProvider,  # TODO: Phase 1, Week 4-5
        # "whatsapp": WhatsAppNotificationProvider,  # TODO: Phase 1, Week 4-5
        # "websocket": WebSocketNotificationProvider,  # TODO: Phase 1, Week 4-5
        # "sms": SMSNotificationProvider,  # TODO: Future
        # "push": PushNotificationProvider,  # TODO: Future
    }

    # Singleton instances
    _instances: dict[str, NotificationProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[NotificationProvider]) -> None:
        """Register a new notification provider.

        Args:
            name: Provider identifier
            provider_class: Provider class implementing NotificationProvider interface
        """
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered notification provider: {name}")

    @classmethod
    def get_provider(cls, name: str) -> NotificationProvider:
        """Get a notification provider instance.

        Args:
            name: Provider name

        Returns:
            NotificationProvider instance

        Raises:
            ValueError: If provider is not registered
        """
        provider_name = name.lower()

        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys()) or "none"
            raise ValueError(
                f"Unknown notification provider: {provider_name}. Available: {available}"
            )

        # Return existing instance if available
        if provider_name in cls._instances:
            return cls._instances[provider_name]

        # Create new instance
        provider_class = cls._providers[provider_name]
        instance = provider_class()
        cls._instances[provider_name] = instance

        return instance

    @classmethod
    def get_all_providers(cls) -> list[NotificationProvider]:
        """Get all registered provider instances.

        Returns:
            List of all provider instances
        """
        providers = []
        for name in cls._providers:
            providers.append(cls.get_provider(name))
        return providers

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())

