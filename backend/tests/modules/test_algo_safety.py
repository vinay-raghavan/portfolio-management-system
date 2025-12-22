"""Tests for algo trading safety controls."""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.algo.models import PositionSizingMethod, UserStrategy
from app.modules.algo.safety import (
    AlgoKillSwitch,
    AlgoRateLimiter,
    CircuitBreaker,
    StrategyCooldown,
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.zadd = AsyncMock(return_value=1)
    mock.zrangebyscore = AsyncMock(return_value=[])
    mock.zremrangebyscore = AsyncMock(return_value=0)
    mock.zcard = AsyncMock(return_value=0)
    mock.expire = AsyncMock(return_value=True)
    mock.ttl = AsyncMock(return_value=-2)
    return mock


@pytest.fixture
def mock_strategy():
    """Create a mock UserStrategy."""
    strategy = MagicMock(spec=UserStrategy)
    strategy.id = "test-strategy-id"
    strategy.user_id = "test-user-id"
    strategy.name = "Test Strategy"
    strategy.max_daily_loss = Decimal("10000")
    strategy.max_consecutive_losses = 5
    strategy.position_sizing_method = PositionSizingMethod.FIXED_QUANTITY
    strategy.position_sizing_value = Decimal("10")
    return strategy


class TestAlgoKillSwitch:
    """Tests for AlgoKillSwitch."""

    @pytest.mark.asyncio
    async def test_activate_kill_switch(self, mock_redis):
        """Test activating kill switch."""
        kill_switch = AlgoKillSwitch(mock_redis)

        state = await kill_switch.activate(
            user_id="test-user",
            reason="Test activation",
            square_off=True,
        )

        assert state.is_active is True
        assert state.reason == "Test activation"
        assert state.square_off_initiated is True
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_kill_switch(self, mock_redis):
        """Test deactivating kill switch."""
        kill_switch = AlgoKillSwitch(mock_redis)

        state = await kill_switch.deactivate("test-user")

        assert state.is_active is False
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_active_when_not_set(self, mock_redis):
        """Test is_active returns False when not set."""
        mock_redis.get.return_value = None
        kill_switch = AlgoKillSwitch(mock_redis)

        result = await kill_switch.is_active("test-user")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_active_when_set(self, mock_redis):
        """Test is_active returns True when set."""
        mock_redis.get.return_value = json.dumps({"is_active": True})
        kill_switch = AlgoKillSwitch(mock_redis)

        result = await kill_switch.is_active("test-user")

        assert result is True


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_no_trigger_below_threshold(self, mock_redis, mock_strategy):
        """Test circuit breaker doesn't trigger below thresholds."""
        mock_redis.get.return_value = None
        circuit_breaker = CircuitBreaker(mock_redis)

        state = await circuit_breaker.check_and_update(
            strategy=mock_strategy,
            trade_pnl=Decimal("-1000"),
            is_loss=True,
        )

        assert state.is_triggered is False
        assert state.daily_loss == Decimal("1000")
        assert state.consecutive_losses == 1

    @pytest.mark.asyncio
    async def test_trigger_on_daily_loss(self, mock_redis, mock_strategy):
        """Test circuit breaker triggers on daily loss limit."""
        mock_redis.get.return_value = json.dumps(
            {
                "daily_loss": "9500",
                "consecutive_losses": 2,
            }
        )
        circuit_breaker = CircuitBreaker(mock_redis)

        state = await circuit_breaker.check_and_update(
            strategy=mock_strategy,
            trade_pnl=Decimal("-600"),
            is_loss=True,
        )

        assert state.is_triggered is True
        assert "Daily loss limit" in state.trigger_reason

    @pytest.mark.asyncio
    async def test_trigger_on_consecutive_losses(self, mock_redis, mock_strategy):
        """Test circuit breaker triggers on consecutive losses."""
        mock_redis.get.return_value = json.dumps(
            {
                "daily_loss": "1000",
                "consecutive_losses": 4,
            }
        )
        circuit_breaker = CircuitBreaker(mock_redis)

        state = await circuit_breaker.check_and_update(
            strategy=mock_strategy,
            is_loss=True,
        )

        assert state.is_triggered is True
        assert "Consecutive losses" in state.trigger_reason

    @pytest.mark.asyncio
    async def test_reset_consecutive_on_win(self, mock_redis, mock_strategy):
        """Test consecutive losses reset on win."""
        mock_redis.get.return_value = json.dumps(
            {
                "daily_loss": "1000",
                "consecutive_losses": 3,
            }
        )
        circuit_breaker = CircuitBreaker(mock_redis)

        state = await circuit_breaker.check_and_update(
            strategy=mock_strategy,
            is_loss=False,
        )

        assert state.consecutive_losses == 0
        assert state.is_triggered is False

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self, mock_redis):
        """Test resetting circuit breaker."""
        circuit_breaker = CircuitBreaker(mock_redis)

        await circuit_breaker.reset("test-strategy-id")

        mock_redis.delete.assert_called_once()


class TestAlgoRateLimiter:
    """Tests for AlgoRateLimiter."""

    @pytest.mark.asyncio
    async def test_can_place_order_when_under_limit(self, mock_redis):
        """Test order allowed when under rate limit."""
        mock_redis.zcard.return_value = 3  # 3 orders
        rate_limiter = AlgoRateLimiter(mock_redis, max_orders_per_minute=10)

        can_place, reason = await rate_limiter.can_place_order("test-user")

        assert can_place is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_cannot_place_order_when_at_limit(self, mock_redis):
        """Test order blocked when at rate limit."""
        mock_redis.zcard.return_value = 10  # 10 orders
        rate_limiter = AlgoRateLimiter(mock_redis, max_orders_per_minute=10)

        can_place, reason = await rate_limiter.can_place_order("test-user")

        assert can_place is False
        assert "Rate limit" in reason

    @pytest.mark.asyncio
    async def test_record_order(self, mock_redis):
        """Test recording an order."""
        rate_limiter = AlgoRateLimiter(mock_redis)

        await rate_limiter.record_order("test-user")

        mock_redis.zadd.assert_called_once()
        mock_redis.expire.assert_called_once()


class TestStrategyCooldown:
    """Tests for StrategyCooldown."""

    @pytest.mark.asyncio
    async def test_not_in_cooldown(self, mock_redis):
        """Test when not in cooldown."""
        mock_redis.ttl.return_value = -2  # Key doesn't exist
        cooldown = StrategyCooldown(mock_redis)

        in_cooldown, remaining = await cooldown.is_in_cooldown("test-strategy", 60)

        assert in_cooldown is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_in_cooldown(self, mock_redis):
        """Test when in cooldown."""
        mock_redis.ttl.return_value = 30  # 30 seconds remaining
        cooldown = StrategyCooldown(mock_redis)

        in_cooldown, remaining = await cooldown.is_in_cooldown("test-strategy", 60)

        assert in_cooldown is True
        assert remaining == 30

    @pytest.mark.asyncio
    async def test_start_cooldown(self, mock_redis):
        """Test starting cooldown."""
        cooldown = StrategyCooldown(mock_redis)

        await cooldown.start_cooldown("test-strategy", 60)

        mock_redis.setex.assert_called_once()
