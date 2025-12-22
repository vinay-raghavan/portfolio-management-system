"""Algo trading service for strategy management."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import (
    StrategyExecution,
    StrategyStatus,
    UserStrategy,
)
from app.modules.algo.scheduler import StrategyScheduler
from app.modules.algo.schemas import StrategyCreate, StrategyUpdate

logger = logging.getLogger(__name__)


class AlgoService:
    """Service for managing algo trading strategies."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.scheduler = StrategyScheduler(db)

    async def create_strategy(self, user_id: str, data: StrategyCreate) -> UserStrategy:
        """Create a new strategy."""
        strategy = UserStrategy(
            user_id=user_id,
            name=data.name,
            description=data.description,
            strategy_name=data.strategy_type,
            strategy_params=data.strategy_config,
            universe_id=data.universe_id,
            custom_symbols=data.symbols,
            schedule_type=data.schedule_type,
            interval_seconds=data.interval_seconds,
            cron_expression=data.cron_expression,
            position_sizing_method=data.position_sizing_method,
            portfolio_percent=data.position_size_value,
            max_position_value=data.max_position_value,
            max_daily_loss=data.max_daily_loss,
            max_consecutive_losses=data.max_consecutive_losses,
            is_paper_trading=data.is_paper_trading,
            status=StrategyStatus.DISABLED,
        )
        self.db.add(strategy)
        await self.db.flush()
        await self.db.refresh(strategy)
        logger.info(f"Created strategy {strategy.id}: {strategy.name}")
        return strategy

    async def get_strategy(self, user_id: str, strategy_id: str) -> UserStrategy | None:
        """Get a strategy by ID for a user."""
        result = await self.db.execute(
            select(UserStrategy).where(
                UserStrategy.id == strategy_id,
                UserStrategy.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_strategies(
        self, user_id: str, status_filter: StrategyStatus | None = None
    ) -> list[UserStrategy]:
        """Get all strategies for a user."""
        query = select(UserStrategy).where(UserStrategy.user_id == user_id)
        if status_filter:
            query = query.where(UserStrategy.status == status_filter)
        result = await self.db.execute(query.order_by(UserStrategy.created_at.desc()))
        return list(result.scalars().all())

    async def update_strategy(
        self, user_id: str, strategy_id: str, data: StrategyUpdate
    ) -> UserStrategy | None:
        """Update a strategy."""
        strategy = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(strategy, field, value)

        await self.db.flush()
        await self.db.refresh(strategy)
        return strategy

    async def delete_strategy(self, user_id: str, strategy_id: str) -> bool:
        """Delete a strategy."""
        strategy = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return False

        await self.db.delete(strategy)
        await self.db.flush()
        return True

    async def enable_strategy(self, user_id: str, strategy_id: str) -> UserStrategy | None:
        """Enable a strategy for execution."""
        strategy = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return None

        await self.scheduler.enable_strategy(strategy)
        await self.db.refresh(strategy)
        logger.info(f"Enabled strategy {strategy_id}")
        return strategy

    async def disable_strategy(self, user_id: str, strategy_id: str) -> UserStrategy | None:
        """Disable a strategy."""
        strategy = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return None

        await self.scheduler.disable_strategy(strategy)
        await self.db.refresh(strategy)
        logger.info(f"Disabled strategy {strategy_id}")
        return strategy

    async def disable_all_strategies(self, user_id: str) -> int:
        """Disable all active strategies for a user. Returns count disabled."""
        result = await self.db.execute(
            select(UserStrategy).where(
                UserStrategy.user_id == user_id,
                UserStrategy.status == StrategyStatus.ACTIVE,
            )
        )
        strategies = result.scalars().all()

        for strategy in strategies:
            await self.scheduler.disable_strategy(strategy, StrategyStatus.KILLED)

        return len(strategies)

    async def get_execution_history(
        self, user_id: str, strategy_id: str, limit: int = 50
    ) -> list[StrategyExecution]:
        """Get execution history for a strategy."""
        # Verify ownership
        strategy = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return []

        result = await self.db.execute(
            select(StrategyExecution)
            .where(StrategyExecution.strategy_id == strategy_id)
            .order_by(StrategyExecution.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_active_strategies_count(self, user_id: str) -> int:
        """Get count of active strategies for a user."""
        result = await self.db.execute(
            select(UserStrategy).where(
                UserStrategy.user_id == user_id,
                UserStrategy.status == StrategyStatus.ACTIVE,
            )
        )
        return len(result.scalars().all())
