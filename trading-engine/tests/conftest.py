"""Pytest configuration and fixtures."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from engine.config import settings
from engine.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def internal_headers():
    """Headers with valid internal API key."""
    return {"X-Internal-Key": settings.INTERNAL_API_KEY}


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.ttl = AsyncMock(return_value=-1)
    redis.zcard = AsyncMock(return_value=0)
    redis.zadd = AsyncMock(return_value=1)
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def sample_strategy_config():
    """Create sample strategy configuration for testing."""
    from engine.algo.executor import StrategyConfig
    from engine.models.algo import PositionSizingMethod

    return StrategyConfig(
        id="test-strategy-123",
        user_id="test-user-456",
        name="Test RSI Strategy",
        strategy_name="rsi",
        strategy_params={"period": 14, "overbought": 70, "oversold": 30},
        timeframe="1d",
        symbols=["RELIANCE.NS", "TCS.NS", "INFY.NS"],
        position_sizing_method=PositionSizingMethod.FIXED_QUANTITY,
        fixed_quantity=10,
        fixed_amount=Decimal("100000"),
        portfolio_percent=Decimal("5.0"),
        risk_per_trade_percent=Decimal("2.0"),
    )


@pytest.fixture
def mock_user_strategy():
    """Create a mock UserStrategy object."""
    from datetime import datetime, UTC
    from engine.models.algo import (
        UserStrategy,
        StrategyStatus,
        ScheduleType,
        PositionSizingMethod
    )

    strategy = MagicMock(spec=UserStrategy)
    strategy.id = "test-strat-id"
    strategy.user_id = "test-user-id"
    strategy.name = "Test Strategy"
    strategy.strategy_name = "rsi"
    strategy.status = StrategyStatus.ACTIVE
    strategy.strategy_params = {"period": 14}
    strategy.schedule_type = ScheduleType.INTERVAL
    strategy.interval_seconds = 300
    strategy.timeframe = "1d"
    strategy.custom_symbols = ["RELIANCE.NS"]
    strategy.universe = None
    strategy.position_sizing_method = PositionSizingMethod.FIXED_QUANTITY
    strategy.fixed_quantity = 10
    strategy.fixed_amount = Decimal("100000")
    strategy.portfolio_percent = Decimal("5.0")
    strategy.risk_per_trade_percent = Decimal("2.0")
    strategy.max_daily_trades = 10
    strategy.max_daily_loss = Decimal("5000")
    strategy.cooldown_seconds = 60
    strategy.max_consecutive_losses = 3
    strategy.max_drawdown_percent = Decimal("10.0")
    strategy.max_open_positions = 5
    strategy.total_trades = 0
    strategy.winning_trades = 0
    strategy.total_pnl = Decimal("0")
    strategy.consecutive_losses = 0
    strategy.last_run_at = None
    strategy.next_run_at = datetime.now(UTC)
    strategy.is_paper_trading = True
    return strategy
