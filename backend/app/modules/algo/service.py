"""Algo trading service for strategy management."""

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from shared.providers.schemas import ProductType
from shared.strategies import StrategyRegistry
from shared.strategies.registry import METADATA_KEYS
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import (
    AlgoPosition,
    PositionSide,
    PositionStatus,
    StrategyExecution,
    StrategyStatus,
    UserStrategy,
)
from app.modules.algo.scheduler import StrategyScheduler
from app.modules.algo.schemas import (
    ClosePositionResponse,
    DailyPnL,
    PnLByStrategyResponse,
    PnLHistoryResponse,
    PnLSummary,
    PositionResponse,
    SquareOffStrategyResponse,
    StrategyCreate,
    StrategyPnL,
    StrategyUpdate,
    UnrealizedPnLPosition,
    UnrealizedPnLResponse,
)
from app.modules.portfolio.schemas import (
    ProfitBookingRules,
    ProfitLockConfig,
    ProfitLockUpdate,
    TrailingStopConfig,
    TrailingStopUpdate,
)
from app.providers.funds_provider import DatabaseFundsProvider

logger = logging.getLogger(__name__)


class AlgoService:
    """Service for managing algo trading strategies."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.scheduler = StrategyScheduler(db)

    async def create_strategy(self, user_id: str, data: StrategyCreate) -> UserStrategy:
        """Create a new strategy."""
        # Validate strategy type exists
        if not StrategyRegistry.has_strategy(data.strategy_type):
            raise ValueError(f"Unknown strategy type: {data.strategy_type}")

        # Validate strategy parameters if provided
        if data.strategy_config:
            is_valid, errors = StrategyRegistry.validate_params(
                data.strategy_type, data.strategy_config
            )
            if not is_valid:
                raise ValueError(f"Invalid strategy parameters: {'; '.join(errors)}")

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
            max_daily_profit=data.max_daily_profit,
            overall_profit_target=data.overall_profit_target,
            profit_cutoff_action=data.profit_cutoff_action,
            is_paper_trading=data.is_paper_trading,
            product_type=data.product_type,
            default_trailing_stop_enabled=data.default_trailing_stop_enabled,
            default_trailing_stop_pct=data.default_trailing_stop_pct,
            default_profit_booking_rules=(
                data.default_profit_booking_rules.model_dump(mode="json")
                if data.default_profit_booking_rules
                else None
            ),
            # Trading time window fields
            trading_start_time=data.trading_start_time,
            trading_end_time=data.trading_end_time,
            trading_timezone=data.trading_timezone,
            active_trading_days=data.active_trading_days,
            status=StrategyStatus.DISABLED,
        )
        self.db.add(strategy)
        await self.db.flush()
        await self.db.refresh(strategy)
        logger.info(f"Created strategy {strategy.id}: {strategy.name}")
        return strategy

    async def get_strategy(
        self,
        user_id: str,
        strategy_id: str,
        load_universe: bool = False,
        load_recent_executions: bool = False,
    ) -> tuple[UserStrategy | None, list[StrategyExecution]]:
        """Get a strategy by ID for a user.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            load_universe: Whether to eager-load universe
            load_recent_executions: Whether to load recent executions with orders

        Returns:
            Tuple of (strategy, recent_executions)
        """
        from sqlalchemy.orm import selectinload

        query = select(UserStrategy).where(
            UserStrategy.id == strategy_id,
            UserStrategy.user_id == user_id,
        )
        if load_universe:
            query = query.options(selectinload(UserStrategy.universe))
        # Note: We don't eager-load executions here anymore - use optimized loading instead
        result = await self.db.execute(query)
        strategy = result.scalar_one_or_none()

        recent_executions: list[StrategyExecution] = []
        if strategy and load_recent_executions:
            # Load only 5 most recent executions (much faster than loading all)
            executions_map = await self._load_recent_executions_optimized([strategy], limit=5)
            recent_executions = executions_map.get(strategy.id, [])

        return strategy, recent_executions

    async def get_user_strategies(
        self,
        user_id: str,
        status_filter: StrategyStatus | None = None,
        load_recent_executions: bool = False,
    ) -> tuple[list[UserStrategy], dict[str, list[StrategyExecution]]]:
        """Get all strategies for a user.

        Args:
            user_id: User ID
            status_filter: Optional filter by strategy status
            load_recent_executions: Whether to load recent executions with orders

        Returns:
            Tuple of (strategies, executions_map) where executions_map maps strategy_id -> executions
        """
        query = select(UserStrategy).where(UserStrategy.user_id == user_id)
        if status_filter:
            query = query.where(UserStrategy.status == status_filter)
        # Note: We don't eager-load executions here anymore - too slow for large datasets
        # Instead, we load them separately with LIMIT per strategy
        result = await self.db.execute(query.order_by(UserStrategy.created_at.desc()))
        strategies = list(result.scalars().all())

        executions_map: dict[str, list[StrategyExecution]] = {}
        if load_recent_executions and strategies:
            # Load only 5 most recent executions per strategy (much faster than loading all)
            executions_map = await self._load_recent_executions_optimized(strategies, limit=5)

        return strategies, executions_map

    async def _load_recent_executions_optimized(
        self, strategies: list[UserStrategy], limit: int = 5
    ) -> dict[str, list[StrategyExecution]]:
        """Load recent executions for strategies efficiently with LIMIT.

        Uses a single query with ROW_NUMBER() to get top N executions per strategy,
        instead of loading ALL executions and slicing in Python.

        Returns:
            Dictionary mapping strategy_id -> list of recent executions
        """
        from sqlalchemy import func as sqla_func
        from sqlalchemy.orm import selectinload

        strategy_ids = [s.id for s in strategies]
        if not strategy_ids:
            return {}

        # Use a subquery with row_number to get only the N most recent executions per strategy
        # This is much faster than loading all executions
        row_num = (
            sqla_func.row_number()
            .over(
                partition_by=StrategyExecution.strategy_id,
                order_by=StrategyExecution.started_at.desc(),
            )
            .label("row_num")
        )
        subq = (
            select(StrategyExecution.id, row_num)
            .where(StrategyExecution.strategy_id.in_(strategy_ids))
            .subquery()
        )
        # Get execution IDs that are in the top N per strategy
        top_exec_ids_query = select(subq.c.id).where(subq.c.row_num <= limit)
        top_exec_ids_result = await self.db.execute(top_exec_ids_query)
        top_exec_ids = [r[0] for r in top_exec_ids_result.fetchall()]

        if not top_exec_ids:
            return {}

        # Load only those executions with their orders
        exec_result = await self.db.execute(
            select(StrategyExecution)
            .options(selectinload(StrategyExecution.algo_orders))
            .where(StrategyExecution.id.in_(top_exec_ids))
            .order_by(StrategyExecution.started_at.desc())
        )
        all_executions = list(exec_result.scalars().all())

        # Group executions by strategy_id
        exec_by_strategy: dict[str, list[StrategyExecution]] = {}
        for ex in all_executions:
            exec_by_strategy.setdefault(ex.strategy_id, []).append(ex)

        # Sort each group by started_at descending
        for execs in exec_by_strategy.values():
            execs.sort(key=lambda e: e.started_at, reverse=True)

        return exec_by_strategy

    async def update_strategy(
        self, user_id: str, strategy_id: str, data: StrategyUpdate
    ) -> UserStrategy | None:
        """Update a strategy."""
        strategy, _ = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return None

        # Validate strategy parameters if being updated
        if data.strategy_config is not None:
            # Auto-trade metadata keys that should be excluded from validation
            # These are stored alongside strategy params for traceability
            auto_trade_metadata_keys = {
                "screener_id",
                "pending_trade_id",
                "recommendation_date",
                "dominant_confidence",
                "avg_technical_score",
                "avg_fundamental_score",
                "avg_combined_score",
                "avg_position_size_multiplier",
            }
            # Combine with METADATA_KEYS from the registry
            all_metadata_keys = METADATA_KEYS | auto_trade_metadata_keys

            # Check if this is a composite strategy config (has components key)
            if "components" in data.strategy_config:
                # Composite strategy config - validate component structure
                components = data.strategy_config.get("components", [])
                if not isinstance(components, list) or len(components) < 2:
                    raise ValueError("Composite strategy requires at least 2 components")
                # Validate each component has a strategy name
                for i, comp in enumerate(components):
                    if not isinstance(comp, dict) or not comp.get("strategy"):
                        raise ValueError(f"Component {i + 1} must have a strategy name")
                    # Optionally validate component strategy params if provided
                    comp_strategy = comp.get("strategy")
                    comp_params = comp.get("params", {})
                    if comp_params and StrategyRegistry.has_strategy(comp_strategy):
                        is_valid, errors = StrategyRegistry.validate_params(
                            comp_strategy, comp_params
                        )
                        if not is_valid:
                            raise ValueError(
                                f"Invalid parameters for component '{comp_strategy}': {'; '.join(errors)}"
                            )
            else:
                # Regular strategy parameter validation
                # Filter out metadata keys before validation
                config_to_validate = {
                    k: v for k, v in data.strategy_config.items() if k not in all_metadata_keys
                }
                if config_to_validate:
                    is_valid, errors = StrategyRegistry.validate_params(
                        strategy.strategy_name, config_to_validate
                    )
                    if not is_valid:
                        raise ValueError(f"Invalid strategy parameters: {'; '.join(errors)}")

        update_data = data.model_dump(exclude_unset=True)

        # Handle special field mappings
        field_mappings = {
            "strategy_config": "strategy_params",
            "symbols": "custom_symbols",
            "position_size_value": "portfolio_percent",
        }

        for field, value in update_data.items():
            # Apply field mapping if exists
            model_field = field_mappings.get(field, field)

            # Handle default_profit_booking_rules - convert Decimals to JSON-serializable types
            if field == "default_profit_booking_rules" and value is not None:
                # Use model_dump with mode="json" to convert Decimals to floats
                if data.default_profit_booking_rules is not None:
                    value = data.default_profit_booking_rules.model_dump(mode="json")
                setattr(strategy, model_field, value)
            else:
                setattr(strategy, model_field, value)

        await self.db.flush()
        await self.db.refresh(strategy)
        return strategy

    async def delete_strategy(self, user_id: str, strategy_id: str) -> bool:
        """Delete a strategy."""
        strategy, _ = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return False

        await self.db.delete(strategy)
        await self.db.flush()
        return True

    async def enable_strategy(self, user_id: str, strategy_id: str) -> UserStrategy | None:
        """Enable a strategy for execution."""
        strategy, _ = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return None

        await self.scheduler.enable_strategy(strategy)
        await self.db.refresh(strategy)
        logger.info(f"Enabled strategy {strategy_id}")
        return strategy

    async def disable_strategy(self, user_id: str, strategy_id: str) -> UserStrategy | None:
        """Disable a strategy."""
        strategy, _ = await self.get_strategy(user_id, strategy_id)
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
        """Get execution history for a strategy with order details.

        Returns execution records with eager-loaded algo_orders containing
        symbol, price, quantity, side, filled_price, filled_quantity, etc.
        """
        from sqlalchemy.orm import selectinload

        # Verify ownership
        strategy, _ = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return []

        result = await self.db.execute(
            select(StrategyExecution)
            .options(selectinload(StrategyExecution.algo_orders))
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
        self,
        user_id: str,
        strategy_id: str | None = None,
        status: str | None = None,
        current_prices: dict[str, Decimal] | None = None,
    ) -> list[PositionResponse]:
        """Get positions for a user, optionally filtered by strategy and status.

        Args:
            user_id: User ID
            strategy_id: Optional strategy ID filter
            status: Optional status filter (OPEN, CLOSED, PARTIAL)
            current_prices: Optional dict of symbol -> current price for unrealized P&L
        """
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

        responses = []
        for p in positions:
            # Calculate unrealized P&L for open positions
            current_price = None
            unrealized_pnl = None
            unrealized_pnl_percent = None

            # Calculate unrealized P&L for positions with remaining quantity (OPEN or PARTIAL)
            if p.status in (PositionStatus.OPEN, PositionStatus.PARTIAL) and current_prices:
                current_price = current_prices.get(p.symbol)
                if current_price is not None and p.remaining_quantity > 0:
                    if p.side == PositionSide.LONG:
                        unrealized_pnl = (current_price - p.entry_price) * p.remaining_quantity
                    else:  # SHORT
                        unrealized_pnl = (p.entry_price - current_price) * p.remaining_quantity

                    entry_value = p.entry_price * p.remaining_quantity
                    if entry_value > 0:
                        unrealized_pnl_percent = (unrealized_pnl / entry_value) * 100

            responses.append(
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
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_percent=unrealized_pnl_percent,
                    is_winner=p.is_winner,
                    stop_loss=p.stop_loss,
                    take_profit=p.take_profit,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
            )

        return responses

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
        partial_positions = [p for p in positions if p.status == PositionStatus.PARTIAL]
        # Include both OPEN and PARTIAL positions for unrealized P&L calculations
        open_positions = [
            p for p in positions if p.status in (PositionStatus.OPEN, PositionStatus.PARTIAL)
        ]

        # Total realized P&L includes CLOSED positions + realized portion of PARTIAL positions
        total_realized_pnl = sum(p.realized_pnl for p in closed_positions) + sum(
            p.realized_pnl for p in partial_positions
        )
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
            partial = [p for p in strat_positions if p.status == PositionStatus.PARTIAL]
            # Include both OPEN and PARTIAL positions for unrealized P&L calculations
            open_pos = [
                p
                for p in strat_positions
                if p.status in (PositionStatus.OPEN, PositionStatus.PARTIAL)
            ]

            # Realized P&L includes CLOSED positions + realized portion of PARTIAL positions
            realized_pnl = sum(p.realized_pnl for p in closed) + sum(
                p.realized_pnl for p in partial
            )
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
        # Get all CLOSED and PARTIAL positions for the user
        # PARTIAL positions have realized_pnl from the sold portion
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.user_id == user_id,
                AlgoPosition.status.in_([PositionStatus.CLOSED, PositionStatus.PARTIAL]),
            )
        )
        positions = list(result.scalars().all())

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Group positions by exit date (for CLOSED) or updated_at (for PARTIAL)
        pnl_by_date: dict[str, dict] = defaultdict(
            lambda: {"realized_pnl": Decimal("0"), "trades_closed": 0, "trades_opened": 0}
        )

        for p in positions:
            # For CLOSED positions, use exit_at
            # For PARTIAL positions, use updated_at (when partial sale happened)
            if p.status == PositionStatus.CLOSED and p.exit_at:
                pnl_date = p.exit_at.date()
            elif p.status == PositionStatus.PARTIAL and p.updated_at:
                pnl_date = p.updated_at.date()
            else:
                continue

            pnl_date_str = pnl_date.isoformat()
            if start_date.isoformat() <= pnl_date_str <= end_date.isoformat():
                pnl_by_date[pnl_date_str]["realized_pnl"] += p.realized_pnl
                if p.status == PositionStatus.CLOSED:
                    pnl_by_date[pnl_date_str]["trades_closed"] += 1

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
        # Include both OPEN and PARTIAL positions for unrealized P&L
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.user_id == user_id,
                AlgoPosition.status.in_([PositionStatus.OPEN, PositionStatus.PARTIAL]),
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

    # ============ Profit Booking Management ============

    async def get_profit_booking_rules(
        self, user_id: str, position_id: str
    ) -> ProfitBookingRules | None:
        """Get profit booking rules for an algo position."""
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.id == position_id, AlgoPosition.user_id == user_id
            )
        )
        position = result.scalar_one_or_none()

        if not position or not position.profit_booking_rules:
            return None

        return ProfitBookingRules.model_validate(position.profit_booking_rules)

    async def update_profit_booking_rules(
        self, user_id: str, position_id: str, rules: ProfitBookingRules
    ) -> ProfitBookingRules | None:
        """Update profit booking rules for an algo position."""
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.id == position_id, AlgoPosition.user_id == user_id
            )
        )
        position = result.scalar_one_or_none()

        if not position:
            return None

        # Convert to dict for JSON storage, converting Decimals to floats
        position.profit_booking_rules = rules.model_dump(mode="json")
        await self.db.flush()
        await self.db.refresh(position)

        return ProfitBookingRules.model_validate(position.profit_booking_rules)

    # ============ Trailing Stop Management ============

    async def get_trailing_stop_config(
        self, user_id: str, position_id: str
    ) -> TrailingStopConfig | None:
        """Get trailing stop configuration for an algo position."""
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.id == position_id, AlgoPosition.user_id == user_id
            )
        )
        position = result.scalar_one_or_none()

        if not position:
            return None

        return TrailingStopConfig(
            enabled=position.trailing_stop_enabled,
            percentage=position.trailing_stop_pct,
            current_stop_price=position.trailing_stop_price,
            highest_price=position.highest_price_since_entry,
            lowest_price=position.lowest_price_since_entry,
        )

    async def update_trailing_stop(
        self, user_id: str, position_id: str, config: TrailingStopUpdate
    ) -> TrailingStopConfig | None:
        """Update trailing stop configuration for an algo position."""
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.id == position_id, AlgoPosition.user_id == user_id
            )
        )
        position = result.scalar_one_or_none()

        if not position:
            return None

        position.trailing_stop_enabled = config.enabled

        if config.enabled:
            if config.percentage is None:
                raise ValueError("Trailing stop percentage is required when enabling")

            position.trailing_stop_pct = config.percentage

            # Initialize highest/lowest price tracking if not set
            entry_price = position.entry_price
            if position.highest_price_since_entry is None:
                position.highest_price_since_entry = entry_price
            if position.lowest_price_since_entry is None:
                position.lowest_price_since_entry = entry_price

            # Calculate initial trailing stop price based on position side
            is_long = position.side == PositionSide.LONG
            reference_price = (
                position.highest_price_since_entry if is_long else position.lowest_price_since_entry
            )
            if is_long:
                position.trailing_stop_price = reference_price * (1 - config.percentage)
            else:
                position.trailing_stop_price = reference_price * (1 + config.percentage)
        else:
            position.trailing_stop_pct = None
            position.trailing_stop_price = None
            # Keep highest/lowest price for reference

        await self.db.flush()
        await self.db.refresh(position)

        return TrailingStopConfig(
            enabled=position.trailing_stop_enabled,
            percentage=position.trailing_stop_pct,
            current_stop_price=position.trailing_stop_price,
            highest_price=position.highest_price_since_entry,
            lowest_price=position.lowest_price_since_entry,
        )

    async def get_profit_lock_config(
        self, user_id: str, position_id: str
    ) -> ProfitLockConfig | None:
        """Get profit lock configuration for an algo position."""
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.id == position_id, AlgoPosition.user_id == user_id
            )
        )
        position = result.scalar_one_or_none()

        if not position:
            return None

        return ProfitLockConfig(
            enabled=position.profit_lock_enabled,
            activated=position.profit_lock_activated,
            profit_lock_price=position.profit_lock_price,
        )

    async def update_profit_lock(
        self, user_id: str, position_id: str, config: ProfitLockUpdate
    ) -> ProfitLockConfig | None:
        """Update profit lock configuration for an algo position."""
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.id == position_id, AlgoPosition.user_id == user_id
            )
        )
        position = result.scalar_one_or_none()

        if not position:
            return None

        position.profit_lock_enabled = config.enabled

        # If disabling profit lock, reset the activated state and price
        if not config.enabled:
            position.profit_lock_activated = False
            position.profit_lock_price = None

        await self.db.flush()
        await self.db.refresh(position)

        return ProfitLockConfig(
            enabled=position.profit_lock_enabled,
            activated=position.profit_lock_activated,
            profit_lock_price=position.profit_lock_price,
        )

    # ============== Exit Position Methods ==============

    async def get_open_position(
        self, user_id: str, strategy_id: str, symbol: str
    ) -> AlgoPosition | None:
        """Get an open position for a specific symbol in a strategy."""
        # Include both OPEN and PARTIAL positions (both have remaining quantity)
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.user_id == user_id,
                AlgoPosition.strategy_id == strategy_id,
                AlgoPosition.symbol == symbol.upper(),
                AlgoPosition.status.in_([PositionStatus.OPEN, PositionStatus.PARTIAL]),
            )
        )
        return result.scalar_one_or_none()

    async def close_position(
        self,
        user_id: str,
        strategy_id: str,
        symbol: str,
        exit_price: Decimal,
        quantity: int | None = None,
        product_type: ProductType = ProductType.DELIVERY,
    ) -> ClosePositionResponse | None:
        """Close a position (fully or partially) and calculate P&L.

        Also updates user_funds: releases margin (if applicable) and
        updates cumulative realized_pnl.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            symbol: Symbol to close
            exit_price: Exit price
            quantity: Quantity to close (None = full close)
            product_type: Product type (DELIVERY, INTRADAY, MARGIN)

        Returns:
            ClosePositionResponse or None if position not found
        """
        position = await self.get_open_position(user_id, strategy_id, symbol)
        if not position:
            return None

        # Default to full close
        close_qty = quantity if quantity else position.remaining_quantity
        close_qty = min(close_qty, position.remaining_quantity)

        # Calculate P&L
        if position.side == PositionSide.LONG:
            pnl = (exit_price - position.entry_price) * close_qty
        else:  # SHORT
            pnl = (position.entry_price - exit_price) * close_qty

        pnl_percent = (pnl / (position.entry_price * close_qty)) * 100
        is_winner = pnl > 0

        # Update position
        position.remaining_quantity -= close_qty
        position.exit_price = exit_price
        position.realized_pnl = (position.realized_pnl or Decimal("0")) + pnl
        position.realized_pnl_percent = pnl_percent
        position.is_winner = is_winner

        from datetime import UTC, datetime

        position.exit_at = datetime.now(UTC)

        if position.remaining_quantity <= 0:
            position.status = PositionStatus.CLOSED
            position.exit_quantity = position.entry_quantity
            final_status = "CLOSED"
        else:
            position.status = PositionStatus.PARTIAL
            position.exit_quantity = (position.exit_quantity or 0) + close_qty
            final_status = "PARTIAL"

        await self.db.flush()

        # Update user_funds: credit sale proceeds and update realized P&L
        await self._update_funds_for_closed_position(
            user_id=user_id,
            side=position.side,
            close_qty=close_qty,
            entry_price=position.entry_price,
            exit_price=exit_price,
            pnl=pnl,
            product_type=product_type,
        )

        logger.info(f"Closed position {symbol}: qty={close_qty}, pnl={pnl}, is_winner={is_winner}")

        return ClosePositionResponse(
            position_id=position.id,
            symbol=symbol.upper(),
            side=position.side.value,
            closed_quantity=close_qty,
            remaining_quantity=position.remaining_quantity,
            entry_price=position.entry_price,
            exit_price=exit_price,
            realized_pnl=pnl,
            realized_pnl_percent=pnl_percent,
            is_winner=is_winner,
            status=final_status,
            message=f"Successfully closed {close_qty} units of {symbol}",
        )

    async def _update_funds_for_closed_position(
        self,
        user_id: str,
        side: PositionSide,
        close_qty: int,
        entry_price: Decimal,
        exit_price: Decimal,
        pnl: Decimal,
        product_type: ProductType = ProductType.DELIVERY,
    ) -> None:
        """Update user_funds when a position is closed.

        This handles:
        1. Crediting sale proceeds (for LONG) or debiting buy cost (for SHORT)
        2. Releasing margin (for INTRADAY/MARGIN products)
        3. Updating cumulative realized P&L

        Args:
            user_id: User ID
            side: Position side (LONG or SHORT)
            close_qty: Quantity being closed
            entry_price: Original entry price (for margin release)
            exit_price: Exit price
            pnl: Realized P&L from this close
            product_type: Product type for margin handling
        """
        try:
            funds_provider = DatabaseFundsProvider(db=self.db)

            # For LONG positions, closing means SELL (credit proceeds)
            # For SHORT positions, closing means BUY (debit cost to cover)
            trade_side = "SELL" if side == PositionSide.LONG else "BUY"

            await funds_provider.update_funds_for_trade(
                user_id=user_id,
                side=trade_side,
                quantity=Decimal(str(close_qty)),
                price=exit_price,
                fees=Decimal("0"),  # Fees handled separately if needed
                product_type=product_type,
                existing_position_qty=Decimal(str(close_qty)),  # Closing position
                entry_price=entry_price,  # For proper margin release
            )

            # Update cumulative realized P&L
            if pnl != Decimal("0"):
                await funds_provider.update_realized_pnl(user_id, pnl)
                logger.debug(
                    f"Updated realized P&L for user {user_id[:8]}...: "
                    f"{'+' if pnl > 0 else ''}₹{pnl:.2f}"
                )

        except Exception as e:
            logger.warning(f"Failed to update funds for closed position: {e}")

    async def square_off_strategy(
        self,
        user_id: str,
        strategy_id: str,
        exit_prices: dict[str, Decimal] | None = None,
    ) -> SquareOffStrategyResponse | None:
        """Square off all open positions for a strategy.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            exit_prices: Dict of symbol -> exit price (optional)

        Returns:
            SquareOffStrategyResponse or None if strategy not found
        """
        if exit_prices is None:
            exit_prices = {}
        strategy, _ = await self.get_strategy(user_id, strategy_id)
        if not strategy:
            return None

        # Get all open positions for this strategy
        # Include both OPEN and PARTIAL positions for square off
        result = await self.db.execute(
            select(AlgoPosition).where(
                AlgoPosition.user_id == user_id,
                AlgoPosition.strategy_id == strategy_id,
                AlgoPosition.status.in_([PositionStatus.OPEN, PositionStatus.PARTIAL]),
            )
        )
        open_positions = list(result.scalars().all())

        if not open_positions:
            return SquareOffStrategyResponse(
                strategy_id=strategy_id,
                strategy_name=strategy.name,
                positions_closed=0,
                total_realized_pnl=Decimal("0"),
                closed_positions=[],
                message="No open positions to close",
            )

        closed_responses: list[ClosePositionResponse] = []
        total_pnl = Decimal("0")

        # Map strategy product type to shared ProductType for funds handling
        strategy_product_type = ProductType(strategy.product_type.value)

        for position in open_positions:
            exit_price = exit_prices.get(position.symbol, position.entry_price)
            response = await self.close_position(
                user_id=user_id,
                strategy_id=strategy_id,
                symbol=position.symbol,
                exit_price=exit_price,
                product_type=strategy_product_type,
            )
            if response:
                closed_responses.append(response)
                total_pnl += response.realized_pnl

        logger.info(
            f"Squared off strategy {strategy.name}: {len(closed_responses)} positions, total P&L={total_pnl}"
        )

        return SquareOffStrategyResponse(
            strategy_id=strategy_id,
            strategy_name=strategy.name,
            positions_closed=len(closed_responses),
            total_realized_pnl=total_pnl,
            closed_positions=closed_responses,
            message=f"Successfully closed {len(closed_responses)} positions",
        )

    async def create_composite_strategy(
        self,
        user_id: str,
        name: str,
        description: str | None,
        components: list[dict],
        combine_logic: str,
        min_agreement_pct: float,
        strategy_config: dict,
    ) -> UserStrategy:
        """Create and register a composite strategy.

        Args:
            user_id: User creating the strategy
            name: User-friendly name for the composite strategy
            description: Optional description
            components: List of component strategy configs
            combine_logic: AND, OR, MAJORITY, or WEIGHTED
            min_agreement_pct: Minimum agreement for MAJORITY logic
            strategy_config: Full strategy configuration for execution settings

        Returns:
            Created UserStrategy record
        """
        from shared.strategies.composite import CompositeStrategyFactory
        from shared.strategies.registry import StrategyRegistry

        # Validate component strategies exist
        for comp in components:
            if not StrategyRegistry.has_strategy(comp["strategy"]):
                raise ValueError(f"Unknown component strategy: {comp['strategy']}")

        # Create the composite strategy and register it
        composite_name = f"composite_{name.lower().replace(' ', '_')}"

        # Create composite strategy instance
        composite = CompositeStrategyFactory.create(
            name=composite_name,
            description=description or f"Composite strategy: {name}",
            components=components,
            combine_logic=combine_logic,
            min_agreement_pct=min_agreement_pct,
        )

        # Register it with the strategy registry for runtime use
        CompositeStrategyFactory.register(composite)

        logger.info(f"Registered composite strategy: {composite_name}")

        # Store the strategy configuration including components
        strategy_params = {
            "type": "composite",
            "components": components,
            "combine_logic": combine_logic,
            "min_agreement_pct": min_agreement_pct,
        }

        # Create the UserStrategy record
        strategy = UserStrategy(
            user_id=user_id,
            name=name,
            description=description,
            strategy_name=composite_name,
            strategy_params=strategy_params,
            universe_id=strategy_config.get("universe_id"),
            custom_symbols=strategy_config.get("symbols"),
            schedule_type=strategy_config.get("schedule_type", "market_open"),
            interval_seconds=strategy_config.get("interval_seconds"),
            cron_expression=strategy_config.get("cron_expression"),
            position_sizing_method=strategy_config.get(
                "position_sizing_method", "percent_of_portfolio"
            ),
            portfolio_percent=Decimal(str(strategy_config.get("position_size_value", "5.00"))),
            max_position_value=(
                Decimal(str(strategy_config["max_position_value"]))
                if strategy_config.get("max_position_value")
                else None
            ),
            max_daily_loss=Decimal(str(strategy_config.get("max_daily_loss", "5000.00"))),
            max_consecutive_losses=strategy_config.get("max_consecutive_losses", 3),
            is_paper_trading=strategy_config.get("is_paper_trading", True),
            product_type=strategy_config.get("product_type", "delivery"),
        )

        self.db.add(strategy)
        await self.db.flush()

        logger.info(f"Created composite strategy '{name}' (id={strategy.id}) for user {user_id}")

        return strategy

    async def create_dsl_strategy(
        self,
        user_id: str,
        name: str,
        description: str | None,
        definition: dict,
        strategy_config: dict,
    ) -> UserStrategy:
        """Create and register a DSL-based custom strategy.

        Args:
            user_id: User creating the strategy
            name: User-friendly name for the DSL strategy
            description: Optional description
            definition: DSL strategy definition with rules, indicators, etc.
            strategy_config: Full strategy configuration for execution settings

        Returns:
            Created UserStrategy record
        """
        from shared.strategies.dsl import (
            DSLStrategy,
            DSLStrategyDefinition,
            validate_dsl_strategy,
        )
        from shared.strategies.registry import StrategyRegistry

        # Validate the DSL definition
        try:
            dsl_definition = DSLStrategyDefinition(**definition)
            validation_result = validate_dsl_strategy(dsl_definition)
            if not validation_result.valid:
                error_msgs = [e.message for e in validation_result.errors]
                raise ValueError(f"Invalid DSL definition: {'; '.join(error_msgs)}")
        except Exception as e:
            raise ValueError(f"Failed to parse DSL definition: {e}") from e

        # Create a unique strategy name for registry
        dsl_strategy_name = f"dsl_{name.lower().replace(' ', '_')}"

        # Create and register the DSL strategy
        dsl_strategy = DSLStrategy(dsl_definition)
        dsl_strategy.name = dsl_strategy_name

        # Register dynamically
        StrategyRegistry._strategies[dsl_strategy_name] = type(
            dsl_strategy_name,
            (DSLStrategy,),
            {"name": dsl_strategy_name, "_definition": dsl_definition},
        )

        logger.info(f"Registered DSL strategy: {dsl_strategy_name}")

        # Store the DSL definition in strategy_params
        strategy_params = {
            "type": "dsl",
            "definition": definition,
        }

        # Create the UserStrategy record
        strategy = UserStrategy(
            user_id=user_id,
            name=name,
            description=description,
            strategy_name=dsl_strategy_name,
            strategy_params=strategy_params,
            universe_id=strategy_config.get("universe_id"),
            custom_symbols=strategy_config.get("symbols"),
            schedule_type=strategy_config.get("schedule_type", "market_open"),
            interval_seconds=strategy_config.get("interval_seconds"),
            cron_expression=strategy_config.get("cron_expression"),
            position_sizing_method=strategy_config.get(
                "position_sizing_method", "percent_of_portfolio"
            ),
            portfolio_percent=Decimal(str(strategy_config.get("position_size_value", "5.00"))),
            max_position_value=(
                Decimal(str(strategy_config["max_position_value"]))
                if strategy_config.get("max_position_value")
                else None
            ),
            max_daily_loss=Decimal(str(strategy_config.get("max_daily_loss", "5000.00"))),
            max_consecutive_losses=strategy_config.get("max_consecutive_losses", 3),
            is_paper_trading=strategy_config.get("is_paper_trading", True),
            product_type=strategy_config.get("product_type", "delivery"),
            default_trailing_stop_enabled=strategy_config.get(
                "default_trailing_stop_enabled", False
            ),
            default_trailing_stop_pct=(
                Decimal(str(strategy_config["default_trailing_stop_pct"]))
                if strategy_config.get("default_trailing_stop_pct")
                else None
            ),
            default_profit_booking_rules=strategy_config.get("default_profit_booking_rules"),
        )

        self.db.add(strategy)
        await self.db.flush()

        logger.info(f"Created DSL strategy '{name}' (id={strategy.id}) for user {user_id}")

        return strategy
