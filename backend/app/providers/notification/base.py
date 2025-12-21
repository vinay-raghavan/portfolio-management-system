"""Abstract base class for notification providers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"  # Daily summaries, reports
    MEDIUM = "medium"  # Order fills, signals
    HIGH = "high"  # Risk alerts, price alerts
    CRITICAL = "critical"  # Kill switch, margin call


class NotificationType(str, Enum):
    """Types of notifications."""

    # Trading
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"

    # Alerts
    PRICE_ALERT = "price_alert"

    # Algo
    SIGNAL_GENERATED = "signal_generated"
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"
    STRATEGY_ERROR = "strategy_error"

    # Risk
    RISK_LIMIT_WARNING = "risk_limit_warning"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    MARGIN_WARNING = "margin_warning"
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"

    # Reports
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_REPORT = "weekly_report"

    # System
    SYSTEM_ALERT = "system_alert"
    MAINTENANCE = "maintenance"


class NotificationProvider(ABC):
    """Abstract base class for notification providers.

    All notification providers (Email, WhatsApp, WebSocket, etc.) must
    implement this interface.
    """

    name: str = "base"
    supports_rich_content: bool = False  # HTML, images, etc.

    @abstractmethod
    async def send(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send a notification to a user.

        Args:
            user_id: User identifier
            title: Notification title
            message: Notification message body
            priority: Notification priority level
            notification_type: Type of notification
            data: Additional structured data

        Returns:
            True if notification was sent successfully
        """
        pass

    @abstractmethod
    async def send_bulk(
        self,
        user_ids: list[str],
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
    ) -> dict[str, bool]:
        """Send notification to multiple users.

        Args:
            user_ids: List of user identifiers
            title: Notification title
            message: Notification message body
            priority: Notification priority level
            notification_type: Type of notification

        Returns:
            Dict mapping user_id to success status
        """
        pass

    @abstractmethod
    async def is_available(self, user_id: str) -> bool:
        """Check if this channel is configured for a user.

        Args:
            user_id: User identifier

        Returns:
            True if channel is available for user
        """
        pass

    async def get_user_preference(self, user_id: str) -> dict[str, Any]:
        """Get user's notification preferences for this channel.

        Args:
            user_id: User identifier

        Returns:
            User's preferences for this channel
        """
        return {}

    def format_message(
        self,
        template: str,
        **kwargs: Any,
    ) -> str:
        """Format a message template with variables.

        Args:
            template: Message template with {variable} placeholders
            **kwargs: Variables to substitute

        Returns:
            Formatted message string
        """
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

