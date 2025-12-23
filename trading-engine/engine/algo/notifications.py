"""Notification service for algo trading events."""

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class AlgoNotificationService:
    """Service for sending algo trading notifications.

    Handles notifications for:
    - Strategy started/stopped
    - Order execution
    - Risk limit breaches
    - Kill switch activation
    - Circuit breaker triggers
    
    Currently logs to console. Can be extended to support
    email, SMS, push notifications, etc.
    """

    async def notify_strategy_started(
        self,
        user_id: str,
        strategy_name: str,
        strategy_id: str,
    ) -> bool:
        """Notify when a strategy execution starts."""
        logger.info(
            f"[NOTIFICATION] Strategy Started: {strategy_name} "
            f"(id={strategy_id}, user={user_id})"
        )
        return True

    async def notify_strategy_stopped(
        self,
        user_id: str,
        strategy_name: str,
        strategy_id: str,
        reason: str | None = None,
    ) -> bool:
        """Notify when a strategy is stopped."""
        message = f"[NOTIFICATION] Strategy Stopped: {strategy_name}"
        if reason:
            message += f" - Reason: {reason}"
        logger.info(message)
        return True

    async def notify_strategy_error(
        self,
        user_id: str,
        strategy_name: str,
        strategy_id: str,
        error: str,
    ) -> bool:
        """Notify when a strategy encounters an error."""
        logger.error(
            f"[NOTIFICATION] Strategy Error: {strategy_name} - {error} "
            f"(id={strategy_id}, user={user_id})"
        )
        return True

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
        price_str = f" at ₹{price:,.2f}" if price else ""
        logger.info(
            f"[NOTIFICATION] Order Placed: {side} {quantity} {symbol}{price_str} "
            f"by strategy '{strategy_name}'"
        )
        return True

    async def notify_circuit_breaker_triggered(
        self,
        user_id: str,
        strategy_name: str,
        strategy_id: str,
        reason: str,
    ) -> bool:
        """Notify when circuit breaker is triggered."""
        logger.warning(
            f"[NOTIFICATION] Circuit Breaker Triggered: {strategy_name} - {reason} "
            f"(id={strategy_id}, user={user_id})"
        )
        return True

    async def notify_kill_switch_activated(
        self,
        user_id: str,
        reason: str | None = None,
        strategies_disabled: int = 0,
    ) -> bool:
        """Notify when kill switch is activated."""
        message = f"[NOTIFICATION] 🚨 KILL SWITCH ACTIVATED for user {user_id}"
        if reason:
            message += f" - Reason: {reason}"
        if strategies_disabled > 0:
            message += f" - {strategies_disabled} strategies disabled"
        logger.critical(message)
        return True

    async def notify_execution_complete(
        self,
        user_id: str,
        strategy_name: str,
        strategy_id: str,
        signals_generated: int,
        orders_placed: int,
    ) -> bool:
        """Notify when strategy execution completes."""
        logger.info(
            f"[NOTIFICATION] Execution Complete: {strategy_name} - "
            f"{signals_generated} signals, {orders_placed} orders "
            f"(id={strategy_id}, user={user_id})"
        )
        return True

