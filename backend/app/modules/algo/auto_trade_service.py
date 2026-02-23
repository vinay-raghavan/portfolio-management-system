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
    ScheduleType,
    ScreenerSourceType,
    StrategyStatus,
    StrategyTemplate,
    UserStrategy,
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

    async def get_default_for_category(
        self, user_id: str, category: str
    ) -> StrategyTemplate | None:
        """Get the default template for a category.

        Args:
            user_id: User ID
            category: Recommendation category (momentum, breakout, pullback, sector)

        Returns:
            Default StrategyTemplate for the category or None
        """
        # Map categories to strategy types
        category_strategy_map = {
            "momentum": "rsi",
            "breakout": "bollinger_breakout",
            "pullback": "pullback_macd",
            "sector": "rsi",
            "value": "rsi",
        }

        # First try to find a default template for this user matching the category's strategy
        preferred_strategy = category_strategy_map.get(category, "rsi")

        # Try to find user's default template with matching strategy
        result = await self.db.execute(
            select(StrategyTemplate)
            .where(
                StrategyTemplate.user_id == user_id,
                StrategyTemplate.is_active == True,  # noqa: E712
                StrategyTemplate.is_default == True,  # noqa: E712
                StrategyTemplate.strategy_type == preferred_strategy,
            )
            .limit(1)
        )
        template = result.scalar_one_or_none()
        if template:
            return template

        # Fall back to any default template
        result = await self.db.execute(
            select(StrategyTemplate)
            .where(
                StrategyTemplate.user_id == user_id,
                StrategyTemplate.is_active == True,  # noqa: E712
                StrategyTemplate.is_default == True,  # noqa: E712
            )
            .limit(1)
        )
        template = result.scalar_one_or_none()
        if template:
            return template

        # Fall back to any active template with matching strategy
        result = await self.db.execute(
            select(StrategyTemplate)
            .where(
                StrategyTemplate.user_id == user_id,
                StrategyTemplate.is_active == True,  # noqa: E712
                StrategyTemplate.strategy_type == preferred_strategy,
            )
            .order_by(StrategyTemplate.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_strategy_from_template(
        self,
        user_id: str,
        template: StrategyTemplate,
        symbols: list[str],
        name_suffix: str | None = None,
        position_size_multiplier: float = 1.0,
    ) -> "UserStrategy":
        """Create a UserStrategy from a template.

        Args:
            user_id: User ID
            template: StrategyTemplate to use as base
            symbols: List of symbols to trade
            name_suffix: Optional suffix for strategy name (e.g., "Momentum_20260223")
            position_size_multiplier: Multiply position size by this factor (0.25-1.0)

        Returns:
            Created UserStrategy
        """
        from decimal import Decimal

        # Generate name
        name = f"{template.name}"
        if name_suffix:
            name = f"{name} - {name_suffix}"

        # Calculate adjusted position size
        adjusted_position_size = template.position_size_value * Decimal(
            str(position_size_multiplier)
        )

        strategy = UserStrategy(
            user_id=user_id,
            name=name,
            description=f"Auto-created from template '{template.name}'",
            strategy_name=template.strategy_type,
            strategy_params=template.strategy_params or {},
            custom_symbols=symbols,
            schedule_type=ScheduleType.MARKET_OPEN,
            position_sizing_method=template.position_sizing_method,
            portfolio_percent=adjusted_position_size,
            max_position_value=template.max_position_value,
            max_daily_loss=template.max_daily_loss,
            max_consecutive_losses=template.max_consecutive_losses,
            is_paper_trading=True,  # Auto-created strategies start in paper mode
            product_type=template.product_type,
            status=StrategyStatus.ACTIVE,
        )
        self.db.add(strategy)
        await self.db.flush()
        logger.info(f"Created strategy '{name}' from template '{template.name}' for user {user_id}")
        return strategy


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
            run_time=data.run_time,
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

    def __init__(self, db: AsyncSession, send_notifications: bool = True):
        """Initialize with database session.

        Args:
            db: Database session
            send_notifications: Whether to send notifications (disable for testing)
        """
        self.db = db
        self._send_notifications = send_notifications
        self._notification_service = None

    @property
    def notification_service(self):
        """Lazy load notification service."""
        if self._notification_service is None and self._send_notifications:
            from app.modules.algo.notifications import AlgoNotificationService

            self._notification_service = AlgoNotificationService()
        return self._notification_service

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

        # Send notification
        if self.notification_service:
            try:
                await self.notification_service.notify_auto_trade_pending(
                    user_id=user_id,
                    pending_trade_id=pending.id,
                    category=config.category,
                    symbols=symbols,
                    strategy_type=recommended_strategy_type,
                    expires_at=expires_at.isoformat(),
                )
            except Exception as e:
                logger.warning(f"Failed to send pending trade notification: {e}")

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

        # Get the auto-trade config to find the template
        config_result = await self.db.execute(
            select(AutoTradeConfig).where(AutoTradeConfig.id == pending.auto_trade_config_id)
        )
        config = config_result.scalar_one_or_none()

        created_strategy_id = None

        if config and config.strategy_template_id:
            # Use the configured template
            template_service = StrategyTemplateService(self.db)
            template = await template_service.get_template(user_id, config.strategy_template_id)

            if template:
                # Calculate position size multiplier from scores
                position_multiplier = 1.0
                if pending.scores and "position_size_multiplier" in pending.scores:
                    position_multiplier = float(pending.scores["position_size_multiplier"])

                # Create strategy from template
                strategy = await template_service.create_strategy_from_template(
                    user_id=user_id,
                    template=template,
                    symbols=pending.symbols,
                    name_suffix=f"{pending.category}_{pending.recommendation_date.strftime('%Y%m%d')}",
                    position_size_multiplier=position_multiplier,
                )
                created_strategy_id = strategy.id
                logger.info(f"Created strategy {strategy.id} from pending trade {trade_id}")
            else:
                logger.warning(
                    f"Template {config.strategy_template_id} not found for pending trade {trade_id}"
                )
        else:
            logger.warning(f"No template configured for pending trade {trade_id}")

        # Mark as approved
        pending.status = PendingTradeStatus.APPROVED
        pending.actioned_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"Approved pending auto-trade {trade_id}")

        # Send notification
        if self.notification_service and created_strategy_id:
            try:
                await self.notification_service.notify_auto_trade_executed(
                    user_id=user_id,
                    strategy_id=created_strategy_id,
                    strategy_name=f"{pending.category}_strategy",
                    category=pending.category,
                    symbols=pending.symbols,
                    confirmation_mode="approved",
                )
            except Exception as e:
                logger.warning(f"Failed to send approval notification: {e}")

        return pending, created_strategy_id

    async def reject_pending_trade(
        self, user_id: str, trade_id: str, reason: str | None = None
    ) -> PendingAutoTrade | None:
        """Reject a pending auto-trade.

        Args:
            user_id: User ID
            trade_id: Pending trade ID
            reason: Optional rejection reason

        Returns:
            Updated PendingAutoTrade or None if not found
        """
        pending = await self.get_pending_trade(user_id, trade_id)
        if not pending:
            return None

        if pending.status != PendingTradeStatus.PENDING:
            return pending  # Already actioned

        pending.status = PendingTradeStatus.REJECTED
        pending.actioned_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"Rejected pending auto-trade {trade_id}")

        # Send notification
        if self.notification_service:
            try:
                await self.notification_service.notify_auto_trade_rejected(
                    user_id=user_id,
                    pending_trade_id=trade_id,
                    category=pending.category,
                    symbols=pending.symbols,
                    reason=reason,
                )
            except Exception as e:
                logger.warning(f"Failed to send rejection notification: {e}")

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

        # Send notifications for expired trades
        if expired and self.notification_service:
            for pending in expired:
                try:
                    await self.notification_service.notify_auto_trade_expired(
                        user_id=pending.user_id,
                        pending_trade_id=pending.id,
                        category=pending.category,
                        symbols=pending.symbols,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send expiry notification for {pending.id}: {e}")

        if expired:
            logger.info(f"Expired {len(expired)} pending auto-trades")
        return len(expired)


class AutoTradeService:
    """Service for processing auto-trades using multi-factor scoring.

    Orchestrates the auto-trade pipeline:
    1. Fetch enhanced recommendations with multi-factor scores
    2. Filter by user-specific confidence thresholds
    3. Create pending trades or execute immediately based on confirmation mode
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.config_service = AutoTradeConfigService(db)
        self.pending_service = PendingAutoTradeService(db)

    async def process_recommendations(
        self,
        category: str,
        symbols: list[str],
        recommendation_date: datetime,
    ) -> dict:
        """Process recommendations for all users with auto-trade enabled.

        Args:
            category: Recommendation category (momentum, breakout, value, sector)
            symbols: List of recommended symbols
            recommendation_date: Date of recommendations

        Returns:
            Summary dict with {user_id: {status, details}}
        """
        from sqlalchemy import func

        from app.modules.screener.models import DailyRecommendation

        results: dict[str, dict] = {}

        # Get all enabled auto-trade configs for this category
        configs_result = await self.db.execute(
            select(AutoTradeConfig).where(
                AutoTradeConfig.category == category,
                AutoTradeConfig.enabled == True,  # noqa: E712
            )
        )
        configs = list(configs_result.scalars().all())

        if not configs:
            logger.info(f"No auto-trade configs enabled for category {category}")
            return {"status": "no_configs", "category": category}

        # Fetch recommendations with multi-factor scores
        rec_result = await self.db.execute(
            select(DailyRecommendation).where(
                func.date(DailyRecommendation.date) == func.date(recommendation_date),
                DailyRecommendation.category == category,
                DailyRecommendation.symbol.in_(symbols),
            )
        )
        recommendations = list(rec_result.scalars().all())

        if not recommendations:
            logger.warning(f"No recommendations found for {category} on {recommendation_date}")
            return {"status": "no_recommendations", "category": category}

        # Process for each user with enabled config
        for config in configs:
            try:
                result = await self._process_user_recommendations(config, recommendations)
                results[config.user_id] = result
            except Exception as e:
                logger.exception(f"Error processing auto-trade for user {config.user_id}: {e}")
                results[config.user_id] = {"status": "error", "error": str(e)}

        return {
            "status": "processed",
            "category": category,
            "users_processed": len(results),
            "results": results,
        }

    async def _process_user_recommendations(
        self,
        config: AutoTradeConfig,
        recommendations: list,
    ) -> dict:
        """Process recommendations for a single user's config.

        Args:
            config: User's auto-trade configuration
            recommendations: List of DailyRecommendation objects

        Returns:
            Result dict with status and details
        """
        # Filter recommendations by confidence threshold
        filtered_recs = []
        for rec in recommendations:
            if self._meets_confidence_threshold(rec, config):
                filtered_recs.append(rec)

        if not filtered_recs:
            return {
                "status": "no_matches",
                "reason": "No recommendations meet confidence threshold",
            }

        # Prepare scores dict for pending trade
        scores = {}
        for rec in filtered_recs:
            scores[rec.symbol] = {
                "technical_score": rec.technical_score,
                "fundamental_score": rec.fundamental_score,
                "sentiment_score": rec.sentiment_score,
                "combined_score": rec.combined_score,
                "direction": rec.signal_direction,
                "confidence": rec.confidence_level,
                "recommended_strategy": rec.recommended_strategy,
                "position_size_multiplier": rec.position_size_multiplier,
            }

        # Get primary strategy type
        primary_strategy = self._get_primary_strategy(filtered_recs)
        symbols = [rec.symbol for rec in filtered_recs]

        # Check confirmation mode
        if config.confirmation_mode == ConfirmationMode.AUTO:
            # Create strategy immediately using template
            template_service = StrategyTemplateService(self.db)

            # Get template - use configured template or find default for category
            template = None
            if config.strategy_template_id:
                template = await template_service.get_template(
                    config.user_id, config.strategy_template_id
                )
            if not template:
                template = await template_service.get_default_for_category(
                    config.user_id, config.category
                )

            if not template:
                return {
                    "status": "error",
                    "reason": "No strategy template configured for auto-trade",
                    "symbols": symbols,
                }

            # Calculate average position multiplier from recommendations
            multipliers = [
                scores[s].get("position_size_multiplier", 1.0) for s in symbols if s in scores
            ]
            avg_multiplier = sum(multipliers) / len(multipliers) if multipliers else 1.0

            # Create strategy from template
            try:
                from datetime import date

                strategy = await template_service.create_strategy_from_template(
                    user_id=config.user_id,
                    template=template,
                    symbols=symbols,
                    name_suffix=f"{config.category}_{date.today().strftime('%Y%m%d')}",
                    position_size_multiplier=avg_multiplier,
                )
                return {
                    "status": "auto_executed",
                    "symbols": symbols,
                    "strategy_type": primary_strategy,
                    "strategy_id": strategy.id,
                    "strategy_name": strategy.name,
                }
            except Exception as e:
                logger.exception(f"Failed to create strategy from template: {e}")
                return {
                    "status": "error",
                    "reason": f"Failed to create strategy: {e}",
                    "symbols": symbols,
                }
        elif config.confirmation_mode == ConfirmationMode.NOTIFY:
            # Create pending trade
            # Get template params if available
            suggested_params = {}
            if config.strategy_template_id:
                template_service = StrategyTemplateService(self.db)
                template = await template_service.get_template(
                    config.user_id, config.strategy_template_id
                )
                if template and template.strategy_params:
                    suggested_params = template.strategy_params

            pending = await self.pending_service.create_pending_trade(
                user_id=config.user_id,
                config=config,
                symbols=symbols,
                scores=scores,
                recommended_strategy_type=primary_strategy,
                suggested_params=suggested_params,
            )
            return {
                "status": "pending_created",
                "pending_trade_id": pending.id,
                "symbols": symbols,
                "strategy_type": primary_strategy,
            }
        else:
            # DISABLED mode
            return {"status": "disabled", "reason": "Auto-trade disabled for this config"}

    def _meets_confidence_threshold(self, rec, config: AutoTradeConfig) -> bool:
        """Check if recommendation meets user's confidence threshold.

        Args:
            rec: DailyRecommendation object
            config: User's auto-trade config

        Returns:
            True if recommendation meets threshold
        """
        # Skip if explicitly marked as skip
        if rec.confidence_level == "skip":
            return False

        # Map confidence level to numeric value
        confidence_values = {
            "high": 80,
            "medium": 60,
            "low": 40,
        }
        rec_confidence = confidence_values.get(rec.confidence_level, 0)

        # Check against user's minimum confidence setting
        return rec_confidence >= config.min_confidence

    def _get_primary_strategy(self, recommendations: list) -> str:
        """Get the most common recommended strategy from filtered recommendations.

        Args:
            recommendations: List of filtered DailyRecommendation objects

        Returns:
            Strategy type string
        """
        strategy_counts: dict[str, int] = {}
        for rec in recommendations:
            strategy = rec.recommended_strategy or "rsi"
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        if not strategy_counts:
            return "rsi"

        # Return most common strategy
        return max(strategy_counts, key=lambda k: strategy_counts[k])
