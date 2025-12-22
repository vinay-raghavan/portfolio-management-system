"""Tests for position sizing service."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.modules.algo.models import PositionSizingMethod
from app.modules.algo.position_sizer import PositionSizer
from app.providers.schemas import Funds


@pytest.fixture
def mock_funds():
    """Create mock funds."""
    return Funds(
        available_cash=Decimal("500000"),
        used_margin=Decimal("100000"),
        total_balance=Decimal("600000"),
    )


class TestPositionSizer:
    """Tests for PositionSizer."""

    def test_fixed_quantity(self, mock_funds):
        """Test fixed quantity position sizing."""
        sizer = PositionSizer()
        result = sizer.calculate(
            method=PositionSizingMethod.FIXED_QUANTITY,
            price=Decimal("2500"),
            funds=mock_funds,
            fixed_quantity=25,
        )

        assert result.quantity == 25
        assert result.method_used == PositionSizingMethod.FIXED_QUANTITY

    def test_fixed_amount(self, mock_funds):
        """Test fixed amount position sizing."""
        sizer = PositionSizer()
        result = sizer.calculate(
            method=PositionSizingMethod.FIXED_AMOUNT,
            price=Decimal("2500"),
            funds=mock_funds,
            fixed_amount=Decimal("50000"),
        )

        # 50000 / 2500 = 20
        assert result.quantity == 20
        assert result.method_used == PositionSizingMethod.FIXED_AMOUNT

    def test_fixed_amount_rounds_down(self, mock_funds):
        """Test fixed amount rounds down to whole shares."""
        sizer = PositionSizer()
        result = sizer.calculate(
            method=PositionSizingMethod.FIXED_AMOUNT,
            price=Decimal("2500"),
            funds=mock_funds,
            fixed_amount=Decimal("10000"),
        )

        # 10000 / 2500 = 4
        assert result.quantity == 4

    def test_max_position_value_limit(self, mock_funds):
        """Test max position value is enforced."""
        sizer = PositionSizer()
        result = sizer.calculate(
            method=PositionSizingMethod.FIXED_QUANTITY,
            price=Decimal("2500"),
            funds=mock_funds,
            fixed_quantity=200,
            max_position_value=Decimal("250000"),  # 100 shares max
        )

        # Should be capped at 100 shares (250000 / 2500)
        assert result.quantity == 100

    def test_zero_price_returns_zero(self, mock_funds):
        """Test zero price returns zero quantity."""
        sizer = PositionSizer()
        result = sizer.calculate(
            method=PositionSizingMethod.FIXED_AMOUNT,
            price=Decimal("0"),
            funds=mock_funds,
            fixed_amount=Decimal("50000"),
        )

        assert result.quantity == 0

    def test_minimum_quantity_one(self, mock_funds):
        """Test minimum quantity is 1 when amount allows."""
        sizer = PositionSizer()
        result = sizer.calculate(
            method=PositionSizingMethod.FIXED_AMOUNT,
            price=Decimal("2500"),
            funds=mock_funds,
            fixed_amount=Decimal("3000"),
        )

        # 3000 / 2500 = 1.2, rounds down to 1
        assert result.quantity == 1

    def test_insufficient_amount_returns_minimum(self, mock_funds):
        """Test insufficient amount returns minimum of 1 if any amount is provided."""
        sizer = PositionSizer()
        result = sizer.calculate(
            method=PositionSizingMethod.FIXED_AMOUNT,
            price=Decimal("2500"),
            funds=mock_funds,
            fixed_amount=Decimal("1000"),
        )

        # 1000 / 2500 = 0.4, but minimum is 1 if amount > 0
        # The implementation returns 1 as minimum
        assert result.quantity == 1

    def test_percentage_of_portfolio(self, mock_funds):
        """Test percentage of portfolio sizing."""
        sizer = PositionSizer()
        result = sizer.calculate(
            method=PositionSizingMethod.PERCENT_OF_PORTFOLIO,
            price=Decimal("2500"),
            funds=mock_funds,
            portfolio_percent=Decimal("10.0"),  # 10% of 600000 = 60000
        )

        # 60000 / 2500 = 24
        assert result.quantity == 24
        assert result.method_used == PositionSizingMethod.PERCENT_OF_PORTFOLIO

