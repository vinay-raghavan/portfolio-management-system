"""Strategy scheduler for algo trading.

Manages strategy execution schedules and timing.
"""

import logging
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.models.algo import ScheduleType, StrategyStatus, UserStrategy

logger = logging.getLogger(__name__)

# Indian market hours (IST = UTC + 5:30)
MARKET_OPEN_UTC = time(3, 45)  # 9:15 AM IST
MARKET_CLOSE_UTC = time(10, 0)  # 3:30 PM IST
PRE_MARKET_OPEN_UTC = time(3, 30)  # 9:00 AM IST (pre-market)


class StrategyScheduler:
    """Manages strategy execution scheduling.

    Determines when strategies should run based on their schedule type:
    - INTERVAL: Run every N seconds
    - CRON: Run at specified cron times
    - MARKET_OPEN: Run at market open
    - MARKET_CLOSE: Run before market close
    - CONTINUOUS: Run continuously during market hours
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    @staticmethod
    def is_market_hours(dt: datetime | None = None) -> bool:
        """Check if it's currently market hours (NSE).

        Args:
            dt: DateTime to check (defaults to now)

        Returns:
            True if within market hours
        """
        if dt is None:
            dt = datetime.now(UTC)

        # Check if it's a weekday (0 = Monday, 6 = Sunday)
        if dt.weekday() >= 5:
            return False

        current_time = dt.time()
        return MARKET_OPEN_UTC <= current_time <= MARKET_CLOSE_UTC

    @staticmethod
    def get_next_market_open() -> datetime:
        """Get datetime of next market open."""
        now = datetime.now(UTC)
        market_open_today = now.replace(
            hour=MARKET_OPEN_UTC.hour,
            minute=MARKET_OPEN_UTC.minute,
            second=0,
            microsecond=0,
        )

        if now < market_open_today and now.weekday() < 5:
            return market_open_today

        # Next trading day
        days_ahead = 1
        if now.weekday() == 4:  # Friday
            days_ahead = 3
        elif now.weekday() == 5:  # Saturday
            days_ahead = 2

        return (now + timedelta(days=days_ahead)).replace(
            hour=MARKET_OPEN_UTC.hour,
            minute=MARKET_OPEN_UTC.minute,
            second=0,
            microsecond=0,
        )

    @staticmethod
    def get_next_market_close() -> datetime:
        """Get datetime of next market close."""
        now = datetime.now(UTC)
        market_close_today = now.replace(
            hour=MARKET_CLOSE_UTC.hour,
            minute=MARKET_CLOSE_UTC.minute,
            second=0,
            microsecond=0,
        )

        if now < market_close_today and now.weekday() < 5:
            return market_close_today

        # Next trading day
        days_ahead = 1
        if now.weekday() == 4:  # Friday
            days_ahead = 3
        elif now.weekday() == 5:  # Saturday
            days_ahead = 2

        return (now + timedelta(days=days_ahead)).replace(
            hour=MARKET_CLOSE_UTC.hour,
            minute=MARKET_CLOSE_UTC.minute,
            second=0,
            microsecond=0,
        )

    def calculate_next_run(self, strategy: UserStrategy) -> datetime | None:
        """Calculate the next run time for a strategy.

        Args:
            strategy: The strategy to calculate for

        Returns:
            Next run datetime, or None if can't determine
        """
        now = datetime.now(UTC)
        schedule_type = strategy.schedule_type

        if schedule_type == ScheduleType.MARKET_OPEN:
            return self.get_next_market_open()

        elif schedule_type == ScheduleType.MARKET_CLOSE:
            # Run 5 minutes before close
            close_time = self.get_next_market_close()
            return close_time - timedelta(minutes=5)

        elif schedule_type == ScheduleType.INTERVAL:
            interval = strategy.interval_seconds or 300  # Default 5 minutes
            if strategy.last_run_at:
                return strategy.last_run_at + timedelta(seconds=interval)
            return now

        elif schedule_type == ScheduleType.CONTINUOUS:
            # Run immediately if during market hours, else next market open
            if self.is_market_hours():
                return now
            return self.get_next_market_open()

        elif schedule_type == ScheduleType.CRON:
            # For cron, we'd need croniter library - for now return next minute
            return now.replace(second=0, microsecond=0) + timedelta(minutes=1)

        return None

    async def get_due_strategies(self) -> list[UserStrategy]:
        """Get all strategies that are due to run now."""
        now = datetime.now(UTC)

        result = await self.db.execute(
            select(UserStrategy).where(
                UserStrategy.status == StrategyStatus.ACTIVE,
                UserStrategy.next_run_at <= now,
            )
        )
        return list(result.scalars().all())

    async def get_active_strategies(self) -> list[UserStrategy]:
        """Get all active strategies."""
        result = await self.db.execute(
            select(UserStrategy).where(UserStrategy.status == StrategyStatus.ACTIVE)
        )
        return list(result.scalars().all())

    async def update_next_run(self, strategy: UserStrategy) -> None:
        """Update the next run time for a strategy after execution."""
        strategy.last_run_at = datetime.now(UTC)
        strategy.next_run_at = self.calculate_next_run(strategy)
        await self.db.flush()

    async def enable_strategy(self, strategy: UserStrategy) -> None:
        """Enable a strategy and schedule its next run."""
        strategy.status = StrategyStatus.ACTIVE
        strategy.next_run_at = self.calculate_next_run(strategy)
        await self.db.flush()
        logger.info(f"Strategy {strategy.id} enabled, next run: {strategy.next_run_at}")

    async def disable_strategy(
        self, strategy: UserStrategy, reason: StrategyStatus = StrategyStatus.DISABLED
    ) -> None:
        """Disable a strategy."""
        strategy.status = reason
        strategy.next_run_at = None
        await self.db.flush()
        logger.info(f"Strategy {strategy.id} disabled: {reason.value}")

    async def get_strategy_by_id(
        self, strategy_id: str, load_universe: bool = True
    ) -> UserStrategy | None:
        """Get a strategy by ID."""
        from sqlalchemy.orm import selectinload

        query = select(UserStrategy).where(UserStrategy.id == strategy_id)
        if load_universe:
            query = query.options(selectinload(UserStrategy.universe))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_strategies(self, user_id: str) -> list[UserStrategy]:
        """Get all strategies for a user."""
        result = await self.db.execute(select(UserStrategy).where(UserStrategy.user_id == user_id))
        return list(result.scalars().all())
