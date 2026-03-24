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
        unrealized_pnl: Decimal | None = None,
        max_daily_profit: Decimal | None = None,
        overall_profit_target: Decimal | None = None,
        max_unrealized_loss: Decimal | None = None,
    ) -> CircuitBreakerState:
        """Check if circuit breaker should trigger and update state.

        Args:
            strategy_id: The strategy ID
            max_daily_loss: Max daily loss limit (realized losses from closed trades)
            max_consecutive_losses: Max consecutive losses allowed
            trade_pnl: P&L of the last trade (if just completed)
            is_loss: Whether the last trade was a loss
            unrealized_pnl: Current unrealized P&L from open positions
            max_daily_profit: Daily profit target (optional)
            overall_profit_target: Overall profit target (optional)
            max_unrealized_loss: Max unrealized loss from open positions (optional).
                If unrealized_pnl is negative and abs(unrealized_pnl) >= this value,
                circuit breaker triggers.
        """
        key = CIRCUIT_BREAKER_KEY.format(strategy_id=strategy_id)

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

        # Calculate total profit including unrealized P&L for profit cutoff checks
        current_unrealized = unrealized_pnl if unrealized_pnl is not None else Decimal("0")
        total_daily_profit = daily_profit + max(current_unrealized, Decimal("0"))
        total_overall_profit = overall_profit + max(current_unrealized, Decimal("0"))

        # Check thresholds
        trigger_reason = None
        profit_cutoff_triggered = False

        if daily_loss >= max_daily_loss:
            trigger_reason = (
                f"Daily loss limit breached: ₹{daily_loss:.2f} >= ₹{max_daily_loss:.2f}"
            )

        if consecutive_losses >= max_consecutive_losses:
            trigger_reason = f"Consecutive losses: {consecutive_losses} >= {max_consecutive_losses}"

        # Profit cutoff thresholds (using total profit = realized + unrealized)
        if max_daily_profit and total_daily_profit >= max_daily_profit:
            trigger_reason = (
                f"Daily profit target reached: ₹{total_daily_profit:.2f} >= "
                f"₹{max_daily_profit:.2f} (realized: ₹{daily_profit:.2f}, "
                f"unrealized: ₹{current_unrealized:.2f})"
            )
            profit_cutoff_triggered = True
            logger.info(
                f"🎯 PROFIT CUTOFF: Strategy {strategy_id} reached daily profit target "
                f"₹{total_daily_profit:.2f}"
            )

        if overall_profit_target and total_overall_profit >= overall_profit_target:
            trigger_reason = (
                f"Overall profit target reached: ₹{total_overall_profit:.2f} >= "
                f"₹{overall_profit_target:.2f} (realized: ₹{overall_profit:.2f}, "
                f"unrealized: ₹{current_unrealized:.2f})"
            )
            profit_cutoff_triggered = True
            logger.info(
                f"🎯 PROFIT CUTOFF: Strategy {strategy_id} reached overall profit target "
                f"₹{total_overall_profit:.2f}"
            )

        # Check unrealized loss threshold (for open positions drawdown protection)
        if max_unrealized_loss and current_unrealized < Decimal("0"):
            unrealized_loss_abs = abs(current_unrealized)
            if unrealized_loss_abs >= max_unrealized_loss:
                trigger_reason = (
                    f"Unrealized loss limit breached: ₹{unrealized_loss_abs:.2f} >= "
                    f"₹{max_unrealized_loss:.2f} (open positions are down)"
                )
                logger.warning(
                    f"🛑 UNREALIZED LOSS CUTOFF: Strategy {strategy_id} "
                    f"open positions down ₹{unrealized_loss_abs:.2f}"
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

        # Expire at midnight (reset daily values)
        now = datetime.now(UTC)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ttl = int((midnight - now).total_seconds())

        await self.redis.setex(key, ttl, json.dumps(state_dict))

        if trigger_reason:
            log_level = logger.info if profit_cutoff_triggered else logger.warning
            log_level(f"Circuit breaker TRIGGERED for strategy {strategy_id}: {trigger_reason}")

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

    async def increment(self, strategy_id: str, count: int = 1) -> int:
        """Increment trade count for today.

        Returns:
            New trade count
        """
        if count <= 0:
            return await self.get_trade_count(strategy_id)

        key = DAILY_TRADES_KEY.format(strategy_id=strategy_id)

        # Increment counter
        new_count = await self.redis.incrby(key, count)

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
    """Safety service for order validation.

    Provides safety checks including:
    - Order value limits
    - Quantity limits
    - Blocked symbols
    - Funds availability (when broker provided)

    For production use with Redis-based rate limiting and circuit breakers,
    see the other classes in this module.
    """

    def __init__(
        self,
        max_order_value: Decimal = Decimal("1000000"),
        max_quantity: int = 10000,
        blocked_symbols: list[str] | None = None,
        broker=None,
    ):
        """Initialize safety service.

        Args:
            max_order_value: Maximum value per order
            max_quantity: Maximum quantity per order
            blocked_symbols: List of symbols that cannot be traded
            broker: Optional broker for funds validation
        """
        self.max_order_value = max_order_value
        self.max_quantity = max_quantity
        self.blocked_symbols = blocked_symbols or []
        self.broker = broker

    def check_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Decimal,
    ) -> SafetyCheck:
        """Check if an order passes safety checks (sync version).

        For async funds validation, use check_order_with_funds().

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

    async def check_order_with_funds(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: Decimal,
        product_type: str = "DELIVERY",
        existing_position_qty: Decimal | None = None,
    ) -> SafetyCheck:
        """Check if an order passes safety checks including funds/margin validation.

        This is the async version that validates available funds/margin based on
        product type (CNC/MIS/MTF).

        Args:
            user_id: User placing the order
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            price: Order price
            product_type: Product type (DELIVERY, INTRADAY, MARGIN)
            existing_position_qty: Current position quantity for SELL validation

        Returns:
            SafetyCheck with pass/fail status
        """
        # Run basic checks first
        basic_check = self.check_order(symbol, side, quantity, price)
        if not basic_check.passed:
            return basic_check

        if self.broker is None:
            logger.error("Broker not configured - cannot validate funds")
            return SafetyCheck(
                passed=False,
                reason="Broker not configured - cannot validate funds. Order blocked.",
            )

        # Get margin percentage based on product type
        margin_percent = self._get_margin_percent(product_type)
        order_value = price * Decimal(quantity)
        estimated_fees = order_value * Decimal("0.001")

        try:
            funds = await self.broker.get_funds(user_id)

            if side == "BUY":
                return self._check_buy_funds(
                    product_type, order_value, estimated_fees, margin_percent, funds
                )
            else:  # SELL
                return self._check_sell_funds(
                    product_type,
                    order_value,
                    estimated_fees,
                    margin_percent,
                    funds,
                    quantity,
                    existing_position_qty,
                )

        except Exception as e:
            logger.error(f"Failed to check funds for {user_id}: {e}")
            # BLOCK order - funds validation is critical for capital protection
            return SafetyCheck(
                passed=False,
                reason=f"Unable to validate funds: {e}. Order blocked for safety.",
            )

    def _get_margin_percent(self, product_type: str) -> Decimal:
        """Get margin percentage for product type.

        Margin percentages:
        - DELIVERY (CNC): 100% - full payment required
        - INTRADAY (MIS): 20% - day trading margin (varies 20-40% by stock)
        - MARGIN (MTF): 50% - leveraged buying
        - SLB: 30% - short selling with stock borrowing
        """
        margins = {
            "DELIVERY": Decimal("1.0"),
            "CNC": Decimal("1.0"),
            "INTRADAY": Decimal("0.25"),
            "MIS": Decimal("0.25"),
            "MARGIN": Decimal("0.50"),
            "MTF": Decimal("0.50"),
            "SLB": Decimal("0.30"),
        }
        return margins.get(product_type.upper(), Decimal("1.0"))

    def _check_buy_funds(
        self,
        product_type: str,
        order_value: Decimal,
        fees: Decimal,
        margin_percent: Decimal,
        funds,
    ) -> SafetyCheck:
        """Check funds for BUY order based on product type."""
        # Block any order if available cash is negative
        if funds.available_cash < Decimal("0"):
            return SafetyCheck(
                passed=False,
                reason=(
                    f"Negative available cash (₹{funds.available_cash:.2f}). "
                    f"Cannot open new positions until existing positions are closed."
                ),
            )

        if product_type.upper() in ("DELIVERY", "CNC"):
            # Full payment required
            total_required = order_value + fees
            if funds.available_cash < total_required:
                return SafetyCheck(
                    passed=False,
                    reason=(
                        f"Insufficient funds for DELIVERY buy: "
                        f"required ₹{total_required:.2f}, available ₹{funds.available_cash:.2f}"
                    ),
                )
        else:
            # Margin required
            margin_required = order_value * margin_percent + fees
            if funds.available_cash < margin_required:
                return SafetyCheck(
                    passed=False,
                    reason=(
                        f"Insufficient margin for {product_type} buy: "
                        f"required ₹{margin_required:.2f} ({margin_percent * 100:.0f}% margin), "
                        f"available ₹{funds.available_cash:.2f}"
                    ),
                )
        return SafetyCheck(passed=True)

    def _check_sell_funds(
        self,
        product_type: str,
        order_value: Decimal,
        fees: Decimal,
        margin_percent: Decimal,
        funds,
        quantity: int,
        existing_position_qty: Decimal | None,
    ) -> SafetyCheck:
        """Check funds/position for SELL order based on product type."""
        owned = existing_position_qty or Decimal("0")

        # Block any new short position if available cash is negative
        if owned <= 0 and funds.available_cash < Decimal("0"):
            return SafetyCheck(
                passed=False,
                reason=(
                    f"Negative available cash (₹{funds.available_cash:.2f}). "
                    f"Cannot open new short positions until existing positions are closed."
                ),
            )

        if product_type.upper() in ("DELIVERY", "CNC"):
            # Must own shares to sell
            if owned < quantity:
                return SafetyCheck(
                    passed=False,
                    reason=(
                        f"Cannot short sell in DELIVERY mode: "
                        f"trying to sell {quantity} but only own {owned}"
                    ),
                )

        elif product_type.upper() in ("INTRADAY", "MIS"):
            # Short selling allowed with margin
            if owned <= 0:
                # Opening short - check margin
                margin_required = order_value * margin_percent + fees
                if funds.available_cash < margin_required:
                    return SafetyCheck(
                        passed=False,
                        reason=(
                            f"Insufficient margin for INTRADAY short: "
                            f"required ₹{margin_required:.2f}, available ₹{funds.available_cash:.2f}"
                        ),
                    )

        elif product_type.upper() in ("MARGIN", "MTF"):
            # No short selling in MTF
            if owned < quantity:
                return SafetyCheck(
                    passed=False,
                    reason=(
                        f"Cannot short sell in MARGIN (MTF) mode: "
                        f"trying to sell {quantity} but only own {owned}"
                    ),
                )

        elif product_type.upper() == "SLB":
            # SLB (Stock Lending & Borrowing) requires margin for short selling
            if owned <= 0:
                # Opening short via SLB - check margin
                margin_required = order_value * margin_percent + fees
                if funds.available_cash < margin_required:
                    return SafetyCheck(
                        passed=False,
                        reason=(
                            f"Insufficient margin for SLB short: "
                            f"required ₹{margin_required:.2f} ({margin_percent * 100:.0f}% margin), "
                            f"available ₹{funds.available_cash:.2f}"
                        ),
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
        trades_count: int = 1,
    ) -> None:
        """Record a trade execution for tracking.

        Call this after a successful trade to:
        - Start cooldown period
        - Increment daily trade counter

        Args:
            strategy_id: The strategy ID
            cooldown_seconds: Cooldown period to start (0 = no cooldown)
            trades_count: Number of trades to count for daily trade limit.
        """
        # Start cooldown if configured
        if cooldown_seconds > 0:
            await self.cooldown.start_cooldown(strategy_id, cooldown_seconds)

        # Increment daily trade counter
        await self.daily_trades.increment(strategy_id, trades_count)


class CircuitBreakerPersistence:
    """Persistence layer for circuit breaker state.

    Handles loading from DB to Redis on startup and
    syncing Redis state to DB periodically and on triggers.
    """

    def __init__(self, redis: Redis):
        """Initialize with Redis client."""
        self.redis = redis

    async def load_from_db_to_redis(self, db, strategy_id: str) -> bool:
        """Load circuit breaker state from DB to Redis.

        Call on startup to restore state after Redis restart.

        Returns:
            True if state was loaded, False if no DB state exists
        """
        from sqlalchemy import select

        from engine.models.algo import CircuitBreakerState as CBStateModel

        result = await db.execute(
            select(CBStateModel).where(CBStateModel.strategy_id == strategy_id)
        )
        db_state = result.scalar_one_or_none()

        if not db_state:
            return False

        # Check if we need to reset daily values (new day)
        today = datetime.now(UTC).date()
        tracking_date = db_state.tracking_date.date() if db_state.tracking_date else None

        if tracking_date and tracking_date < today:
            # New day - reset daily values but keep overall profit
            state_dict = {
                "is_triggered": False,
                "trigger_reason": None,
                "triggered_at": None,
                "daily_loss": "0",
                "daily_profit": "0",
                "consecutive_losses": 0,
                "overall_profit": str(db_state.overall_profit),
                "profit_cutoff_triggered": False,
            }
        else:
            # Same day - restore full state
            state_dict = {
                "is_triggered": db_state.is_triggered,
                "trigger_reason": db_state.trigger_reason,
                "triggered_at": db_state.triggered_at.isoformat()
                if db_state.triggered_at
                else None,
                "daily_loss": str(db_state.daily_loss),
                "daily_profit": str(db_state.daily_profit),
                "consecutive_losses": db_state.consecutive_losses,
                "overall_profit": str(db_state.overall_profit),
                "profit_cutoff_triggered": db_state.profit_cutoff_triggered,
            }

        # Set in Redis with TTL until midnight
        key = CIRCUIT_BREAKER_KEY.format(strategy_id=strategy_id)
        now = datetime.now(UTC)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ttl = int((midnight - now).total_seconds())

        await self.redis.setex(key, ttl, json.dumps(state_dict))
        logger.info(f"Loaded circuit breaker state from DB for strategy {strategy_id}")
        return True

    async def sync_to_db(self, db, strategy_id: str, user_id: str) -> bool:
        """Sync current Redis state to DB.

        Call periodically to persist state.

        Returns:
            True if synced successfully
        """
        from uuid import uuid4

        from sqlalchemy import select

        from engine.models.algo import CircuitBreakerState as CBStateModel

        # Get current state from Redis
        key = CIRCUIT_BREAKER_KEY.format(strategy_id=strategy_id)
        data = await self.redis.get(key)

        if not data:
            return False

        state = json.loads(data)

        # Upsert to DB
        result = await db.execute(
            select(CBStateModel).where(CBStateModel.strategy_id == strategy_id)
        )
        db_state = result.scalar_one_or_none()

        if db_state:
            # Update existing
            db_state.is_triggered = state.get("is_triggered", False)
            db_state.trigger_reason = state.get("trigger_reason")
            db_state.triggered_at = (
                datetime.fromisoformat(state["triggered_at"]) if state.get("triggered_at") else None
            )
            db_state.daily_loss = Decimal(state.get("daily_loss", "0"))
            db_state.daily_profit = Decimal(state.get("daily_profit", "0"))
            db_state.consecutive_losses = state.get("consecutive_losses", 0)
            db_state.overall_profit = Decimal(state.get("overall_profit", "0"))
            db_state.profit_cutoff_triggered = state.get("profit_cutoff_triggered", False)
            db_state.tracking_date = datetime.now(UTC)
        else:
            # Create new
            db_state = CBStateModel(
                id=str(uuid4()),
                strategy_id=strategy_id,
                user_id=user_id,
                is_triggered=state.get("is_triggered", False),
                trigger_reason=state.get("trigger_reason"),
                triggered_at=(
                    datetime.fromisoformat(state["triggered_at"])
                    if state.get("triggered_at")
                    else None
                ),
                daily_loss=Decimal(state.get("daily_loss", "0")),
                daily_profit=Decimal(state.get("daily_profit", "0")),
                consecutive_losses=state.get("consecutive_losses", 0),
                overall_profit=Decimal(state.get("overall_profit", "0")),
                profit_cutoff_triggered=state.get("profit_cutoff_triggered", False),
                tracking_date=datetime.now(UTC),
            )
            db.add(db_state)

        await db.commit()
        logger.debug(f"Synced circuit breaker state to DB for strategy {strategy_id}")
        return True

    async def persist_trigger_event(
        self,
        db,
        strategy_id: str,
        user_id: str,
        event_type: str,
        state: CircuitBreakerState,
    ) -> None:
        """Persist a circuit breaker trigger/reset event to history.

        Call immediately when circuit breaker is triggered or reset.

        Args:
            db: Database session
            strategy_id: Strategy ID
            user_id: User ID
            event_type: TRIGGERED, RESET, or DAILY_RESET
            state: Current circuit breaker state
        """
        from uuid import uuid4

        from engine.models.algo import CircuitBreakerHistory

        event = CircuitBreakerHistory(
            id=str(uuid4()),
            strategy_id=strategy_id,
            user_id=user_id,
            event_type=event_type,
            trigger_reason=state.trigger_reason,
            daily_loss=state.daily_loss,
            daily_profit=state.daily_profit,
            consecutive_losses=state.consecutive_losses,
            overall_profit=state.overall_profit,
        )
        db.add(event)
        await db.commit()

        logger.info(f"Persisted circuit breaker event: {event_type} for strategy {strategy_id}")

    async def load_all_active_strategies(self, db) -> list[str]:
        """Load all active strategy IDs that have circuit breaker state.

        Call on startup to restore all states.

        Returns:
            List of strategy IDs that were loaded
        """
        from sqlalchemy import select

        from engine.models.algo import CircuitBreakerState as CBStateModel

        result = await db.execute(select(CBStateModel.strategy_id))
        strategy_ids = [row[0] for row in result.all()]

        loaded = []
        for strategy_id in strategy_ids:
            if await self.load_from_db_to_redis(db, strategy_id):
                loaded.append(strategy_id)

        logger.info(f"Loaded circuit breaker states for {len(loaded)} strategies")
        return loaded
