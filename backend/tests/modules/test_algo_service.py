"""Tests for algo trading service."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import (
    PositionSizingMethod,
    ScheduleType,
    StrategyStatus,
    UserStrategy,
)
from app.modules.algo.schemas import StrategyCreate, StrategyUpdate
from app.modules.algo.service import AlgoService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def sample_strategy_create():
    """Create a sample strategy creation request."""
    return StrategyCreate(
        name="Test Strategy",
        strategy_type="momentum",
        strategy_config={"period": 14},
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=300,
        position_sizing_method=PositionSizingMethod.FIXED_QUANTITY,
        position_size_value=Decimal("10"),
        max_position_value=Decimal("100000"),
        max_daily_loss=Decimal("10000"),
        max_consecutive_losses=5,
    )


class TestAlgoService:
    """Tests for AlgoService."""

    @pytest.mark.asyncio
    async def test_create_strategy(self, mock_db, sample_strategy_create):
        """Test creating a new strategy."""
        service = AlgoService(mock_db)

        # Mock the refresh to set the id
        async def mock_refresh(obj):
            obj.id = "test-strategy-id"

        mock_db.refresh = mock_refresh

        strategy = await service.create_strategy(
            user_id="test-user-id",
            data=sample_strategy_create,
        )

        assert strategy.name == "Test Strategy"
        assert strategy.strategy_name == "momentum"
        assert strategy.user_id == "test-user-id"
        assert strategy.status == StrategyStatus.DISABLED
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_strategy(self, mock_db):
        """Test updating a strategy."""
        # Create a mock existing strategy
        existing_strategy = MagicMock()
        existing_strategy.id = "test-strategy-id"
        existing_strategy.user_id = "test-user-id"
        existing_strategy.name = "Old Name"
        existing_strategy.strategy_name = "momentum"
        existing_strategy.status = StrategyStatus.DISABLED

        # Mock get_strategy to return the existing strategy
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_strategy
        mock_db.execute.return_value = mock_result

        service = AlgoService(mock_db)

        update_data = StrategyUpdate(name="New Name")
        updated = await service.update_strategy(
            user_id="test-user-id",
            strategy_id="test-strategy-id",
            data=update_data,
        )

        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_strategy_status_values(self):
        """Test that strategy status enum has expected values."""
        assert StrategyStatus.ACTIVE.value == "ACTIVE"
        assert StrategyStatus.PAUSED.value == "PAUSED"
        assert StrategyStatus.DISABLED.value == "DISABLED"
        assert StrategyStatus.ERROR.value == "ERROR"

