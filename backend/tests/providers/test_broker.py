"""Tests for broker abstraction and implementations."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.broker.base import Broker
from app.providers.broker.paper import PaperBroker
from app.providers.broker.factory import BrokerFactory, get_broker
from app.providers.schemas import (
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderType,
    OrderStatus,
    Position,
    Funds,
)


class TestBrokerABC:
    """Tests for Broker abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that Broker cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Broker()


class TestPaperBroker:
    """Tests for paper trading broker."""

    @pytest.fixture
    def broker(self):
        """Create PaperBroker instance."""
        return PaperBroker()

    def test_broker_name(self, broker):
        """Test broker name."""
        assert broker.name == "paper"

    def test_is_paper(self, broker):
        """Test is_paper flag."""
        assert broker.is_paper is True

    @pytest.mark.asyncio
    async def test_connect(self, broker):
        """Test broker connection."""
        result = await broker.connect()
        assert result is True
        assert await broker.is_connected() is True

    @pytest.mark.asyncio
    async def test_disconnect(self, broker):
        """Test broker disconnection."""
        await broker.connect()
        await broker.disconnect()
        assert await broker.is_connected() is False

    @pytest.mark.asyncio
    async def test_get_funds_initial_balance(self, broker):
        """Test initial funds balance."""
        await broker.connect()
        funds = await broker.get_funds("user1")
        assert funds.available_cash > 0
        assert funds.total_balance == funds.available_cash  # No positions initially

    @pytest.mark.asyncio
    async def test_place_market_order_buy(self, broker):
        """Test placing a market buy order."""
        await broker.connect()

        # Mock the data provider to return a fixed price
        mock_provider = MagicMock()
        mock_provider.get_current_price = AsyncMock(return_value=150.00)
        broker._data_provider = mock_provider

        order = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED
        assert response.filled_quantity == 10
        assert response.filled_price == Decimal("150")
        assert response.fees > 0

    @pytest.mark.asyncio
    async def test_place_market_order_sell(self, broker):
        """Test placing a market sell order."""
        await broker.connect()

        # Mock the data provider
        mock_provider = MagicMock()
        mock_provider.get_current_price = AsyncMock(return_value=150.00)
        broker._data_provider = mock_provider

        # First buy
        buy_order = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        await broker.place_order("user1", buy_order)

        # Then sell
        mock_provider.get_current_price = AsyncMock(return_value=155.00)
        sell_order = OrderRequest(
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=5,
        )
        response = await broker.place_order("user1", sell_order)
        assert response.status == OrderStatus.FILLED
        assert response.filled_quantity == 5

    @pytest.mark.asyncio
    async def test_place_order_insufficient_funds(self, broker):
        """Test order rejection for insufficient funds."""
        await broker.connect()

        # Mock the data provider with high price
        mock_provider = MagicMock()
        mock_provider.get_current_price = AsyncMock(return_value=1000000.00)
        broker._data_provider = mock_provider

        order = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100000,  # Very large quantity
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED
        assert "insufficient" in response.message.lower()

    @pytest.mark.asyncio
    async def test_place_order_no_price(self, broker):
        """Test order rejection when price cannot be retrieved."""
        await broker.connect()

        # Mock the data provider to return None
        mock_provider = MagicMock()
        mock_provider.get_current_price = AsyncMock(return_value=None)
        broker._data_provider = mock_provider

        order = OrderRequest(
            symbol="INVALID",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED
        assert "price" in response.message.lower()

    @pytest.mark.asyncio
    async def test_get_positions_empty(self, broker):
        """Test getting positions when none exist."""
        await broker.connect()
        positions = await broker.get_positions("user1")
        assert positions == []

    @pytest.mark.asyncio
    async def test_get_positions_after_buy(self, broker):
        """Test positions after buying."""
        await broker.connect()

        # Mock the data provider
        mock_provider = MagicMock()
        mock_provider.get_current_price = AsyncMock(return_value=150.00)
        broker._data_provider = mock_provider

        order = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        await broker.place_order("user1", order)

        positions = await broker.get_positions("user1")
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == 10
        assert positions[0].avg_cost == Decimal("150")

