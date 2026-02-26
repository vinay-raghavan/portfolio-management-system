"""Tests for the execution routes."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from engine.config import settings
from engine.core.database import get_db
from engine.core.redis import get_redis
from engine.main import app


class FakeRedis:
    """Fake Redis client for testing."""

    def __init__(self, lock_acquired: bool = True):
        """Initialize fake Redis.

        Args:
            lock_acquired: Whether lock acquisition should succeed
        """
        self._lock_acquired = lock_acquired
        self._stored_data: dict[str, str] = {}

    async def get(self, key: str) -> bytes | None:
        value = self._stored_data.get(key)
        return value.encode() if value else None

    async def set(self, key: str, value: str, **kwargs) -> bool:
        # Handle nx (set if not exists) flag for locking
        nx = kwargs.get("nx", False)
        if nx and key in self._stored_data:
            return False  # Key exists, don't overwrite
        if nx and not self._lock_acquired:
            return False  # Simulate lock already held
        self._stored_data[key] = value
        return True

    async def delete(self, key: str) -> int:
        if key in self._stored_data:
            del self._stored_data[key]
            return 1
        return 0

    async def eval(self, script: str, numkeys: int, *args) -> int:
        """Simulate Lua script execution for lock release."""
        if numkeys >= 1:
            key = args[0]
            expected_value = args[1] if len(args) > 1 else None
            current_value = self._stored_data.get(key)
            if current_value == expected_value:
                del self._stored_data[key]
                return 1
        return 0

    async def ttl(self, key: str) -> int:
        return -1


async def get_fake_redis():
    """Get fake Redis for testing."""
    return FakeRedis()


def get_fake_redis_with_lock_held():
    """Get fake Redis where lock is already held."""

    async def _get():
        return FakeRedis(lock_acquired=False)

    return _get


@pytest.fixture
def client():
    """Create a test client with mocked Redis."""
    app.dependency_overrides[get_redis] = get_fake_redis
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def internal_headers():
    """Get headers for internal API calls."""
    return {"X-Internal-Key": settings.INTERNAL_API_KEY}


class TestHealthRoutes:
    """Tests for health check routes."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "trading-engine"

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "trading-engine"
        assert data["status"] == "running"


class TestExecutionRoutes:
    """Tests for execution routes."""

    def test_execute_without_auth(self, client):
        """Test that execute endpoint requires auth."""
        response = client.post("/internal/execute", json={})
        assert response.status_code == 401

    def test_execute_with_invalid_key(self, client):
        """Test that execute endpoint rejects invalid key."""
        response = client.post(
            "/internal/execute",
            json={},
            headers={"X-Internal-Key": "invalid-key"},
        )
        assert response.status_code == 401

    def test_list_strategies(self, client, internal_headers):
        """Test listing available strategies."""
        response = client.get("/internal/strategies", headers=internal_headers)
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert "count" in data
        assert data["count"] > 0

        # Check that expected strategies are present
        strategy_names = [s["name"] for s in data["strategies"]]
        assert "rsi" in strategy_names
        assert "macd" in strategy_names

    def test_execute_strategy_missing_fields(self, client, internal_headers):
        """Test execute with missing required fields."""
        response = client.post(
            "/internal/execute",
            json={"strategy_id": "test"},
            headers=internal_headers,
        )
        # Should fail validation
        assert response.status_code == 422

    def test_execute_strategy_unknown_strategy(self, client, internal_headers):
        """Test execute with unknown strategy name."""
        response = client.post(
            "/internal/execute",
            json={
                "strategy_id": "test-id",
                "user_id": "user-123",
                "name": "Test Strategy",
                "strategy_name": "unknown_strategy",
                "symbols": ["RELIANCE.NS"],
            },
            headers=internal_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should return error/failed status for unknown strategy
        assert data["status"] in ("ERROR", "FAILED")

    def test_kill_switch_status(self, client, internal_headers):
        """Test getting kill switch status."""
        response = client.get(
            "/internal/kill-switch/user-123",
            headers=internal_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-123"
        assert "is_active" in data

    def test_circuit_breaker_status(self, client, internal_headers):
        """Test getting circuit breaker status."""
        response = client.get(
            "/internal/circuit-breaker/strategy-123",
            headers=internal_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_id"] == "strategy-123"
        assert "is_triggered" in data


class TestScheduledRunLocking:
    """Tests for distributed locking in run-scheduled endpoint."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        # Mock execute to return empty result for get_due_strategies
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result
        return db

    @pytest.fixture
    def client_with_lock_held(self):
        """Create a test client where lock is already held by another worker."""
        app.dependency_overrides[get_redis] = get_fake_redis_with_lock_held()
        yield TestClient(app)
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self, mock_db):
        """Create a test client with normal Redis (lock available) and mocked DB."""

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_redis] = get_fake_redis
        app.dependency_overrides[get_db] = override_get_db
        yield TestClient(app)
        app.dependency_overrides.clear()

    @pytest.fixture
    def internal_headers(self):
        """Get headers for internal API calls."""
        return {"X-Internal-Key": settings.INTERNAL_API_KEY}

    def test_run_scheduled_skips_when_lock_held(self, client_with_lock_held, internal_headers):
        """Test that run-scheduled returns skipped when another worker holds the lock."""
        response = client_with_lock_held.post(
            "/internal/run-scheduled",
            headers=internal_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert "Another worker" in data["reason"]
        assert data["executed"] == 0
        assert data["total_due"] == 0
        assert data["results"] == []

    def test_run_scheduled_acquires_lock_when_available(self, client, internal_headers):
        """Test that run-scheduled proceeds when lock is available."""
        response = client.post(
            "/internal/run-scheduled",
            headers=internal_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should not be skipped - lock was acquired
        assert data.get("status") == "success"
        # No strategies due in mock, so executed should be 0
        assert data["executed"] == 0
        assert data["total_due"] == 0

    def test_run_scheduled_requires_auth(self, client):
        """Test that run-scheduled requires authentication."""
        response = client.post("/internal/run-scheduled")
        assert response.status_code == 401

    def test_run_scheduled_rejects_invalid_key(self, client):
        """Test that run-scheduled rejects invalid API key."""
        response = client.post(
            "/internal/run-scheduled",
            headers={"X-Internal-Key": "invalid-key"},
        )
        assert response.status_code == 401


class TestStrategyExecutorTimeWindow:
    """Tests for StrategyExecutor time window checks."""

    @pytest.fixture
    def mock_broker(self):
        """Create a mock broker."""
        broker = MagicMock()
        broker.place_order = AsyncMock(return_value={"order_id": "test_order"})
        return broker

    @pytest.fixture
    def mock_data_provider(self):
        """Create a mock data provider."""
        provider = MagicMock()
        provider.get_historical_data = AsyncMock(return_value=None)
        return provider

    @pytest.fixture
    def mock_safety_service(self):
        """Create a mock safety service."""
        service = MagicMock()
        service.check_order = MagicMock(return_value=(True, ""))
        return service

    @pytest.mark.asyncio
    async def test_execute_skips_when_before_trading_window(
        self,
        mock_broker,
        mock_data_provider,
        mock_safety_service,
    ):
        """Test that execution is skipped when before trading window."""
        from datetime import time

        from engine.algo.executor import ExecutionResult, StrategyConfig, StrategyExecutor
        from engine.models.algo import ExecutionStatus

        executor = StrategyExecutor(
            broker=mock_broker,
            data_provider=mock_data_provider,
            safety_service=mock_safety_service,
        )

        # Configure a strategy with trading window in the future
        config = StrategyConfig(
            id="test-strategy-1",
            user_id="user-1",
            name="Test Strategy",
            strategy_name="SMA_Crossover",
            symbols=["RELIANCE"],
            trading_start_time=time(23, 59),  # Far in future
            trading_end_time=time(23, 59, 59),
            trading_timezone="Asia/Kolkata",
            active_trading_days=[0, 1, 2, 3, 4, 5, 6],  # All days
        )

        result: ExecutionResult = await executor.execute(config)

        assert result.status == ExecutionStatus.SKIPPED
        assert "Outside trading window" in result.error_message
        assert "Before trading window" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_skips_when_after_trading_window(
        self,
        mock_broker,
        mock_data_provider,
        mock_safety_service,
    ):
        """Test that execution is skipped when after trading window."""
        from datetime import time

        from engine.algo.executor import ExecutionResult, StrategyConfig, StrategyExecutor
        from engine.models.algo import ExecutionStatus

        executor = StrategyExecutor(
            broker=mock_broker,
            data_provider=mock_data_provider,
            safety_service=mock_safety_service,
        )

        # Configure a strategy with trading window in the past
        config = StrategyConfig(
            id="test-strategy-2",
            user_id="user-1",
            name="Test Strategy",
            strategy_name="SMA_Crossover",
            symbols=["RELIANCE"],
            trading_start_time=time(0, 0),  # Start of day
            trading_end_time=time(0, 1),  # 1 minute past midnight
            trading_timezone="Asia/Kolkata",
            active_trading_days=[0, 1, 2, 3, 4, 5, 6],  # All days
        )

        result: ExecutionResult = await executor.execute(config)

        assert result.status == ExecutionStatus.SKIPPED
        assert "Outside trading window" in result.error_message
        assert "After trading window" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_proceeds_when_no_time_window(
        self,
        mock_broker,
        mock_data_provider,
        mock_safety_service,
    ):
        """Test that execution proceeds past time window check when no time window is set."""
        from engine.algo.executor import ExecutionResult, StrategyConfig, StrategyExecutor
        from engine.models.algo import ExecutionStatus

        executor = StrategyExecutor(
            broker=mock_broker,
            data_provider=mock_data_provider,
            safety_service=mock_safety_service,
        )

        # Configure a strategy without time window
        config = StrategyConfig(
            id="test-strategy-3",
            user_id="user-1",
            name="Test Strategy",
            strategy_name="SMA_Crossover",  # Strategy not registered in test
            symbols=[],  # No symbols to avoid actual execution
            trading_start_time=None,  # No time window
            trading_end_time=None,
        )

        result: ExecutionResult = await executor.execute(config)

        # Should NOT be SKIPPED due to time window - it proceeds past the check
        # Will be FAILED since SMA_Crossover strategy is not registered in test env
        assert result.status != ExecutionStatus.SKIPPED
        # Confirm it failed for strategy-not-found reason, not time window
        assert result.status == ExecutionStatus.FAILED
        assert "not found in registry" in result.error_message
