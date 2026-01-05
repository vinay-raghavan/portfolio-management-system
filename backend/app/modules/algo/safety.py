"""Safety controls for algo trading.

Implements kill switch, circuit breaker, and rate limiter for safe algo execution.
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from redis.asyncio import Redis

from app.modules.algo.models import UserStrategy

logger = logging.getLogger(__name__)

# Redis key prefixes
KILL_SWITCH_KEY = "algo:kill_switch:{user_id}"
CIRCUIT_BREAKER_KEY = "algo:circuit_breaker:{strategy_id}"
RATE_LIMIT_KEY = "algo:rate_limit:{user_id}"
COOLDOWN_KEY = "algo:cooldown:{strategy_id}"


@dataclass
class KillSwitchState:
    """Kill switch state."""

    is_active: bool
    activated_at: datetime | None = None
    activated_by: str | None = None
    reason: str | None = None
    square_off_initiated: bool = False


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for a strategy."""

    is_triggered: bool
    trigger_reason: str | None = None
    daily_loss: Decimal = Decimal("0")
    consecutive_losses: int = 0
    triggered_at: datetime | None = None
    # Profit cutoff tracking
    daily_profit: Decimal = Decimal("0")
    overall_profit: Decimal = Decimal("0")
    profit_cutoff_triggered: bool = False


class AlgoKillSwitch:
    """Global kill switch for algo trading.

    One-click disable of all algo trading for a user.
    Optionally triggers square-off of all algo positions.
    """

    def __init__(self, redis: Redis):
        """Initialize with Redis client."""
        self.redis = redis

    async def activate(
        self,
        user_id: str,
        reason: str | None = None,
        square_off: bool = False,
    ) -> KillSwitchState:
        """Activate kill switch for a user.

        Args:
            user_id: User to activate kill switch for
            reason: Optional reason for activation
            square_off: Whether to initiate position square-off

        Returns:
            KillSwitchState after activation
        """
        key = KILL_SWITCH_KEY.format(user_id=user_id)
        now = datetime.now(UTC)

        state = {
            "is_active": True,
            "activated_at": now.isoformat(),
            "activated_by": user_id,
            "reason": reason or "Manual activation",
            "square_off_initiated": square_off,
        }

        await self.redis.set(key, json.dumps(state))
        logger.warning(f"Kill switch ACTIVATED for user {user_id}: {reason}")

        return KillSwitchState(
            is_active=True,
            activated_at=now,
            activated_by=user_id,
            reason=reason,
            square_off_initiated=square_off,
        )

    async def deactivate(self, user_id: str) -> KillSwitchState:
        """Deactivate kill switch for a user."""
        key = KILL_SWITCH_KEY.format(user_id=user_id)
        await self.redis.delete(key)
        logger.info(f"Kill switch DEACTIVATED for user {user_id}")

        return KillSwitchState(is_active=False)

    async def is_active(self, user_id: str) -> bool:
        """Check if kill switch is active for a user."""
        key = KILL_SWITCH_KEY.format(user_id=user_id)
        data = await self.redis.get(key)

        if data:
            state = json.loads(data)
            return state.get("is_active", False)
        return False

    async def get_state(self, user_id: str) -> KillSwitchState:
        """Get full kill switch state."""
        key = KILL_SWITCH_KEY.format(user_id=user_id)
        data = await self.redis.get(key)

        if not data:
            return KillSwitchState(is_active=False)

        state = json.loads(data)
        return KillSwitchState(
            is_active=state.get("is_active", False),
            activated_at=datetime.fromisoformat(state["activated_at"])
            if state.get("activated_at")
            else None,
            activated_by=state.get("activated_by"),
            reason=state.get("reason"),
            square_off_initiated=state.get("square_off_initiated", False),
        )


class CircuitBreaker:
    """Circuit breaker for individual strategies.

    Automatically disables strategy when risk thresholds are breached:
    - Max daily loss
    - Max consecutive losing trades
    - Max drawdown
    - Max daily profit (profit cutoff)
    - Overall profit target
    """

    def __init__(self, redis: Redis):
        """Initialize with Redis client."""
        self.redis = redis

    async def check_and_update(
        self,
        strategy: UserStrategy,
        trade_pnl: Decimal | None = None,
        is_loss: bool | None = None,
    ) -> CircuitBreakerState:
        """Check if circuit breaker should trigger and update state.

        Args:
            strategy: The strategy to check
            trade_pnl: P&L of the last trade (if just completed)
            is_loss: Whether the last trade was a loss

        Returns:
            CircuitBreakerState with current status
        """
        key = CIRCUIT_BREAKER_KEY.format(strategy_id=strategy.id)

        # Load current state
        data = await self.redis.get(key)
        if data:
            state_dict = json.loads(data)
            daily_loss = Decimal(state_dict.get("daily_loss", "0"))
            daily_profit = Decimal(state_dict.get("daily_profit", "0"))
            overall_profit = Decimal(state_dict.get("overall_profit", "0"))
            consecutive_losses = state_dict.get("consecutive_losses", 0)
        else:
            daily_loss = Decimal("0")
            daily_profit = Decimal("0")
            overall_profit = Decimal("0")
            consecutive_losses = 0

        # Update with new trade if provided
        if trade_pnl is not None:
            if trade_pnl < 0:
                daily_loss += abs(trade_pnl)
            else:
                daily_profit += trade_pnl
                overall_profit += trade_pnl

        if is_loss is True:
            consecutive_losses += 1
        elif is_loss is False:
            consecutive_losses = 0  # Reset on win

        # Check thresholds
        trigger_reason = None
        profit_cutoff_triggered = False

        # Loss thresholds
        if daily_loss >= strategy.max_daily_loss:
            trigger_reason = (
                f"Daily loss limit breached: ₹{daily_loss:.2f} >= ₹{strategy.max_daily_loss:.2f}"
            )

        if consecutive_losses >= strategy.max_consecutive_losses:
            trigger_reason = (
                f"Consecutive losses: {consecutive_losses} >= {strategy.max_consecutive_losses}"
            )

        # Profit cutoff thresholds
        if strategy.max_daily_profit and daily_profit >= strategy.max_daily_profit:
            trigger_reason = (
                f"Daily profit target reached: ₹{daily_profit:.2f} >= ₹{strategy.max_daily_profit:.2f}"
            )
            profit_cutoff_triggered = True
            logger.info(
                f"🎯 PROFIT CUTOFF: Strategy {strategy.id} reached daily profit target ₹{daily_profit:.2f}"
            )

        if strategy.overall_profit_target and overall_profit >= strategy.overall_profit_target:
            trigger_reason = (
                f"Overall profit target reached: ₹{overall_profit:.2f} >= "
                f"₹{strategy.overall_profit_target:.2f}"
            )
            profit_cutoff_triggered = True
            logger.info(
                f"🎯 PROFIT CUTOFF: Strategy {strategy.id} reached overall profit target "
                f"₹{overall_profit:.2f}"
            )

        # Save state
        state_dict = {
            "daily_loss": str(daily_loss),
            "daily_profit": str(daily_profit),
            "overall_profit": str(overall_profit),
            "consecutive_losses": consecutive_losses,
            "is_triggered": trigger_reason is not None,
            "trigger_reason": trigger_reason,
            "profit_cutoff_triggered": profit_cutoff_triggered,
            "triggered_at": datetime.now(UTC).isoformat() if trigger_reason else None,
        }

        # Expire at midnight (reset daily values, but overall_profit persists via strategy.total_pnl)
        now = datetime.now(UTC)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ttl = int((midnight - now).total_seconds())

        await self.redis.setex(key, ttl, json.dumps(state_dict))

        if trigger_reason:
            log_level = logger.info if profit_cutoff_triggered else logger.warning
            log_level(f"Circuit breaker TRIGGERED for strategy {strategy.id}: {trigger_reason}")

        return CircuitBreakerState(
            is_triggered=trigger_reason is not None,
            trigger_reason=trigger_reason,
            daily_loss=daily_loss,
            consecutive_losses=consecutive_losses,
            triggered_at=datetime.now(UTC) if trigger_reason else None,
            daily_profit=daily_profit,
            overall_profit=overall_profit,
            profit_cutoff_triggered=profit_cutoff_triggered,
        )

    async def is_triggered(self, strategy_id: str) -> bool:
        """Check if circuit breaker is triggered for a strategy."""
        key = CIRCUIT_BREAKER_KEY.format(strategy_id=strategy_id)
        data = await self.redis.get(key)

        if data:
            state = json.loads(data)
            return state.get("is_triggered", False)
        return False

    async def reset(self, strategy_id: str) -> None:
        """Reset circuit breaker for a strategy."""
        key = CIRCUIT_BREAKER_KEY.format(strategy_id=strategy_id)
        await self.redis.delete(key)
        logger.info(f"Circuit breaker RESET for strategy {strategy_id}")

    async def get_state(self, strategy: UserStrategy) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        key = CIRCUIT_BREAKER_KEY.format(strategy_id=strategy.id)
        data = await self.redis.get(key)

        if not data:
            return CircuitBreakerState(is_triggered=False)

        state = json.loads(data)
        return CircuitBreakerState(
            is_triggered=state.get("is_triggered", False),
            trigger_reason=state.get("trigger_reason"),
            daily_loss=Decimal(state.get("daily_loss", "0")),
            consecutive_losses=state.get("consecutive_losses", 0),
            triggered_at=datetime.fromisoformat(state["triggered_at"])
            if state.get("triggered_at")
            else None,
            daily_profit=Decimal(state.get("daily_profit", "0")),
            overall_profit=Decimal(state.get("overall_profit", "0")),
            profit_cutoff_triggered=state.get("profit_cutoff_triggered", False),
        )


class AlgoRateLimiter:
    """Rate limiter for algo order placement.

    Limits orders per minute per user to prevent runaway algos.
    """

    def __init__(self, redis: Redis, max_orders_per_minute: int = 10):
        """Initialize with Redis client.

        Args:
            redis: Redis client
            max_orders_per_minute: Maximum orders allowed per minute
        """
        self.redis = redis
        self.max_orders = max_orders_per_minute

    async def can_place_order(self, user_id: str) -> tuple[bool, str | None]:
        """Check if user can place another order.

        Returns:
            Tuple of (can_place, reason_if_blocked)
        """
        key = RATE_LIMIT_KEY.format(user_id=user_id)
        now = datetime.now(UTC)
        window_start = now - timedelta(minutes=1)

        # Use sorted set for sliding window
        await self.redis.zremrangebyscore(key, 0, window_start.timestamp())
        current_count = await self.redis.zcard(key)

        if current_count >= self.max_orders:
            return False, f"Rate limit: {current_count}/{self.max_orders} orders per minute"

        return True, None

    async def record_order(self, user_id: str) -> None:
        """Record an order placement."""
        key = RATE_LIMIT_KEY.format(user_id=user_id)
        now = datetime.now(UTC)

        # Add to sorted set with timestamp as score
        await self.redis.zadd(key, {str(now.timestamp()): now.timestamp()})
        await self.redis.expire(key, 120)  # 2 minute expiry

    async def get_remaining(self, user_id: str) -> int:
        """Get remaining orders in current window."""
        key = RATE_LIMIT_KEY.format(user_id=user_id)
        now = datetime.now(UTC)
        window_start = now - timedelta(minutes=1)

        await self.redis.zremrangebyscore(key, 0, window_start.timestamp())
        current_count = await self.redis.zcard(key)

        return max(0, self.max_orders - current_count)


class StrategyCooldown:
    """Cooldown manager for strategies.

    Ensures minimum time between trades for a strategy.
    """

    def __init__(self, redis: Redis):
        """Initialize with Redis client."""
        self.redis = redis

    async def is_in_cooldown(self, strategy_id: str, cooldown_seconds: int) -> tuple[bool, int]:
        """Check if strategy is in cooldown.

        Args:
            strategy_id: Strategy to check
            cooldown_seconds: Required cooldown period

        Returns:
            Tuple of (is_in_cooldown, seconds_remaining)
        """
        key = COOLDOWN_KEY.format(strategy_id=strategy_id)
        ttl = await self.redis.ttl(key)

        if ttl > 0:
            return True, ttl
        return False, 0

    async def start_cooldown(self, strategy_id: str, cooldown_seconds: int) -> None:
        """Start cooldown period for a strategy."""
        key = COOLDOWN_KEY.format(strategy_id=strategy_id)
        await self.redis.setex(key, cooldown_seconds, "1")

    async def clear_cooldown(self, strategy_id: str) -> None:
        """Clear cooldown for a strategy."""
        key = COOLDOWN_KEY.format(strategy_id=strategy_id)
        await self.redis.delete(key)
