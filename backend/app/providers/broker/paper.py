"""Paper trading broker implementation."""

import logging
from datetime import datetime, timezone, timedelta
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
        self._pending_trigger_orders: dict[str, dict[str, OrderResponse]] = {}  # SL/GTT orders waiting for trigger
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
        if user_id not in self._pending_trigger_orders:
            self._pending_trigger_orders[user_id] = {}

    async def place_order(
        self,
        user_id: str,
        order: OrderRequest,
    ) -> OrderResponse:
        """Place a paper trading order."""
        self._ensure_user(user_id)

        order_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # Get current market price for validation
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
        market_price = Decimal(str(current_price))

        # Determine execution price
        price = order.price if order.price else market_price
        if order.order_type == OrderType.MARKET:
            price = market_price

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

        # Handle different order types
        if order.order_type == OrderType.MARKET:
            # Market orders execute immediately
            response = await self._execute_order(user_id, order, price, fees, now)
        elif order.order_type == OrderType.LIMIT:
            # Limit orders: check if price condition is met
            can_execute = (
                (order.side == OrderSide.BUY and market_price <= order.price) or
                (order.side == OrderSide.SELL and market_price >= order.price)
            )
            if can_execute:
                response = await self._execute_order(user_id, order, order.price, fees, now)
            else:
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
        elif order.order_type in (OrderType.STOP_LOSS, OrderType.STOP_LOSS_MARKET):
            # SL/SL-M orders: check if trigger price is hit
            if order.trigger_price is None:
                return OrderResponse(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    message="Trigger price is required for SL/SL-M orders",
                    placed_at=now,
                )

            triggered = self._check_trigger_condition(order, market_price)
            if triggered:
                # If SL-M, execute at market; if SL, execute at limit price
                exec_price = market_price if order.order_type == OrderType.STOP_LOSS_MARKET else order.price
                response = await self._execute_order(user_id, order, exec_price, fees, now)
            else:
                # Store as pending trigger order
                response = OrderResponse(
                    order_id=order_id,
                    status=OrderStatus.OPEN,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    price=order.price,
                    placed_at=now,
                    message=f"Trigger price: {order.trigger_price}",
                )
                self._pending_trigger_orders[user_id][order_id] = response
                self._orders[user_id][order_id] = response
        elif order.order_type == OrderType.GTT:
            # GTT orders: store with validity period
            if order.trigger_price is None:
                return OrderResponse(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    message="Trigger price is required for GTT orders",
                    placed_at=now,
                )

            # Check if already triggered
            triggered = self._check_trigger_condition(order, market_price)
            if triggered:
                exec_price = order.price if order.price else market_price
                response = await self._execute_order(user_id, order, exec_price, fees, now)
            else:
                # Store as pending GTT order (valid for 1 year by default)
                valid_till = order.valid_till or (now + timedelta(days=365))
                response = OrderResponse(
                    order_id=order_id,
                    status=OrderStatus.OPEN,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    price=order.price,
                    placed_at=now,
                    message=f"GTT: Trigger at {order.trigger_price}, Valid till: {valid_till.date()}",
                )
                self._pending_trigger_orders[user_id][order_id] = response
                self._orders[user_id][order_id] = response
        else:
            # Unknown order type
            response = OrderResponse(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                message=f"Unsupported order type: {order.order_type}",
                placed_at=now,
            )

        return response

    def _check_trigger_condition(self, order: OrderRequest, current_price: Decimal) -> bool:
        """Check if trigger condition is met for SL/GTT orders.

        For BUY SL orders: trigger when price >= trigger_price (price going up)
        For SELL SL orders: trigger when price <= trigger_price (price going down)
        """
        if order.trigger_price is None:
            return False

        if order.side == OrderSide.BUY:
            return current_price >= order.trigger_price
        else:  # SELL
            return current_price <= order.trigger_price

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

    async def check_trigger_orders(self, user_id: str) -> list[OrderResponse]:
        """Check and execute any triggered SL/GTT orders.

        This should be called periodically (e.g., by a Celery task) to monitor
        and execute trigger-based orders.

        Returns:
            List of orders that were triggered and executed
        """
        self._ensure_user(user_id)
        executed_orders = []
        now = datetime.now(timezone.utc)

        orders_to_remove = []
        for order_id, order in list(self._pending_trigger_orders[user_id].items()):
            if order.status != OrderStatus.OPEN:
                orders_to_remove.append(order_id)
                continue

            # Get current price
            current_price = await self._data_provider.get_current_price(order.symbol)
            if current_price is None:
                continue
            market_price = Decimal(str(current_price))

            # Extract trigger price from message (stored there for now)
            # In a real implementation, this would be stored in order metadata
            trigger_price = self._extract_trigger_price(order.message)
            if trigger_price is None:
                continue

            # Check trigger condition
            triggered = False
            if order.side == OrderSide.BUY:
                triggered = market_price >= trigger_price
            else:
                triggered = market_price <= trigger_price

            if triggered:
                # Execute the order
                exec_price = market_price if order.order_type == OrderType.STOP_LOSS_MARKET else (order.price or market_price)
                order_value = exec_price * order.quantity
                fees = order_value * self.FEE_PERCENT

                # Create order request for execution
                order_request = OrderRequest(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=OrderType.MARKET,  # Execute as market
                    quantity=order.quantity,
                    price=exec_price,
                )

                try:
                    result = await self._execute_order(user_id, order_request, exec_price, fees, now)
                    result.message = f"Triggered at {trigger_price}, executed at {exec_price}"
                    executed_orders.append(result)
                    orders_to_remove.append(order_id)

                    # Update the original order status
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = order.quantity
                    order.filled_price = exec_price
                    order.filled_at = now
                except Exception as e:
                    logger.error(f"Failed to execute triggered order {order_id}: {e}")

        # Clean up executed orders from pending
        for order_id in orders_to_remove:
            self._pending_trigger_orders[user_id].pop(order_id, None)

        return executed_orders

    def _extract_trigger_price(self, message: str | None) -> Decimal | None:
        """Extract trigger price from order message."""
        if not message:
            return None

        # Format: "Trigger price: X" or "GTT: Trigger at X, ..."
        import re
        # Match "Trigger price: 123" or "Trigger at 123" or "Trigger: 123"
        match = re.search(r'[Tt]rigger(?:\s+(?:price|at))?[:\s]+(\d+(?:\.\d+)?)', message)
        if match:
            return Decimal(match.group(1))
        return None

    async def get_pending_trigger_orders(self, user_id: str) -> list[OrderResponse]:
        """Get all pending trigger orders (SL/GTT) for a user."""
        self._ensure_user(user_id)
        return list(self._pending_trigger_orders[user_id].values())

