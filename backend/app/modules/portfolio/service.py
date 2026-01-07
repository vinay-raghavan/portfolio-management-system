"""Portfolio service layer."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portfolio.models import CostLot, Portfolio, Position, Trade
from app.modules.portfolio.schemas import (
    PortfolioCreate,
    PortfolioDetailResponse,
    PortfolioInfo,
    PortfolioResponse,
    PortfolioSummary,
    PortfolioUpdate,
    PositionResponse,
    ProfitBookingRules,
)


class PortfolioService:
    """Service class for portfolio operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ============ Portfolio Management ============

    async def create_portfolio(self, user_id: str, data: PortfolioCreate) -> Portfolio:
        """Create a new portfolio for a user."""
        # If this is set as default, unset other defaults
        if data.is_default:
            await self.db.execute(
                update(Portfolio)
                .where(Portfolio.user_id == user_id, Portfolio.is_default)
                .values(is_default=False)
            )

        portfolio = Portfolio(
            user_id=user_id,
            name=data.name,
            description=data.description,
            currency=data.currency,
            is_default=data.is_default,
        )
        self.db.add(portfolio)
        await self.db.flush()
        await self.db.refresh(portfolio)
        return portfolio

    async def get_portfolios(self, user_id: str) -> list[Portfolio]:
        """Get all portfolios for a user."""
        result = await self.db.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.is_default.desc(), Portfolio.name)
        )
        return list(result.scalars().all())

    async def get_portfolio_by_id(self, user_id: str, portfolio_id: str) -> Portfolio | None:
        """Get a specific portfolio by ID."""
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_default_portfolio(self, user_id: str) -> Portfolio | None:
        """Get the default portfolio for a user."""
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.is_default)
        )
        return result.scalar_one_or_none()

    async def get_or_create_default_portfolio(self, user_id: str) -> Portfolio:
        """Get the default portfolio or create one if it doesn't exist."""
        portfolio = await self.get_default_portfolio(user_id)
        if portfolio is None:
            portfolio = await self.create_portfolio(
                user_id,
                PortfolioCreate(
                    name="Default Portfolio",
                    description="Default portfolio for all positions",
                    is_default=True,
                ),
            )
        return portfolio

    async def update_portfolio(
        self, user_id: str, portfolio_id: str, data: PortfolioUpdate
    ) -> Portfolio | None:
        """Update a portfolio."""
        portfolio = await self.get_portfolio_by_id(user_id, portfolio_id)
        if portfolio is None:
            return None

        # If setting as default, unset other defaults
        if data.is_default is True:
            await self.db.execute(
                update(Portfolio)
                .where(
                    Portfolio.user_id == user_id,
                    Portfolio.is_default,
                    Portfolio.id != portfolio_id,
                )
                .values(is_default=False)
            )

        if data.name is not None:
            portfolio.name = data.name
        if data.description is not None:
            portfolio.description = data.description
        if data.currency is not None:
            portfolio.currency = data.currency
        if data.is_default is not None:
            portfolio.is_default = data.is_default

        await self.db.flush()
        await self.db.refresh(portfolio)
        return portfolio

    async def delete_portfolio(self, user_id: str, portfolio_id: str) -> bool:
        """Delete a portfolio. Returns True if deleted, False if not found."""
        portfolio = await self.get_portfolio_by_id(user_id, portfolio_id)
        if portfolio is None:
            return False

        # Don't allow deleting the default portfolio if it has positions
        if portfolio.is_default:
            positions = await self.get_positions_by_portfolio(user_id, portfolio_id)
            if positions:
                raise ValueError("Cannot delete default portfolio with positions")

        await self.db.delete(portfolio)
        await self.db.flush()
        return True

    async def get_positions_by_portfolio(self, user_id: str, portfolio_id: str) -> list[Position]:
        """Get all positions for a specific portfolio."""
        result = await self.db.execute(
            select(Position)
            .where(Position.user_id == user_id, Position.portfolio_id == portfolio_id)
            .order_by(Position.symbol)
        )
        return list(result.scalars().all())

    # ============ Position Management ============

    async def get_positions(self, user_id: str) -> list[Position]:
        """Get all positions for a user."""
        result = await self.db.execute(
            select(Position).where(Position.user_id == user_id).order_by(Position.symbol)
        )
        return list(result.scalars().all())

    async def get_position(
        self, user_id: str, symbol: str, portfolio_id: str | None = None
    ) -> Position | None:
        """Get a specific position for a user, optionally within a portfolio."""
        if portfolio_id:
            result = await self.db.execute(
                select(Position).where(
                    Position.user_id == user_id,
                    Position.symbol == symbol,
                    Position.portfolio_id == portfolio_id,
                )
            )
        else:
            result = await self.db.execute(
                select(Position).where(Position.user_id == user_id, Position.symbol == symbol)
            )
        return result.scalar_one_or_none()

    async def update_position(
        self,
        user_id: str,
        symbol: str,
        quantity: Decimal,
        avg_cost: Decimal,
        portfolio_id: str | None = None,
    ) -> Position:
        """Create or update a position."""
        position = await self.get_position(user_id, symbol, portfolio_id)

        if position is None:
            position = Position(
                user_id=user_id,
                portfolio_id=portfolio_id,
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
        """Get full portfolio with summary (all positions across all portfolios)."""
        positions = await self.get_positions(user_id)
        summary, position_responses = await self._calculate_portfolio_summary(
            positions, price_getter
        )
        return PortfolioResponse(summary=summary, positions=position_responses)

    async def get_portfolio_detail(
        self,
        user_id: str,
        portfolio_id: str,
        price_getter: Callable | None = None,
    ) -> PortfolioDetailResponse | None:
        """Get detailed portfolio with positions and summary."""
        portfolio = await self.get_portfolio_by_id(user_id, portfolio_id)
        if portfolio is None:
            return None

        positions = await self.get_positions_by_portfolio(user_id, portfolio_id)
        summary, position_responses = await self._calculate_portfolio_summary(
            positions, price_getter, portfolio.id, portfolio.name
        )

        return PortfolioDetailResponse(
            portfolio=PortfolioInfo.model_validate(portfolio),
            summary=summary,
            positions=position_responses,
        )

    async def _calculate_portfolio_summary(
        self,
        positions: list[Position],
        price_getter: Callable | None = None,
        portfolio_id: str | None = None,
        portfolio_name: str | None = None,
    ) -> tuple[PortfolioSummary, list[PositionResponse]]:
        """Calculate portfolio summary from positions."""
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
                    portfolio_id=pos.portfolio_id,
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
            portfolio_id=portfolio_id,
            portfolio_name=portfolio_name,
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            cash_balance=Decimal("0"),  # TODO: Implement cash tracking
            positions_count=len(positions),
        )

        return summary, position_responses

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
        portfolio_id: str | None = None,
    ) -> CostLot:
        """Add a new cost lot when buying shares (FIFO tracking)."""
        lot = CostLot(
            user_id=user_id,
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            original_quantity=quantity,
            remaining_quantity=quantity,
            purchase_price=price,
            trade_id=trade_id,
            purchased_at=datetime.now(UTC),
        )
        self.db.add(lot)
        await self.db.flush()
        await self.db.refresh(lot)
        return lot

    async def get_cost_lots(
        self, user_id: str, symbol: str, portfolio_id: str | None = None
    ) -> list[CostLot]:
        """Get all cost lots for a symbol in FIFO order (oldest first)."""
        conditions = [
            CostLot.user_id == user_id,
            CostLot.symbol == symbol.upper(),
            CostLot.remaining_quantity > 0,
        ]
        if portfolio_id:
            conditions.append(CostLot.portfolio_id == portfolio_id)

        result = await self.db.execute(
            select(CostLot).where(*conditions).order_by(CostLot.purchased_at.asc())
        )
        return list(result.scalars().all())

    async def consume_cost_lots_fifo(
        self,
        user_id: str,
        symbol: str,
        quantity: Decimal,
        sell_price: Decimal,
        portfolio_id: str | None = None,
    ) -> Decimal:
        """Consume cost lots in FIFO order and calculate realized P&L.

        Args:
            user_id: User ID
            symbol: Stock symbol
            quantity: Quantity to sell
            sell_price: Sale price per share
            portfolio_id: Optional portfolio ID

        Returns:
            Realized profit/loss from this sale
        """
        lots = await self.get_cost_lots(user_id, symbol.upper(), portfolio_id)
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
            realized_pnl += sale_value - cost_basis

            # Update the lot
            lot.remaining_quantity -= take_qty
            remaining_to_sell -= take_qty

            # If lot is exhausted, it will be filtered out by remaining_quantity > 0

        await self.db.flush()
        return realized_pnl

    async def calculate_fifo_avg_cost(
        self, user_id: str, symbol: str, portfolio_id: str | None = None
    ) -> Decimal:
        """Calculate the FIFO-based average cost for a position.

        This is the weighted average of remaining cost lots.
        """
        lots = await self.get_cost_lots(user_id, symbol.upper(), portfolio_id)
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
        portfolio_id: str | None = None,
    ) -> tuple[Position, Decimal]:
        """Update position using FIFO cost tracking.

        Args:
            user_id: User ID
            symbol: Stock symbol
            side: 'BUY' or 'SELL'
            quantity: Trade quantity
            price: Trade price
            trade_id: Optional trade ID for lot tracking
            portfolio_id: Optional portfolio ID

        Returns:
            Tuple of (updated position, realized P&L for sells)
        """
        symbol = symbol.upper()
        realized_pnl = Decimal("0")

        if side == "BUY":
            # Add a new cost lot
            await self.add_cost_lot(user_id, symbol, quantity, price, trade_id, portfolio_id)
        else:  # SELL
            # Consume lots in FIFO order
            realized_pnl = await self.consume_cost_lots_fifo(
                user_id, symbol, quantity, price, portfolio_id
            )

        # Calculate new position from remaining lots
        new_avg_cost = await self.calculate_fifo_avg_cost(user_id, symbol, portfolio_id)
        lots = await self.get_cost_lots(user_id, symbol, portfolio_id)
        new_quantity = sum(lot.remaining_quantity for lot in lots)

        # Update position
        position = await self.update_position(
            user_id, symbol, new_quantity, new_avg_cost, portfolio_id
        )

        # Update realized P&L on position
        if realized_pnl != 0 and position.quantity > 0:
            position.realized_pnl = (position.realized_pnl or Decimal("0")) + realized_pnl
            await self.db.flush()
            await self.db.refresh(position)

        return position, realized_pnl

    # ============ Profit Booking Management ============

    async def get_profit_booking_rules(
        self, user_id: str, position_id: str
    ) -> ProfitBookingRules | None:
        """Get profit booking rules for a position."""
        result = await self.db.execute(
            select(Position).where(Position.id == position_id, Position.user_id == user_id)
        )
        position = result.scalar_one_or_none()

        if not position or not position.profit_booking_rules:
            return None

        return ProfitBookingRules.model_validate(position.profit_booking_rules)

    async def update_profit_booking_rules(
        self, user_id: str, position_id: str, rules: ProfitBookingRules
    ) -> ProfitBookingRules | None:
        """Update profit booking rules for a position."""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Looking for position - user_id: {user_id}, position_id: {position_id}")

        # First, let's see all positions for this user
        all_positions = await self.db.execute(
            select(Position).where(Position.user_id == user_id)
        )
        all_pos_list = all_positions.scalars().all()
        logger.info(f"User has {len(all_pos_list)} positions:")
        for p in all_pos_list:
            logger.info(f"  - Position ID: {p.id}, Symbol: {p.symbol}")

        result = await self.db.execute(
            select(Position).where(Position.id == position_id, Position.user_id == user_id)
        )
        position = result.scalar_one_or_none()

        if not position:
            logger.error("Position not found in database!")
            return None

        # Convert to dict for JSON storage, converting Decimals to floats
        position.profit_booking_rules = rules.model_dump(mode='json')
        await self.db.flush()
        await self.db.refresh(position)

        return ProfitBookingRules.model_validate(position.profit_booking_rules)
