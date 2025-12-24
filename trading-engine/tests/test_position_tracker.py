"""Tests for PositionTracker and P&L calculation."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from engine.algo.position_tracker import PnLStats, PositionResult, PositionTracker
from engine.models.algo import AlgoPosition, PositionSide, PositionStatus


class TestPnLStats:
    """Tests for PnLStats dataclass."""

    def test_default_values(self):
        """Test default values are correctly set."""
        stats = PnLStats()
        assert stats.trades_closed == 0
        assert stats.winning_trades == 0
        assert stats.losing_trades == 0
        assert stats.total_pnl == Decimal("0")
        assert stats.consecutive_losses == 0

    def test_custom_values(self):
        """Test PnLStats with custom values."""
        stats = PnLStats(
            trades_closed=5,
            winning_trades=3,
            losing_trades=2,
            total_pnl=Decimal("1500.50"),
            consecutive_losses=1,
        )
        assert stats.trades_closed == 5
        assert stats.winning_trades == 3
        assert stats.losing_trades == 2
        assert stats.total_pnl == Decimal("1500.50")


class TestPositionResult:
    """Tests for PositionResult dataclass."""

    def test_open_position_result(self):
        """Test PositionResult for opened position."""
        result = PositionResult(
            position_id="pos-123",
            symbol="RELIANCE.NS",
            side="LONG",
            quantity=100,
            entry_price=Decimal("2500.00"),
        )
        assert result.position_id == "pos-123"
        assert result.symbol == "RELIANCE.NS"
        assert result.side == "LONG"
        assert result.quantity == 100
        assert result.entry_price == Decimal("2500.00")
        assert result.exit_price is None
        assert result.realized_pnl == Decimal("0")
        assert result.is_winner is None
        assert result.status == "OPEN"

    def test_closed_position_result(self):
        """Test PositionResult for closed position with P&L."""
        result = PositionResult(
            position_id="pos-456",
            symbol="TCS.NS",
            side="LONG",
            quantity=50,
            entry_price=Decimal("3500.00"),
            exit_price=Decimal("3650.00"),
            realized_pnl=Decimal("7500.00"),
            is_winner=True,
            status="CLOSED",
        )
        assert result.exit_price == Decimal("3650.00")
        assert result.realized_pnl == Decimal("7500.00")
        assert result.is_winner is True
        assert result.status == "CLOSED"


class TestPositionTrackerUnit:
    """Unit tests for PositionTracker (mocked database)."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def tracker(self, mock_db):
        """Create PositionTracker with mocked db."""
        return PositionTracker(mock_db)

    def test_long_pnl_calculation_profit(self):
        """Test P&L calculation for LONG position with profit."""
        entry_price = Decimal("100.00")
        exit_price = Decimal("110.00")
        quantity = 10

        # LONG P&L = (exit - entry) * qty
        expected_pnl = (exit_price - entry_price) * quantity
        assert expected_pnl == Decimal("100.00")

    def test_long_pnl_calculation_loss(self):
        """Test P&L calculation for LONG position with loss."""
        entry_price = Decimal("100.00")
        exit_price = Decimal("90.00")
        quantity = 10

        expected_pnl = (exit_price - entry_price) * quantity
        assert expected_pnl == Decimal("-100.00")

    def test_short_pnl_calculation_profit(self):
        """Test P&L calculation for SHORT position with profit."""
        entry_price = Decimal("100.00")
        exit_price = Decimal("90.00")
        quantity = 10

        # SHORT P&L = (entry - exit) * qty
        expected_pnl = (entry_price - exit_price) * quantity
        assert expected_pnl == Decimal("100.00")

    def test_short_pnl_calculation_loss(self):
        """Test P&L calculation for SHORT position with loss."""
        entry_price = Decimal("100.00")
        exit_price = Decimal("110.00")
        quantity = 10

        expected_pnl = (entry_price - exit_price) * quantity
        assert expected_pnl == Decimal("-100.00")

    async def test_open_position_new(self, tracker, mock_db):
        """Test opening a new position."""
        # Mock no existing position
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock refresh to set an id
        async def mock_refresh(pos):
            pos.id = "new-pos-id"

        mock_db.refresh.side_effect = mock_refresh

        result = await tracker.open_position(
            strategy_id="strat-1",
            user_id="user-1",
            symbol="INFY.NS",
            side="BUY",
            quantity=100,
            entry_price=Decimal("1500.00"),
        )

        assert result.symbol == "INFY.NS"
        assert result.side == "LONG"
        assert result.quantity == 100
        assert result.entry_price == Decimal("1500.00")
        assert result.status == "OPEN"
        mock_db.add.assert_called_once()

    async def test_open_position_adds_to_existing(self, tracker, mock_db):
        """Test opening adds to existing position (averaging)."""
        existing = MagicMock(spec=AlgoPosition)
        existing.id = "existing-pos"
        existing.remaining_quantity = 50
        existing.entry_price = Decimal("1400.00")
        existing.side = PositionSide.LONG

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        result = await tracker.open_position(
            strategy_id="strat-1",
            user_id="user-1",
            symbol="INFY.NS",
            side="BUY",
            quantity=50,  # Adding 50 more
            entry_price=Decimal("1600.00"),
        )

        # Should average: (50*1400 + 50*1600) / 100 = 1500
        assert result.position_id == "existing-pos"
        assert result.quantity == 100
        assert result.entry_price == Decimal("1500.00")

    async def test_close_position_profit(self, tracker, mock_db):
        """Test closing a LONG position with profit."""
        existing = MagicMock(spec=AlgoPosition)
        existing.id = "pos-to-close"
        existing.side = PositionSide.LONG
        existing.remaining_quantity = 100
        existing.entry_quantity = 100
        existing.entry_price = Decimal("1000.00")
        existing.realized_pnl = Decimal("0")
        existing.exit_quantity = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        result = await tracker.close_position(
            strategy_id="strat-1",
            user_id="user-1",
            symbol="RELIANCE.NS",
            quantity=None,  # Full close
            exit_price=Decimal("1100.00"),
        )

        assert result is not None
        assert result.realized_pnl == Decimal("10000.00")  # (1100-1000)*100
        assert result.is_winner is True
        assert existing.status == PositionStatus.CLOSED

    async def test_close_position_loss(self, tracker, mock_db):
        """Test closing a LONG position with loss."""
        existing = MagicMock(spec=AlgoPosition)
        existing.id = "pos-to-close"
        existing.side = PositionSide.LONG
        existing.remaining_quantity = 100
        existing.entry_quantity = 100
        existing.entry_price = Decimal("1000.00")
        existing.realized_pnl = Decimal("0")
        existing.exit_quantity = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        result = await tracker.close_position(
            strategy_id="strat-1",
            user_id="user-1",
            symbol="RELIANCE.NS",
            quantity=None,
            exit_price=Decimal("900.00"),
        )

        assert result is not None
        assert result.realized_pnl == Decimal("-10000.00")  # (900-1000)*100
        assert result.is_winner is False

    async def test_process_order_fill_opens_position(self, tracker, mock_db):
        """Test processing BUY fill opens a new LONG position."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        async def mock_refresh(pos):
            pos.id = "new-pos-id"

        mock_db.refresh.side_effect = mock_refresh

        result, stats = await tracker.process_order_fill(
            strategy_id="strat-1",
            user_id="user-1",
            symbol="TCS.NS",
            side="BUY",
            quantity=50,
            fill_price=Decimal("3500.00"),
        )

        assert result is not None
        assert result.side == "LONG"
        assert stats.trades_closed == 0  # No trades closed
        assert stats.total_pnl == Decimal("0")

    async def test_process_order_fill_closes_position(self, tracker, mock_db):
        """Test SELL fill closes an existing LONG position."""
        existing = MagicMock(spec=AlgoPosition)
        existing.id = "pos-to-close"
        existing.side = PositionSide.LONG
        existing.remaining_quantity = 100
        existing.entry_quantity = 100
        existing.entry_price = Decimal("3000.00")
        existing.realized_pnl = Decimal("0")
        existing.exit_quantity = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        result, stats = await tracker.process_order_fill(
            strategy_id="strat-1",
            user_id="user-1",
            symbol="TCS.NS",
            side="SELL",
            quantity=100,
            fill_price=Decimal("3200.00"),
        )

        assert result is not None
        assert stats.trades_closed == 1
        assert stats.winning_trades == 1
        assert stats.total_pnl == Decimal("20000.00")  # (3200-3000)*100


class TestSafetyService:
    """Tests for SafetyService basic checks."""

    def test_check_order_passes_valid_order(self):
        """Test that valid orders pass safety checks."""
        from engine.algo.safety import SafetyService

        service = SafetyService()
        result = service.check_order(
            symbol="RELIANCE.NS",
            side="BUY",
            quantity=100,
            price=Decimal("2500.00"),
        )

        assert result.passed is True

    def test_check_order_fails_blocked_symbol(self):
        """Test that blocked symbols are rejected."""
        from engine.algo.safety import SafetyService

        service = SafetyService(blocked_symbols=["BLOCKED.NS"])
        result = service.check_order(
            symbol="BLOCKED.NS",
            side="BUY",
            quantity=10,
            price=Decimal("100.00"),
        )

        assert result.passed is False
        assert "blocked" in result.reason.lower()

    def test_check_order_fails_max_quantity(self):
        """Test that orders exceeding max quantity are rejected."""
        from engine.algo.safety import SafetyService

        service = SafetyService(max_quantity=100)
        result = service.check_order(
            symbol="RELIANCE.NS",
            side="BUY",
            quantity=200,
            price=Decimal("100.00"),
        )

        assert result.passed is False
        assert "quantity" in result.reason.lower()

    def test_check_order_fails_max_order_value(self):
        """Test that orders exceeding max value are rejected."""
        from engine.algo.safety import SafetyService

        service = SafetyService(max_order_value=Decimal("100000"))
        result = service.check_order(
            symbol="RELIANCE.NS",
            side="BUY",
            quantity=100,
            price=Decimal("5000.00"),  # 500000 > 100000
        )

        assert result.passed is False
        assert "value" in result.reason.lower()
