"""Tests for algo trading P&L endpoints and service methods."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import (
    AlgoPosition,
    PositionSide,
    PositionStatus,
    StrategyStatus,
    UserStrategy,
)
from app.modules.algo.schemas import PnLSummary, PositionResponse, StrategyPnL
from app.modules.algo.service import AlgoService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def sample_positions():
    """Create sample AlgoPosition objects for testing."""
    now = datetime.now(timezone.utc)
    
    pos1 = MagicMock(spec=AlgoPosition)
    pos1.id = "pos-1"
    pos1.strategy_id = "strat-1"
    pos1.user_id = "user-1"
    pos1.symbol = "RELIANCE"
    pos1.side = PositionSide.LONG
    pos1.status = PositionStatus.CLOSED
    pos1.entry_quantity = 100
    pos1.entry_price = Decimal("1500.00")
    pos1.entry_at = now
    pos1.exit_quantity = 100
    pos1.exit_price = Decimal("1600.00")
    pos1.exit_at = now
    pos1.remaining_quantity = 0
    pos1.realized_pnl = Decimal("10000.00")
    pos1.realized_pnl_percent = Decimal("6.67")
    pos1.is_winner = True
    pos1.stop_loss = Decimal("1450.00")
    pos1.take_profit = Decimal("1650.00")
    pos1.created_at = now
    pos1.updated_at = now

    pos2 = MagicMock(spec=AlgoPosition)
    pos2.id = "pos-2"
    pos2.strategy_id = "strat-1"
    pos2.user_id = "user-1"
    pos2.symbol = "TCS"
    pos2.side = PositionSide.LONG
    pos2.status = PositionStatus.OPEN
    pos2.entry_quantity = 50
    pos2.entry_price = Decimal("3500.00")
    pos2.entry_at = now
    pos2.exit_quantity = None
    pos2.exit_price = None
    pos2.exit_at = None
    pos2.remaining_quantity = 50
    pos2.realized_pnl = Decimal("0")
    pos2.realized_pnl_percent = Decimal("0")
    pos2.is_winner = None
    pos2.stop_loss = Decimal("3400.00")
    pos2.take_profit = Decimal("3700.00")
    pos2.created_at = now
    pos2.updated_at = now

    pos3 = MagicMock(spec=AlgoPosition)
    pos3.id = "pos-3"
    pos3.strategy_id = "strat-2"
    pos3.user_id = "user-1"
    pos3.symbol = "INFY"
    pos3.side = PositionSide.LONG
    pos3.status = PositionStatus.CLOSED
    pos3.entry_quantity = 200
    pos3.entry_price = Decimal("1400.00")
    pos3.entry_at = now
    pos3.exit_quantity = 200
    pos3.exit_price = Decimal("1350.00")
    pos3.exit_at = now
    pos3.remaining_quantity = 0
    pos3.realized_pnl = Decimal("-10000.00")
    pos3.realized_pnl_percent = Decimal("-3.57")
    pos3.is_winner = False
    pos3.stop_loss = None
    pos3.take_profit = None
    pos3.created_at = now
    pos3.updated_at = now

    return [pos1, pos2, pos3]


@pytest.fixture
def sample_strategies():
    """Create sample UserStrategy objects for testing."""
    strat1 = MagicMock(spec=UserStrategy)
    strat1.id = "strat-1"
    strat1.name = "RSI Strategy"
    strat1.status = StrategyStatus.ACTIVE

    strat2 = MagicMock(spec=UserStrategy)
    strat2.id = "strat-2"
    strat2.name = "MACD Strategy"
    strat2.status = StrategyStatus.DISABLED

    return [strat1, strat2]


class TestAlgoPnLService:
    """Tests for P&L-related service methods."""

    @pytest.mark.asyncio
    async def test_get_positions_returns_all_positions(self, mock_db, sample_positions):
        """Test get_positions returns all positions for a user."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_positions
        mock_db.execute.return_value = mock_result

        service = AlgoService(mock_db)
        positions = await service.get_positions("user-1")

        assert len(positions) == 3
        assert all(isinstance(p, PositionResponse) for p in positions)
        assert positions[0].symbol == "RELIANCE"
        assert positions[1].symbol == "TCS"
        assert positions[2].symbol == "INFY"

    @pytest.mark.asyncio
    async def test_get_positions_filter_by_status(self, mock_db, sample_positions):
        """Test get_positions filters by status correctly."""
        # Filter to only OPEN positions
        open_positions = [p for p in sample_positions if p.status == PositionStatus.OPEN]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = open_positions
        mock_db.execute.return_value = mock_result

        service = AlgoService(mock_db)
        positions = await service.get_positions("user-1", status="OPEN")

        assert len(positions) == 1
        assert positions[0].status == "OPEN"
        assert positions[0].symbol == "TCS"

    @pytest.mark.asyncio
    async def test_get_pnl_summary_calculates_correctly(self, mock_db, sample_positions):
        """Test get_pnl_summary calculates metrics correctly."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_positions
        mock_db.execute.return_value = mock_result

        service = AlgoService(mock_db)
        summary = await service.get_pnl_summary("user-1")

        assert isinstance(summary, PnLSummary)
        # 10000 - 10000 = 0 total realized P&L
        assert summary.total_realized_pnl == Decimal("0")
        assert summary.total_trades == 2  # 2 closed positions
        assert summary.winning_trades == 1
        assert summary.losing_trades == 1
        assert summary.win_rate == Decimal("50")  # 1 win / 2 trades * 100
        assert summary.open_positions == 1
        assert summary.closed_positions == 2
        assert summary.best_trade_pnl == Decimal("10000.00")
        assert summary.worst_trade_pnl == Decimal("-10000.00")

    @pytest.mark.asyncio
    async def test_get_pnl_summary_empty_positions(self, mock_db):
        """Test get_pnl_summary returns empty summary when no positions."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = AlgoService(mock_db)
        summary = await service.get_pnl_summary("user-1")

        assert summary.total_realized_pnl == Decimal("0")
        assert summary.total_trades == 0
        assert summary.open_positions == 0

    @pytest.mark.asyncio
    async def test_get_pnl_by_strategy(self, mock_db, sample_positions, sample_strategies):
        """Test get_pnl_by_strategy groups positions correctly."""
        # Mock strategies query
        strat_result = MagicMock()
        strat_result.scalars.return_value.all.return_value = sample_strategies

        # Mock positions query
        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = sample_positions

        mock_db.execute.side_effect = [strat_result, pos_result]

        service = AlgoService(mock_db)
        result = await service.get_pnl_by_strategy("user-1")

        assert len(result.strategies) == 2

        # Find the RSI Strategy (strat-1)
        rsi_strat = next(s for s in result.strategies if s.strategy_id == "strat-1")
        assert rsi_strat.strategy_name == "RSI Strategy"
        assert rsi_strat.realized_pnl == Decimal("10000.00")
        assert rsi_strat.open_positions == 1
        assert rsi_strat.closed_positions == 1

        # Find the MACD Strategy (strat-2)
        macd_strat = next(s for s in result.strategies if s.strategy_id == "strat-2")
        assert macd_strat.strategy_name == "MACD Strategy"
        assert macd_strat.realized_pnl == Decimal("-10000.00")
        assert macd_strat.closed_positions == 1


class TestAlgoPnLAPI:
    """Tests for P&L API endpoints."""

    @pytest.mark.asyncio
    async def test_positions_endpoint_requires_auth(self, client):
        """Test that positions endpoint requires authentication."""
        response = await client.get("/api/v1/algo/positions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_pnl_summary_endpoint_requires_auth(self, client):
        """Test that P&L summary endpoint requires authentication."""
        response = await client.get("/api/v1/algo/pnl/summary")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_pnl_by_strategy_endpoint_requires_auth(self, client):
        """Test that P&L by strategy endpoint requires authentication."""
        response = await client.get("/api/v1/algo/pnl/by-strategy")
        assert response.status_code == 401


class TestPositionModels:
    """Tests for position-related models and enums."""

    def test_position_side_enum(self):
        """Test PositionSide enum values."""
        assert PositionSide.LONG.value == "LONG"
        assert PositionSide.SHORT.value == "SHORT"

    def test_position_status_enum(self):
        """Test PositionStatus enum values."""
        assert PositionStatus.OPEN.value == "OPEN"
        assert PositionStatus.CLOSED.value == "CLOSED"
        assert PositionStatus.PARTIAL.value == "PARTIAL"

