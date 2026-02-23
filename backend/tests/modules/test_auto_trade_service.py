"""Tests for auto-trade services."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.auto_trade_service import (
    AutoTradeConfigService,
    PendingAutoTradeService,
    StrategyTemplateService,
)
from app.modules.algo.models import (
    AutoTradeConfig,
    ConfirmationMode,
    PendingAutoTrade,
    PendingTradeStatus,
    ScreenerSourceType,
    StrategyTemplate,
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def sample_template():
    """Create a sample strategy template."""
    template = MagicMock(spec=StrategyTemplate)
    template.id = "template-id"
    template.user_id = "test-user"
    template.name = "Test Template"
    template.strategy_type = "rsi"
    template.strategy_params = {"rsi_period": 14, "overbought": 70, "oversold": 30}
    template.position_sizing_method = "portfolio_percent"
    template.position_size_value = Decimal("5.0")
    template.max_position_value = Decimal("50000")
    template.max_daily_loss = Decimal("5000")
    template.max_consecutive_losses = 3
    template.product_type = "intraday"
    template.is_default = True
    return template


@pytest.fixture
def sample_config():
    """Create a sample auto-trade config."""
    config = MagicMock(spec=AutoTradeConfig)
    config.id = "config-id"
    config.user_id = "test-user"
    config.category = "momentum"
    config.is_enabled = True
    config.confirmation_mode = ConfirmationMode.NOTIFY
    config.expiry_hours = 24
    config.min_confidence = 60
    config.screener_source = ScreenerSourceType.PRESET
    config.strategy_template_id = "template-id"
    return config


@pytest.fixture
def sample_pending_trade(sample_config):
    """Create a sample pending auto-trade."""
    pending = MagicMock(spec=PendingAutoTrade)
    pending.id = "pending-id"
    pending.user_id = "test-user"
    pending.auto_trade_config_id = sample_config.id
    pending.category = "momentum"
    pending.status = PendingTradeStatus.PENDING
    pending.symbols = ["RELIANCE", "TCS", "INFY"]
    pending.scores = {"RELIANCE": {"combined_score": 85}, "TCS": {"combined_score": 78}}
    pending.recommended_strategy_type = "rsi"
    pending.suggested_params = {"rsi_period": 14}
    pending.recommendation_date = datetime.utcnow()
    pending.expires_at = datetime.utcnow() + timedelta(hours=24)
    return pending


class TestStrategyTemplateService:
    """Tests for StrategyTemplateService."""

    @pytest.mark.asyncio
    async def test_get_templates(self, mock_db, sample_template):
        """Test getting templates for a user."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_template]
        mock_db.execute.return_value = mock_result

        service = StrategyTemplateService(mock_db)
        templates = await service.get_templates("test-user")

        assert len(templates) == 1
        assert templates[0].name == "Test Template"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_template(self, mock_db, sample_template):
        """Test getting a single template."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_db.execute.return_value = mock_result

        service = StrategyTemplateService(mock_db)
        template = await service.get_template("test-user", "template-id")

        assert template is not None
        assert template.id == "template-id"
        assert template.strategy_type == "rsi"

    @pytest.mark.asyncio
    async def test_get_default_for_category_momentum(self, mock_db, sample_template):
        """Test getting default template for momentum category."""
        sample_template.strategy_type = "rsi"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_db.execute.return_value = mock_result

        service = StrategyTemplateService(mock_db)
        template = await service.get_default_for_category("test-user", "momentum")

        assert template is not None
        assert template.strategy_type == "rsi"


class TestPendingAutoTradeService:
    """Tests for PendingAutoTradeService."""

    @pytest.mark.asyncio
    async def test_get_pending_trades(self, mock_db, sample_pending_trade):
        """Test getting pending trades for a user."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_pending_trade]
        mock_db.execute.return_value = mock_result

        service = PendingAutoTradeService(mock_db, send_notifications=False)
        trades = await service.get_pending_trades("test-user")

        assert len(trades) == 1
        assert trades[0].id == "pending-id"
        assert trades[0].symbols == ["RELIANCE", "TCS", "INFY"]

    @pytest.mark.asyncio
    async def test_create_pending_trade(self, mock_db, sample_config):
        """Test creating a pending trade."""
        service = PendingAutoTradeService(mock_db, send_notifications=False)

        # Call the method (return value not needed for verification)
        await service.create_pending_trade(
            user_id="test-user",
            config=sample_config,
            symbols=["RELIANCE", "TCS"],
            scores={"RELIANCE": {"combined_score": 85}},
            recommended_strategy_type="rsi",
            suggested_params={"rsi_period": 14},
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_pending_trade(self, mock_db, sample_pending_trade):
        """Test rejecting a pending trade."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_pending_trade
        mock_db.execute.return_value = mock_result

        service = PendingAutoTradeService(mock_db, send_notifications=False)
        pending = await service.reject_pending_trade(
            "test-user", "pending-id", reason="Not interested"
        )

        assert pending is not None
        assert pending.status == PendingTradeStatus.REJECTED
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_already_actioned_trade(self, mock_db, sample_pending_trade):
        """Test rejecting an already actioned trade returns the trade without changes."""
        sample_pending_trade.status = PendingTradeStatus.APPROVED
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_pending_trade
        mock_db.execute.return_value = mock_result

        service = PendingAutoTradeService(mock_db, send_notifications=False)
        pending = await service.reject_pending_trade("test-user", "pending-id")

        assert pending is not None
        assert pending.status == PendingTradeStatus.APPROVED
        # flush not called since no update was made
        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_expire_old_trades(self, mock_db, sample_pending_trade):
        """Test expiring old pending trades."""
        # Set trade to be already expired
        sample_pending_trade.expires_at = datetime.utcnow() - timedelta(hours=1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_pending_trade]
        mock_db.execute.return_value = mock_result

        service = PendingAutoTradeService(mock_db, send_notifications=False)
        count = await service.expire_old_trades()

        assert count == 1
        assert sample_pending_trade.status == PendingTradeStatus.EXPIRED
        mock_db.flush.assert_called_once()


class TestAutoTradeConfigService:
    """Tests for AutoTradeConfigService."""

    @pytest.mark.asyncio
    async def test_get_configs(self, mock_db, sample_config):
        """Test getting auto-trade configs for a user."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_config]
        mock_db.execute.return_value = mock_result

        service = AutoTradeConfigService(mock_db)
        configs = await service.get_configs("test-user")

        assert len(configs) == 1
        assert configs[0].category == "momentum"
        assert configs[0].is_enabled is True

    @pytest.mark.asyncio
    async def test_get_config_by_category(self, mock_db, sample_config):
        """Test getting config by category."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_config
        mock_db.execute.return_value = mock_result

        service = AutoTradeConfigService(mock_db)
        config = await service.get_config_by_category("test-user", "momentum")

        assert config is not None
        assert config.category == "momentum"
