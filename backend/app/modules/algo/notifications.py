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

    # =========================================================================
    # Auto-Trade Pipeline Notifications
    # =========================================================================

    async def notify_auto_trade_pending(
        self,
        user_id: str,
        pending_trade_id: str,
        category: str,
        symbols: list[str],
        strategy_type: str,
        expires_at: str,
    ) -> bool:
        """Notify when a pending auto-trade is created (NOTIFY mode).

        Args:
            user_id: User ID to notify
            pending_trade_id: ID of the pending auto-trade
            category: Trade category (momentum, breakout, value, sector)
            symbols: List of symbols in the trade
            strategy_type: Recommended strategy type
            expires_at: Expiry timestamp as ISO string

        Returns:
            True if notification was sent successfully
        """
        if not self._provider:
            return False

        symbols_str = ", ".join(symbols[:3])
        if len(symbols) > 3:
            symbols_str += f" (+{len(symbols) - 3} more)"

        return await self._provider.send(
            user_id=user_id,
            title=f"📊 Auto-Trade Pending: {category.title()}",
            message=(
                f"New auto-trade ready for {category}: {symbols_str}. "
                f"Strategy: {strategy_type}. Approve or reject before expiry."
            ),
            priority=NotificationPriority.MEDIUM,
            notification_type=NotificationType.AUTO_TRADE_PENDING,
            data={
                "pending_trade_id": pending_trade_id,
                "category": category,
                "symbols": symbols,
                "strategy_type": strategy_type,
                "expires_at": expires_at,
                "actions": ["approve", "reject"],
            },
        )

    async def notify_auto_trade_executed(
        self,
        user_id: str,
        strategy_id: str,
        strategy_name: str,
        category: str,
        symbols: list[str],
        confirmation_mode: str,
    ) -> bool:
        """Notify when an auto-trade is executed.

        Args:
            user_id: User ID to notify
            strategy_id: ID of the created strategy
            strategy_name: Name of the strategy
            category: Trade category
            symbols: List of symbols in the trade
            confirmation_mode: Whether it was AUTO or approved

        Returns:
            True if notification was sent successfully
        """
        if not self._provider:
            return False

        symbols_str = ", ".join(symbols[:3])
        if len(symbols) > 3:
            symbols_str += f" (+{len(symbols) - 3} more)"

        mode_str = "Auto-executed" if confirmation_mode == "auto" else "Approved and executed"

        return await self._provider.send(
            user_id=user_id,
            title=f"✅ Auto-Trade Executed: {strategy_name}",
            message=f"{mode_str}: {category.title()} strategy for {symbols_str}.",
            priority=NotificationPriority.MEDIUM,
            notification_type=NotificationType.AUTO_TRADE_EXECUTED,
            data={
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "category": category,
                "symbols": symbols,
                "confirmation_mode": confirmation_mode,
            },
        )

    async def notify_auto_trade_expired(
        self,
        user_id: str,
        pending_trade_id: str,
        category: str,
        symbols: list[str],
    ) -> bool:
        """Notify when a pending auto-trade expires without action.

        Args:
            user_id: User ID to notify
            pending_trade_id: ID of the expired pending trade
            category: Trade category
            symbols: List of symbols that expired

        Returns:
            True if notification was sent successfully
        """
        if not self._provider:
            return False

        symbols_str = ", ".join(symbols[:3])
        if len(symbols) > 3:
            symbols_str += f" (+{len(symbols) - 3} more)"

        return await self._provider.send(
            user_id=user_id,
            title=f"⏰ Auto-Trade Expired: {category.title()}",
            message=(
                f"Pending auto-trade for {category} has expired: {symbols_str}. "
                "No action was taken."
            ),
            priority=NotificationPriority.LOW,
            notification_type=NotificationType.AUTO_TRADE_EXPIRED,
            data={
                "pending_trade_id": pending_trade_id,
                "category": category,
                "symbols": symbols,
            },
        )

    async def notify_auto_trade_approved(
        self,
        user_id: str,
        pending_trade_id: str,
        strategy_id: str,
        strategy_name: str,
        category: str,
    ) -> bool:
        """Notify when a pending auto-trade is approved by user.

        Args:
            user_id: User ID to notify
            pending_trade_id: ID of the approved pending trade
            strategy_id: ID of the created strategy
            strategy_name: Name of the created strategy
            category: Trade category

        Returns:
            True if notification was sent successfully
        """
        if not self._provider:
            return False

        return await self._provider.send(
            user_id=user_id,
            title=f"✅ Auto-Trade Approved: {strategy_name}",
            message=f"Your {category.title()} auto-trade has been approved and strategy created.",
            priority=NotificationPriority.LOW,
            notification_type=NotificationType.AUTO_TRADE_APPROVED,
            data={
                "pending_trade_id": pending_trade_id,
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "category": category,
            },
        )

    async def notify_auto_trade_rejected(
        self,
        user_id: str,
        pending_trade_id: str,
        category: str,
        symbols: list[str],
        reason: str | None = None,
    ) -> bool:
        """Notify when a pending auto-trade is rejected by user.

        Args:
            user_id: User ID to notify
            pending_trade_id: ID of the rejected pending trade
            category: Trade category
            symbols: List of symbols that were rejected
            reason: Optional rejection reason

        Returns:
            True if notification was sent successfully
        """
        if not self._provider:
            return False

        symbols_str = ", ".join(symbols[:3])
        if len(symbols) > 3:
            symbols_str += f" (+{len(symbols) - 3} more)"

        message = f"Auto-trade for {category.title()} was rejected: {symbols_str}."
        if reason:
            message += f" Reason: {reason}"

        return await self._provider.send(
            user_id=user_id,
            title=f"❌ Auto-Trade Rejected: {category.title()}",
            message=message,
            priority=NotificationPriority.LOW,
            notification_type=NotificationType.AUTO_TRADE_REJECTED,
            data={
                "pending_trade_id": pending_trade_id,
                "category": category,
                "symbols": symbols,
                "reason": reason,
            },
        )
