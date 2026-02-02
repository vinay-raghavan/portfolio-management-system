"""Tests for AMO (After Market Orders) functionality."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import get_password_hash
from app.modules.auth.models import User
from app.modules.portfolio.models import UserFunds
from app.modules.trading.models import Order, OrderStatus
from app.modules.trading.schemas import OrderCreate, OrderSide, OrderType
from app.modules.trading.service import TradingService


class TestAMOOrders:
    """Tests for AMO order functionality."""

    @pytest.fixture
    async def test_user(self, db_session):
        """Create a test user."""
        user = User(
            email="amo_test@example.com",
            password_hash=get_password_hash("testpass123"),
            full_name="AMO Test User",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def test_user_with_funds(self, db_session, test_user):
        """Create a test user with funds."""
        funds = UserFunds(
            user_id=test_user.id,
            cash_balance=Decimal("1000000.00"),
            margin_used=Decimal("0"),
            collateral=Decimal("0"),
        )
        db_session.add(funds)
        await db_session.flush()
        return test_user

    @pytest.fixture
    def trading_service(self, db_session):
        """Create TradingService instance with validation skipped."""
        service = TradingService(db_session, skip_validation=True)
        return service

    async def test_amo_order_status_enum_exists(self):
        """Test that AMO_PENDING status exists in OrderStatus enum."""
        assert hasattr(OrderStatus, "AMO_PENDING")
        assert OrderStatus.AMO_PENDING.value == "AMO_PENDING"

    async def test_order_create_schema_has_is_amo_field(self):
        """Test that OrderCreate schema has is_amo field."""
        order_data = OrderCreate(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10"),
            is_amo=True,
        )
        assert order_data.is_amo is True

    async def test_order_create_schema_is_amo_defaults_to_false(self):
        """Test that is_amo defaults to False."""
        order_data = OrderCreate(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10"),
        )
        assert order_data.is_amo is False

    async def test_create_amo_order_when_market_closed(
        self, trading_service, test_user_with_funds, db_session
    ):
        """Test creating AMO order when market is closed queues as AMO_PENDING."""
        order_data = OrderCreate(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10"),
            price=Decimal("2500.00"),
            is_amo=True,
        )

        # Mock market as closed
        with patch("app.modules.trading.service.get_data_provider") as mock_provider:
            mock_data_provider = MagicMock()
            mock_data_provider.is_market_open = AsyncMock(return_value=False)
            mock_data_provider.get_next_market_open = MagicMock(
                return_value=datetime(2025, 12, 23, 9, 15, tzinfo=UTC)
            )
            mock_provider.return_value = mock_data_provider

            order = await trading_service.create_order(test_user_with_funds.id, order_data)

        assert order.status == OrderStatus.AMO_PENDING.value
        assert order.is_amo is True
        assert order.symbol == "RELIANCE"

    async def test_create_amo_order_when_market_open_executes_immediately(
        self, trading_service, test_user_with_funds, db_session
    ):
        """Test AMO order placed during market hours executes immediately."""
        order_data = OrderCreate(
            symbol="TCS",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("5"),
            price=Decimal("3500.00"),
            is_amo=True,
        )

        # Mock market as open
        with patch("app.modules.trading.service.get_data_provider") as mock_provider:
            mock_data_provider = MagicMock()
            mock_data_provider.is_market_open = AsyncMock(return_value=True)
            mock_provider.return_value = mock_data_provider

            order = await trading_service.create_order(test_user_with_funds.id, order_data)

        # Should be PENDING (not AMO_PENDING) since market is open
        assert order.status == OrderStatus.PENDING.value
        # is_amo should be False since it was executed immediately
        assert order.is_amo is False

    async def test_get_pending_amo_orders(self, trading_service, test_user_with_funds, db_session):
        """Test retrieving pending AMO orders."""
        # Create an AMO pending order directly
        amo_order = Order(
            user_id=test_user_with_funds.id,
            symbol="INFY",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("15"),
            price=Decimal("1500.00"),
            status=OrderStatus.AMO_PENDING.value,
            is_amo=True,
            scheduled_for=datetime(2025, 12, 23, 9, 15, tzinfo=UTC),
        )
        db_session.add(amo_order)
        await db_session.flush()

        # Retrieve AMO orders
        amo_orders = await trading_service.get_pending_amo_orders(test_user_with_funds.id)

        assert len(amo_orders) == 1
        assert amo_orders[0].symbol == "INFY"
        assert amo_orders[0].is_amo is True

    async def test_cancel_amo_pending_order(
        self, trading_service, test_user_with_funds, db_session
    ):
        """Test that AMO pending orders can be cancelled."""
        # Create an AMO pending order
        amo_order = Order(
            user_id=test_user_with_funds.id,
            symbol="HDFC",
            side="BUY",
            order_type="LIMIT",
            quantity=Decimal("20"),
            price=Decimal("1600.00"),
            status=OrderStatus.AMO_PENDING.value,
            is_amo=True,
        )
        db_session.add(amo_order)
        await db_session.flush()
        await db_session.refresh(amo_order)

        # Cancel the AMO order
        cancelled = await trading_service.cancel_order(test_user_with_funds.id, str(amo_order.id))

        assert cancelled is not None
        assert cancelled.status == OrderStatus.CANCELLED.value

    async def test_get_pending_amo_orders_all_users(
        self, trading_service, test_user_with_funds, db_session
    ):
        """Test retrieving all pending AMO orders (no user filter)."""
        # Create AMO orders for the user
        order1 = Order(
            user_id=test_user_with_funds.id,
            symbol="SBIN",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("50"),
            status=OrderStatus.AMO_PENDING.value,
            is_amo=True,
        )
        order2 = Order(
            user_id=test_user_with_funds.id,
            symbol="ICICI",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("30"),
            status=OrderStatus.AMO_PENDING.value,
            is_amo=True,
        )
        db_session.add_all([order1, order2])
        await db_session.flush()

        # Get all AMO orders (no user filter)
        all_amo_orders = await trading_service.get_pending_amo_orders()

        assert len(all_amo_orders) == 2

    async def test_process_amo_order_updates_status(
        self, trading_service, test_user_with_funds, db_session
    ):
        """Test processing AMO order updates its status."""
        # Create an AMO pending order
        amo_order = Order(
            user_id=test_user_with_funds.id,
            symbol="WIPRO",
            side="BUY",
            order_type="LIMIT",  # Limit order won't execute immediately
            quantity=Decimal("25"),
            price=Decimal("450.00"),
            status=OrderStatus.AMO_PENDING.value,
            is_amo=True,
        )
        db_session.add(amo_order)
        await db_session.flush()
        await db_session.refresh(amo_order)

        # Process the AMO order
        processed = await trading_service.process_amo_order(amo_order)

        # Should be PENDING now (not AMO_PENDING), waiting for limit fill
        assert processed.status == OrderStatus.PENDING.value
        assert "[AMO] Processed at market open" in (processed.notes or "")

    async def test_process_all_amo_orders_when_market_closed(self, trading_service, db_session):
        """Test that AMO processing is skipped when market is closed."""
        with patch("app.modules.trading.service.get_data_provider") as mock_provider:
            mock_data_provider = MagicMock()
            mock_data_provider.is_market_open = AsyncMock(return_value=False)
            mock_provider.return_value = mock_data_provider

            result = await trading_service.process_all_amo_orders()

        assert result["status"] == "market_closed"
        assert result["processed"] == 0

    async def test_order_model_has_amo_fields(self, db_session, test_user_with_funds):
        """Test that Order model has is_amo and scheduled_for fields."""
        scheduled_time = datetime(2025, 12, 23, 9, 15, tzinfo=UTC)
        order = Order(
            user_id=test_user_with_funds.id,
            symbol="AXISBANK",
            side="SELL",
            order_type="MARKET",
            quantity=Decimal("10"),
            status=OrderStatus.AMO_PENDING.value,
            is_amo=True,
            scheduled_for=scheduled_time,
        )
        db_session.add(order)
        await db_session.flush()
        await db_session.refresh(order)

        assert order.is_amo is True
        # Compare without timezone (SQLite doesn't preserve timezone info)
        assert order.scheduled_for is not None
        assert order.scheduled_for.year == 2025
        assert order.scheduled_for.month == 12
        assert order.scheduled_for.day == 23
        assert order.scheduled_for.hour == 9
        assert order.scheduled_for.minute == 15
