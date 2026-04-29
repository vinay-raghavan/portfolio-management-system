"""Auto-trade service for managing recommendation-to-strategy pipeline.

This service handles:
- Auto-trade configuration management
- Strategy template management
- Pending auto-trade queue management
- Processing recommendations into strategies
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from shared.strategies import StrategyRegistry
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import (
    AlgoPosition,
    AutoTradeConfig,
    ConfirmationMode,
    PendingAutoTrade,
    PendingTradeStatus,
    PositionSizingMethod,
    PositionStatus,
    ScheduleType,
    ScreenerSourceType,
    SignalDirection,
    StrategyProductType,
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

    async def find_or_create_strategy_for_screener(
        self,
        user_id: str,
        screener_id: str,
        screener_name: str,
        config: "AutoTradeConfig",
        symbols: list[str],
        strategy_type: str = "momentum",
    ) -> tuple["UserStrategy", bool]:
        """Find existing strategy linked to screener or create new one.

        If strategy exists and sync_from_screener is True, updates its settings
        from the auto_trade_config master settings.

        Args:
            user_id: User ID
            screener_id: Custom screener ID
            screener_name: Screener name for strategy naming
            config: AutoTradeConfig with master settings
            symbols: List of symbols to trade
            strategy_type: Type of strategy (momentum, pullback, etc.)

        Returns:
            Tuple of (strategy, created) where created is True if new strategy
        """
        from datetime import date

        # Try to find existing strategy linked to this screener
        result = await self.db.execute(
            select(UserStrategy).where(
                UserStrategy.user_id == user_id,
                UserStrategy.linked_screener_id == screener_id,
            )
        )
        existing_strategy = result.scalar_one_or_none()

        if existing_strategy:
            # Strategy exists - update settings if sync is enabled
            if existing_strategy.sync_from_screener:
                existing_strategy.signal_direction = config.signal_direction
                existing_strategy.product_type = config.product_type
                existing_strategy.max_open_positions = config.max_positions_per_day or 5
                existing_strategy.custom_symbols = symbols
                existing_strategy.status = StrategyStatus.ACTIVE
                await self.db.flush()
                logger.info(
                    f"Updated linked strategy '{existing_strategy.name}' "
                    f"with screener settings (direction={config.signal_direction.value})"
                )
            else:
                logger.info(
                    f"Strategy '{existing_strategy.name}' is unsynced, skipping update entirely"
                )
                # Do NOT overwrite symbols for unsynced strategies
                # Manual symbol curation should be preserved

            return existing_strategy, False

        # Create new strategy linked to screener
        name_slug = screener_name.lower().replace(" ", "_")
        strategy_name = f"{name_slug}_{date.today().strftime('%Y%m%d')}"

        strategy = UserStrategy(
            user_id=user_id,
            name=strategy_name,
            description=f"Auto-created from screener '{screener_name}'",
            strategy_name=strategy_type,
            strategy_params={},
            custom_symbols=symbols,
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=300,  # Check every 5 minutes
            signal_direction=config.signal_direction,
            product_type=config.product_type,
            position_sizing_method=PositionSizingMethod.PORTFOLIO_PERCENT,
            portfolio_percent=Decimal("3.0"),
            max_open_positions=config.max_positions_per_day or 5,
            is_paper_trading=True,
            status=StrategyStatus.ACTIVE,
            # Link to screener
            linked_screener_id=screener_id,
            sync_from_screener=True,
        )
        self.db.add(strategy)
        await self.db.flush()
        logger.info(
            f"Created strategy '{strategy_name}' linked to screener '{screener_name}' "
            f"(direction={config.signal_direction.value})"
        )
        return strategy, True


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

    async def get_config_for_screener(
        self, user_id: str, screener_id: str
    ) -> AutoTradeConfig | None:
        """Get auto-trade config for a specific saved screener.

        Returns the first matching config (should be unique per user+screener).
        """
        result = await self.db.execute(
            select(AutoTradeConfig).where(
                AutoTradeConfig.user_id == user_id,
                AutoTradeConfig.saved_screener_id == screener_id,
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
            product_type=StrategyProductType(data.product_type),
            signal_direction=SignalDirection(data.signal_direction),
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
        if "product_type" in update_fields and update_fields["product_type"]:
            update_fields["product_type"] = StrategyProductType(update_fields["product_type"])
        if "signal_direction" in update_fields and update_fields["signal_direction"]:
            update_fields["signal_direction"] = SignalDirection(update_fields["signal_direction"])

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

    async def _find_existing_strategy_for_screener(
        self, user_id: str, screener_id: str | None
    ) -> UserStrategy | None:
        """Find an existing strategy linked to a screener.

        First checks the linked_screener_id field (new approach),
        then falls back to checking strategy_params (legacy).
        """
        if not screener_id:
            return None

        # First, check for strategy with linked_screener_id (new approach)
        result = await self.db.execute(
            select(UserStrategy).where(
                and_(
                    UserStrategy.user_id == user_id,
                    UserStrategy.linked_screener_id == screener_id,
                )
            )
        )
        strategy = result.scalar_one_or_none()
        if strategy:
            return strategy

        # Fallback: Check strategy_params for screener_id (legacy)
        result = await self.db.execute(
            select(UserStrategy).where(
                and_(
                    UserStrategy.user_id == user_id,
                    UserStrategy.strategy_params.isnot(None),
                )
            )
        )
        strategies = result.scalars().all()

        for strategy in strategies:
            params = strategy.strategy_params or {}
            if (
                params.get("source") == "auto_trade_screener"
                and params.get("screener_id") == screener_id
            ):
                # Migrate: set linked_screener_id for future lookups
                strategy.linked_screener_id = screener_id
                strategy.sync_from_screener = True
                await self.db.flush()
                logger.info(f"Migrated strategy {strategy.id} to use linked_screener_id")
                return strategy

        return None

    async def _get_open_position_symbols(self, strategy_id: str) -> set[str]:
        """Get symbols with open positions for a strategy."""
        result = await self.db.execute(
            select(AlgoPosition.symbol).where(
                and_(
                    AlgoPosition.strategy_id == strategy_id,
                    AlgoPosition.status.in_([PositionStatus.OPEN, PositionStatus.PARTIAL]),
                )
            )
        )
        return set(result.scalars().all())

    @staticmethod
    def _timeframe_to_interval_seconds(timeframe: str) -> int | None:
        """Convert a timeframe like 5m/15m/1h to seconds."""
        normalized = (timeframe or "").strip().lower()
        if not normalized:
            return None

        if normalized.endswith("m") and normalized[:-1].isdigit():
            return int(normalized[:-1]) * 60
        if normalized.endswith("h") and normalized[:-1].isdigit():
            return int(normalized[:-1]) * 3600
        return None

    @classmethod
    def _resolve_auto_trade_schedule(
        cls, strategy_name: str | None
    ) -> tuple[ScheduleType, int | None, str]:
        """Resolve schedule settings from strategy default timeframe."""
        default_timeframe = "1d"

        if strategy_name and StrategyRegistry.has_strategy(strategy_name):
            strategy_class = StrategyRegistry.get_class(strategy_name)
            if strategy_class and getattr(strategy_class, "default_timeframe", None):
                default_timeframe = str(strategy_class.default_timeframe)

        interval_seconds = cls._timeframe_to_interval_seconds(default_timeframe)
        if interval_seconds:
            # Intraday strategies should run on interval instead of continuous polling.
            return ScheduleType.INTERVAL, max(60, interval_seconds), default_timeframe

        # Daily/weekly/monthly strategies run once at market open by default.
        return ScheduleType.MARKET_OPEN, None, default_timeframe

    async def approve_pending_trade(
        self, user_id: str, trade_id: str
    ) -> tuple[PendingAutoTrade | None, str | None]:
        """Approve a pending auto-trade and create or update a strategy.

        If an existing strategy exists for this screener, updates its symbols:
        - New symbols are added to custom_symbols
        - Removed symbols with open positions are moved to exit_only_symbols
        - Removed symbols without positions are dropped

        If no existing strategy, creates a new one.

        Returns:
            Tuple of (updated pending trade, created/updated strategy ID or error message)
        """
        pending = await self.get_pending_trade(user_id, trade_id)
        if not pending:
            return None, "Pending trade not found"

        if pending.status != PendingTradeStatus.PENDING:
            return pending, f"Trade already {pending.status.value}"

        if datetime.now(UTC) > pending.expires_at:
            pending.status = PendingTradeStatus.EXPIRED
            await self.db.flush()
            return pending, "Trade has expired"

        # Extract screener_id to check for existing strategy
        screener_id = (
            pending.suggested_params.get("screener_id") if pending.suggested_params else None
        )

        # Fetch screener name for strategy naming
        screener_name = None
        if screener_id:
            from app.modules.screener.models import CustomScreener

            result = await self.db.execute(
                select(CustomScreener.name).where(CustomScreener.id == screener_id)
            )
            screener_name = result.scalar_one_or_none()

        # Fetch AutoTradeConfig to get product_type and signal_direction
        config_result = await self.db.execute(
            select(AutoTradeConfig).where(
                and_(
                    AutoTradeConfig.user_id == user_id,
                    AutoTradeConfig.category == pending.category,
                )
            )
        )
        auto_trade_config = config_result.scalar_one_or_none()

        strategy_type = pending.recommended_strategy_type or "ma_crossover"
        resolved_schedule_type, resolved_interval_seconds, resolved_timeframe = (
            self._resolve_auto_trade_schedule(strategy_type)
        )

        # Check for existing strategy linked to this screener
        existing_strategy = await self._find_existing_strategy_for_screener(user_id, screener_id)

        created_strategy_id = None

        if pending.scores and pending.symbols:
            # Calculate aggregated metrics from per-symbol scores
            scores_list = list(pending.scores.values())
            num_symbols = len(scores_list)

            # Average position size multiplier across all symbols
            avg_position_multiplier = (
                sum(s.get("position_size_multiplier", 1.0) for s in scores_list) / num_symbols
            )

            # Average scores for strategy tuning
            avg_technical = sum(s.get("technical_score", 50) for s in scores_list) / num_symbols
            avg_fundamental = sum(s.get("fundamental_score", 50) for s in scores_list) / num_symbols
            avg_combined = sum(s.get("combined_score", 50) for s in scores_list) / num_symbols

            # Determine confidence level (most common among symbols)
            confidence_counts: dict[str, int] = {}
            for s in scores_list:
                conf = s.get("confidence_level", "medium")
                confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
            dominant_confidence = max(confidence_counts, key=lambda k: confidence_counts[k])

            # Calculate position size based on confidence and scores
            # Base position: 5%, adjusted by confidence and position multiplier
            base_position_pct = 5.0
            if dominant_confidence == "high":
                confidence_factor = 1.2
            elif dominant_confidence == "low":
                confidence_factor = 0.8
            else:
                confidence_factor = 1.0

            adjusted_position_pct = base_position_pct * avg_position_multiplier * confidence_factor
            # Cap at reasonable limits
            adjusted_position_pct = max(1.0, min(adjusted_position_pct, 10.0))

            # Dynamic stop-loss based on technical score (higher score = tighter stop)
            # Technical score 80+ -> 1.5% stop, 60 -> 2.5% stop, 40 -> 3.5% stop
            stop_loss_pct = max(1.5, 4.0 - (avg_technical / 40.0))

            # Dynamic take-profit based on combined score
            # Higher combined score = more aggressive take profit
            take_profit_pct = max(3.0, min(8.0, avg_combined / 10.0))

            # Strategy params include source data for traceability
            strategy_params = {
                "source": "auto_trade_screener",
                "screener_id": screener_id,
                "pending_trade_id": str(pending.id),
                "avg_technical_score": round(avg_technical, 2),
                "avg_fundamental_score": round(avg_fundamental, 2),
                "avg_combined_score": round(avg_combined, 2),
                "dominant_confidence": dominant_confidence,
                "recommendation_date": pending.recommendation_date.isoformat(),
            }

            from decimal import Decimal

            new_symbols = set(pending.symbols)

            if existing_strategy:
                # UPDATE EXISTING STRATEGY
                # Calculate symbol transitions
                current_symbols = set(existing_strategy.custom_symbols or [])
                current_exit_only = set(existing_strategy.exit_only_symbols or [])

                # Get symbols with open positions
                open_position_symbols = await self._get_open_position_symbols(existing_strategy.id)

                # Removed symbols = in current but not in new
                removed_symbols = current_symbols - new_symbols

                # Symbols to move to exit_only = removed symbols with open positions
                new_exit_only_symbols = removed_symbols & open_position_symbols

                # Also keep existing exit_only symbols that still have positions
                retained_exit_only = current_exit_only & open_position_symbols

                # Final exit_only_symbols = new + retained (still with positions)
                final_exit_only = new_exit_only_symbols | retained_exit_only

                # Update the strategy
                existing_strategy.custom_symbols = list(new_symbols)
                existing_strategy.exit_only_symbols = (
                    list(final_exit_only) if final_exit_only else []
                )

                # Update strategy params with latest scores
                existing_params = existing_strategy.strategy_params or {}
                existing_params.update(strategy_params)
                existing_strategy.strategy_params = existing_params

                # Update description
                existing_strategy.description = (
                    f"Auto-generated from screener, updated on {pending.recommendation_date.strftime('%Y-%m-%d')}. "
                    f"Symbols: {len(new_symbols)}, Exit-only: {len(final_exit_only)}, Avg Score: {avg_combined:.1f}"
                )

                # Update next_run_at for immediate execution
                existing_strategy.next_run_at = datetime.now(UTC)

                # === SYNC SETTINGS FROM SCREENER (if enabled) ===
                if existing_strategy.sync_from_screener and auto_trade_config:
                    # Override strategy settings with screener master settings
                    existing_strategy.signal_direction = auto_trade_config.signal_direction
                    existing_strategy.product_type = auto_trade_config.product_type
                    existing_strategy.max_open_positions = (
                        auto_trade_config.max_positions_per_day or 5
                    )
                    logger.info(
                        f"Synced strategy settings from screener: "
                        f"direction={auto_trade_config.signal_direction.value}, "
                        f"product={auto_trade_config.product_type.value}"
                    )

                # Fix old auto-generated schedule/timeframe skew (CONTINUOUS + 1d).
                # Keep user-customized schedules intact.
                if (
                    existing_strategy.schedule_type == ScheduleType.CONTINUOUS
                    and existing_strategy.timeframe == "1d"
                ):
                    existing_strategy.schedule_type = resolved_schedule_type
                    existing_strategy.interval_seconds = (
                        resolved_interval_seconds
                        if resolved_schedule_type == ScheduleType.INTERVAL
                        else None
                    )
                    existing_strategy.timeframe = resolved_timeframe

                await self.db.flush()
                created_strategy_id = existing_strategy.id
                pending.created_strategy_id = created_strategy_id

                logger.info(
                    f"Updated existing strategy {existing_strategy.id} from pending trade {trade_id}. "
                    f"New symbols: {len(new_symbols)}, removed: {len(removed_symbols)}, "
                    f"exit_only: {len(final_exit_only)}"
                )
            else:
                # CREATE NEW STRATEGY
                # Use screener name if available, otherwise fall back to category
                name_prefix = screener_name or pending.category
                # Sanitize name: replace spaces with underscores, keep it concise
                name_prefix = name_prefix.replace(" ", "_")[:30]
                strategy_name_display = (
                    f"{name_prefix}_{pending.recommendation_date.strftime('%Y%m%d')}"
                )

                # Default profit booking rules: 25% at 1%, 25% at 5%, 25% at 10%, 25% at 15%
                default_profit_booking = [
                    {"profit_percent": 1.0, "book_percent": 25.0},
                    {"profit_percent": 5.0, "book_percent": 25.0},
                    {"profit_percent": 10.0, "book_percent": 25.0},
                    {"profit_percent": 15.0, "book_percent": 25.0},
                ]

                # Get product_type and signal_direction from auto-trade config
                # Default to DELIVERY/LONG if config not found
                product_type = StrategyProductType.DELIVERY
                signal_direction = SignalDirection.LONG
                if auto_trade_config:
                    product_type = auto_trade_config.product_type
                    signal_direction = auto_trade_config.signal_direction
                    logger.info(
                        f"Using auto-trade config: product_type={product_type.value}, "
                        f"signal_direction={signal_direction.value}"
                    )

                strategy = UserStrategy(
                    user_id=user_id,
                    name=strategy_name_display,
                    description=f"Auto-generated from screener on {pending.recommendation_date.strftime('%Y-%m-%d')}. "
                    f"Symbols: {len(pending.symbols)}, Avg Score: {avg_combined:.1f}",
                    strategy_name=strategy_type,
                    status=StrategyStatus.DISABLED,  # Start disabled, user can enable
                    is_paper_trading=True,  # Start with paper trading for safety
                    strategy_params=strategy_params,
                    custom_symbols=pending.symbols,
                    exit_only_symbols=[],  # No exit-only symbols for new strategy
                    schedule_type=resolved_schedule_type,
                    interval_seconds=(
                        resolved_interval_seconds
                        if resolved_schedule_type == ScheduleType.INTERVAL
                        else None
                    ),
                    timeframe=resolved_timeframe,
                    next_run_at=datetime.now(UTC),  # Execute immediately when enabled
                    # Position sizing
                    position_sizing_method=PositionSizingMethod.PERCENT_OF_PORTFOLIO,
                    portfolio_percent=Decimal(str(round(adjusted_position_pct, 2))),
                    risk_per_trade_percent=Decimal(str(round(stop_loss_pct, 2))),
                    # Fixed SL/TP as backstop (stored as decimal, e.g. 0.02 = 2%)
                    default_stop_loss_pct=Decimal(str(round(stop_loss_pct / 100, 4))),
                    default_take_profit_pct=Decimal(str(round(take_profit_pct / 100, 4))),
                    # Risk controls
                    max_daily_trades=10,
                    max_daily_loss=Decimal("5000.00"),
                    max_open_positions=min(len(pending.symbols), 5),  # Up to 5 positions
                    max_consecutive_losses=3,
                    max_drawdown_percent=Decimal("10.00"),
                    # Trailing stop: 1%
                    default_trailing_stop_enabled=True,
                    default_trailing_stop_pct=Decimal("0.01"),  # 1%
                    # Profit booking rules
                    default_profit_booking_rules=default_profit_booking,
                    # Product type and signal direction from auto-trade config
                    product_type=product_type,
                    signal_direction=signal_direction,
                    # Link to screener for future settings sync
                    linked_screener_id=screener_id,
                    sync_from_screener=True,
                )

                self.db.add(strategy)
                await self.db.flush()
                created_strategy_id = strategy.id
                pending.created_strategy_id = created_strategy_id

                logger.info(
                    f"Created strategy {strategy.id} from pending trade {trade_id} "
                    f"with {len(pending.symbols)} symbols, position={adjusted_position_pct:.2f}%, "
                    f"stop_loss={stop_loss_pct:.2f}%, take_profit={take_profit_pct:.2f}%"
                )
        else:
            logger.warning(
                f"No scores or symbols in pending trade {trade_id}, cannot create strategy"
            )

        # Mark as approved
        pending.status = PendingTradeStatus.APPROVED
        pending.actioned_at = datetime.now(UTC)
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
