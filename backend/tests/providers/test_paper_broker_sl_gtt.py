"""Tests for Paper Broker SL/SL-M and GTT order types."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.providers.broker.paper import PaperBroker
from app.providers.schemas import (
    OrderRequest,
    OrderSide,
    OrderType,
    OrderStatus,
)


class TestPaperBrokerStopLossOrders:
    """Tests for Stop Loss and Stop Loss Market orders."""

    @pytest.fixture
    def broker(self):
        """Create PaperBroker instance with mocked data provider."""
        broker = PaperBroker()
        mock_provider = MagicMock()
        mock_provider.get_current_price = AsyncMock(return_value=100.00)
        broker._data_provider = mock_provider
        broker._connected = True
        return broker

    @pytest.mark.asyncio
    async def test_sl_order_requires_trigger_price(self, broker):
        """Test that SL orders require a trigger price."""
        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            price=Decimal("95"),
            # No trigger_price
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED
        assert "trigger price" in response.message.lower()

    @pytest.mark.asyncio
    async def test_slm_order_requires_trigger_price(self, broker):
        """Test that SL-M orders require a trigger price."""
        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS_MARKET,
            quantity=10,
            # No trigger_price
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED
        assert "trigger price" in response.message.lower()

    @pytest.mark.asyncio
    async def test_sl_order_not_triggered_stays_pending(self, broker):
        """Test that SL order stays pending when trigger not hit."""
        # Current price is 100, trigger at 90 for SELL
        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            price=Decimal("89"),
            trigger_price=Decimal("90"),
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.OPEN
        assert "90" in response.message

    @pytest.mark.asyncio
    async def test_sl_order_triggered_executes(self, broker):
        """Test that SL order executes when trigger is hit."""
        # Set current price at trigger level
        broker._data_provider.get_current_price = AsyncMock(return_value=89.00)

        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            price=Decimal("88"),
            trigger_price=Decimal("90"),  # Price is below trigger, so triggers
        )

        # First need a position to sell
        broker._ensure_user("user1")
        from app.providers.schemas import Position
        broker._positions["user1"]["RELIANCE"] = Position(
            symbol="RELIANCE",
            quantity=Decimal("20"),
            avg_cost=Decimal("100"),
            current_price=Decimal("89"),
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED
        assert response.filled_price == Decimal("88")  # SL executes at limit price

    @pytest.mark.asyncio
    async def test_slm_order_triggered_executes_at_market(self, broker):
        """Test that SL-M order executes at market price when triggered."""
        broker._data_provider.get_current_price = AsyncMock(return_value=85.00)

        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS_MARKET,
            quantity=10,
            trigger_price=Decimal("90"),
        )

        # First need a position to sell
        broker._ensure_user("user1")
        from app.providers.schemas import Position
        broker._positions["user1"]["RELIANCE"] = Position(
            symbol="RELIANCE",
            quantity=Decimal("20"),
            avg_cost=Decimal("100"),
            current_price=Decimal("85"),
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED
        assert response.filled_price == Decimal("85")  # SL-M executes at market

    @pytest.mark.asyncio
    async def test_buy_sl_order_trigger_condition(self, broker):
        """Test BUY SL order triggers when price goes up."""
        # For BUY SL, triggers when price >= trigger_price
        broker._data_provider.get_current_price = AsyncMock(return_value=110.00)

        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            price=Decimal("112"),
            trigger_price=Decimal("105"),  # Price is above trigger
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED


class TestPaperBrokerGTTOrders:
    """Tests for Good Till Triggered orders."""

    @pytest.fixture
    def broker(self):
        """Create PaperBroker instance with mocked data provider."""
        broker = PaperBroker()
        mock_provider = MagicMock()
        mock_provider.get_current_price = AsyncMock(return_value=100.00)
        broker._data_provider = mock_provider
        broker._connected = True
        return broker

    @pytest.mark.asyncio
    async def test_gtt_order_requires_trigger_price(self, broker):
        """Test that GTT orders require a trigger price."""
        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            order_type=OrderType.GTT,
            quantity=10,
            price=Decimal("95"),
            # No trigger_price
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED
        assert "trigger price" in response.message.lower()

    @pytest.mark.asyncio
    async def test_gtt_order_not_triggered_stays_pending(self, broker):
        """Test that GTT order stays pending when trigger not hit."""
        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            order_type=OrderType.GTT,
            quantity=10,
            price=Decimal("90"),
            trigger_price=Decimal("105"),  # Current is 100, needs to go up
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.OPEN
        assert "GTT" in response.message
        assert "105" in response.message

    @pytest.mark.asyncio
    async def test_gtt_order_triggered_executes(self, broker):
        """Test that GTT order executes when trigger is hit."""
        broker._data_provider.get_current_price = AsyncMock(return_value=110.00)

        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            order_type=OrderType.GTT,
            quantity=10,
            price=Decimal("108"),
            trigger_price=Decimal("105"),
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED
        assert response.filled_quantity == 10

    @pytest.mark.asyncio
    async def test_pending_trigger_orders_list(self, broker):
        """Test getting list of pending trigger orders."""
        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            price=Decimal("95"),
            trigger_price=Decimal("105"),
        )

        await broker.place_order("user1", order)
        pending = await broker.get_pending_trigger_orders("user1")

        assert len(pending) == 1
        assert pending[0].symbol == "RELIANCE"
        assert pending[0].status == OrderStatus.OPEN


class TestPaperBrokerTriggerCheck:
    """Tests for checking and executing triggered orders."""

    @pytest.fixture
    def broker(self):
        """Create PaperBroker instance with mocked data provider."""
        broker = PaperBroker()
        mock_provider = MagicMock()
        mock_provider.get_current_price = AsyncMock(return_value=100.00)
        broker._data_provider = mock_provider
        broker._connected = True
        return broker

    @pytest.mark.asyncio
    async def test_check_trigger_orders_executes_when_condition_met(self, broker):
        """Test that check_trigger_orders executes orders when conditions are met."""
        # Place SL order that's not triggered yet
        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            price=Decimal("88"),
            trigger_price=Decimal("90"),
        )

        # First need a position to sell
        broker._ensure_user("user1")
        from app.providers.schemas import Position
        broker._positions["user1"]["RELIANCE"] = Position(
            symbol="RELIANCE",
            quantity=Decimal("20"),
            avg_cost=Decimal("100"),
            current_price=Decimal("100"),
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.OPEN

        # Now price drops below trigger
        broker._data_provider.get_current_price = AsyncMock(return_value=85.00)

        executed = await broker.check_trigger_orders("user1")
        assert len(executed) == 1
        assert executed[0].status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_check_trigger_orders_no_execution_when_not_triggered(self, broker):
        """Test that check_trigger_orders doesn't execute when conditions aren't met."""
        order = OrderRequest(
            symbol="RELIANCE",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LOSS,
            quantity=10,
            price=Decimal("88"),
            trigger_price=Decimal("90"),
        )

        broker._ensure_user("user1")
        from app.providers.schemas import Position
        broker._positions["user1"]["RELIANCE"] = Position(
            symbol="RELIANCE",
            quantity=Decimal("20"),
            avg_cost=Decimal("100"),
            current_price=Decimal("100"),
        )

        await broker.place_order("user1", order)

        # Price stays above trigger
        broker._data_provider.get_current_price = AsyncMock(return_value=95.00)

        executed = await broker.check_trigger_orders("user1")
        assert len(executed) == 0

    @pytest.mark.asyncio
    async def test_extract_trigger_price(self, broker):
        """Test extracting trigger price from order message."""
        assert broker._extract_trigger_price("Trigger price: 100.50") == Decimal("100.50")
        assert broker._extract_trigger_price("GTT: Trigger at 150, Valid till: 2025-12-31") == Decimal("150")
        assert broker._extract_trigger_price(None) is None
        assert broker._extract_trigger_price("No trigger info") is None

