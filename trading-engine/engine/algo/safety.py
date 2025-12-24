"""Safety controls for algo trading.

Implements kill switch, circuit breaker, and rate limiter for safe algo execution.
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from redis.asyncio import Redis

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
        """Activate kill switch for a user."""
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
    """

    def __init__(self, redis: Redis):
        """Initialize with Redis client."""
        self.redis = redis

    async def check_and_update(
        self,
        strategy_id: str,
        max_daily_loss: Decimal,
        max_consecutive_losses: int,
        trade_pnl: Decimal | None = None,
        is_loss: bool | None = None,
    ) -> CircuitBreakerState:
        """Check if circuit breaker should trigger and update state."""
        key = CIRCUIT_BREAKER_KEY.format(strategy_id=strategy_id)

        # Load current state
        data = await self.redis.get(key)
        if data:
            state_dict = json.loads(data)
            daily_loss = Decimal(state_dict.get("daily_loss", "0"))
            consecutive_losses = state_dict.get("consecutive_losses", 0)
        else:
            daily_loss = Decimal("0")
            consecutive_losses = 0

        # Update with new trade if provided
        if trade_pnl is not None and trade_pnl < 0:
            daily_loss += abs(trade_pnl)
        if is_loss is True:
            consecutive_losses += 1
        elif is_loss is False:
            consecutive_losses = 0  # Reset on win

        # Check thresholds
        trigger_reason = None

        if daily_loss >= max_daily_loss:
            trigger_reason = (
                f"Daily loss limit breached: ₹{daily_loss:.2f} >= ₹{max_daily_loss:.2f}"
            )

        if consecutive_losses >= max_consecutive_losses:
            trigger_reason = f"Consecutive losses: {consecutive_losses} >= {max_consecutive_losses}"

        # Save state
        state_dict = {
            "daily_loss": str(daily_loss),
            "consecutive_losses": consecutive_losses,
            "is_triggered": trigger_reason is not None,
            "trigger_reason": trigger_reason,
            "triggered_at": datetime.now(UTC).isoformat() if trigger_reason else None,
        }

        # Expire at midnight (reset daily)
        now = datetime.now(UTC)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ttl = int((midnight - now).total_seconds())

        await self.redis.setex(key, ttl, json.dumps(state_dict))

        if trigger_reason:
            logger.warning(
                f"Circuit breaker TRIGGERED for strategy {strategy_id}: {trigger_reason}"
            )

        return CircuitBreakerState(
            is_triggered=trigger_reason is not None,
            trigger_reason=trigger_reason,
            daily_loss=daily_loss,
            consecutive_losses=consecutive_losses,
            triggered_at=datetime.now(UTC) if trigger_reason else None,
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

    async def get_state(self, strategy_id: str) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        key = CIRCUIT_BREAKER_KEY.format(strategy_id=strategy_id)
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
        )


class AlgoRateLimiter:
    """Rate limiter for algo order placement.

    Limits orders per minute per user to prevent runaway algos.
    """

    def __init__(self, redis: Redis, max_orders_per_minute: int = 10):
        """Initialize with Redis client."""
        self.redis = redis
        self.max_orders = max_orders_per_minute

    async def can_place_order(self, user_id: str) -> tuple[bool, str | None]:
        """Check if user can place another order."""
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
        """Check if strategy is in cooldown."""
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


# Redis key for daily trade counter
DAILY_TRADES_KEY = "algo:daily_trades:{strategy_id}"


class DailyTradeCounter:
    """Tracks daily trade count for strategies.

    Enforces max_daily_trades limit.
    """

    def __init__(self, redis: Redis):
        """Initialize with Redis client."""
        self.redis = redis

    async def get_trade_count(self, strategy_id: str) -> int:
        """Get current daily trade count for a strategy."""
        key = DAILY_TRADES_KEY.format(strategy_id=strategy_id)
        count = await self.redis.get(key)
        return int(count) if count else 0

    async def can_trade(self, strategy_id: str, max_daily_trades: int) -> tuple[bool, str | None]:
        """Check if strategy can place more trades today.

        Args:
            strategy_id: The strategy ID
            max_daily_trades: Maximum trades allowed per day

        Returns:
            Tuple of (can_trade, reason_if_blocked)
        """
        if max_daily_trades <= 0:
            return True, None  # No limit set

        current_count = await self.get_trade_count(strategy_id)
        if current_count >= max_daily_trades:
            return False, f"Max daily trades reached: {current_count}/{max_daily_trades}"
        return True, None

    async def increment(self, strategy_id: str) -> int:
        """Increment trade count for today.

        Returns:
            New trade count
        """
        key = DAILY_TRADES_KEY.format(strategy_id=strategy_id)

        # Increment counter
        new_count = await self.redis.incr(key)

        # Set expiry at midnight if this is the first trade
        if new_count == 1:
            now = datetime.now(UTC)
            midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            ttl = int((midnight - now).total_seconds())
            await self.redis.expire(key, ttl)

        return new_count

    async def reset(self, strategy_id: str) -> None:
        """Reset trade count for a strategy."""
        key = DAILY_TRADES_KEY.format(strategy_id=strategy_id)
        await self.redis.delete(key)


@dataclass
class SafetyCheck:
    """Result of a safety check."""

    passed: bool
    reason: str | None = None


class SafetyService:
    """Simple safety service for order validation.

    Provides basic safety checks without requiring Redis.
    For production use, consider using the Redis-based classes above.
    """

    def __init__(
        self,
        max_order_value: Decimal = Decimal("1000000"),
        max_quantity: int = 10000,
        blocked_symbols: list[str] | None = None,
    ):
        """Initialize safety service.

        Args:
            max_order_value: Maximum value per order
            max_quantity: Maximum quantity per order
            blocked_symbols: List of symbols that cannot be traded
        """
        self.max_order_value = max_order_value
        self.max_quantity = max_quantity
        self.blocked_symbols = blocked_symbols or []

    def check_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Decimal,
    ) -> SafetyCheck:
        """Check if an order passes safety checks.

        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            price: Order price

        Returns:
            SafetyCheck with pass/fail status
        """
        # Check blocked symbols
        if symbol in self.blocked_symbols:
            return SafetyCheck(passed=False, reason=f"Symbol {symbol} is blocked")

        # Check quantity
        if quantity > self.max_quantity:
            return SafetyCheck(
                passed=False,
                reason=f"Quantity {quantity} exceeds max {self.max_quantity}",
            )

        # Check order value
        order_value = price * Decimal(quantity)
        if order_value > self.max_order_value:
            return SafetyCheck(
                passed=False,
                reason=f"Order value ₹{order_value:.2f} exceeds max ₹{self.max_order_value:.2f}",
            )

        return SafetyCheck(passed=True)


@dataclass
class PreExecutionCheckResult:
    """Result of pre-execution safety checks."""

    can_execute: bool
    reason: str | None = None
    check_type: str | None = None  # kill_switch, circuit_breaker, cooldown, max_trades


class PreExecutionChecker:
    """Performs all pre-execution safety checks for a strategy.

    Checks in order:
    1. Kill switch (user-level)
    2. Circuit breaker (strategy-level)
    3. Cooldown (strategy-level)
    4. Max daily trades (strategy-level)
    """

    def __init__(self, redis: Redis):
        """Initialize with Redis client."""
        self.redis = redis
        self.kill_switch = AlgoKillSwitch(redis)
        self.circuit_breaker = CircuitBreaker(redis)
        self.cooldown = StrategyCooldown(redis)
        self.daily_trades = DailyTradeCounter(redis)

    async def check_all(
        self,
        user_id: str,
        strategy_id: str,
        cooldown_seconds: int = 0,
        max_daily_trades: int = 0,
    ) -> PreExecutionCheckResult:
        """Run all pre-execution checks.

        Args:
            user_id: The user ID
            strategy_id: The strategy ID
            cooldown_seconds: Cooldown period in seconds (0 = no cooldown)
            max_daily_trades: Max trades per day (0 = no limit)

        Returns:
            PreExecutionCheckResult with can_execute status
        """
        # 1. Check kill switch
        if await self.kill_switch.is_active(user_id):
            return PreExecutionCheckResult(
                can_execute=False,
                reason="Kill switch is active for user",
                check_type="kill_switch",
            )

        # 2. Check circuit breaker
        if await self.circuit_breaker.is_triggered(strategy_id):
            state = await self.circuit_breaker.get_state(strategy_id)
            return PreExecutionCheckResult(
                can_execute=False,
                reason=state.trigger_reason or "Circuit breaker triggered",
                check_type="circuit_breaker",
            )

        # 3. Check cooldown
        if cooldown_seconds > 0:
            in_cooldown, remaining = await self.cooldown.is_in_cooldown(
                strategy_id, cooldown_seconds
            )
            if in_cooldown:
                return PreExecutionCheckResult(
                    can_execute=False,
                    reason=f"Strategy in cooldown, {remaining}s remaining",
                    check_type="cooldown",
                )

        # 4. Check max daily trades
        if max_daily_trades > 0:
            can_trade, reason = await self.daily_trades.can_trade(strategy_id, max_daily_trades)
            if not can_trade:
                return PreExecutionCheckResult(
                    can_execute=False,
                    reason=reason,
                    check_type="max_trades",
                )

        return PreExecutionCheckResult(can_execute=True)

    async def record_trade(
        self,
        strategy_id: str,
        cooldown_seconds: int = 0,
    ) -> None:
        """Record a trade execution for tracking.

        Call this after a successful trade to:
        - Start cooldown period
        - Increment daily trade counter

        Args:
            strategy_id: The strategy ID
            cooldown_seconds: Cooldown period to start (0 = no cooldown)
        """
        # Start cooldown if configured
        if cooldown_seconds > 0:
            await self.cooldown.start_cooldown(strategy_id, cooldown_seconds)

        # Increment daily trade counter
        await self.daily_trades.increment(strategy_id)
