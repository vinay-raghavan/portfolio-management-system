"""Paper trading broker implementation."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.core.config import settings
from app.providers.broker.base import Broker
from app.providers.schemas import (
    OrderRequest,
    OrderResponse,
    OrderStatus,
    OrderSide,
    OrderType,
    Position,
    Funds,
)
from app.providers.data.factory import get_data_provider

logger = logging.getLogger(__name__)


class PaperBroker(Broker):
    """Paper trading broker for simulated trading.

    Stores positions and balances in memory. For persistence across
    restarts, the TradingService should sync with database.
    """

    name = "paper"
    is_paper = True

    # Simulated fees (0.1%)
    FEE_PERCENT = Decimal("0.001")

    def __init__(self):
        """Initialize paper broker."""
        self._connected = False
        # In-memory storage per user
        self._positions: dict[str, dict[str, Position]] = {}
        self._funds: dict[str, Funds] = {}
        self._orders: dict[str, dict[str, OrderResponse]] = {}
        self._data_provider = None

    async def connect(self) -> bool:
        """Connect (always succeeds for paper trading)."""
        self._connected = True
        self._data_provider = get_data_provider()
        logger.info("Paper broker connected")
        return True

    async def disconnect(self) -> None:
        """Disconnect from broker."""
        self._connected = False
        logger.info("Paper broker disconnected")

    async def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def _ensure_user(self, user_id: str) -> None:
        """Ensure user has initialized storage."""
        if user_id not in self._positions:
            self._positions[user_id] = {}
        if user_id not in self._funds:
            initial_balance = Decimal(str(settings.PAPER_TRADING_INITIAL_BALANCE))
            self._funds[user_id] = Funds(
                available_cash=initial_balance,
                used_margin=Decimal("0"),
                total_balance=initial_balance,
            )
        if user_id not in self._orders:
            self._orders[user_id] = {}

    async def place_order(
        self,
        user_id: str,
        order: OrderRequest,
    ) -> OrderResponse:
        """Place a paper trading order."""
        self._ensure_user(user_id)

        order_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # Get current price
        price = order.price
        if order.order_type == OrderType.MARKET:
            current_price = await self._data_provider.get_current_price(order.symbol)
            if current_price is None:
                return OrderResponse(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    message="Could not get current price",
                    placed_at=now,
                )
            price = Decimal(str(current_price))

        # Calculate order value and fees
        order_value = price * order.quantity
        fees = order_value * self.FEE_PERCENT

        # Check funds for buy orders
        funds = self._funds[user_id]
        if order.side == OrderSide.BUY:
            total_cost = order_value + fees
            if total_cost > funds.available_cash:
                return OrderResponse(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    message=f"Insufficient funds. Required: {total_cost}, Available: {funds.available_cash}",
                    placed_at=now,
                )

        # Execute order (paper trading is instant for market orders)
        if order.order_type == OrderType.MARKET:
            response = await self._execute_order(user_id, order, price, fees, now)
        else:
            # For limit orders, store as pending
            response = OrderResponse(
                order_id=order_id,
                status=OrderStatus.OPEN,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                placed_at=now,
            )
            self._orders[user_id][order_id] = response

        return response

    async def _execute_order(
        self,
        user_id: str,
        order: OrderRequest,
        price: Decimal,
        fees: Decimal,
        timestamp: datetime,
    ) -> OrderResponse:
        """Execute an order immediately."""
        order_id = str(uuid4())
        order_value = price * order.quantity

        # Update funds
        funds = self._funds[user_id]
        if order.side == OrderSide.BUY:
            funds.available_cash -= (order_value + fees)
        else:
            funds.available_cash += (order_value - fees)
        funds.total_balance = funds.available_cash + funds.used_margin

        # Update position
        await self._update_position(user_id, order, price)

        response = OrderResponse(
            order_id=order_id,
            status=OrderStatus.FILLED,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            filled_quantity=order.quantity,
            price=price,
            filled_price=price,
            fees=fees,
            placed_at=timestamp,
            filled_at=timestamp,
        )
        self._orders[user_id][order_id] = response
        return response

    async def _update_position(
        self,
        user_id: str,
        order: OrderRequest,
        price: Decimal,
    ) -> None:
        """Update position after trade execution."""
        positions = self._positions[user_id]
        symbol = order.symbol.upper()

        if order.side == OrderSide.BUY:
            if symbol in positions:
                pos = positions[symbol]
                total_cost = (pos.quantity * pos.avg_cost) + (order.quantity * price)
                new_qty = pos.quantity + order.quantity
                new_avg = total_cost / new_qty
                positions[symbol] = Position(
                    symbol=symbol,
                    quantity=new_qty,
                    avg_cost=new_avg,
                    current_price=price,
                )
            else:
                positions[symbol] = Position(
                    symbol=symbol,
                    quantity=Decimal(str(order.quantity)),
                    avg_cost=price,
                    current_price=price,
                )
        else:  # SELL
            if symbol in positions:
                pos = positions[symbol]
                new_qty = pos.quantity - order.quantity
                if new_qty <= 0:
                    del positions[symbol]
                else:
                    positions[symbol] = Position(
                        symbol=symbol,
                        quantity=new_qty,
                        avg_cost=pos.avg_cost,
                        current_price=price,
                    )

    async def cancel_order(self, user_id: str, order_id: str) -> bool:
        """Cancel a pending order."""
        self._ensure_user(user_id)
        if order_id in self._orders[user_id]:
            order = self._orders[user_id][order_id]
            if order.status == OrderStatus.OPEN:
                order.status = OrderStatus.CANCELLED
                return True
        return False

    async def modify_order(
        self,
        user_id: str,
        order_id: str,
        quantity: int | None = None,
        price: Decimal | None = None,
        trigger_price: Decimal | None = None,
    ) -> OrderResponse:
        """Modify an existing order."""
        self._ensure_user(user_id)
        if order_id not in self._orders[user_id]:
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                symbol="",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=0,
                message="Order not found",
            )

        order = self._orders[user_id][order_id]
        if order.status != OrderStatus.OPEN:
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                message="Cannot modify non-open order",
            )

        if quantity:
            order.quantity = quantity
        if price:
            order.price = price

        return order

    async def get_order_status(self, user_id: str, order_id: str) -> OrderResponse | None:
        """Get current status of an order."""
        self._ensure_user(user_id)
        return self._orders[user_id].get(order_id)

    async def get_positions(self, user_id: str) -> list[Position]:
        """Get all open positions."""
        self._ensure_user(user_id)
        return list(self._positions[user_id].values())

    async def get_funds(self, user_id: str) -> Funds:
        """Get account funds."""
        self._ensure_user(user_id)
        return self._funds[user_id]

