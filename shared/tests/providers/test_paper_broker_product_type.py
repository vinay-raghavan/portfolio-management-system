"""Tests for PaperBroker product type validation.

These tests verify that PaperBroker correctly validates orders
based on product type (CNC/MIS/MTF) rules.
"""

from decimal import Decimal

import pytest

from shared.providers.broker.paper import PaperBroker
from shared.providers.schemas import (
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    ProductType,
)


class TestPaperBrokerProductTypeValidation:
    """Tests for product type validation in PaperBroker."""

    @pytest.fixture
    def broker(self):
        """Create PaperBroker instance with initial funds."""
        broker = PaperBroker(initial_balance=Decimal("100000"))
        return broker

    @pytest.fixture
    async def connected_broker(self, broker):
        """Create and connect a PaperBroker."""
        await broker.connect()
        broker._price_fetcher = lambda _: 1000.0  # Fixed price for testing
        return broker

    @pytest.mark.asyncio
    async def test_delivery_buy_requires_full_funds(self, connected_broker):
        """Test DELIVERY buy requires full order value."""
        broker = connected_broker
        broker._ensure_user("user1")

        # Try to buy more than available funds
        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=200,  # 200 * 1000 = 200000 > 100000 available
            product_type=ProductType.DELIVERY,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED
        assert "Insufficient funds" in response.message

    @pytest.mark.asyncio
    async def test_delivery_buy_succeeds_with_funds(self, connected_broker):
        """Test DELIVERY buy succeeds when funds are available."""
        broker = connected_broker
        broker._ensure_user("user1")

        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=50,  # 50 * 1000 = 50000 < 100000 available
            product_type=ProductType.DELIVERY,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_delivery_sell_without_position_rejected(self, connected_broker):
        """Test DELIVERY sell without owning shares is rejected (no naked shorting)."""
        broker = connected_broker
        broker._ensure_user("user1")

        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=10,
            product_type=ProductType.DELIVERY,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED
        assert "short sell" in response.message.lower()

    @pytest.mark.asyncio
    async def test_delivery_sell_with_position_succeeds(self, connected_broker):
        """Test DELIVERY sell succeeds when shares are owned."""
        broker = connected_broker
        broker._ensure_user("user1")

        # First buy some shares
        buy_order = OrderRequest(
            symbol="TEST",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
            product_type=ProductType.DELIVERY,
        )
        await broker.place_order("user1", buy_order)

        # Now sell them
        sell_order = OrderRequest(
            symbol="TEST",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=10,
            product_type=ProductType.DELIVERY,
        )
        response = await broker.place_order("user1", sell_order)
        assert response.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_intraday_short_sell_allowed_with_margin(self, connected_broker):
        """Test INTRADAY short sell is allowed when margin is available."""
        broker = connected_broker
        broker._ensure_user("user1")

        # Short sell with INTRADAY - should work with margin
        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=10,  # 10 * 1000 * 0.25 = 2500 margin required
            product_type=ProductType.INTRADAY,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_intraday_buy_uses_margin(self, connected_broker):
        """Test INTRADAY buy only requires margin, not full amount."""
        broker = connected_broker
        broker._ensure_user("user1")

        # Buy with INTRADAY - should allow larger position with margin
        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=200,  # 200 * 1000 * 0.25 = 50000 margin < 100000
            product_type=ProductType.INTRADAY,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_margin_mtf_no_short_selling(self, connected_broker):
        """Test MARGIN (MTF) does not allow short selling."""
        broker = connected_broker
        broker._ensure_user("user1")

        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=10,
            product_type=ProductType.MARGIN,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED
        assert "short sell" in response.message.lower()

    @pytest.mark.asyncio
    async def test_margin_mtf_buy_uses_50_percent_margin(self, connected_broker):
        """Test MARGIN (MTF) buy uses 50% margin."""
        broker = connected_broker
        broker._ensure_user("user1")

        # Buy with MARGIN - 50% margin required
        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=150,  # 150 * 1000 * 0.50 = 75000 margin < 100000
            product_type=ProductType.MARGIN,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_margin_mtf_buy_insufficient_margin(self, connected_broker):
        """Test MARGIN (MTF) buy fails with insufficient margin."""
        broker = connected_broker
        broker._ensure_user("user1")

        # Try to buy more than margin allows
        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=250,  # 250 * 1000 * 0.50 = 125000 margin > 100000
            product_type=ProductType.MARGIN,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED
        assert "margin" in response.message.lower()

    @pytest.mark.asyncio
    async def test_product_type_aliases_cnc(self, connected_broker):
        """Test CNC alias works like DELIVERY."""
        broker = connected_broker
        broker._ensure_user("user1")

        # CNC should behave like DELIVERY - no short selling
        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=10,
            product_type=ProductType.CNC,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.REJECTED

    @pytest.mark.asyncio
    async def test_product_type_aliases_mis(self, connected_broker):
        """Test MIS alias works like INTRADAY."""
        broker = connected_broker
        broker._ensure_user("user1")

        # MIS should behave like INTRADAY - short selling allowed
        order = OrderRequest(
            symbol="TEST",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=10,
            product_type=ProductType.MIS,
        )

        response = await broker.place_order("user1", order)
        assert response.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_partial_sell_allowed_in_delivery(self, connected_broker):
        """Test partial sell of owned shares is allowed in DELIVERY."""
        broker = connected_broker
        broker._ensure_user("user1")

        # Buy 20 shares
        buy_order = OrderRequest(
            symbol="TEST",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=20,
            product_type=ProductType.DELIVERY,
        )
        await broker.place_order("user1", buy_order)

        # Sell only 10 shares
        sell_order = OrderRequest(
            symbol="TEST",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=10,
            product_type=ProductType.DELIVERY,
        )
        response = await broker.place_order("user1", sell_order)
        assert response.status == OrderStatus.FILLED

        # Verify remaining position
        positions = await broker.get_positions("user1")
        assert len(positions) == 1
        assert positions[0].quantity == 10

    @pytest.mark.asyncio
    async def test_oversell_rejected_in_delivery(self, connected_broker):
        """Test selling more than owned is rejected in DELIVERY."""
        broker = connected_broker
        broker._ensure_user("user1")

        # Buy 10 shares
        buy_order = OrderRequest(
            symbol="TEST",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
            product_type=ProductType.DELIVERY,
        )
        await broker.place_order("user1", buy_order)

        # Try to sell 20 shares
        sell_order = OrderRequest(
            symbol="TEST",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=20,
            product_type=ProductType.DELIVERY,
        )
        response = await broker.place_order("user1", sell_order)
        assert response.status == OrderStatus.REJECTED
        assert "short sell" in response.message.lower()
