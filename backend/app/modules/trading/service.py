"""Trading service layer with broker provider abstraction."""

from datetime import datetime, timezone
from decimal import Decimal
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.models import Order, OrderStatus
from app.modules.trading.schemas import OrderCreate, OrderSide
from app.modules.trading.validator import OrderValidator, ValidationResult, create_validation_error_response
from app.modules.portfolio.models import Position, Trade
from app.modules.portfolio.service import PortfolioService
from app.modules.portfolio.funds_service import FundsService
from app.providers.broker.factory import get_broker, BrokerFactory
from app.providers.broker.base import Broker
from app.providers.schemas import (
    OrderRequest,
    OrderSide as ProviderOrderSide,
    OrderType as ProviderOrderType,
    OrderStatus as ProviderOrderStatus,
)

logger = logging.getLogger(__name__)


class OrderValidationError(Exception):
    """Exception raised when order validation fails."""

    def __init__(self, result: ValidationResult):
        self.result = result
        self.detail = create_validation_error_response(result)
        super().__init__(self.detail["message"])


class TradingService:
    """Service class for trading operations.

    Integrates with broker provider for order execution while maintaining
    database persistence for order history and positions.
    """

    # Simulated trading fee (0.1%) - used for paper trading
    TRADING_FEE_PCT = Decimal("0.001")

    def __init__(
        self,
        db: AsyncSession,
        broker: Broker | None = None,
        skip_validation: bool = False
    ) -> None:
        """Initialize trading service.

        Args:
            db: Database session for persistence
            broker: Optional broker instance. If None, uses default from config.
            skip_validation: Skip order validation (for testing only)
        """
        self.db = db
        self.portfolio_service = PortfolioService(db)
        self.funds_service = FundsService(db)
        self.validator = OrderValidator(db)
        self._broker = broker
        self._skip_validation = skip_validation

    @property
    def broker(self) -> Broker:
        """Get broker instance (lazy initialization)."""
        if self._broker is None:
            self._broker = get_broker()
        return self._broker

    @property
    def is_paper_trading(self) -> bool:
        """Check if using paper trading mode."""
        return BrokerFactory.is_paper_trading()

    async def create_order(
        self,
        user_id: str,
        order_data: OrderCreate,
        skip_market_hours_check: bool = False
    ) -> Order:
        """Create a new order and execute via broker provider.

        For market orders, execution is immediate. For limit orders,
        the order is stored as pending.

        Args:
            user_id: User placing the order
            order_data: Order details
            skip_market_hours_check: Skip market hours validation (for testing)

        Returns:
            Created/executed Order

        Raises:
            OrderValidationError: If order validation fails
        """
        # Run validation unless explicitly skipped
        if not self._skip_validation:
            # Convert to provider schema for validation
            provider_order = OrderRequest(
                symbol=order_data.symbol.upper(),
                side=ProviderOrderSide(order_data.side.value),
                order_type=ProviderOrderType.MARKET
                if order_data.order_type.value == "MARKET"
                else ProviderOrderType.LIMIT,
                quantity=int(order_data.quantity),
                price=order_data.price,
            )

            validation_result = await self.validator.validate(
                user_id=user_id,
                order=provider_order,
                skip_market_hours=skip_market_hours_check,
                skip_funds_check=(order_data.order_type.value != "MARKET"),
            )

            # Additional check for SELL orders
            if order_data.side == OrderSide.SELL:
                await self.validator.validate_sell_quantity(
                    user_id=user_id,
                    symbol=order_data.symbol.upper(),
                    quantity=order_data.quantity,
                    result=validation_result,
                )

            if not validation_result.is_valid:
                raise OrderValidationError(validation_result)

        # Create database record
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

        # Execute via broker provider for market orders
        if order_data.order_type.value == "MARKET":
            order = await self._execute_via_broker(user_id, order, order_data)

        return order

    async def _execute_via_broker(
        self,
        user_id: str,
        order: Order,
        order_data: OrderCreate,
    ) -> Order:
        """Execute order through broker provider and settle funds."""
        # Ensure broker is connected
        if not await self.broker.is_connected():
            await self.broker.connect()

        # Convert to provider schema
        provider_order = OrderRequest(
            symbol=order_data.symbol.upper(),
            side=ProviderOrderSide(order_data.side.value),
            order_type=ProviderOrderType.MARKET
            if order_data.order_type.value == "MARKET"
            else ProviderOrderType.LIMIT,
            quantity=int(order_data.quantity),
            price=order_data.price,
            stop_loss=order_data.stop_loss,
            take_profit=order_data.take_profit,
        )

        # Execute via broker
        response = await self.broker.place_order(user_id, provider_order)

        # Update order with response
        if response.status == ProviderOrderStatus.FILLED:
            order.status = OrderStatus.FILLED.value
            order.filled_quantity = Decimal(str(response.filled_quantity))
            order.filled_price = response.filled_price
            order.fees = response.fees
            order.filled_at = response.filled_at or datetime.now(timezone.utc)

            # Create trade record for persistence
            trade = Trade(
                user_id=user_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=response.filled_price,
                fees=response.fees,
            )
            self.db.add(trade)

            # Settle funds (deduct for BUY, add for SELL)
            await self.funds_service.process_trade_settlement(
                user_id=user_id,
                side=order.side,
                quantity=order.quantity,
                price=response.filled_price,
                fees=response.fees,
            )
            logger.info(
                f"Funds settled for {order.side} {order.quantity} {order.symbol} "
                f"@ {response.filled_price}"
            )

            # Update position in database
            await self._update_position_after_trade(
                user_id=user_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=response.filled_price,
            )
        elif response.status == ProviderOrderStatus.REJECTED:
            order.status = OrderStatus.REJECTED.value
            order.notes = (order.notes or "") + f"\nRejected: {response.message}"
            logger.warning(f"Order rejected: {response.message}")
        else:
            order.status = response.status.value

        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def execute_market_order(
        self, order: Order, current_price: Decimal
    ) -> Order:
        """Execute a market order immediately (legacy method for backward compatibility).

        Prefer using create_order() which handles broker execution automatically.
        """
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

