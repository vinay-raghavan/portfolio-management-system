"""Integration tests for Signals API endpoints."""

import uuid

import pytest
from httpx import AsyncClient

from app.modules.signals.models import SignalStatus, SignalType


class TestSignalsAPI:
    """Tests for Signals API endpoints."""

    @pytest.mark.asyncio
    async def test_list_strategies_no_auth_required(self, client: AsyncClient):
        """Test listing available strategies (no auth required for this endpoint)."""
        response = await client.get("/api/v1/signals/strategies")

        # This endpoint doesn't require auth
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data

    @pytest.mark.asyncio
    async def test_generate_signals_requires_auth(self, client: AsyncClient):
        """Test that signal generation requires authentication."""
        response = await client.post(
            "/api/v1/signals/generate",
            json={"symbols": ["AAPL", "MSFT"]},
        )

        # Should require authentication
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_signals_requires_auth(self, client: AsyncClient):
        """Test that getting signals requires authentication."""
        response = await client.get("/api/v1/signals")

        # Should require authentication
        assert response.status_code == 401


class TestBacktestAPI:
    """Tests for Backtest API endpoints."""

    @pytest.mark.asyncio
    async def test_list_backtest_strategies_no_auth(self, client: AsyncClient):
        """Test listing available backtest strategies (no auth required)."""
        # Note: backtest router has prefix="/backtest" and is included with prefix="/backtest"
        # So the actual path is /api/v1/backtest/backtest/strategies
        response = await client.get("/api/v1/backtest/backtest/strategies")

        # This endpoint doesn't require auth
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_run_backtest_requires_auth(self, client: AsyncClient):
        """Test that running backtest requires authentication."""
        # Note: double prefix due to router configuration
        response = await client.post(
            "/api/v1/backtest/backtest",
            json={
                "symbol": "AAPL",
                "strategy_name": "rsi",
                "start_date": "2023-01-01T00:00:00Z",
                "end_date": "2023-12-31T00:00:00Z",
            },
        )

        # Should require authentication
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_backtests_requires_auth(self, client: AsyncClient):
        """Test that getting backtests requires authentication."""
        response = await client.get("/api/v1/backtest/backtest")

        # Should require authentication
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_backtest_by_id_requires_auth(self, client: AsyncClient):
        """Test that getting a specific backtest requires authentication."""
        backtest_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/backtest/backtest/{backtest_id}")

        # Should require authentication
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_backtest_requires_auth(self, client: AsyncClient):
        """Test that deleting a backtest requires authentication."""
        backtest_id = str(uuid.uuid4())
        response = await client.delete(f"/api/v1/backtest/backtest/{backtest_id}")

        # Should require authentication
        assert response.status_code == 401


class TestSignalModel:
    """Tests for Signal model."""

    def test_signal_type_enum(self):
        """Test SignalType enum values."""
        assert SignalType.BUY.value == "BUY"
        assert SignalType.SELL.value == "SELL"
        assert SignalType.HOLD.value == "HOLD"

    def test_signal_status_enum(self):
        """Test SignalStatus enum values."""
        assert SignalStatus.ACTIVE.value == "ACTIVE"
        assert SignalStatus.EXECUTED.value == "EXECUTED"
        assert SignalStatus.EXPIRED.value == "EXPIRED"
        assert SignalStatus.CANCELLED.value == "CANCELLED"
