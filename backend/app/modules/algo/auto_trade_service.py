"""Auto-trade service for managing recommendation-to-strategy pipeline.

This service handles:
- Auto-trade configuration management
- Strategy template management
- Pending auto-trade queue management
- Processing recommendations into strategies
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import (
    AutoTradeConfig,
    ConfirmationMode,
    PendingAutoTrade,
    PendingTradeStatus,
    ScreenerSourceType,
    StrategyTemplate,
)
from app.modules.algo.schemas import (
    AutoTradeConfigCreate,
    AutoTradeConfigUpdate,
    StrategyTemplateCreate,
    StrategyTemplateUpdate,
)

logger = logging.getLogger(__name__)


class StrategyTemplateService:
    """Service for managing strategy templates."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_templates(self, user_id: str) -> list[StrategyTemplate]:
        """Get all strategy templates for a user."""
        result = await self.db.execute(
            select(StrategyTemplate)
            .where(
                StrategyTemplate.user_id == user_id,
                StrategyTemplate.is_active == True,  # noqa: E712
            )
            .order_by(StrategyTemplate.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_template(self, user_id: str, template_id: str) -> StrategyTemplate | None:
        """Get a specific strategy template."""
        result = await self.db.execute(
            select(StrategyTemplate).where(
                StrategyTemplate.id == template_id,
                StrategyTemplate.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_template(self, user_id: str, data: StrategyTemplateCreate) -> StrategyTemplate:
        """Create a new strategy template."""
        template = StrategyTemplate(
            user_id=user_id,
            name=data.name,
            description=data.description,
            strategy_type=data.strategy_type,
            strategy_params=data.strategy_params,
            position_sizing_method=data.position_sizing_method,
            position_size_value=data.position_size_value,
            max_position_value=data.max_position_value,
            stop_loss_percent=data.stop_loss_percent,
            take_profit_percent=data.take_profit_percent,
            max_daily_loss=data.max_daily_loss,
            max_consecutive_losses=data.max_consecutive_losses,
            product_type=data.product_type,
            trading_start_time=data.trading_start_time,
            trading_end_time=data.trading_end_time,
            is_default=data.is_default,
        )
        self.db.add(template)
        await self.db.flush()
        logger.info(f"Created strategy template '{data.name}' for user {user_id}")
        return template

    async def update_template(
        self, user_id: str, template_id: str, data: StrategyTemplateUpdate
    ) -> StrategyTemplate | None:
        """Update a strategy template."""
        template = await self.get_template(user_id, template_id)
        if not template:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(template, field, value)

        await self.db.flush()
        logger.info(f"Updated strategy template {template_id}")
        return template

    async def delete_template(self, user_id: str, template_id: str) -> bool:
        """Soft delete a strategy template."""
        template = await self.get_template(user_id, template_id)
        if not template:
            return False

        template.is_active = False
        await self.db.flush()
        logger.info(f"Deleted strategy template {template_id}")
        return True


class AutoTradeConfigService:
    """Service for managing auto-trade configurations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_configs(self, user_id: str) -> list[AutoTradeConfig]:
        """Get all auto-trade configurations for a user."""
        result = await self.db.execute(
            select(AutoTradeConfig)
            .where(AutoTradeConfig.user_id == user_id)
            .order_by(AutoTradeConfig.category)
        )
        return list(result.scalars().all())

    async def get_config(self, user_id: str, config_id: str) -> AutoTradeConfig | None:
        """Get a specific auto-trade configuration."""
        result = await self.db.execute(
            select(AutoTradeConfig).where(
                AutoTradeConfig.id == config_id,
                AutoTradeConfig.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_config_by_category(self, user_id: str, category: str) -> AutoTradeConfig | None:
        """Get auto-trade config for a specific category."""
        result = await self.db.execute(
            select(AutoTradeConfig).where(
                AutoTradeConfig.user_id == user_id,
                AutoTradeConfig.category == category,
            )
        )
        return result.scalar_one_or_none()

    async def create_config(self, user_id: str, data: AutoTradeConfigCreate) -> AutoTradeConfig:
        """Create a new auto-trade configuration."""
        # Validate weights sum to 100
        total_weight = data.weight_technical + data.weight_fundamental + data.weight_sentiment
        if total_weight != 100:
            raise ValueError(f"Weights must sum to 100, got {total_weight}")

        # Validate screener source
        if data.screener_source_type == "custom" and not data.saved_screener_id:
            raise ValueError("saved_screener_id required when source is custom")
        if data.screener_source_type == "preset" and not data.preset_category:
            raise ValueError("preset_category required when source is preset")

        config = AutoTradeConfig(
            user_id=user_id,
            category=data.category,
            enabled=data.enabled,
            confirmation_mode=ConfirmationMode(data.confirmation_mode),
            strategy_template_id=data.strategy_template_id,
            max_positions_per_day=data.max_positions_per_day,
            max_capital_per_day=data.max_capital_per_day,
            expiry_hours=data.expiry_hours,
            weight_technical=data.weight_technical,
            weight_fundamental=data.weight_fundamental,
            weight_sentiment=data.weight_sentiment,
            min_confidence=data.min_confidence,
            screener_source_type=ScreenerSourceType(data.screener_source_type),
            preset_category=data.preset_category,
            saved_screener_id=data.saved_screener_id,
        )
        self.db.add(config)
        await self.db.flush()
        logger.info(f"Created auto-trade config for category '{data.category}' user {user_id}")
        return config

    async def update_config(
        self, user_id: str, config_id: str, data: AutoTradeConfigUpdate
    ) -> AutoTradeConfig | None:
        """Update an auto-trade configuration."""
        config = await self.get_config(user_id, config_id)
        if not config:
            return None

        update_fields = data.model_dump(exclude_unset=True)

        # Handle enum conversions
        if "confirmation_mode" in update_fields and update_fields["confirmation_mode"]:
            update_fields["confirmation_mode"] = ConfirmationMode(
                update_fields["confirmation_mode"]
            )
        if "screener_source_type" in update_fields and update_fields["screener_source_type"]:
            update_fields["screener_source_type"] = ScreenerSourceType(
                update_fields["screener_source_type"]
            )

        # Validate weights if being updated
        weight_fields = ["weight_technical", "weight_fundamental", "weight_sentiment"]
        if any(f in update_fields for f in weight_fields):
            tech = update_fields.get("weight_technical", config.weight_technical)
            fund = update_fields.get("weight_fundamental", config.weight_fundamental)
            sent = update_fields.get("weight_sentiment", config.weight_sentiment)
            if tech + fund + sent != 100:
                raise ValueError(f"Weights must sum to 100, got {tech + fund + sent}")

        for field, value in update_fields.items():
            setattr(config, field, value)

        await self.db.flush()
        logger.info(f"Updated auto-trade config {config_id}")
        return config

    async def delete_config(self, user_id: str, config_id: str) -> bool:
        """Delete an auto-trade configuration."""
        config = await self.get_config(user_id, config_id)
        if not config:
            return False

        await self.db.delete(config)
        await self.db.flush()
        logger.info(f"Deleted auto-trade config {config_id}")
        return True


class PendingAutoTradeService:
    """Service for managing pending auto-trade queue."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_pending_trades(
        self, user_id: str, status: PendingTradeStatus | None = None
    ) -> list[PendingAutoTrade]:
        """Get pending auto-trades for a user."""
        query = select(PendingAutoTrade).where(PendingAutoTrade.user_id == user_id)
        if status:
            query = query.where(PendingAutoTrade.status == status)
        query = query.order_by(PendingAutoTrade.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_pending_trade(self, user_id: str, trade_id: str) -> PendingAutoTrade | None:
        """Get a specific pending auto-trade."""
        result = await self.db.execute(
            select(PendingAutoTrade).where(
                PendingAutoTrade.id == trade_id,
                PendingAutoTrade.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_pending_trade(
        self,
        user_id: str,
        config: AutoTradeConfig,
        symbols: list[str],
        scores: dict | None,
        recommended_strategy_type: str,
        suggested_params: dict | None,
    ) -> PendingAutoTrade:
        """Create a new pending auto-trade entry."""
        expires_at = datetime.utcnow() + timedelta(hours=config.expiry_hours)

        pending = PendingAutoTrade(
            user_id=user_id,
            auto_trade_config_id=config.id,
            category=config.category,
            recommendation_date=datetime.utcnow(),
            symbols=symbols,
            scores=scores,
            recommended_strategy_type=recommended_strategy_type,
            suggested_params=suggested_params,
            expires_at=expires_at,
        )
        self.db.add(pending)
        await self.db.flush()
        logger.info(f"Created pending auto-trade for user {user_id}, expires at {expires_at}")
        return pending

    async def approve_pending_trade(
        self, user_id: str, trade_id: str
    ) -> tuple[PendingAutoTrade | None, str | None]:
        """Approve a pending auto-trade and create the strategy.

        Returns:
            Tuple of (updated pending trade, created strategy ID or error message)
        """
        pending = await self.get_pending_trade(user_id, trade_id)
        if not pending:
            return None, "Pending trade not found"

        if pending.status != PendingTradeStatus.PENDING:
            return pending, f"Trade already {pending.status.value}"

        if datetime.utcnow() > pending.expires_at:
            pending.status = PendingTradeStatus.EXPIRED
            await self.db.flush()
            return pending, "Trade has expired"

        # TODO: Create the actual strategy using AlgoService
        # For now, mark as approved but don't create strategy
        pending.status = PendingTradeStatus.APPROVED
        pending.actioned_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"Approved pending auto-trade {trade_id}")
        return pending, None

    async def reject_pending_trade(self, user_id: str, trade_id: str) -> PendingAutoTrade | None:
        """Reject a pending auto-trade."""
        pending = await self.get_pending_trade(user_id, trade_id)
        if not pending:
            return None

        if pending.status != PendingTradeStatus.PENDING:
            return pending  # Already actioned

        pending.status = PendingTradeStatus.REJECTED
        pending.actioned_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"Rejected pending auto-trade {trade_id}")
        return pending

    async def expire_old_trades(self) -> int:
        """Mark expired pending trades. Called by scheduled task.

        Returns:
            Number of trades expired
        """
        now = datetime.utcnow()
        result = await self.db.execute(
            select(PendingAutoTrade).where(
                PendingAutoTrade.status == PendingTradeStatus.PENDING,
                PendingAutoTrade.expires_at < now,
            )
        )
        expired = list(result.scalars().all())

        for pending in expired:
            pending.status = PendingTradeStatus.EXPIRED
            pending.actioned_at = now

        await self.db.flush()
        if expired:
            logger.info(f"Expired {len(expired)} pending auto-trades")
        return len(expired)
