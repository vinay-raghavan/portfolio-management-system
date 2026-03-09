"""Position tracker for algo trading.

Tracks open positions for strategies and calculates P&L when positions are closed.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.models.algo import (
    AlgoPosition,
    PositionSide,
    PositionStatus,
    StrategyProductType,
    UserStrategy,
)

logger = logging.getLogger(__name__)


@dataclass
class PositionResult:
    """Result of position operation."""

    position_id: str
    symbol: str
    side: str
    quantity: int
    entry_price: Decimal
    exit_price: Decimal | None = None
    realized_pnl: Decimal = Decimal("0")
    is_winner: bool | None = None
    status: str = "OPEN"
    product_type: StrategyProductType | None = None  # Product type at position open


@dataclass
class PnLStats:
    """P&L statistics from position operations."""

    trades_closed: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: Decimal = Decimal("0")
    consecutive_losses: int = 0


class PositionTracker:
    """Track algo positions and calculate P&L."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_open_position(
        self,
        strategy_id: str,
        user_id: str,
        symbol: str,
        include_partial: bool = True,
    ) -> AlgoPosition | None:
        """Get open position for a symbol in a strategy.

        Args:
            strategy_id: Strategy ID
            user_id: User ID
            symbol: Stock symbol
            include_partial: If True, also match PARTIAL positions (default True)

        Returns:
            The position if found, None otherwise
        """
        if include_partial:
            result = await self.db.execute(
                select(AlgoPosition).where(
                    AlgoPosition.strategy_id == strategy_id,
                    AlgoPosition.user_id == user_id,
                    AlgoPosition.symbol == symbol,
                    AlgoPosition.status.in_([PositionStatus.OPEN, PositionStatus.PARTIAL]),
                )
            )
        else:
            result = await self.db.execute(
                select(AlgoPosition).where(
                    AlgoPosition.strategy_id == strategy_id,
                    AlgoPosition.user_id == user_id,
                    AlgoPosition.symbol == symbol,
                    AlgoPosition.status == PositionStatus.OPEN,
                )
            )
        return result.scalar_one_or_none()

    async def get_all_open_positions(
        self,
        strategy_id: str,
        user_id: str,
        include_partial: bool = False,
    ) -> list[AlgoPosition]:
        """Get all open positions for a strategy.

        Args:
            strategy_id: Strategy ID
            user_id: User ID
            include_partial: If True, include PARTIAL positions as well as OPEN

        Returns:
            List of open (and optionally partial) positions
        """
        if include_partial:
            result = await self.db.execute(
                select(AlgoPosition).where(
                    AlgoPosition.strategy_id == strategy_id,
                    AlgoPosition.user_id == user_id,
                    AlgoPosition.status.in_([PositionStatus.OPEN, PositionStatus.PARTIAL]),
                )
            )
        else:
            result = await self.db.execute(
                select(AlgoPosition).where(
                    AlgoPosition.strategy_id == strategy_id,
                    AlgoPosition.user_id == user_id,
                    AlgoPosition.status == PositionStatus.OPEN,
                )
            )
        return list(result.scalars().all())

    async def calculate_unrealized_pnl(
        self,
        strategy_id: str,
        user_id: str,
        current_prices: dict[str, Decimal],
    ) -> Decimal:
        """Calculate total unrealized P&L for all open positions.

        Args:
            strategy_id: Strategy ID
            user_id: User ID
            current_prices: Dict of symbol -> current price

        Returns:
            Total unrealized P&L
        """
        open_positions = await self.get_all_open_positions(strategy_id, user_id)
        total_unrealized = Decimal("0")

        for position in open_positions:
            current_price = current_prices.get(position.symbol)
            if current_price is None:
                continue

            entry_value = position.entry_price * position.remaining_quantity
            current_value = current_price * position.remaining_quantity

            if position.side == PositionSide.LONG:
                unrealized_pnl = current_value - entry_value
            else:  # SHORT
                unrealized_pnl = entry_value - current_value

            total_unrealized += unrealized_pnl

        return total_unrealized

    async def open_position(
        self,
        strategy_id: str,
        user_id: str,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: Decimal,
        order_id: str | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        product_type: StrategyProductType | None = None,
    ) -> PositionResult:
        """Open a new position or add to existing one.

        Automatically applies strategy's default trailing stop settings to new positions.

        Returns PositionResult with position details.
        """
        symbol = symbol.upper()
        position_side = PositionSide.LONG if side == "BUY" else PositionSide.SHORT

        # Fetch strategy for default trailing stop settings
        strategy_result = await self.db.execute(
            select(UserStrategy).where(UserStrategy.id == strategy_id)
        )
        strategy = strategy_result.scalar_one_or_none()

        # Check for existing open position
        existing = await self.get_open_position(strategy_id, user_id, symbol)

        if existing:
            # Average into existing position
            total_qty = existing.remaining_quantity + quantity
            total_cost = (existing.entry_price * existing.remaining_quantity) + (
                entry_price * quantity
            )
            new_avg_price = total_cost / total_qty

            existing.entry_quantity = total_qty
            existing.remaining_quantity = total_qty
            existing.entry_price = new_avg_price

            # Update trailing stop price if enabled (recalculate based on new avg price)
            if existing.trailing_stop_enabled and existing.trailing_stop_pct:
                if position_side == PositionSide.LONG:
                    # For LONG: update highest price if new avg is higher
                    if (
                        existing.highest_price_since_entry is None
                        or new_avg_price > existing.highest_price_since_entry
                    ):
                        existing.highest_price_since_entry = new_avg_price
                    existing.trailing_stop_price = existing.highest_price_since_entry * (
                        Decimal("1") - existing.trailing_stop_pct
                    )
                else:
                    # For SHORT: update lowest price if new avg is lower
                    if (
                        existing.lowest_price_since_entry is None
                        or new_avg_price < existing.lowest_price_since_entry
                    ):
                        existing.lowest_price_since_entry = new_avg_price
                    existing.trailing_stop_price = existing.lowest_price_since_entry * (
                        Decimal("1") + existing.trailing_stop_pct
                    )

            await self.db.flush()

            logger.info(f"Added to position {symbol}: qty={total_qty}, avg={new_avg_price}")
            return PositionResult(
                position_id=existing.id,
                symbol=symbol,
                side=position_side.value,
                quantity=total_qty,
                entry_price=new_avg_price,
                status="OPEN",
            )

        # Initialize trailing stop from strategy defaults
        trailing_stop_enabled = False
        trailing_stop_pct = None
        trailing_stop_price = None
        highest_price = None
        lowest_price = None

        if (
            strategy
            and strategy.default_trailing_stop_enabled
            and strategy.default_trailing_stop_pct
        ):
            trailing_stop_enabled = True
            trailing_stop_pct = strategy.default_trailing_stop_pct

            # Initialize price tracking and calculate initial stop price
            if position_side == PositionSide.LONG:
                highest_price = entry_price
                trailing_stop_price = entry_price * (Decimal("1") - trailing_stop_pct)
            else:  # SHORT
                lowest_price = entry_price
                trailing_stop_price = entry_price * (Decimal("1") + trailing_stop_pct)

            logger.info(
                f"Initialized trailing stop for {symbol}: enabled={trailing_stop_enabled}, "
                f"pct={trailing_stop_pct}, stop_price={trailing_stop_price}"
            )

        # Initialize profit lock from strategy defaults
        profit_lock_enabled = False
        if strategy and strategy.default_profit_lock_enabled:
            profit_lock_enabled = True
            logger.info(f"Initialized profit lock for {symbol}: enabled={profit_lock_enabled}")

        # Get product_type from strategy if not provided
        position_product_type = product_type
        if position_product_type is None and strategy:
            position_product_type = strategy.product_type

        # Create new position with trailing stop and profit lock settings
        position = AlgoPosition(
            strategy_id=strategy_id,
            user_id=user_id,
            symbol=symbol,
            side=position_side,
            entry_quantity=quantity,
            entry_price=entry_price,
            entry_order_id=order_id,
            remaining_quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=PositionStatus.OPEN,
            product_type=position_product_type,
            trailing_stop_enabled=trailing_stop_enabled,
            trailing_stop_pct=trailing_stop_pct,
            trailing_stop_price=trailing_stop_price,
            highest_price_since_entry=highest_price,
            lowest_price_since_entry=lowest_price,
            profit_lock_enabled=profit_lock_enabled,
            profit_lock_activated=False,
            profit_lock_price=None,
        )
        self.db.add(position)
        await self.db.flush()
        await self.db.refresh(position)

        logger.info(f"Opened position {symbol}: {side} {quantity} @ {entry_price}")
        return PositionResult(
            position_id=position.id,
            symbol=symbol,
            side=position_side.value,
            quantity=quantity,
            entry_price=entry_price,
            status="OPEN",
        )

    async def close_position(
        self,
        strategy_id: str,
        user_id: str,
        symbol: str,
        quantity: int | None,
        exit_price: Decimal,
        order_id: str | None = None,
    ) -> PositionResult | None:
        """Close a position (fully or partially) and calculate P&L."""
        symbol = symbol.upper()
        position = await self.get_open_position(strategy_id, user_id, symbol)

        if not position:
            logger.warning(f"No open position found for {symbol} to close")
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
        position.exit_order_id = order_id
        position.exit_at = datetime.now(UTC)
        position.realized_pnl += pnl
        position.realized_pnl_percent = pnl_percent
        position.is_winner = is_winner

        if position.remaining_quantity <= 0:
            position.status = PositionStatus.CLOSED
            position.exit_quantity = position.entry_quantity

            # Auto-remove from exit_only_symbols if position is fully closed
            await self._cleanup_exit_only_symbol(strategy_id, symbol)
        else:
            position.status = PositionStatus.PARTIAL
            position.exit_quantity = (position.exit_quantity or 0) + close_qty

        await self.db.flush()

        logger.info(f"Closed position {symbol}: qty={close_qty}, pnl={pnl}, is_winner={is_winner}")
        return PositionResult(
            position_id=position.id,
            symbol=symbol,
            side=position.side.value,
            quantity=close_qty,
            entry_price=position.entry_price,
            exit_price=exit_price,
            realized_pnl=pnl,
            is_winner=is_winner,
            status=position.status.value,
            product_type=position.product_type,
        )

    async def _cleanup_exit_only_symbol(self, strategy_id: str, symbol: str) -> None:
        """Remove symbol from exit_only_symbols when its position is fully closed.

        This is called automatically when a position reaches CLOSED status.
        If the symbol was in exit_only_symbols (meaning it was a screener-dropped
        symbol waiting for position close), it will be removed from the list.
        """
        # Fetch the strategy
        result = await self.db.execute(select(UserStrategy).where(UserStrategy.id == strategy_id))
        strategy = result.scalar_one_or_none()

        if not strategy:
            logger.warning(f"Strategy {strategy_id} not found for exit_only cleanup")
            return

        exit_only_symbols = strategy.exit_only_symbols or []
        if symbol.upper() in [s.upper() for s in exit_only_symbols]:
            # Remove the symbol (case-insensitive match)
            updated_list = [s for s in exit_only_symbols if s.upper() != symbol.upper()]
            strategy.exit_only_symbols = updated_list
            logger.info(
                f"Removed {symbol} from exit_only_symbols for strategy {strategy.name}. "
                f"Remaining: {updated_list}"
            )

    async def process_order_fill(
        self,
        strategy_id: str,
        user_id: str,
        symbol: str,
        side: str,
        quantity: int,
        fill_price: Decimal,
        order_id: str | None = None,
    ) -> tuple[PositionResult | None, PnLStats]:
        """Process an order fill and update positions.

        For BUY orders:
        - If we have a SHORT position, close it (calculate P&L)
        - Otherwise, open/add to LONG position

        For SELL orders:
        - If we have a LONG position, close it (calculate P&L)
        - Otherwise, open/add to SHORT position

        Returns (position_result, pnl_stats)
        """
        symbol = symbol.upper()
        stats = PnLStats()

        # Check for existing position
        existing = await self.get_open_position(strategy_id, user_id, symbol)

        if existing:
            # Determine if this closes or opens position
            if side == "BUY" and existing.side == PositionSide.SHORT:
                # Close SHORT position
                result = await self.close_position(
                    strategy_id, user_id, symbol, quantity, fill_price, order_id
                )
                if result:
                    stats.trades_closed = 1
                    stats.total_pnl = result.realized_pnl
                    if result.is_winner:
                        stats.winning_trades = 1
                    else:
                        stats.losing_trades = 1
                        stats.consecutive_losses = 1
                return result, stats

            elif side == "SELL" and existing.side == PositionSide.LONG:
                # Close LONG position
                result = await self.close_position(
                    strategy_id, user_id, symbol, quantity, fill_price, order_id
                )
                if result:
                    stats.trades_closed = 1
                    stats.total_pnl = result.realized_pnl
                    if result.is_winner:
                        stats.winning_trades = 1
                    else:
                        stats.losing_trades = 1
                        stats.consecutive_losses = 1
                return result, stats

            # Same direction - add to position
            result = await self.open_position(
                strategy_id, user_id, symbol, side, quantity, fill_price, order_id
            )
            return result, stats

        # No existing position - open new
        result = await self.open_position(
            strategy_id, user_id, symbol, side, quantity, fill_price, order_id
        )
        return result, stats

    async def _update_trailing_stop(
        self,
        position: AlgoPosition,
        current_price: Decimal,
        strategy: UserStrategy | None = None,
    ) -> bool:
        """Update trailing stop price based on current market price.

        For LONG positions: if current price > highest, update highest and recalculate stop.
        For SHORT positions: if current price < lowest, update lowest and recalculate stop.

        Uses position-level settings if configured, otherwise falls back to strategy-level defaults.

        Returns True if trailing stop was updated.
        """
        # Determine effective trailing stop settings (hierarchical: position -> strategy)
        trailing_enabled = position.trailing_stop_enabled
        trailing_pct = position.trailing_stop_pct

        # If position-level trailing stop is not configured, use strategy defaults
        if not trailing_enabled and trailing_pct is None and strategy:
            trailing_enabled = strategy.default_trailing_stop_enabled
            trailing_pct = strategy.default_trailing_stop_pct

        if not trailing_enabled or not trailing_pct:
            return False

        updated = False
        is_long = position.side == PositionSide.LONG

        if is_long:
            # For LONG positions: trailing stop moves up when price moves up
            if (
                position.highest_price_since_entry is None
                or current_price > position.highest_price_since_entry
            ):
                position.highest_price_since_entry = current_price
                new_stop = current_price * (Decimal("1") - trailing_pct)
                # Only update if new stop is higher than current stop (never lower)
                if position.trailing_stop_price is None or new_stop > position.trailing_stop_price:
                    position.trailing_stop_price = new_stop
                    updated = True
        else:
            # For SHORT positions: trailing stop moves down when price moves down
            if (
                position.lowest_price_since_entry is None
                or current_price < position.lowest_price_since_entry
            ):
                position.lowest_price_since_entry = current_price
                new_stop = current_price * (Decimal("1") + trailing_pct)
                # Only update if new stop is lower than current stop (never higher)
                if position.trailing_stop_price is None or new_stop < position.trailing_stop_price:
                    position.trailing_stop_price = new_stop
                    updated = True

        if updated:
            await self.db.flush()

        return updated

    async def _check_profit_lock(
        self,
        position: AlgoPosition,
        current_price: Decimal,
        strategy: UserStrategy | None = None,
    ) -> bool:
        """Check and update profit lock based on profit booking rule thresholds.

        When profit lock is enabled and a profit booking threshold is reached,
        the stop loss is locked at the current profit price level (minus buffer).

        The profit lock "ratchets up" as higher thresholds are crossed - each time
        a new threshold is reached, the lock price is updated to protect more profit.

        Args:
            position: The position to check
            current_price: Current market price
            strategy: Optional strategy for fallback settings

        Returns:
            True if profit lock was activated or updated
        """
        # Determine if profit lock is enabled (position -> strategy hierarchy)
        profit_lock_enabled = position.profit_lock_enabled
        if not profit_lock_enabled and strategy:
            profit_lock_enabled = strategy.default_profit_lock_enabled

        if not profit_lock_enabled:
            return False

        # Get profit booking rules (position -> strategy hierarchy)
        rules_data = position.profit_booking_rules
        if not rules_data and strategy and strategy.default_profit_booking_rules:
            rules_data = strategy.default_profit_booking_rules

        if not rules_data or not rules_data.get("enabled", False):
            return False

        rules = rules_data.get("rules", [])
        if not rules:
            return False

        # Calculate current profit percentage
        if position.side == PositionSide.LONG:
            profit_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        else:  # SHORT
            profit_pct = ((position.entry_price - current_price) / position.entry_price) * 100

        # Get trailing stop percentage for buffer (position -> strategy hierarchy)
        trailing_pct = position.trailing_stop_pct
        if trailing_pct is None and strategy:
            trailing_pct = strategy.default_trailing_stop_pct

        # Sort rules by threshold (ascending) and find the HIGHEST crossed threshold
        sorted_rules = sorted(rules, key=lambda r: float(r.get("target_pct", 0)))
        highest_crossed_threshold: Decimal | None = None

        for rule in sorted_rules:
            threshold = Decimal(str(rule.get("target_pct", 0)))
            if profit_pct >= threshold:
                highest_crossed_threshold = threshold
            else:
                # Rules are sorted, so no need to check higher ones
                break

        if highest_crossed_threshold is None:
            return False

        # Calculate new profit lock price with trailing buffer
        # For LONG: stop = current_price * (1 - trailing_pct)
        # For SHORT: stop = current_price * (1 + trailing_pct)
        if trailing_pct:
            if position.side == PositionSide.LONG:
                new_lock_price = current_price * (Decimal("1") - trailing_pct)
            else:  # SHORT
                new_lock_price = current_price * (Decimal("1") + trailing_pct)
        else:
            # No trailing stop configured, lock at current price
            new_lock_price = current_price

        # Check if this is a new activation or an update (ratchet up)
        is_new_activation = not position.profit_lock_activated
        current_lock = position.profit_lock_price

        # For LONG: only update if new lock is HIGHER (protecting more profit)
        # For SHORT: only update if new lock is LOWER (protecting more profit)
        should_update = False
        if is_new_activation:
            should_update = True
        elif position.side == PositionSide.LONG:
            should_update = current_lock is None or new_lock_price > current_lock
        else:  # SHORT
            should_update = current_lock is None or new_lock_price < current_lock

        if should_update:
            old_lock = position.profit_lock_price
            position.profit_lock_activated = True
            position.profit_lock_price = new_lock_price
            await self.db.flush()

            buffer_info = f" (with {trailing_pct * 100:.2f}% buffer)" if trailing_pct else ""

            if is_new_activation:
                logger.info(
                    f"🔒 Profit lock activated for {position.symbol}: "
                    f"{profit_pct:.2f}% profit >= {highest_crossed_threshold}% threshold, "
                    f"stop locked at {new_lock_price}{buffer_info}"
                )
            else:
                logger.info(
                    f"🔒 Profit lock RATCHETED UP for {position.symbol}: "
                    f"{profit_pct:.2f}% profit >= {highest_crossed_threshold}% threshold, "
                    f"stop moved from {old_lock} to {new_lock_price}{buffer_info}"
                )
            return True

        return False

    async def check_stop_loss_take_profit(
        self,
        strategy_id: str,
        user_id: str,
        current_prices: dict[str, Decimal],
    ) -> tuple[list[PositionResult], PnLStats]:
        """Check open positions for stop-loss, take-profit, or profit booking triggers.

        Args:
            strategy_id: Strategy ID
            user_id: User ID
            current_prices: Dict of symbol -> current price

        Returns:
            Tuple of (closed positions, aggregated PnL stats)
        """
        # Fetch the strategy for strategy-level default settings
        strategy_result = await self.db.execute(
            select(UserStrategy).where(UserStrategy.id == strategy_id)
        )
        strategy = strategy_result.scalar_one_or_none()

        # Include partial positions for profit booking checks
        open_positions = await self.get_all_open_positions(
            strategy_id, user_id, include_partial=True
        )
        closed_results: list[PositionResult] = []
        stats = PnLStats()

        for position in open_positions:
            current_price = current_prices.get(position.symbol)
            if not current_price:
                continue

            # Check and activate profit lock (uses first profit booking rule threshold)
            await self._check_profit_lock(position, current_price, strategy)

            # Determine effective trailing stop settings (hierarchical: position -> strategy)
            trailing_enabled = position.trailing_stop_enabled
            trailing_pct = position.trailing_stop_pct
            if not trailing_enabled and trailing_pct is None and strategy:
                trailing_enabled = strategy.default_trailing_stop_enabled
                trailing_pct = strategy.default_trailing_stop_pct

            # Determine if profit lock is enabled and activated
            profit_lock_enabled = position.profit_lock_enabled
            if not profit_lock_enabled and strategy:
                profit_lock_enabled = strategy.default_profit_lock_enabled

            # Update trailing stop price before checking SL (pass strategy for fallback)
            # Only use trailing stop if profit lock is OFF
            if not profit_lock_enabled and trailing_enabled:
                await self._update_trailing_stop(position, current_price, strategy)

            should_close = False
            close_reason = ""

            # Determine effective stop loss (priority: profit_lock > trailing > fixed)
            # - If profit lock is activated, use profit_lock_price
            # - Else if trailing stop is enabled, use trailing_stop_price
            # - Otherwise, use fixed stop_loss
            if position.profit_lock_activated and position.profit_lock_price:
                effective_stop = position.profit_lock_price
                stop_type = "profit-lock-stop"
            elif trailing_enabled and position.trailing_stop_price:
                effective_stop = position.trailing_stop_price
                stop_type = "trailing-stop-loss"
            else:
                effective_stop = position.stop_loss
                stop_type = "stop-loss"

            # Check stop-loss / trailing stop / profit lock (for OPEN and PARTIAL positions)
            # PARTIAL positions still need stop loss protection for remaining quantity
            if position.status in (PositionStatus.OPEN, PositionStatus.PARTIAL) and effective_stop:
                if position.side == PositionSide.LONG and current_price <= effective_stop:
                    should_close = True
                    close_reason = stop_type
                elif position.side == PositionSide.SHORT and current_price >= effective_stop:
                    should_close = True
                    close_reason = stop_type

            # Check take-profit (for OPEN and PARTIAL positions)
            if (
                not should_close
                and position.status in (PositionStatus.OPEN, PositionStatus.PARTIAL)
                and position.take_profit
            ):
                if position.side == PositionSide.LONG and current_price >= position.take_profit:
                    should_close = True
                    close_reason = "take-profit"
                elif position.side == PositionSide.SHORT and current_price <= position.take_profit:
                    should_close = True
                    close_reason = "take-profit"

            if should_close:
                logger.info(
                    f"Closing position {position.symbol} due to {close_reason}: "
                    f"entry={position.entry_price}, current={current_price}, "
                    f"effective_stop={effective_stop}, tp={position.take_profit}"
                )
                result = await self.close_position(
                    strategy_id,
                    user_id,
                    position.symbol,
                    None,  # Close full position
                    current_price,
                )
                if result:
                    closed_results.append(result)
                    stats.trades_closed += 1
                    stats.total_pnl += result.realized_pnl
                    if result.is_winner:
                        stats.winning_trades += 1
                    else:
                        stats.losing_trades += 1
                        stats.consecutive_losses += 1
                continue  # Skip profit booking check if position was closed

            # Check profit booking rules (for both OPEN and PARTIAL positions)
            profit_booking_result = await self._check_profit_booking_rules(
                position, current_price, strategy_id, user_id, strategy
            )
            if profit_booking_result:
                closed_results.append(profit_booking_result)
                stats.trades_closed += 1
                stats.total_pnl += profit_booking_result.realized_pnl
                if profit_booking_result.is_winner:
                    stats.winning_trades += 1

        return closed_results, stats

    async def _check_profit_booking_rules(
        self,
        position: AlgoPosition,
        current_price: Decimal,
        strategy_id: str,
        user_id: str,
        strategy: UserStrategy | None = None,
    ) -> PositionResult | None:
        """Check and execute profit booking rules for a position.

        Uses position-level settings if configured, otherwise falls back to strategy-level defaults.

        Args:
            position: The position to check
            current_price: Current market price
            strategy_id: Strategy ID
            user_id: User ID
            strategy: Optional strategy for fallback to default profit booking rules

        Returns:
            PositionResult if a partial exit was executed, None otherwise
        """
        # Determine effective profit booking rules (hierarchical: position -> strategy)
        rules_data = position.profit_booking_rules

        # If position doesn't have profit booking rules, use strategy defaults
        if not rules_data and strategy and strategy.default_profit_booking_rules:
            rules_data = strategy.default_profit_booking_rules

        if not rules_data:
            return None
        if not rules_data.get("enabled", False):
            return None

        rules = rules_data.get("rules", [])

        # Get executed targets from position's profit_booking_rules (not strategy's)
        # This ensures we track execution per-position even when using strategy defaults
        position_rules = position.profit_booking_rules or {}
        executed = position_rules.get("executed", [])

        if not rules:
            return None

        # Calculate current profit percentage based on position side
        if position.side == PositionSide.LONG:
            profit_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        else:  # SHORT
            profit_pct = ((position.entry_price - current_price) / position.entry_price) * 100

        # Sort rules by target_pct to process in order
        sorted_rules = sorted(rules, key=lambda r: float(r.get("target_pct", 0)))

        for rule in sorted_rules:
            target_pct = Decimal(str(rule.get("target_pct", 0)))
            quantity_pct = Decimal(str(rule.get("quantity_pct", 0)))

            # Skip if already executed
            if float(target_pct) in executed:
                continue

            # Check if target is reached
            if profit_pct >= target_pct:
                # Calculate quantity to sell (based on remaining quantity)
                sell_qty = int((position.remaining_quantity * quantity_pct) / 100)
                if sell_qty <= 0:
                    continue

                logger.info(
                    f"📈 Profit booking triggered for {position.symbol}: "
                    f"{profit_pct:.2f}% profit >= {target_pct}% target, "
                    f"selling {quantity_pct}% ({sell_qty} shares)"
                )

                # Execute partial close
                result = await self.close_position(
                    strategy_id,
                    user_id,
                    position.symbol,
                    sell_qty,
                    current_price,
                )

                if result:
                    # Refresh the position object to get the latest state
                    # (close_position fetches its own copy and modifies it)
                    await self.db.refresh(position)

                    # Mark this rule as executed
                    executed.append(float(target_pct))
                    position.profit_booking_rules = {
                        "enabled": True,
                        "rules": rules,
                        "executed": executed,
                    }
                    await self.db.flush()

                    logger.info(
                        f"✅ Profit booking executed for {position.symbol}: "
                        f"sold {sell_qty} @ {current_price}, P&L: {result.realized_pnl}"
                    )
                    return result

        return None

    async def calculate_strategy_pnl_stats(
        self,
        strategy_id: str,
        user_id: str,
    ) -> PnLStats:
        """Calculate P&L stats from all closed positions for a strategy."""
        from sqlalchemy import and_

        result = await self.db.execute(
            select(AlgoPosition).where(
                and_(
                    AlgoPosition.strategy_id == strategy_id,
                    AlgoPosition.user_id == user_id,
                    AlgoPosition.status == PositionStatus.CLOSED,
                )
            )
        )
        closed_positions = result.scalars().all()

        stats = PnLStats()
        consecutive_losses = 0
        max_consecutive_losses = 0

        for pos in closed_positions:
            stats.trades_closed += 1
            stats.total_pnl += pos.realized_pnl

            if pos.is_winner:
                stats.winning_trades += 1
                consecutive_losses = 0
            else:
                stats.losing_trades += 1
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

        stats.consecutive_losses = max_consecutive_losses
        return stats
