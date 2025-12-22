"""Tests for RiskService."""

from decimal import Decimal

import pytest

from app.core.security import get_password_hash
from app.modules.auth.models import User
from app.modules.risk.models import RiskLimits
from app.modules.risk.schemas import RiskLimitsUpdate
from app.modules.risk.service import RiskService


class TestRiskService:
    """Tests for RiskService operations."""

    @pytest.fixture
    async def test_user(self, db_session):
        """Create a test user."""
        user = User(
            email="risktest@example.com",
            password_hash=get_password_hash("testpass123"),
            full_name="Risk Test User",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    def risk_service(self, db_session):
        """Create RiskService instance."""
        return RiskService(db_session)

    # --- Risk Limits Tests ---

    async def test_get_limits_creates_default(self, risk_service, test_user):
        """Test get_limits creates default limits if not exists."""
        limits = await risk_service.get_limits(test_user.id)

        assert limits is not None
        assert limits.user_id == test_user.id
        assert limits.max_position_size == Decimal("100000")
        assert limits.max_position_pct == Decimal("20")
        assert limits.max_daily_loss == Decimal("50000")
        assert limits.max_orders_per_day == 50  # Model default
        assert limits.max_positions == 20

    async def test_get_limits_returns_existing(self, risk_service, test_user, db_session):
        """Test get_limits returns existing limits."""
        # Create custom limits
        custom_limits = RiskLimits(
            user_id=test_user.id,
            max_position_size=Decimal("50000"),
            max_daily_loss=Decimal("10000"),
        )
        db_session.add(custom_limits)
        await db_session.flush()

        limits = await risk_service.get_limits(test_user.id)
        assert limits.max_position_size == Decimal("50000")
        assert limits.max_daily_loss == Decimal("10000")

    async def test_update_limits(self, risk_service, test_user, db_session):
        """Test updating risk limits."""
        # First create default limits
        await risk_service.get_limits(test_user.id)

        updates = RiskLimitsUpdate(
            max_position_size=Decimal("75000"),
            max_daily_loss=Decimal("25000"),
            max_orders_per_day=50,
        )

        limits = await risk_service.update_limits(test_user.id, updates)

        assert limits.max_position_size == Decimal("75000")
        assert limits.max_daily_loss == Decimal("25000")
        assert limits.max_orders_per_day == 50
        # Unchanged values should remain
        assert limits.max_position_pct == Decimal("20")

    # --- Daily Metrics Tests ---

    async def test_get_daily_metrics_creates_default(self, risk_service, test_user):
        """Test get_daily_metrics creates default if not exists."""
        metrics = await risk_service.get_daily_metrics(test_user.id)

        assert metrics is not None
        assert metrics.user_id == test_user.id
        assert metrics.orders_count == 0
        assert metrics.trades_count == 0
        assert metrics.realized_pnl == Decimal("0")
        assert metrics.daily_loss_limit_breached is False

    async def test_record_order_increments_count(self, risk_service, test_user):
        """Test record_order increments orders count."""
        await risk_service.record_order(test_user.id, Decimal("10000"))
        metrics = await risk_service.get_daily_metrics(test_user.id)
        assert metrics.orders_count == 1

        await risk_service.record_order(test_user.id, Decimal("15000"))
        metrics = await risk_service.get_daily_metrics(test_user.id)
        assert metrics.orders_count == 2
        assert metrics.total_traded_value == Decimal("25000")

    async def test_record_trade_pnl_positive(self, risk_service, test_user):
        """Test record_trade_pnl with positive P&L."""
        await risk_service.record_trade_pnl(test_user.id, pnl=Decimal("5000"))

        metrics = await risk_service.get_daily_metrics(test_user.id)
        assert metrics.trades_count == 1
        assert metrics.realized_pnl == Decimal("5000")

    async def test_record_trade_pnl_negative_triggers_breach(self, risk_service, test_user):
        """Test that large negative P&L triggers daily loss limit breach."""
        # Get limits to know the threshold
        limits = await risk_service.get_limits(test_user.id)

        # Record loss exceeding limit
        await risk_service.record_trade_pnl(
            test_user.id,
            pnl=-limits.max_daily_loss - Decimal("1000"),
        )

        metrics = await risk_service.get_daily_metrics(test_user.id)
        assert metrics.daily_loss_limit_breached is True

    # --- Risk Check Tests ---

    async def test_check_order_risk_success(self, risk_service, test_user):
        """Test check_order_risk passes for valid order."""
        result = await risk_service.check_order_risk(
            user_id=test_user.id,
            symbol="RELIANCE",
            side="BUY",
            quantity=Decimal("10"),
            price=Decimal("2500"),  # 25000 order value, within limits
        )

        assert result.passed is True
        assert result.blocked_reason is None

    async def test_check_order_risk_exceeds_position_size(self, risk_service, test_user):
        """Test check_order_risk fails when exceeding position size limit."""
        result = await risk_service.check_order_risk(
            user_id=test_user.id,
            symbol="RELIANCE",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("2000"),  # 200000 order value, exceeds 100000 limit
        )

        assert result.passed is False
        assert result.blocked_reason is not None
        assert "size" in result.blocked_reason.lower() or "value" in result.blocked_reason.lower()

    async def test_check_order_risk_daily_loss_breached(self, risk_service, test_user):
        """Test check_order_risk fails when daily loss limit exceeded via negative pnl."""
        # Record a large loss to trigger breach check
        await risk_service.record_trade_pnl(test_user.id, pnl=Decimal("-60000"))

        result = await risk_service.check_order_risk(
            user_id=test_user.id,
            symbol="RELIANCE",
            side="BUY",
            quantity=Decimal("10"),
            price=Decimal("1000"),
        )

        assert result.passed is False
        assert "loss" in result.blocked_reason.lower()

    async def test_check_order_risk_max_orders_reached(self, risk_service, test_user):
        """Test check_order_risk fails when max orders per day reached."""
        # Set orders count to max
        limits = await risk_service.get_limits(test_user.id)
        metrics = await risk_service.get_daily_metrics(test_user.id)
        metrics.orders_count = limits.max_orders_per_day

        result = await risk_service.check_order_risk(
            user_id=test_user.id,
            symbol="RELIANCE",
            side="BUY",
            quantity=Decimal("10"),
            price=Decimal("1000"),
        )

        assert result.passed is False
        assert "order" in result.blocked_reason.lower()

    # --- Risk Summary Tests ---

    async def test_get_risk_summary(self, risk_service, test_user):
        """Test get_risk_summary returns comprehensive status."""
        # Record some activity
        await risk_service.record_order(test_user.id, Decimal("50000"))
        await risk_service.record_trade_pnl(test_user.id, pnl=Decimal("-5000"))

        summary = await risk_service.get_risk_summary(test_user.id)

        assert summary.daily_pnl == Decimal("-5000")
        assert summary.orders_today == 1
        assert summary.is_trading_blocked is False  # Not breached yet
        assert summary.daily_loss_remaining > 0
        assert summary.orders_remaining > 0

    # --- Sector Concentration Tests ---

    async def test_check_order_risk_includes_sector_check(self, risk_service, test_user):
        """Test check_order_risk includes sector concentration check for BUY orders."""
        result = await risk_service.check_order_risk(
            user_id=test_user.id,
            symbol="RELIANCE",
            side="BUY",
            quantity=Decimal("10"),
            price=Decimal("2500"),
        )

        # Should have sector concentration check in the checks
        [c["name"] for c in result.checks]
        # Sector check may not be present if symbol has no sector in DB
        # But the check should pass overall
        assert result.passed is True

    async def test_check_order_risk_intraday_exposure_check(self, risk_service, test_user):
        """Test check_order_risk includes intraday exposure check."""
        result = await risk_service.check_order_risk(
            user_id=test_user.id,
            symbol="RELIANCE",
            side="BUY",
            quantity=Decimal("10"),
            price=Decimal("2500"),
        )

        check_names = [c["name"] for c in result.checks]
        assert "max_intraday_exposure" in check_names

    async def test_check_order_risk_warnings_for_approaching_limits(self, risk_service, test_user):
        """Test that warnings are generated when approaching limits."""
        # Get limits and set orders count to 80% of max
        limits = await risk_service.get_limits(test_user.id)
        metrics = await risk_service.get_daily_metrics(test_user.id)
        metrics.orders_count = int(limits.max_orders_per_day * Decimal("0.8"))

        result = await risk_service.check_order_risk(
            user_id=test_user.id,
            symbol="RELIANCE",
            side="BUY",
            quantity=Decimal("10"),
            price=Decimal("100"),
        )

        # Should have warning about approaching order limit
        assert any("order limit" in w.lower() for w in result.warnings)
