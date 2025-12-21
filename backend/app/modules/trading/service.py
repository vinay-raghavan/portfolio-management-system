"""Trading service layer with paper trading simulator."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.models import Order, OrderStatus
from app.modules.trading.schemas import OrderCreate
from app.modules.portfolio.models import Position, Trade
from app.modules.portfolio.service import PortfolioService


class TradingService:
    """Service class for trading operations."""

    # Simulated trading fee (0.1%)
    TRADING_FEE_PCT = Decimal("0.001")

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.portfolio_service = PortfolioService(db)

    async def create_order(self, user_id: str, order_data: OrderCreate) -> Order:
        """Create a new order."""
        order = Order(
            user_id=user_id,
            symbol=order_data.symbol.upper(),
            side=order_data.side.value,
            order_type=order_data.order_type.value,
            quantity=order_data.quantity,
            price=order_data.price,
            stop_loss=order_data.stop_loss,
            take_profit=order_data.take_profit,
            status=OrderStatus.PENDING.value,
            notes=order_data.notes,
        )
        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def execute_market_order(
        self, order: Order, current_price: Decimal
    ) -> Order:
        """Execute a market order immediately (paper trading)."""
        # Calculate fees
        order_value = order.quantity * current_price
        fees = order_value * self.TRADING_FEE_PCT

        # Update order
        order.status = OrderStatus.FILLED.value
        order.filled_quantity = order.quantity
        order.filled_price = current_price
        order.fees = fees
        order.filled_at = datetime.now(timezone.utc)

        # Create trade record
        trade = Trade(
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=current_price,
            fees=fees,
        )
        self.db.add(trade)

        # Update position
        await self._update_position_after_trade(
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=current_price,
        )

        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def _update_position_after_trade(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
    ) -> None:
        """Update position after a trade execution."""
        position = await self.portfolio_service.get_position(user_id, symbol)

        if side == "BUY":
            if position is None:
                # New position
                await self.portfolio_service.update_position(
                    user_id, symbol, quantity, price
                )
            else:
                # Average up/down
                total_cost = (position.quantity * position.avg_cost) + (quantity * price)
                new_quantity = position.quantity + quantity
                new_avg_cost = total_cost / new_quantity
                await self.portfolio_service.update_position(
                    user_id, symbol, new_quantity, new_avg_cost
                )
        else:  # SELL
            if position is None:
                # Short selling not supported in paper trading
                return
            new_quantity = position.quantity - quantity
            if new_quantity <= 0:
                # Close position
                await self.portfolio_service.update_position(
                    user_id, symbol, Decimal("0"), position.avg_cost
                )
            else:
                # Partial sell - keep same avg cost
                await self.portfolio_service.update_position(
                    user_id, symbol, new_quantity, position.avg_cost
                )

    async def get_orders(
        self, user_id: str, status: str | None = None, page: int = 1, page_size: int = 50
    ) -> tuple[list[Order], int]:
        """Get orders with optional status filter and pagination."""
        query = select(Order).where(Order.user_id == user_id)

        if status:
            query = query.where(Order.status == status)

        # Get count
        count_query = select(func.count(Order.id)).where(Order.user_id == user_id)
        if status:
            count_query = count_query.where(Order.status == status)
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        query = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        orders = list(result.scalars().all())

        return orders, total_count

    async def cancel_order(self, user_id: str, order_id: str) -> Order | None:
        """Cancel a pending order."""
        result = await self.db.execute(
            select(Order).where(
                Order.id == order_id,
                Order.user_id == user_id,
                Order.status == OrderStatus.PENDING.value,
            )
        )
        order = result.scalar_one_or_none()

        if order:
            order.status = OrderStatus.CANCELLED.value
            await self.db.flush()
            await self.db.refresh(order)

        return order

