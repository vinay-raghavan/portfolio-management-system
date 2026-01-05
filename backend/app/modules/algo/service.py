"""Algo trading service for strategy management."""

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import (
    AlgoPosition,
    PositionStatus,
    StrategyExecution,
    StrategyStatus,
    UserStrategy,
)
from app.modules.algo.scheduler import StrategyScheduler
from app.modules.algo.schemas import (
    DailyPnL,
    PnLByStrategyResponse,
    PnLHistoryResponse,
    PnLSummary,
    PositionResponse,
    StrategyCreate,
    StrategyPnL,
    StrategyUpdate,
    UnrealizedPnLPosition,
    UnrealizedPnLResponse,
)

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

    async def get_strategy(
        self, user_id: str, strategy_id: str, load_universe: bool = False
    ) -> UserStrategy | None:
        """Get a strategy by ID for a user."""
        from sqlalchemy.orm import selectinload

        query = select(UserStrategy).where(
            UserStrategy.id == strategy_id,
            UserStrategy.user_id == user_id,
        )
        if load_universe:
            query = query.options(selectinload(UserStrategy.universe))
        result = await self.db.execute(query)
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

    # ============== P&L Methods ==============

    async def get_positions(
        self, user_id: str, strategy_id: str | None = None, status: str | None = None
    ) -> list[PositionResponse]:
        """Get positions for a user, optionally filtered by strategy and status."""
        query = select(AlgoPosition).where(AlgoPosition.user_id == user_id)

        if strategy_id:
            query = query.where(AlgoPosition.strategy_id == strategy_id)

        if status:
            try:
                pos_status = PositionStatus(status.upper())
                query = query.where(AlgoPosition.status == pos_status)
            except ValueError:
                pass  # Invalid status, ignore filter

        query = query.order_by(AlgoPosition.created_at.desc())
        result = await self.db.execute(query)
        positions = result.scalars().all()

        return [
            PositionResponse(
                id=p.id,
                strategy_id=p.strategy_id,
                user_id=p.user_id,
                symbol=p.symbol,
                side=p.side.value,
                status=p.status.value,
                entry_quantity=p.entry_quantity,
                entry_price=p.entry_price,
                entry_at=p.entry_at,
                exit_quantity=p.exit_quantity,
                exit_price=p.exit_price,
                exit_at=p.exit_at,
                remaining_quantity=p.remaining_quantity,
                realized_pnl=p.realized_pnl,
                realized_pnl_percent=p.realized_pnl_percent,
                is_winner=p.is_winner,
                stop_loss=p.stop_loss,
                take_profit=p.take_profit,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in positions
        ]

    async def get_pnl_summary(
        self, user_id: str, current_prices: dict[str, Decimal] | None = None
    ) -> PnLSummary:
        """Get overall P&L summary for a user.

        Args:
            user_id: The user ID
            current_prices: Optional dict mapping symbol to current price for unrealized P&L
        """
        if current_prices is None:
            current_prices = {}

        # Get all positions for the user
        result = await self.db.execute(select(AlgoPosition).where(AlgoPosition.user_id == user_id))
        positions = list(result.scalars().all())

        if not positions:
            return PnLSummary()

        # Calculate metrics
        closed_positions = [p for p in positions if p.status == PositionStatus.CLOSED]
        open_positions = [p for p in positions if p.status == PositionStatus.OPEN]

        total_realized_pnl = sum(p.realized_pnl for p in closed_positions)
        winning_trades = [p for p in closed_positions if p.is_winner is True]
        losing_trades = [p for p in closed_positions if p.is_winner is False]

        win_rate = Decimal("0")
        if closed_positions:
            win_rate = Decimal(len(winning_trades)) / Decimal(len(closed_positions)) * 100

        best_trade_pnl = max((p.realized_pnl for p in closed_positions), default=Decimal("0"))
        worst_trade_pnl = min((p.realized_pnl for p in closed_positions), default=Decimal("0"))
        avg_trade_pnl = (
            total_realized_pnl / len(closed_positions) if closed_positions else Decimal("0")
        )

        # Calculate unrealized P&L for open positions
        total_unrealized_pnl = Decimal("0")
        for p in open_positions:
            current_price = current_prices.get(p.symbol, p.entry_price)
            entry_value = p.entry_price * p.remaining_quantity
            current_value = current_price * p.remaining_quantity

            if p.side.value == "LONG":
                unrealized_pnl = current_value - entry_value
            else:  # SHORT
                unrealized_pnl = entry_value - current_value

            total_unrealized_pnl += unrealized_pnl

        return PnLSummary(
            total_realized_pnl=total_realized_pnl,
            total_unrealized_pnl=total_unrealized_pnl,
            total_pnl=total_realized_pnl + total_unrealized_pnl,
            total_trades=len(closed_positions),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            open_positions=len(open_positions),
            closed_positions=len(closed_positions),
            best_trade_pnl=best_trade_pnl,
            worst_trade_pnl=worst_trade_pnl,
            average_trade_pnl=avg_trade_pnl,
        )

    async def get_pnl_by_strategy(
        self, user_id: str, current_prices: dict[str, Decimal] | None = None
    ) -> PnLByStrategyResponse:
        """Get P&L breakdown by strategy.

        Args:
            user_id: The user ID
            current_prices: Optional dict mapping symbol to current price for unrealized P&L
        """
        if current_prices is None:
            current_prices = {}

        # Get all strategies for the user
        strategies_result = await self.db.execute(
            select(UserStrategy).where(UserStrategy.user_id == user_id)
        )
        strategies = list(strategies_result.scalars().all())

        # Get all positions for the user
        positions_result = await self.db.execute(
            select(AlgoPosition).where(AlgoPosition.user_id == user_id)
        )
        positions = list(positions_result.scalars().all())

        # Group positions by strategy
        positions_by_strategy: dict[str, list[AlgoPosition]] = {}
        for p in positions:
            if p.strategy_id not in positions_by_strategy:
                positions_by_strategy[p.strategy_id] = []
            positions_by_strategy[p.strategy_id].append(p)

        strategy_pnls = []
        total_realized = Decimal("0")
        total_unrealized = Decimal("0")

        for strategy in strategies:
            strat_positions = positions_by_strategy.get(strategy.id, [])
            closed = [p for p in strat_positions if p.status == PositionStatus.CLOSED]
            open_pos = [p for p in strat_positions if p.status == PositionStatus.OPEN]

            realized_pnl = sum(p.realized_pnl for p in closed)
            winning = [p for p in closed if p.is_winner is True]
            losing = [p for p in closed if p.is_winner is False]

            win_rate = Decimal("0")
            if closed:
                win_rate = Decimal(len(winning)) / Decimal(len(closed)) * 100

            # Calculate unrealized P&L for open positions in this strategy
            strategy_unrealized_pnl = Decimal("0")
            for p in open_pos:
                current_price = current_prices.get(p.symbol, p.entry_price)
                entry_value = p.entry_price * p.remaining_quantity
                current_value = current_price * p.remaining_quantity

                if p.side.value == "LONG":
                    unrealized_pnl = current_value - entry_value
                else:  # SHORT
                    unrealized_pnl = entry_value - current_value

                strategy_unrealized_pnl += unrealized_pnl

            strategy_pnls.append(
                StrategyPnL(
                    strategy_id=strategy.id,
                    strategy_name=strategy.name,
                    total_pnl=realized_pnl + strategy_unrealized_pnl,
                    realized_pnl=realized_pnl,
                    unrealized_pnl=strategy_unrealized_pnl,
                    total_trades=len(closed),
                    winning_trades=len(winning),
                    losing_trades=len(losing),
                    win_rate=win_rate,
                    open_positions=len(open_pos),
                    closed_positions=len(closed),
                    status=strategy.status.value,
                )
            )
            total_realized += realized_pnl
            total_unrealized += strategy_unrealized_pnl

        return PnLByStrategyResponse(
            strategies=strategy_pnls,
            total_realized_pnl=total_realized,
            total_unrealized_pnl=total_unrealized,
            total_pnl=total_realized + total_unrealized,
        )

    async def get_pnl_history(self, user_id: str, days: int = 30) -> PnLHistoryResponse:
        """Get P&L history over time for a user."""
        # Get all closed positions for the user
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.user_id == user_id,
                AlgoPosition.status == PositionStatus.CLOSED,
            )
        )
        positions = list(result.scalars().all())

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Group positions by exit date
        pnl_by_date: dict[str, dict] = defaultdict(
            lambda: {"realized_pnl": Decimal("0"), "trades_closed": 0, "trades_opened": 0}
        )

        for p in positions:
            if p.exit_at:
                exit_date_str = p.exit_at.date().isoformat()
                if start_date.isoformat() <= exit_date_str <= end_date.isoformat():
                    pnl_by_date[exit_date_str]["realized_pnl"] += p.realized_pnl
                    pnl_by_date[exit_date_str]["trades_closed"] += 1

            if p.entry_at:
                entry_date_str = p.entry_at.date().isoformat()
                if start_date.isoformat() <= entry_date_str <= end_date.isoformat():
                    pnl_by_date[entry_date_str]["trades_opened"] += 1

        # Build daily P&L list
        daily_pnl = []
        cumulative = Decimal("0")
        total_realized = Decimal("0")
        profitable_days = 0
        losing_days = 0

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            day_data = pnl_by_date.get(date_str, {})
            day_pnl = day_data.get("realized_pnl", Decimal("0"))
            cumulative += day_pnl
            total_realized += day_pnl

            if day_pnl > 0:
                profitable_days += 1
            elif day_pnl < 0:
                losing_days += 1

            daily_pnl.append(
                DailyPnL(
                    date=date_str,
                    realized_pnl=day_pnl,
                    unrealized_pnl=Decimal("0"),
                    total_pnl=day_pnl,
                    trades_opened=day_data.get("trades_opened", 0),
                    trades_closed=day_data.get("trades_closed", 0),
                    cumulative_pnl=cumulative,
                )
            )
            current_date += timedelta(days=1)

        return PnLHistoryResponse(
            daily_pnl=daily_pnl,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            total_realized_pnl=total_realized,
            total_days=days,
            profitable_days=profitable_days,
            losing_days=losing_days,
        )

    async def get_unrealized_pnl(
        self, user_id: str, current_prices: dict[str, Decimal]
    ) -> UnrealizedPnLResponse:
        """Get unrealized P&L for all open positions.

        Args:
            user_id: The user ID
            current_prices: Dict mapping symbol to current price
        """
        # Get all open positions
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.user_id == user_id,
                AlgoPosition.status == PositionStatus.OPEN,
            )
        )
        positions = list(result.scalars().all())

        unrealized_positions = []
        total_unrealized = Decimal("0")
        total_entry_value = Decimal("0")
        total_current_value = Decimal("0")

        for p in positions:
            current_price = current_prices.get(p.symbol, p.entry_price)
            entry_value = p.entry_price * p.remaining_quantity
            current_value = current_price * p.remaining_quantity

            # Calculate unrealized P&L based on position side
            if p.side.value == "LONG":
                unrealized_pnl = current_value - entry_value
            else:  # SHORT
                unrealized_pnl = entry_value - current_value

            unrealized_pnl_percent = (
                (unrealized_pnl / entry_value * 100) if entry_value else Decimal("0")
            )

            unrealized_positions.append(
                UnrealizedPnLPosition(
                    position_id=p.id,
                    strategy_id=p.strategy_id,
                    symbol=p.symbol,
                    side=p.side.value,
                    quantity=p.remaining_quantity,
                    entry_price=p.entry_price,
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_percent=unrealized_pnl_percent,
                    entry_value=entry_value,
                    current_value=current_value,
                )
            )

            total_unrealized += unrealized_pnl
            total_entry_value += entry_value
            total_current_value += current_value

        return UnrealizedPnLResponse(
            positions=unrealized_positions,
            total_unrealized_pnl=total_unrealized,
            total_entry_value=total_entry_value,
            total_current_value=total_current_value,
            positions_count=len(positions),
        )
