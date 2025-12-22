"""Console notification provider for development and testing."""

import logging
from typing import Any

from app.providers.notification.base import (
    NotificationPriority,
    NotificationProvider,
    NotificationType,
)

logger = logging.getLogger(__name__)


class ConsoleNotificationProvider(NotificationProvider):
    """Console notification provider that logs notifications.

    Useful for development and testing. In production, this can be
    replaced with email, SMS, or push notification providers.
    """

    name = "console"
    supports_rich_content = False

    async def send(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Log notification to console."""
        priority_emoji = {
            NotificationPriority.LOW: "📝",
            NotificationPriority.MEDIUM: "📢",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.CRITICAL: "🚨",
        }

        emoji = priority_emoji.get(priority, "📢")
        log_level = (
            logging.WARNING
            if priority in (NotificationPriority.HIGH, NotificationPriority.CRITICAL)
            else logging.INFO
        )

        logger.log(
            log_level,
            f"{emoji} NOTIFICATION [{priority.value.upper()}] [{notification_type.value}] "
            f"User: {user_id} | {title}: {message}",
        )

        if data:
            logger.debug(f"Notification data: {data}")

        return True

    async def send_bulk(
        self,
        user_ids: list[str],
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
    ) -> dict[str, bool]:
        """Send notification to multiple users."""
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.send(user_id, title, message, priority, notification_type)
        return results

    async def is_available(self, user_id: str) -> bool:
        """Console is always available."""
        return True
