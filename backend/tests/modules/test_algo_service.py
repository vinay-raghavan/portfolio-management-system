"""Tests for algo trading service."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import (
    AlgoPosition,
    PositionSide,
    PositionSizingMethod,
    PositionStatus,
    ScheduleType,
    StrategyProductType,
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


class TestClosePosition:
    """Tests for close_position functionality."""

    @pytest.fixture
    def mock_position(self):
        """Create a mock open position."""
        position = MagicMock(spec=AlgoPosition)
        position.id = "test-position-id"
        position.user_id = "test-user-id"
        position.strategy_id = "test-strategy-id"
        position.symbol = "AAPL"
        position.side = PositionSide.LONG  # Use LONG not BUY
        position.status = PositionStatus.OPEN
        position.entry_quantity = Decimal("100")
        position.remaining_quantity = Decimal("100")
        position.entry_price = Decimal("150.00")
        position.exit_price = None
        position.realized_pnl = Decimal("0")
        position.realized_pnl_percent = Decimal("0")
        position.entry_at = datetime.now()
        position.exit_at = None
        return position

    @pytest.mark.asyncio
    async def test_close_position_full_quantity(self, mock_db, mock_position):
        """Test closing a position with full quantity."""
        # Mock get_open_position to return the mock position
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_position
        mock_db.execute.return_value = mock_result

        service = AlgoService(mock_db)

        # Patch get_open_position to return our mock
        with patch.object(service, "get_open_position", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_position

            result = await service.close_position(
                user_id="test-user-id",
                strategy_id="test-strategy-id",
                symbol="AAPL",
                exit_price=Decimal("160.00"),
            )

            assert result is not None
            assert result.symbol == "AAPL"
            assert result.closed_quantity == Decimal("100")
            assert result.remaining_quantity == Decimal("0")
            assert result.exit_price == Decimal("160.00")
            assert result.realized_pnl == Decimal("1000.00")  # (160 - 150) * 100
            assert result.is_winner is True
            assert result.status == "CLOSED"

    @pytest.mark.asyncio
    async def test_close_position_partial_quantity(self, mock_db, mock_position):
        """Test closing a position with partial quantity."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_position
        mock_db.execute.return_value = mock_result

        service = AlgoService(mock_db)

        with patch.object(service, "get_open_position", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_position

            result = await service.close_position(
                user_id="test-user-id",
                strategy_id="test-strategy-id",
                symbol="AAPL",
                exit_price=Decimal("160.00"),
                quantity=Decimal("50"),  # Only close half
            )

            assert result is not None
            assert result.closed_quantity == Decimal("50")
            assert result.remaining_quantity == Decimal("50")
            assert result.realized_pnl == Decimal("500.00")  # (160 - 150) * 50
            assert result.status == "PARTIAL"

    @pytest.mark.asyncio
    async def test_close_position_not_found(self, mock_db):
        """Test closing a position that doesn't exist."""
        service = AlgoService(mock_db)

        with patch.object(service, "get_open_position", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await service.close_position(
                user_id="test-user-id",
                strategy_id="test-strategy-id",
                symbol="AAPL",
                exit_price=Decimal("160.00"),
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_close_position_short_side(self, mock_db, mock_position):
        """Test closing a short position (SHORT side)."""
        mock_position.side = PositionSide.SHORT
        mock_position.entry_price = Decimal("160.00")

        service = AlgoService(mock_db)

        with patch.object(service, "get_open_position", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_position

            result = await service.close_position(
                user_id="test-user-id",
                strategy_id="test-strategy-id",
                symbol="AAPL",
                exit_price=Decimal("150.00"),  # Lower exit = profit for short
            )

            assert result is not None
            assert result.realized_pnl == Decimal("1000.00")  # (160 - 150) * 100
            assert result.is_winner is True


class TestSquareOffStrategy:
    """Tests for square_off_strategy functionality."""

    @pytest.fixture
    def mock_strategy(self):
        """Create a mock strategy."""
        strategy = MagicMock(spec=UserStrategy)
        strategy.id = "test-strategy-id"
        strategy.user_id = "test-user-id"
        strategy.name = "Test Strategy"
        strategy.product_type = StrategyProductType.DELIVERY
        return strategy

    @pytest.fixture
    def mock_positions(self):
        """Create mock open positions."""
        positions = []
        for i, symbol in enumerate(["AAPL", "GOOGL", "MSFT"]):
            position = MagicMock(spec=AlgoPosition)
            position.id = f"position-{i}"
            position.user_id = "test-user-id"
            position.strategy_id = "test-strategy-id"
            position.symbol = symbol
            position.side = PositionSide.LONG  # Use LONG not BUY
            position.status = PositionStatus.OPEN
            position.entry_quantity = Decimal("100")
            position.remaining_quantity = Decimal("100")
            position.entry_price = Decimal("100.00")
            position.exit_price = None
            position.realized_pnl = Decimal("0")
            positions.append(position)
        return positions

    @pytest.mark.asyncio
    async def test_square_off_strategy_success(self, mock_db, mock_strategy, mock_positions):
        """Test squaring off all positions for a strategy."""
        service = AlgoService(mock_db)

        # Mock the database result for open positions query
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_positions
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        with (
            patch.object(service, "get_strategy", new_callable=AsyncMock) as mock_get_strategy,
            patch.object(service, "close_position", new_callable=AsyncMock) as mock_close,
        ):
            # get_strategy now returns a tuple (strategy, executions)
            mock_get_strategy.return_value = (mock_strategy, [])
            # Set up the db.execute to return our mock result
            mock_db.execute.return_value = mock_result

            # Mock close_position to return realistic responses
            async def mock_close_position(
                user_id, strategy_id, symbol, exit_price, quantity=None, product_type=None
            ):
                from app.modules.algo.schemas import ClosePositionResponse

                return ClosePositionResponse(
                    position_id=f"position-{symbol}",
                    symbol=symbol,
                    side="LONG",
                    closed_quantity=Decimal("100"),
                    remaining_quantity=Decimal("0"),
                    entry_price=Decimal("100.00"),
                    exit_price=exit_price,
                    realized_pnl=Decimal("500.00"),
                    realized_pnl_percent=Decimal("5.00"),
                    is_winner=True,
                    status="CLOSED",
                    message=f"Closed {symbol}",
                )

            mock_close.side_effect = mock_close_position

            result = await service.square_off_strategy(
                user_id="test-user-id",
                strategy_id="test-strategy-id",
                exit_prices={
                    "AAPL": Decimal("105.00"),
                    "GOOGL": Decimal("105.00"),
                    "MSFT": Decimal("105.00"),
                },
            )

            assert result is not None
            assert result.strategy_id == "test-strategy-id"
            assert result.strategy_name == "Test Strategy"
            assert result.positions_closed == 3
            assert result.total_realized_pnl == Decimal("1500.00")  # 500 * 3
            assert len(result.closed_positions) == 3

    @pytest.mark.asyncio
    async def test_square_off_strategy_no_positions(self, mock_db, mock_strategy):
        """Test squaring off when there are no open positions."""
        service = AlgoService(mock_db)

        # Mock the database result for empty positions query
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        with patch.object(service, "get_strategy", new_callable=AsyncMock) as mock_get_strategy:
            # get_strategy now returns a tuple (strategy, executions)
            mock_get_strategy.return_value = (mock_strategy, [])
            mock_db.execute.return_value = mock_result

            result = await service.square_off_strategy(
                user_id="test-user-id",
                strategy_id="test-strategy-id",
            )

            assert result is not None
            assert result.positions_closed == 0
            assert result.total_realized_pnl == Decimal("0")
            assert "No open positions" in result.message

    @pytest.mark.asyncio
    async def test_square_off_strategy_not_found(self, mock_db):
        """Test squaring off when strategy doesn't exist."""
        service = AlgoService(mock_db)

        with patch.object(service, "get_strategy", new_callable=AsyncMock) as mock_get_strategy:
            # get_strategy returns tuple (strategy, executions) - None strategy means not found
            mock_get_strategy.return_value = (None, [])

            result = await service.square_off_strategy(
                user_id="test-user-id",
                strategy_id="nonexistent-strategy",
            )

            assert result is None
