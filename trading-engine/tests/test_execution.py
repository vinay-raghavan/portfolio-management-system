"""Tests for the execution routes."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from engine.main import app
from engine.config import settings
from engine.core.redis import get_redis


class FakeRedis:
    """Fake Redis client for testing."""

    async def get(self, key: str) -> bytes | None:
        return None

    async def set(self, key: str, value: str, **kwargs) -> bool:
        return True

    async def delete(self, key: str) -> int:
        return 1


async def get_fake_redis():
    """Get fake Redis for testing."""
    return FakeRedis()


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
        assert "macd_crossover" in strategy_names

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

