"""Tests for DatabaseFundsProvider.

These tests verify that the shared DatabaseFundsProvider correctly
manages user funds for paper trading.

We mock _get_or_create_funds since DatabaseFundsProvider uses SQLAlchemy
select() which requires a proper SQLAlchemy model.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared.providers.funds import DatabaseFundsProvider
from shared.providers.schemas import Funds


class MockUserFunds:
    """Mock UserFunds model for testing."""

    def __init__(
        self,
        user_id: str = "",
        cash_balance: Decimal = Decimal("1000000"),
        margin_used: Decimal = Decimal("0"),
        collateral: Decimal = Decimal("0"),
        realized_pnl: Decimal = Decimal("0"),
        unrealized_pnl: Decimal = Decimal("0"),
        **kwargs,
    ):
        self.id = kwargs.get("id", str(uuid4()))
        self.user_id = user_id
        self.cash_balance = cash_balance
        self.margin_used = margin_used
        self.collateral = collateral
        self.realized_pnl = realized_pnl
        self.unrealized_pnl = unrealized_pnl

    @property
    def available_cash(self) -> Decimal:
        return self.cash_balance - self.margin_used

    @property
    def total_balance(self) -> Decimal:
        return self.cash_balance + self.collateral


def create_provider() -> DatabaseFundsProvider:
    """Create a DatabaseFundsProvider with mocked dependencies."""
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
    return DatabaseFundsProvider(
        db=mock_db,
        user_funds_model=MagicMock(),  # Won't be used since we mock internal methods
        initial_balance=Decimal("1000000"),
    )


class TestDatabaseFundsProvider:
    """Tests for DatabaseFundsProvider class."""

    @pytest.mark.asyncio
    async def test_get_funds_existing_user(self):
        """Test getting funds for an existing user."""
        user_id = str(uuid4())
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=Decimal("500000"),
            margin_used=Decimal("50000"),
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            funds = await provider.get_funds(user_id)

        assert isinstance(funds, Funds)
        assert funds.available_cash == Decimal("450000")  # 500000 - 50000
        assert funds.used_margin == Decimal("50000")
        assert funds.total_balance == Decimal("550000")  # 500000 + 50000

    @pytest.mark.asyncio
    async def test_get_funds_new_user_creates_funds(self):
        """Test that getting funds for a new user creates initial funds."""
        user_id = str(uuid4())
        new_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=Decimal("1000000"),
            margin_used=Decimal("0"),
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=new_funds):
            funds = await provider.get_funds(user_id)

        assert isinstance(funds, Funds)
        assert funds.available_cash == Decimal("1000000")

    @pytest.mark.asyncio
    async def test_update_funds_for_buy_trade(self):
        """Test that BUY trade deducts from cash balance."""
        user_id = str(uuid4())
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=Decimal("100000"),
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            funds = await provider.update_funds_for_trade(
                user_id=user_id,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("1000"),
                fees=Decimal("10"),
            )

        # Should deduct 10*1000 + 10 = 10010
        assert existing_funds.cash_balance == Decimal("89990")
        assert funds.available_cash == Decimal("89990")

    @pytest.mark.asyncio
    async def test_update_funds_for_sell_trade(self):
        """Test that SELL trade adds to cash balance when closing a position."""
        user_id = str(uuid4())
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=Decimal("50000"),
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            funds = await provider.update_funds_for_trade(
                user_id=user_id,
                side="SELL",
                quantity=Decimal("10"),
                price=Decimal("1100"),
                fees=Decimal("10"),
                existing_position_qty=Decimal("10"),  # Owns 10 shares
            )

        # Should add 10*1100 - 10 = 10990
        assert existing_funds.cash_balance == Decimal("60990")
        assert funds.available_cash == Decimal("60990")

    @pytest.mark.asyncio
    async def test_update_funds_insufficient_funds_raises_error(self):
        """Test that BUY with insufficient funds raises ValueError."""
        user_id = str(uuid4())
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=Decimal("1000"),  # Only 1000 available
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            # Try to buy 10 shares at 1000 each = 10000 (more than available)
            with pytest.raises(ValueError, match="Insufficient funds"):
                await provider.update_funds_for_trade(
                    user_id=user_id,
                    side="BUY",
                    quantity=Decimal("10"),
                    price=Decimal("1000"),
                    fees=Decimal("0"),
                )

    @pytest.mark.asyncio
    async def test_check_buying_power_sufficient(self):
        """Test check_buying_power returns True when funds are sufficient."""
        user_id = str(uuid4())
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=Decimal("100000"),
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            result = await provider.check_buying_power(
                user_id=user_id,
                required_amount=Decimal("50000"),
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_buying_power_insufficient(self):
        """Test check_buying_power returns False when funds are insufficient."""
        user_id = str(uuid4())
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=Decimal("1000"),
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            result = await provider.check_buying_power(
                user_id=user_id,
                required_amount=Decimal("50000"),
            )

        assert result is False


class TestFundsReflection:
    """Tests to verify funds correctly reflect position changes."""

    @pytest.mark.asyncio
    async def test_buy_reduces_available_cash(self):
        """Test that buying a position reduces available cash."""
        user_id = str(uuid4())
        initial_balance = Decimal("100000")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("500"),
                fees=Decimal("50"),
            )

        # Available cash should be reduced by 100*500 + 50 = 50050
        expected_balance = initial_balance - Decimal("50050")
        assert existing_funds.cash_balance == expected_balance
        assert existing_funds.available_cash == expected_balance

    @pytest.mark.asyncio
    async def test_sell_increases_available_cash(self):
        """Test that selling a position increases available cash."""
        user_id = str(uuid4())
        initial_balance = Decimal("50000")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="SELL",
                quantity=Decimal("100"),
                price=Decimal("600"),
                fees=Decimal("50"),
                existing_position_qty=Decimal("100"),  # Owns 100 shares
            )

        # Available cash should increase by 100*600 - 50 = 59950
        expected_balance = initial_balance + Decimal("59950")
        assert existing_funds.cash_balance == expected_balance
        assert existing_funds.available_cash == expected_balance

    @pytest.mark.asyncio
    async def test_round_trip_trade_with_profit(self):
        """Test a complete buy-sell cycle with profit."""
        user_id = str(uuid4())
        initial_balance = Decimal("100000")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            # Buy 50 shares at 1000 each
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="BUY",
                quantity=Decimal("50"),
                price=Decimal("1000"),
                fees=Decimal("25"),
            )

            balance_after_buy = existing_funds.cash_balance
            assert balance_after_buy == Decimal("49975")  # 100000 - 50025

            # Sell 50 shares at 1100 each (10% profit)
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="SELL",
                quantity=Decimal("50"),
                price=Decimal("1100"),
                fees=Decimal("25"),
                existing_position_qty=Decimal("50"),  # Owns 50 shares after buy
            )

        # Final balance: 49975 + (50*1100 - 25) = 49975 + 54975 = 104950
        assert existing_funds.cash_balance == Decimal("104950")
        # Net profit: 104950 - 100000 = 4950 (after fees)

    @pytest.mark.asyncio
    async def test_round_trip_trade_with_loss(self):
        """Test a complete buy-sell cycle with loss."""
        user_id = str(uuid4())
        initial_balance = Decimal("100000")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            # Buy 50 shares at 1000 each
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="BUY",
                quantity=Decimal("50"),
                price=Decimal("1000"),
                fees=Decimal("25"),
            )

            # Sell 50 shares at 900 each (10% loss)
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="SELL",
                quantity=Decimal("50"),
                price=Decimal("900"),
                fees=Decimal("25"),
                existing_position_qty=Decimal("50"),  # Owns 50 shares after buy
            )

        # Final balance: 49975 + (50*900 - 25) = 49975 + 44975 = 94950
        assert existing_funds.cash_balance == Decimal("94950")
        # Net loss: 100000 - 94950 = 5050 (including fees)


class TestProductTypeValidation:
    """Tests for product type (CNC/MIS/MTF) validation in funds handling."""

    @pytest.mark.asyncio
    async def test_delivery_buy_deducts_full_amount(self):
        """Test DELIVERY buy deducts full order value from cash."""
        user_id = str(uuid4())
        initial_balance = Decimal("100000")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("1000"),
                fees=Decimal("10"),
                product_type="DELIVERY",
            )

        # Full deduction: 10 * 1000 + 10 = 10010
        assert existing_funds.cash_balance == Decimal("89990")

    @pytest.mark.asyncio
    async def test_intraday_buy_blocks_margin(self):
        """Test INTRADAY buy blocks only margin (25%) from available cash."""
        user_id = str(uuid4())
        initial_balance = Decimal("100000")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
            margin_used=Decimal("0"),
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("1000"),
                fees=Decimal("10"),
                product_type="INTRADAY",
            )

        # Margin blocked: 10 * 1000 * 0.25 + 10 = 2510
        # Cash NOT reduced - only margin_used increases
        # (available_cash = cash_balance - margin_used handles the reduction)
        assert existing_funds.cash_balance == Decimal("100000")
        assert existing_funds.margin_used == Decimal("2510")

    @pytest.mark.asyncio
    async def test_margin_buy_blocks_50_percent(self):
        """Test MARGIN (MTF) buy blocks 50% margin."""
        user_id = str(uuid4())
        initial_balance = Decimal("100000")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
            margin_used=Decimal("0"),
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("1000"),
                fees=Decimal("10"),
                product_type="MARGIN",
            )

        # Margin blocked: 10 * 1000 * 0.50 + 10 = 5010
        # Cash NOT reduced - only margin_used increases
        # (available_cash = cash_balance - margin_used handles the reduction)
        assert existing_funds.cash_balance == Decimal("100000")
        assert existing_funds.margin_used == Decimal("5010")

    @pytest.mark.asyncio
    async def test_intraday_short_sell_blocks_margin(self):
        """Test INTRADAY short sell (no existing position) blocks margin."""
        user_id = str(uuid4())
        initial_balance = Decimal("100000")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
            margin_used=Decimal("0"),
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="SELL",
                quantity=Decimal("10"),
                price=Decimal("1000"),
                fees=Decimal("10"),
                product_type="INTRADAY",
                existing_position_qty=Decimal("0"),  # No existing position = short sell
            )

        # Short sell margin: 10 * 1000 * 0.25 + 10 = 2510
        assert existing_funds.margin_used == Decimal("2510")

    @pytest.mark.asyncio
    async def test_delivery_sell_closing_position_adds_proceeds(self):
        """Test DELIVERY sell of owned shares adds proceeds to cash."""
        user_id = str(uuid4())
        initial_balance = Decimal("50000")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="SELL",
                quantity=Decimal("10"),
                price=Decimal("1000"),
                fees=Decimal("10"),
                product_type="DELIVERY",
                existing_position_qty=Decimal("10"),  # Owns 10 shares
            )

        # Proceeds: 10 * 1000 - 10 = 9990
        assert existing_funds.cash_balance == Decimal("59990")

    @pytest.mark.asyncio
    async def test_intraday_close_short_releases_margin(self):
        """Test closing INTRADAY short position releases margin.

        With the updated logic, entry_price should be provided to correctly:
        - Calculate P&L for the short trade
        - Release the correct margin amount based on entry price

        Note: Fees are NOT included in margin blocking/release - they are
        deducted from P&L directly.
        """
        user_id = str(uuid4())
        initial_balance = Decimal("100000")
        # Short was opened at 1000, blocking 25% margin = 10*1000*0.25 = 2500
        # (fees are NOT part of margin)
        initial_margin = Decimal("2500")
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
            margin_used=initial_margin,
        )

        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("900"),  # Buying back at lower price (profit!)
                fees=Decimal("10"),
                product_type="INTRADAY",
                existing_position_qty=Decimal("-10"),  # Short position
                entry_price=Decimal("1000"),  # Original short entry price
            )

        # Closing short with entry_price:
        # - P&L = (entry_price - exit_price) * qty = (1000 - 900) * 10 = 1000 profit
        # - Cash change: +1000 (profit) - 10 (fees) = +990
        # - New cash: 100000 + 990 = 100990
        # - Margin to release: min(2500, 10*1000*0.25) = min(2500, 2500) = 2500
        # - New margin: 2500 - 2500 = 0
        assert existing_funds.cash_balance == Decimal("100990")
        assert existing_funds.margin_used == Decimal("0")

    @pytest.mark.asyncio
    async def test_product_type_aliases_work(self):
        """Test that CNC, MIS, MTF aliases work correctly."""
        user_id = str(uuid4())
        initial_balance = Decimal("100000")

        # Test CNC alias for DELIVERY
        existing_funds = MockUserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
        )
        provider = create_provider()

        with patch.object(provider, "_get_or_create_funds", return_value=existing_funds):
            await provider.update_funds_for_trade(
                user_id=user_id,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("1000"),
                fees=Decimal("10"),
                product_type="CNC",  # Alias for DELIVERY
            )

        # Should behave like DELIVERY - full deduction
        assert existing_funds.cash_balance == Decimal("89990")
