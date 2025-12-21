"""Portfolio service layer."""

from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portfolio.models import Position, Trade, CostLot
from app.modules.portfolio.schemas import (
    PositionResponse,
    PortfolioSummary,
    PortfolioResponse,
    TradeResponse,
)


class PortfolioService:
    """Service class for portfolio operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_positions(self, user_id: str) -> list[Position]:
        """Get all positions for a user."""
        result = await self.db.execute(
            select(Position).where(Position.user_id == user_id).order_by(Position.symbol)
        )
        return list(result.scalars().all())

    async def get_position(self, user_id: str, symbol: str) -> Position | None:
        """Get a specific position for a user."""
        result = await self.db.execute(
            select(Position).where(Position.user_id == user_id, Position.symbol == symbol)
        )
        return result.scalar_one_or_none()

    async def update_position(
        self, user_id: str, symbol: str, quantity: Decimal, avg_cost: Decimal
    ) -> Position:
        """Create or update a position."""
        position = await self.get_position(user_id, symbol)

        if position is None:
            position = Position(
                user_id=user_id,
                symbol=symbol,
                quantity=quantity,
                avg_cost=avg_cost,
            )
            self.db.add(position)
        else:
            # Update existing position
            if quantity == 0:
                await self.db.delete(position)
                return position
            position.quantity = quantity
            position.avg_cost = avg_cost

        await self.db.flush()
        await self.db.refresh(position)
        return position

    async def get_portfolio(
        self, user_id: str, price_getter: Callable | None = None
    ) -> PortfolioResponse:
        """Get full portfolio with summary."""
        positions = await self.get_positions(user_id)

        total_value = Decimal("0")
        total_cost = Decimal("0")
        position_responses = []

        for pos in positions:
            cost = pos.quantity * pos.avg_cost
            total_cost += cost

            # Get current price if price_getter provided
            current_price = None
            if price_getter:
                current_price = await price_getter(pos.symbol)

            if current_price:
                market_value = pos.quantity * current_price
                unrealized_pnl = market_value - cost
                unrealized_pnl_pct = (unrealized_pnl / cost * 100) if cost else Decimal("0")
                total_value += market_value
            else:
                market_value = cost
                unrealized_pnl = Decimal("0")
                unrealized_pnl_pct = Decimal("0")
                total_value += cost

            position_responses.append(
                PositionResponse(
                    id=pos.id,
                    symbol=pos.symbol,
                    quantity=pos.quantity,
                    avg_cost=pos.avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                )
            )

        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else Decimal("0")

        summary = PortfolioSummary(
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            cash_balance=Decimal("0"),  # TODO: Implement cash tracking
            positions_count=len(positions),
        )

        return PortfolioResponse(summary=summary, positions=position_responses)

    async def get_trades(
        self, user_id: str, page: int = 1, page_size: int = 50
    ) -> tuple[list[Trade], int]:
        """Get trade history with pagination."""
        # Get total count
        count_result = await self.db.execute(
            select(func.count(Trade.id)).where(Trade.user_id == user_id)
        )
        total_count = count_result.scalar() or 0

        # Get paginated trades
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Trade)
            .where(Trade.user_id == user_id)
            .order_by(Trade.executed_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        trades = list(result.scalars().all())

        return trades, total_count

    # ============ FIFO Cost Lot Management ============

    async def add_cost_lot(
        self,
        user_id: str,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        trade_id: str | None = None,
    ) -> CostLot:
        """Add a new cost lot when buying shares (FIFO tracking)."""
        lot = CostLot(
            user_id=user_id,
            symbol=symbol.upper(),
            original_quantity=quantity,
            remaining_quantity=quantity,
            purchase_price=price,
            trade_id=trade_id,
            purchased_at=datetime.now(timezone.utc),
        )
        self.db.add(lot)
        await self.db.flush()
        await self.db.refresh(lot)
        return lot

    async def get_cost_lots(self, user_id: str, symbol: str) -> list[CostLot]:
        """Get all cost lots for a symbol in FIFO order (oldest first)."""
        result = await self.db.execute(
            select(CostLot)
            .where(
                CostLot.user_id == user_id,
                CostLot.symbol == symbol.upper(),
                CostLot.remaining_quantity > 0,
            )
            .order_by(CostLot.purchased_at.asc())
        )
        return list(result.scalars().all())

    async def consume_cost_lots_fifo(
        self,
        user_id: str,
        symbol: str,
        quantity: Decimal,
        sell_price: Decimal,
    ) -> Decimal:
        """Consume cost lots in FIFO order and calculate realized P&L.

        Args:
            user_id: User ID
            symbol: Stock symbol
            quantity: Quantity to sell
            sell_price: Sale price per share

        Returns:
            Realized profit/loss from this sale
        """
        lots = await self.get_cost_lots(user_id, symbol.upper())
        remaining_to_sell = quantity
        realized_pnl = Decimal("0")

        for lot in lots:
            if remaining_to_sell <= 0:
                break

            # How much can we take from this lot?
            take_qty = min(lot.remaining_quantity, remaining_to_sell)

            # Calculate P&L for this portion
            cost_basis = take_qty * lot.purchase_price
            sale_value = take_qty * sell_price
            realized_pnl += (sale_value - cost_basis)

            # Update the lot
            lot.remaining_quantity -= take_qty
            remaining_to_sell -= take_qty

            # If lot is exhausted, it will be filtered out by remaining_quantity > 0

        await self.db.flush()
        return realized_pnl

    async def calculate_fifo_avg_cost(self, user_id: str, symbol: str) -> Decimal:
        """Calculate the FIFO-based average cost for a position.

        This is the weighted average of remaining cost lots.
        """
        lots = await self.get_cost_lots(user_id, symbol.upper())
        if not lots:
            return Decimal("0")

        total_cost = sum(lot.remaining_quantity * lot.purchase_price for lot in lots)
        total_qty = sum(lot.remaining_quantity for lot in lots)

        if total_qty == 0:
            return Decimal("0")

        return total_cost / total_qty

    async def update_position_with_fifo(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        trade_id: str | None = None,
    ) -> tuple[Position, Decimal]:
        """Update position using FIFO cost tracking.

        Args:
            user_id: User ID
            symbol: Stock symbol
            side: 'BUY' or 'SELL'
            quantity: Trade quantity
            price: Trade price
            trade_id: Optional trade ID for lot tracking

        Returns:
            Tuple of (updated position, realized P&L for sells)
        """
        symbol = symbol.upper()
        realized_pnl = Decimal("0")

        if side == "BUY":
            # Add a new cost lot
            await self.add_cost_lot(user_id, symbol, quantity, price, trade_id)
        else:  # SELL
            # Consume lots in FIFO order
            realized_pnl = await self.consume_cost_lots_fifo(
                user_id, symbol, quantity, price
            )

        # Calculate new position from remaining lots
        new_avg_cost = await self.calculate_fifo_avg_cost(user_id, symbol)
        lots = await self.get_cost_lots(user_id, symbol)
        new_quantity = sum(lot.remaining_quantity for lot in lots)

        # Update position
        position = await self.update_position(user_id, symbol, new_quantity, new_avg_cost)

        # Update realized P&L on position
        if realized_pnl != 0 and position.quantity > 0:
            position.realized_pnl = (position.realized_pnl or Decimal("0")) + realized_pnl
            await self.db.flush()
            await self.db.refresh(position)

        return position, realized_pnl

