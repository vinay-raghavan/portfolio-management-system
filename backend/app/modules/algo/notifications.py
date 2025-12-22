"""Notification service for algo trading events."""

import logging
from decimal import Decimal

from app.providers.notification import (
    NotificationPriority,
    NotificationProviderFactory,
    NotificationType,
)

logger = logging.getLogger(__name__)


class AlgoNotificationService:
    """Service for sending algo trading notifications.

    Handles notifications for:
    - Strategy started/stopped
    - Order execution
    - Risk limit breaches
    - Kill switch activation
    - Circuit breaker triggers
    """

    def __init__(self):
        """Initialize with console provider (can be extended)."""
        try:
            self._provider = NotificationProviderFactory.get_provider("console")
        except ValueError:
            logger.warning("Console notification provider not available")
            self._provider = None

    async def notify_strategy_started(
        self,
        user_id: str,
        strategy_name: str,
        strategy_id: str,
    ) -> bool:
        """Notify when a strategy execution starts."""
        if not self._provider:
            return False

        return await self._provider.send(
            user_id=user_id,
            title=f"Strategy Started: {strategy_name}",
            message=f"Algo strategy '{strategy_name}' has started execution.",
            priority=NotificationPriority.LOW,
            notification_type=NotificationType.STRATEGY_STARTED,
            data={"strategy_id": strategy_id, "strategy_name": strategy_name},
        )

    async def notify_strategy_stopped(
        self,
        user_id: str,
        strategy_name: str,
        strategy_id: str,
        reason: str | None = None,
    ) -> bool:
        """Notify when a strategy is stopped."""
        if not self._provider:
            return False

        message = f"Algo strategy '{strategy_name}' has been stopped."
        if reason:
            message += f" Reason: {reason}"

        return await self._provider.send(
            user_id=user_id,
            title=f"Strategy Stopped: {strategy_name}",
            message=message,
            priority=NotificationPriority.MEDIUM,
            notification_type=NotificationType.STRATEGY_STOPPED,
            data={"strategy_id": strategy_id, "strategy_name": strategy_name, "reason": reason},
        )

    async def notify_strategy_error(
        self,
        user_id: str,
        strategy_name: str,
        strategy_id: str,
        error: str,
    ) -> bool:
        """Notify when a strategy encounters an error."""
        if not self._provider:
            return False

        return await self._provider.send(
            user_id=user_id,
            title=f"Strategy Error: {strategy_name}",
            message=f"Algo strategy '{strategy_name}' encountered an error: {error}",
            priority=NotificationPriority.HIGH,
            notification_type=NotificationType.STRATEGY_ERROR,
            data={"strategy_id": strategy_id, "strategy_name": strategy_name, "error": error},
        )

    async def notify_order_placed(
        self,
        user_id: str,
        strategy_name: str,
        symbol: str,
        side: str,
        quantity: int,
        price: Decimal | None = None,
    ) -> bool:
        """Notify when an algo order is placed."""
        if not self._provider:
            return False

        price_str = f" at ₹{price:,.2f}" if price else ""
        return await self._provider.send(
            user_id=user_id,
            title=f"Algo Order: {side} {symbol}",
            message=f"Strategy '{strategy_name}' placed {side} order for {quantity} {symbol}{price_str}",
            priority=NotificationPriority.MEDIUM,
            notification_type=NotificationType.ORDER_PLACED,
            data={
                "strategy_name": strategy_name,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": str(price) if price else None,
            },
        )

    async def notify_circuit_breaker_triggered(
        self,
        user_id: str,
        strategy_name: str,
        strategy_id: str,
        reason: str,
    ) -> bool:
        """Notify when circuit breaker is triggered."""
        if not self._provider:
            return False

        return await self._provider.send(
            user_id=user_id,
            title=f"Circuit Breaker Triggered: {strategy_name}",
            message=f"Strategy '{strategy_name}' has been paused due to: {reason}",
            priority=NotificationPriority.HIGH,
            notification_type=NotificationType.RISK_LIMIT_BREACH,
            data={"strategy_id": strategy_id, "strategy_name": strategy_name, "reason": reason},
        )

    async def notify_kill_switch_activated(
        self,
        user_id: str,
        reason: str | None = None,
        strategies_disabled: int = 0,
    ) -> bool:
        """Notify when kill switch is activated."""
        if not self._provider:
            return False

        message = "Emergency kill switch has been activated. All algo trading is disabled."
        if reason:
            message += f" Reason: {reason}"
        if strategies_disabled > 0:
            message += f" {strategies_disabled} strategies were disabled."

        return await self._provider.send(
            user_id=user_id,
            title="🚨 KILL SWITCH ACTIVATED",
            message=message,
            priority=NotificationPriority.CRITICAL,
            notification_type=NotificationType.KILL_SWITCH_TRIGGERED,
            data={"reason": reason, "strategies_disabled": strategies_disabled},
        )
