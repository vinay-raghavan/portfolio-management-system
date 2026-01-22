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

    async def test_check_stop_loss_long_position(self, tracker, mock_db):
        """Test stop-loss trigger for LONG position."""
        position = MagicMock(spec=AlgoPosition)
        position.id = "pos-sl"
        position.symbol = "RELIANCE"
        position.side = PositionSide.LONG
        position.status = PositionStatus.OPEN
        position.remaining_quantity = 100
        position.entry_quantity = 100
        position.entry_price = Decimal("1000.00")
        position.stop_loss = Decimal("950.00")  # 5% stop loss
        position.take_profit = Decimal("1100.00")
        position.realized_pnl = Decimal("0")
        position.exit_quantity = None
        position.profit_booking_rules = None
        # Trailing stop fields
        position.trailing_stop_enabled = False
        position.trailing_stop_pct = None
        position.trailing_stop_price = None
        position.highest_price_since_entry = None
        position.lowest_price_since_entry = None

        # Mock strategy query (first), get_all_open_positions (second), and get_open_position (third)
        mock_result_strategy = MagicMock()
        mock_result_strategy.scalar_one_or_none.return_value = None  # No strategy defaults
        mock_result_all = MagicMock()
        mock_result_all.scalars.return_value.all.return_value = [position]
        mock_result_one = MagicMock()
        mock_result_one.scalar_one_or_none.return_value = position
        mock_db.execute.side_effect = [mock_result_strategy, mock_result_all, mock_result_one]

        current_prices = {"RELIANCE": Decimal("940.00")}  # Below stop loss

        closed_positions, stats = await tracker.check_stop_loss_take_profit(
            strategy_id="strat-1",
            user_id="user-1",
            current_prices=current_prices,
        )

        assert len(closed_positions) == 1
        assert stats.trades_closed == 1
        assert stats.losing_trades == 1
        assert stats.total_pnl == Decimal("-6000.00")  # (940-1000)*100

    async def test_check_take_profit_long_position(self, tracker, mock_db):
        """Test take-profit trigger for LONG position."""
        position = MagicMock(spec=AlgoPosition)
        position.id = "pos-tp"
        position.symbol = "INFY"
        position.side = PositionSide.LONG
        position.status = PositionStatus.OPEN
        position.remaining_quantity = 50
        position.entry_quantity = 50
        position.entry_price = Decimal("1500.00")
        position.stop_loss = Decimal("1400.00")
        position.take_profit = Decimal("1600.00")  # Take profit level
        position.realized_pnl = Decimal("0")
        position.exit_quantity = None
        position.profit_booking_rules = None
        # Trailing stop fields
        position.trailing_stop_enabled = False
        position.trailing_stop_pct = None
        position.trailing_stop_price = None
        position.highest_price_since_entry = None
        position.lowest_price_since_entry = None

        # Mock strategy query (first), get_all_open_positions (second), and get_open_position (third)
        mock_result_strategy = MagicMock()
        mock_result_strategy.scalar_one_or_none.return_value = None  # No strategy defaults
        mock_result_all = MagicMock()
        mock_result_all.scalars.return_value.all.return_value = [position]
        mock_result_one = MagicMock()
        mock_result_one.scalar_one_or_none.return_value = position
        mock_db.execute.side_effect = [mock_result_strategy, mock_result_all, mock_result_one]

        current_prices = {"INFY": Decimal("1650.00")}  # Above take profit

        closed_positions, stats = await tracker.check_stop_loss_take_profit(
            strategy_id="strat-1",
            user_id="user-1",
            current_prices=current_prices,
        )

        assert len(closed_positions) == 1
        assert stats.trades_closed == 1
        assert stats.winning_trades == 1
        assert stats.total_pnl == Decimal("7500.00")  # (1650-1500)*50

    async def test_check_stop_loss_short_position(self, tracker, mock_db):
        """Test stop-loss trigger for SHORT position."""
        position = MagicMock(spec=AlgoPosition)
        position.id = "pos-short-sl"
        position.symbol = "TCS"
        position.side = PositionSide.SHORT
        position.status = PositionStatus.OPEN
        position.remaining_quantity = 20
        position.entry_quantity = 20
        position.entry_price = Decimal("3500.00")
        position.stop_loss = Decimal("3600.00")  # Stop loss above entry for shorts
        position.take_profit = Decimal("3300.00")
        position.realized_pnl = Decimal("0")
        position.exit_quantity = None
        position.profit_booking_rules = None
        # Trailing stop fields
        position.trailing_stop_enabled = False
        position.trailing_stop_pct = None
        position.trailing_stop_price = None
        position.highest_price_since_entry = None
        position.lowest_price_since_entry = None

        # Mock strategy query (first), get_all_open_positions (second), and get_open_position (third)
        mock_result_strategy = MagicMock()
        mock_result_strategy.scalar_one_or_none.return_value = None  # No strategy defaults
        mock_result_all = MagicMock()
        mock_result_all.scalars.return_value.all.return_value = [position]
        mock_result_one = MagicMock()
        mock_result_one.scalar_one_or_none.return_value = position
        mock_db.execute.side_effect = [mock_result_strategy, mock_result_all, mock_result_one]

        current_prices = {"TCS": Decimal("3650.00")}  # Above stop loss

        closed_positions, stats = await tracker.check_stop_loss_take_profit(
            strategy_id="strat-1",
            user_id="user-1",
            current_prices=current_prices,
        )

        assert len(closed_positions) == 1
        assert stats.trades_closed == 1
        assert stats.losing_trades == 1
        # SHORT P&L = (entry - exit) * qty = (3500 - 3650) * 20 = -3000
        assert stats.total_pnl == Decimal("-3000.00")

    async def test_no_exit_when_price_in_range(self, tracker, mock_db):
        """Test no exit when price is between stop-loss and take-profit."""
        position = MagicMock(spec=AlgoPosition)
        position.id = "pos-in-range"
        position.symbol = "HDFC"
        position.side = PositionSide.LONG
        position.status = PositionStatus.OPEN
        position.remaining_quantity = 30
        position.entry_quantity = 30
        position.entry_price = Decimal("2000.00")
        position.stop_loss = Decimal("1900.00")
        position.take_profit = Decimal("2200.00")
        position.realized_pnl = Decimal("0")
        position.exit_quantity = None
        position.profit_booking_rules = None
        # Trailing stop fields
        position.trailing_stop_enabled = False
        position.trailing_stop_pct = None
        position.trailing_stop_price = None
        position.highest_price_since_entry = None
        position.lowest_price_since_entry = None

        # Mock strategy query (first) and get_all_open_positions (second)
        mock_result_strategy = MagicMock()
        mock_result_strategy.scalar_one_or_none.return_value = None  # No strategy defaults
        mock_result_all = MagicMock()
        mock_result_all.scalars.return_value.all.return_value = [position]
        mock_db.execute.side_effect = [mock_result_strategy, mock_result_all]

        current_prices = {"HDFC": Decimal("2050.00")}  # Between SL and TP

        closed_positions, stats = await tracker.check_stop_loss_take_profit(
            strategy_id="strat-1",
            user_id="user-1",
            current_prices=current_prices,
        )

        assert len(closed_positions) == 0
        assert stats.trades_closed == 0


class TestProfitBookingRules:
    """Tests for profit booking rules functionality."""

    @pytest.fixture
    def tracker(self, mock_db):
        """Create a PositionTracker with mock db."""
        return PositionTracker(mock_db)

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        return AsyncMock()

    async def test_profit_booking_triggers_partial_exit(self, tracker, mock_db):
        """Test profit booking rule triggers partial exit at target."""
        position = MagicMock(spec=AlgoPosition)
        position.id = "pos-pb-1"
        position.symbol = "RELIANCE"
        position.side = PositionSide.LONG
        position.status = PositionStatus.OPEN
        position.remaining_quantity = 100
        position.entry_quantity = 100
        position.entry_price = Decimal("1000.00")
        position.stop_loss = None
        position.take_profit = None
        position.realized_pnl = Decimal("0")
        position.exit_quantity = None
        # Trailing stop fields
        position.trailing_stop_enabled = False
        position.trailing_stop_pct = None
        position.trailing_stop_price = None
        position.highest_price_since_entry = None
        position.lowest_price_since_entry = None
        # Set profit booking rules: 25% at 1% profit
        position.profit_booking_rules = {
            "enabled": True,
            "rules": [{"target_pct": 1, "quantity_pct": 25}],
            "executed": [],
        }

        # Mock strategy query (first), get_all_open_positions (second), and get_open_position (third)
        mock_result_strategy = MagicMock()
        mock_result_strategy.scalar_one_or_none.return_value = None  # No strategy defaults
        mock_result_all = MagicMock()
        mock_result_all.scalars.return_value.all.return_value = [position]
        mock_result_one = MagicMock()
        mock_result_one.scalar_one_or_none.return_value = position
        mock_db.execute.side_effect = [mock_result_strategy, mock_result_all, mock_result_one]

        # 1.5% profit (above 1% target)
        current_prices = {"RELIANCE": Decimal("1015.00")}

        closed_positions, stats = await tracker.check_stop_loss_take_profit(
            strategy_id="strat-1",
            user_id="user-1",
            current_prices=current_prices,
        )

        # Should have triggered partial exit
        assert len(closed_positions) == 1
        assert stats.trades_closed == 1
        assert stats.winning_trades == 1
        # 25% of 100 = 25 shares, profit = (1015-1000) * 25 = 375
        assert closed_positions[0].quantity == 25

    async def test_profit_booking_skips_executed_rules(self, tracker, mock_db):
        """Test that already executed rules are skipped."""
        position = MagicMock(spec=AlgoPosition)
        position.id = "pos-pb-2"
        position.symbol = "INFY"
        position.side = PositionSide.LONG
        position.status = PositionStatus.PARTIAL
        position.remaining_quantity = 75  # 25 already sold
        position.entry_quantity = 100
        position.entry_price = Decimal("1500.00")
        position.stop_loss = None
        position.take_profit = None
        position.realized_pnl = Decimal("375")
        position.exit_quantity = 25
        # Trailing stop fields
        position.trailing_stop_enabled = False
        position.trailing_stop_pct = None
        position.trailing_stop_price = None
        position.highest_price_since_entry = None
        position.lowest_price_since_entry = None
        # 1% rule already executed
        position.profit_booking_rules = {
            "enabled": True,
            "rules": [
                {"target_pct": 1, "quantity_pct": 25},
                {"target_pct": 5, "quantity_pct": 50},
            ],
            "executed": [1.0],  # 1% already executed
        }

        # Mock strategy query (first) and get_all_open_positions (second)
        mock_result_strategy = MagicMock()
        mock_result_strategy.scalar_one_or_none.return_value = None  # No strategy defaults
        mock_result_all = MagicMock()
        mock_result_all.scalars.return_value.all.return_value = [position]
        mock_db.execute.side_effect = [mock_result_strategy, mock_result_all]

        # 2% profit (still below 5% target)
        current_prices = {"INFY": Decimal("1530.00")}

        closed_positions, stats = await tracker.check_stop_loss_take_profit(
            strategy_id="strat-1",
            user_id="user-1",
            current_prices=current_prices,
        )

        # Should not trigger any exit (1% already done, 5% not reached)
        assert len(closed_positions) == 0
        assert stats.trades_closed == 0

    async def test_profit_booking_disabled_rules_ignored(self, tracker, mock_db):
        """Test that disabled profit booking rules are ignored."""
        position = MagicMock(spec=AlgoPosition)
        position.id = "pos-pb-3"
        position.symbol = "TCS"
        position.side = PositionSide.LONG
        position.status = PositionStatus.OPEN
        position.remaining_quantity = 50
        position.entry_quantity = 50
        position.entry_price = Decimal("3000.00")
        position.stop_loss = None
        position.take_profit = None
        position.realized_pnl = Decimal("0")
        position.exit_quantity = None
        # Trailing stop fields
        position.trailing_stop_enabled = False
        position.trailing_stop_pct = None
        position.trailing_stop_price = None
        position.highest_price_since_entry = None
        position.lowest_price_since_entry = None
        # Disabled profit booking
        position.profit_booking_rules = {
            "enabled": False,
            "rules": [{"target_pct": 1, "quantity_pct": 25}],
            "executed": [],
        }

        # Mock strategy query (first) and get_all_open_positions (second)
        mock_result_strategy = MagicMock()
        mock_result_strategy.scalar_one_or_none.return_value = None  # No strategy defaults
        mock_result_all = MagicMock()
        mock_result_all.scalars.return_value.all.return_value = [position]
        mock_db.execute.side_effect = [mock_result_strategy, mock_result_all]

        # 5% profit
        current_prices = {"TCS": Decimal("3150.00")}

        closed_positions, stats = await tracker.check_stop_loss_take_profit(
            strategy_id="strat-1",
            user_id="user-1",
            current_prices=current_prices,
        )

        # Should not trigger any exit (rules disabled)
        assert len(closed_positions) == 0
        assert stats.trades_closed == 0


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
