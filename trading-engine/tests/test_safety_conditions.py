"""Tests for strategy condition enforcement - risk limits, cooldowns, circuit breaker."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from engine.algo.safety import (
    AlgoKillSwitch,
    CircuitBreaker,
    DailyTradeCounter,
    PreExecutionChecker,
    StrategyCooldown,
)


class TestKillSwitch:
    """Tests for AlgoKillSwitch."""

    @pytest.fixture
    def kill_switch(self, mock_redis):
        """Create kill switch with mock redis."""
        return AlgoKillSwitch(mock_redis)

    async def test_kill_switch_initially_inactive(self, kill_switch, mock_redis):
        """Test kill switch is inactive when no data in Redis."""
        mock_redis.get.return_value = None
        is_active = await kill_switch.is_active("user-123")
        assert is_active is False

    async def test_kill_switch_activate(self, kill_switch, mock_redis):
        """Test activating kill switch."""
        state = await kill_switch.activate(
            user_id="user-123",
            reason="Manual stop",
            square_off=False,
        )

        assert state.is_active is True
        assert state.reason == "Manual stop"
        mock_redis.set.assert_called_once()

    async def test_kill_switch_deactivate(self, kill_switch, mock_redis):
        """Test deactivating kill switch."""
        state = await kill_switch.deactivate("user-123")
        assert state.is_active is False
        mock_redis.delete.assert_called_once()

    async def test_kill_switch_is_active_when_set(self, kill_switch, mock_redis):
        """Test kill switch returns active when data exists."""
        mock_redis.get.return_value = json.dumps(
            {
                "is_active": True,
                "activated_at": datetime.now(UTC).isoformat(),
                "reason": "Test",
            }
        ).encode()

        is_active = await kill_switch.is_active("user-123")
        assert is_active is True


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.fixture
    def circuit_breaker(self, mock_redis):
        """Create circuit breaker with mock redis."""
        return CircuitBreaker(mock_redis)

    async def test_circuit_breaker_not_triggered_initially(self, circuit_breaker, mock_redis):
        """Test circuit breaker is not triggered initially."""
        mock_redis.get.return_value = None

        state = await circuit_breaker.check_and_update(
            strategy_id="strat-1",
            max_daily_loss=Decimal("5000"),
            max_consecutive_losses=3,
        )

        assert state.is_triggered is False

    async def test_circuit_breaker_triggers_on_daily_loss(self, circuit_breaker, mock_redis):
        """Test circuit breaker triggers when daily loss limit exceeded."""
        mock_redis.get.return_value = json.dumps(
            {
                "daily_loss": "4000",
                "consecutive_losses": 0,
            }
        ).encode()

        # Add a loss that pushes us over the limit
        state = await circuit_breaker.check_and_update(
            strategy_id="strat-1",
            max_daily_loss=Decimal("5000"),
            max_consecutive_losses=3,
            trade_pnl=Decimal("-1500"),  # Takes us to 5500
            is_loss=True,
        )

        assert state.is_triggered is True
        assert "Daily loss" in (state.trigger_reason or "")

    async def test_circuit_breaker_triggers_on_consecutive_losses(
        self, circuit_breaker, mock_redis
    ):
        """Test circuit breaker triggers on consecutive losses."""
        mock_redis.get.return_value = json.dumps(
            {
                "daily_loss": "0",
                "consecutive_losses": 2,  # Already at 2
            }
        ).encode()

        state = await circuit_breaker.check_and_update(
            strategy_id="strat-1",
            max_daily_loss=Decimal("5000"),
            max_consecutive_losses=3,
            is_loss=True,  # This makes it 3
        )

        assert state.is_triggered is True
        assert "Consecutive" in (state.trigger_reason or "")

    async def test_circuit_breaker_resets_on_win(self, circuit_breaker, mock_redis):
        """Test consecutive losses reset on winning trade."""
        mock_redis.get.return_value = json.dumps(
            {
                "daily_loss": "1000",
                "consecutive_losses": 2,
            }
        ).encode()

        state = await circuit_breaker.check_and_update(
            strategy_id="strat-1",
            max_daily_loss=Decimal("5000"),
            max_consecutive_losses=3,
            is_loss=False,  # This is a win
        )

        assert state.is_triggered is False
        assert state.consecutive_losses == 0  # Should reset


class TestStrategyCooldown:
    """Tests for StrategyCooldown."""

    @pytest.fixture
    def cooldown(self, mock_redis):
        """Create cooldown manager with mock redis."""
        return StrategyCooldown(mock_redis)

    async def test_not_in_cooldown_initially(self, cooldown, mock_redis):
        """Test no cooldown when no data exists."""
        mock_redis.ttl.return_value = -1

        in_cooldown, remaining = await cooldown.is_in_cooldown("strat-1", 60)

        assert in_cooldown is False
        assert remaining == 0

    async def test_in_cooldown_when_set(self, cooldown, mock_redis):
        """Test cooldown is active when TTL exists."""
        mock_redis.ttl.return_value = 45  # 45 seconds remaining

        in_cooldown, remaining = await cooldown.is_in_cooldown("strat-1", 60)

        assert in_cooldown is True
        assert remaining == 45

    async def test_start_cooldown(self, cooldown, mock_redis):
        """Test starting a cooldown period."""
        await cooldown.start_cooldown("strat-1", 120)
        mock_redis.setex.assert_called_once_with("algo:cooldown:strat-1", 120, "1")

    async def test_clear_cooldown(self, cooldown, mock_redis):
        """Test clearing cooldown."""
        await cooldown.clear_cooldown("strat-1")
        mock_redis.delete.assert_called_once()


class TestDailyTradeCounter:
    """Tests for DailyTradeCounter."""

    @pytest.fixture
    def counter(self, mock_redis):
        """Create daily trade counter with mock redis."""
        return DailyTradeCounter(mock_redis)

    async def test_get_trade_count_zero_initially(self, counter, mock_redis):
        """Test trade count is 0 when no data exists."""
        mock_redis.get.return_value = None

        count = await counter.get_trade_count("strat-1")

        assert count == 0

    async def test_get_trade_count_returns_value(self, counter, mock_redis):
        """Test trade count returns stored value."""
        mock_redis.get.return_value = b"5"

        count = await counter.get_trade_count("strat-1")

        assert count == 5

    async def test_can_trade_when_under_limit(self, counter, mock_redis):
        """Test can trade when under daily limit."""
        mock_redis.get.return_value = b"3"

        can_trade, reason = await counter.can_trade("strat-1", max_daily_trades=10)

        assert can_trade is True
        assert reason is None

    async def test_cannot_trade_when_at_limit(self, counter, mock_redis):
        """Test cannot trade when at daily limit."""
        mock_redis.get.return_value = b"10"

        can_trade, reason = await counter.can_trade("strat-1", max_daily_trades=10)

        assert can_trade is False
        assert "Max daily trades" in reason

    async def test_can_trade_when_no_limit(self, counter, mock_redis):
        """Test can always trade when no limit set."""
        mock_redis.get.return_value = b"100"

        can_trade, reason = await counter.can_trade("strat-1", max_daily_trades=0)

        assert can_trade is True

    async def test_increment_trade_count(self, counter, mock_redis):
        """Test incrementing trade count."""
        mock_redis.incr.return_value = 1

        new_count = await counter.increment("strat-1")

        assert new_count == 1
        mock_redis.incr.assert_called_once()


class TestPreExecutionChecker:
    """Tests for PreExecutionChecker."""

    @pytest.fixture
    def checker(self, mock_redis):
        """Create pre-execution checker with mock redis."""
        return PreExecutionChecker(mock_redis)

    async def test_check_all_passes_when_no_blocks(self, checker, mock_redis):
        """Test all checks pass when nothing is blocking."""
        mock_redis.get.return_value = None
        mock_redis.ttl.return_value = -1

        result = await checker.check_all(
            user_id="user-1",
            strategy_id="strat-1",
            cooldown_seconds=60,
            max_daily_trades=10,
        )

        assert result.can_execute is True
        assert result.reason is None

    async def test_check_all_blocks_on_kill_switch(self, checker, mock_redis):
        """Test execution blocked when kill switch is active."""
        # Kill switch is active
        mock_redis.get.side_effect = lambda key: (
            json.dumps({"is_active": True}).encode() if "kill_switch" in key else None
        )
        mock_redis.ttl.return_value = -1

        result = await checker.check_all(
            user_id="user-1",
            strategy_id="strat-1",
        )

        assert result.can_execute is False
        assert result.check_type == "kill_switch"

    async def test_check_all_blocks_on_circuit_breaker(self, checker, mock_redis):
        """Test execution blocked when circuit breaker is triggered."""

        def mock_get(key):
            if "kill_switch" in key:
                return None
            if "circuit_breaker" in key:
                return json.dumps(
                    {
                        "is_triggered": True,
                        "trigger_reason": "Daily loss exceeded",
                    }
                ).encode()
            return None

        mock_redis.get.side_effect = mock_get
        mock_redis.ttl.return_value = -1

        result = await checker.check_all(
            user_id="user-1",
            strategy_id="strat-1",
        )

        assert result.can_execute is False
        assert result.check_type == "circuit_breaker"

    async def test_check_all_blocks_on_cooldown(self, checker, mock_redis):
        """Test execution blocked when in cooldown."""
        mock_redis.get.return_value = None
        mock_redis.ttl.return_value = 30  # 30 seconds remaining

        result = await checker.check_all(
            user_id="user-1",
            strategy_id="strat-1",
            cooldown_seconds=60,
        )

        assert result.can_execute is False
        assert result.check_type == "cooldown"
        assert "30s remaining" in result.reason

    async def test_check_all_blocks_on_max_trades(self, checker, mock_redis):
        """Test execution blocked when max daily trades reached."""

        def mock_get(key):
            if "daily_trades" in key:
                return b"10"
            return None

        mock_redis.get.side_effect = mock_get
        mock_redis.ttl.return_value = -1

        result = await checker.check_all(
            user_id="user-1",
            strategy_id="strat-1",
            max_daily_trades=10,
        )

        assert result.can_execute is False
        assert result.check_type == "max_trades"
