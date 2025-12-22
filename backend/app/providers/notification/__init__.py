"""Notification provider abstraction layer."""

from app.providers.notification.base import (
    NotificationPriority,
    NotificationProvider,
    NotificationType,
)
from app.providers.notification.console import ConsoleNotificationProvider
from app.providers.notification.factory import NotificationProviderFactory

__all__ = [
    "NotificationProvider",
    "NotificationPriority",
    "NotificationType",
    "NotificationProviderFactory",
    "ConsoleNotificationProvider",
]
