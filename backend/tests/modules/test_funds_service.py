"""Tests for FundsService."""

from decimal import Decimal

import pytest

from app.core.security import get_password_hash
from app.modules.auth.models import User
from app.modules.portfolio.funds_service import FundsService


class TestFundsService:
    """Tests for FundsService operations."""

    @pytest.fixture
    async def test_user(self, db_session):
        """Create a test user."""
        user = User(
            email="test@example.com",
            password_hash=get_password_hash("testpass123"),
            full_name="Test User",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    def funds_service(self, db_session):
        """Create FundsService instance."""
        return FundsService(db_session)

    async def test_initialize_funds_default_balance(self, funds_service, test_user):
        """Test initializing funds with default balance."""
        funds = await funds_service.initialize_funds(test_user.id)

        assert funds is not None
        assert funds.user_id == test_user.id
        assert funds.cash_balance == Decimal("1000000.0")  # Default from config
        assert funds.margin_used == Decimal("0")
        assert funds.collateral == Decimal("0")

    async def test_initialize_funds_custom_balance(self, funds_service, test_user):
        """Test initializing funds with custom balance."""
        custom_balance = Decimal("500000.00")
        funds = await funds_service.initialize_funds(test_user.id, custom_balance)

        assert funds.cash_balance == custom_balance

    async def test_get_funds_returns_none_when_not_exists(self, funds_service, test_user):
        """Test get_funds returns None for user without funds."""
        funds = await funds_service.get_funds(test_user.id)
        assert funds is None

    async def test_get_or_create_funds_creates_when_not_exists(self, funds_service, test_user):
        """Test get_or_create_funds creates funds if not exists."""
        funds = await funds_service.get_or_create_funds(test_user.id)

        assert funds is not None
        assert funds.user_id == test_user.id
        assert funds.cash_balance == Decimal("1000000.0")

    async def test_get_or_create_funds_returns_existing(self, funds_service, test_user):
        """Test get_or_create_funds returns existing funds."""
        # Create funds first
        await funds_service.initialize_funds(test_user.id, Decimal("250000"))

        # Get or create should return same funds
        funds = await funds_service.get_or_create_funds(test_user.id)
        assert funds.cash_balance == Decimal("250000")

    async def test_add_cash_success(self, funds_service, test_user):
        """Test adding cash to balance."""
        await funds_service.initialize_funds(test_user.id, Decimal("100000"))

        funds = await funds_service.add_cash(test_user.id, Decimal("50000"), "deposit")

        assert funds.cash_balance == Decimal("150000")

    async def test_add_cash_negative_amount_raises(self, funds_service, test_user):
        """Test adding negative amount raises ValueError."""
        await funds_service.initialize_funds(test_user.id)

        with pytest.raises(ValueError, match="must be positive"):
            await funds_service.add_cash(test_user.id, Decimal("-1000"), "invalid")

    async def test_deduct_cash_success(self, funds_service, test_user):
        """Test deducting cash from balance."""
        await funds_service.initialize_funds(test_user.id, Decimal("100000"))

        funds = await funds_service.deduct_cash(test_user.id, Decimal("25000"), "withdrawal")

        assert funds.cash_balance == Decimal("75000")

    async def test_deduct_cash_insufficient_funds_raises(self, funds_service, test_user):
        """Test deducting more than available raises ValueError."""
        await funds_service.initialize_funds(test_user.id, Decimal("10000"))

        with pytest.raises(ValueError, match="Insufficient funds"):
            await funds_service.deduct_cash(test_user.id, Decimal("50000"), "too much")

    async def test_block_margin_success(self, funds_service, test_user):
        """Test blocking margin."""
        await funds_service.initialize_funds(test_user.id, Decimal("100000"))

        funds = await funds_service.block_margin(test_user.id, Decimal("20000"))

        assert funds.margin_used == Decimal("20000")
        assert funds.available_cash == Decimal("80000")

    async def test_block_margin_insufficient_raises(self, funds_service, test_user):
        """Test blocking more margin than available raises ValueError."""
        await funds_service.initialize_funds(test_user.id, Decimal("10000"))

        with pytest.raises(ValueError, match="Insufficient margin"):
            await funds_service.block_margin(test_user.id, Decimal("50000"))

    async def test_release_margin_success(self, funds_service, test_user):
        """Test releasing blocked margin."""
        await funds_service.initialize_funds(test_user.id, Decimal("100000"))
        await funds_service.block_margin(test_user.id, Decimal("30000"))

        funds = await funds_service.release_margin(test_user.id, Decimal("10000"))

        assert funds.margin_used == Decimal("20000")
        assert funds.available_cash == Decimal("80000")

    async def test_release_margin_caps_at_blocked_amount(self, funds_service, test_user):
        """Test releasing more margin than blocked caps at blocked amount."""
        await funds_service.initialize_funds(test_user.id, Decimal("100000"))
        await funds_service.block_margin(test_user.id, Decimal("20000"))

        funds = await funds_service.release_margin(test_user.id, Decimal("50000"))

        assert funds.margin_used == Decimal("0")

    async def test_process_trade_settlement_buy(self, funds_service, test_user):
        """Test trade settlement for BUY order."""
        await funds_service.initialize_funds(test_user.id, Decimal("100000"))

        funds = await funds_service.process_trade_settlement(
            user_id=test_user.id,
            side="BUY",
            quantity=Decimal("10"),
            price=Decimal("1500"),
            fees=Decimal("15"),
        )

        # 10 * 1500 + 15 = 15015
        assert funds.cash_balance == Decimal("100000") - Decimal("15015")

    async def test_process_trade_settlement_sell(self, funds_service, test_user):
        """Test trade settlement for SELL order."""
        await funds_service.initialize_funds(test_user.id, Decimal("100000"))

        funds = await funds_service.process_trade_settlement(
            user_id=test_user.id,
            side="SELL",
            quantity=Decimal("10"),
            price=Decimal("1500"),
            fees=Decimal("15"),
        )

        # 10 * 1500 - 15 = 14985 credited
        assert funds.cash_balance == Decimal("100000") + Decimal("14985")

    async def test_check_buying_power_sufficient(self, funds_service, test_user):
        """Test check_buying_power returns True when sufficient funds."""
        await funds_service.initialize_funds(test_user.id, Decimal("100000"))

        result = await funds_service.check_buying_power(test_user.id, Decimal("50000"))
        assert result is True

    async def test_check_buying_power_insufficient(self, funds_service, test_user):
        """Test check_buying_power returns False when insufficient funds."""
        await funds_service.initialize_funds(test_user.id, Decimal("10000"))

        result = await funds_service.check_buying_power(test_user.id, Decimal("50000"))
        assert result is False

    async def test_check_buying_power_considers_margin(self, funds_service, test_user):
        """Test check_buying_power considers blocked margin."""
        await funds_service.initialize_funds(test_user.id, Decimal("100000"))
        await funds_service.block_margin(test_user.id, Decimal("80000"))

        # Only 20000 available
        assert await funds_service.check_buying_power(test_user.id, Decimal("20000")) is True
        assert await funds_service.check_buying_power(test_user.id, Decimal("25000")) is False
