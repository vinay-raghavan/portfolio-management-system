"""Tests for CapitalGainsService."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.security import get_password_hash
from app.modules.auth.models import User
from app.modules.portfolio.gains_service import CapitalGainsService
from app.modules.portfolio.models import RealizedGain, TaxType


class TestCapitalGainsService:
    """Tests for CapitalGainsService operations."""

    @pytest.fixture
    async def test_user(self, db_session):
        """Create a test user."""
        user = User(
            email="gains_test@example.com",
            password_hash=get_password_hash("testpass123"),
            full_name="Gains Test User",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    def gains_service(self, db_session):
        """Create CapitalGainsService instance."""
        return CapitalGainsService(db_session)

    @pytest.mark.asyncio
    async def test_record_realized_gain_stcg(self, gains_service, test_user):
        """Test recording a short-term capital gain."""
        purchase_date = datetime.now(UTC) - timedelta(days=100)
        sale_date = datetime.now(UTC)

        gain = await gains_service.record_realized_gain(
            user_id=test_user.id,
            symbol="RELIANCE",
            quantity=Decimal("10"),
            cost_basis=Decimal("20000.00"),  # Total cost (10 * 2000)
            sale_proceeds=Decimal("25000.00"),  # Total proceeds (10 * 2500)
            purchase_date=purchase_date,
            sale_date=sale_date,
        )

        assert gain is not None
        assert gain.symbol == "RELIANCE"
        assert gain.tax_type == TaxType.STCG.value
        assert gain.gain_loss == Decimal("5000.00")  # 25000 - 20000
        assert gain.holding_days == 100

    @pytest.mark.asyncio
    async def test_record_realized_gain_ltcg(self, gains_service, test_user):
        """Test recording a long-term capital gain (>365 days)."""
        purchase_date = datetime.now(UTC) - timedelta(days=400)
        sale_date = datetime.now(UTC)

        gain = await gains_service.record_realized_gain(
            user_id=test_user.id,
            symbol="TCS",
            quantity=Decimal("5"),
            cost_basis=Decimal("15000.00"),  # Total cost (5 * 3000)
            sale_proceeds=Decimal("17500.00"),  # Total proceeds (5 * 3500)
            purchase_date=purchase_date,
            sale_date=sale_date,
        )

        assert gain.tax_type == TaxType.LTCG.value
        assert gain.holding_days == 400

    @pytest.mark.asyncio
    async def test_record_realized_gain_speculative(self, gains_service, test_user):
        """Test recording a speculative gain (same day)."""
        today = datetime.now(UTC)

        gain = await gains_service.record_realized_gain(
            user_id=test_user.id,
            symbol="INFY",
            quantity=Decimal("20"),
            cost_basis=Decimal("30000.00"),  # Total cost (20 * 1500)
            sale_proceeds=Decimal("30400.00"),  # Total proceeds (20 * 1520)
            purchase_date=today,
            sale_date=today,
        )

        assert gain.tax_type == TaxType.SPECULATIVE.value
        assert gain.holding_days == 0

    @pytest.mark.asyncio
    async def test_get_realized_gains_pagination(self, gains_service, test_user, db_session):
        """Test getting paginated gains."""
        now = datetime.now(UTC)
        # Create multiple gains
        for i in range(5):
            gain = RealizedGain(
                user_id=test_user.id,
                symbol=f"STOCK{i}",
                quantity=Decimal("10"),
                cost_basis=Decimal("1000.00"),
                sale_proceeds=Decimal("1100.00"),
                purchase_date=now - timedelta(days=30),
                sale_date=now,
                gain_loss=Decimal("100.00"),
                gain_loss_pct=Decimal("10.00"),
                holding_days=30,
                is_long_term=False,
                tax_type=TaxType.STCG.value,
                financial_year="2025-26",
            )
            db_session.add(gain)
        await db_session.flush()

        gains, total = await gains_service.get_realized_gains(
            user_id=test_user.id,
            page=1,
            page_size=3,
        )

        assert len(gains) == 3
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_gains_summary(self, gains_service, test_user, db_session):
        """Test getting gains summary by financial year."""
        now = datetime.now(UTC)
        # Create STCG gain
        stcg = RealizedGain(
            user_id=test_user.id,
            symbol="RELIANCE",
            quantity=Decimal("10"),
            cost_basis=Decimal("20000.00"),
            sale_proceeds=Decimal("22000.00"),
            purchase_date=now - timedelta(days=100),
            sale_date=now,
            gain_loss=Decimal("2000.00"),
            gain_loss_pct=Decimal("10.00"),
            holding_days=100,
            is_long_term=False,
            tax_type=TaxType.STCG.value,
            financial_year="2025-26",
        )
        db_session.add(stcg)

        # Create LTCG gain
        ltcg = RealizedGain(
            user_id=test_user.id,
            symbol="TCS",
            quantity=Decimal("5"),
            cost_basis=Decimal("15000.00"),
            sale_proceeds=Decimal("17500.00"),
            purchase_date=now - timedelta(days=400),
            sale_date=now,
            gain_loss=Decimal("2500.00"),
            gain_loss_pct=Decimal("16.67"),
            holding_days=400,
            is_long_term=True,
            tax_type=TaxType.LTCG.value,
            financial_year="2025-26",
        )
        db_session.add(ltcg)
        await db_session.flush()

        summary = await gains_service.get_gains_summary(
            user_id=test_user.id,
            financial_year="2025-26",
        )

        # Summary keys are "stcg", "ltcg", "net_gain_loss" (not stcg_total, etc.)
        assert summary["stcg"] == Decimal("2000.00")
        assert summary["ltcg"] == Decimal("2500.00")
        assert summary["net_gain_loss"] == Decimal("4500.00")
