"""Portfolio service layer."""

from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portfolio.models import Position, Trade
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
        self, user_id: str, price_getter: callable | None = None
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

