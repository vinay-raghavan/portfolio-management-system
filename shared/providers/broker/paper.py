"""Paper trading broker implementation."""

import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Callable
from uuid import uuid4

from .base import Broker
from ..schemas import (
    Funds,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)

logger = logging.getLogger(__name__)


# Type for price fetching function - allows dependency injection of data provider
PriceFetcher = Callable[[str], float | None]


# Default initial balance and configuration
_default_initial_balance: Decimal = Decimal("1000000")


def set_initial_balance(balance: Decimal | float | int) -> None:
    """Set the default initial balance for paper trading.

    Args:
        balance: Initial balance amount
    """
    global _default_initial_balance
    _default_initial_balance = Decimal(str(balance))


class PaperBroker(Broker):
    """Paper trading broker for simulated trading.

    Stores positions and balances in memory. For persistence across
    restarts, the TradingService should sync with database.
    """

    name = "paper"
    is_paper = True

    # Simulated fees (0.1%)
    FEE_PERCENT = Decimal("0.001")

    def __init__(
        self,
        initial_balance: Decimal | None = None,
        price_fetcher: PriceFetcher | None = None,
    ):
        """Initialize paper broker.

        Args:
            initial_balance: Starting balance for new users
            price_fetcher: Function to fetch current price for a symbol
        """
        self._connected = False
        self._initial_balance = initial_balance or _default_initial_balance
        self._price_fetcher = price_fetcher

        # In-memory storage per user
        self._positions: dict[str, dict[str, Position]] = {}
        self._funds: dict[str, Funds] = {}
        self._orders: dict[str, dict[str, OrderResponse]] = {}
        self._pending_trigger_orders: dict[str, dict[str, OrderResponse]] = {}

    def set_price_fetcher(self, fetcher: PriceFetcher) -> None:
        """Set the price fetcher function.

        Args:
            fetcher: Function that takes a symbol and returns current price
        """
        self._price_fetcher = fetcher

    async def _get_current_price(self, symbol: str) -> float | None:
        """Get current price for a symbol."""
        if self._price_fetcher is None:
            logger.warning("No price fetcher configured, using default price")
            return 100.0  # Default price for testing
        return self._price_fetcher(symbol)

    async def connect(self) -> bool:
        """Connect (always succeeds for paper trading)."""
        self._connected = True
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
            self._funds[user_id] = Funds(
                available_cash=self._initial_balance,
                used_margin=Decimal("0"),
                total_balance=self._initial_balance,
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
        now = datetime.now(UTC)

        # Get current market price for validation
        current_price = await self._get_current_price(order.symbol)
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
        return await self._process_order(user_id, order, order_id, now, market_price, price, fees)

    async def _process_order(
        self,
        user_id: str,
        order: OrderRequest,
        order_id: str,
        now: datetime,
        market_price: Decimal,
        price: Decimal,
        fees: Decimal,
    ) -> OrderResponse:
        """Process order based on type."""
        if order.order_type == OrderType.MARKET:
            return await self._execute_order(user_id, order, price, fees, now)

        elif order.order_type == OrderType.LIMIT:
            can_execute = (order.side == OrderSide.BUY and market_price <= order.price) or (
                order.side == OrderSide.SELL and market_price >= order.price
            )
            if can_execute:
                return await self._execute_order(user_id, order, order.price, fees, now)
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
                return response

        elif order.order_type in (OrderType.STOP_LOSS, OrderType.STOP_LOSS_MARKET):
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
                exec_price = (
                    market_price if order.order_type == OrderType.STOP_LOSS_MARKET else order.price
                )
                return await self._execute_order(user_id, order, exec_price, fees, now)
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
                    message=f"Trigger price: {order.trigger_price}",
                )
                self._pending_trigger_orders[user_id][order_id] = response
                self._orders[user_id][order_id] = response
                return response

        elif order.order_type == OrderType.GTT:
            return await self._process_gtt_order(
                user_id, order, order_id, now, market_price, fees
            )

        else:
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                message=f"Unsupported order type: {order.order_type}",
                placed_at=now,
            )

    async def _process_gtt_order(
        self,
        user_id: str,
        order: OrderRequest,
        order_id: str,
        now: datetime,
        market_price: Decimal,
        fees: Decimal,
    ) -> OrderResponse:
        """Process GTT order."""
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

        triggered = self._check_trigger_condition(order, market_price)
        if triggered:
            exec_price = order.price if order.price else market_price
            return await self._execute_order(user_id, order, exec_price, fees, now)
        else:
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
            return response

    def _check_trigger_condition(self, order: OrderRequest, current_price: Decimal) -> bool:
        """Check if trigger condition is met for SL/GTT orders."""
        if order.trigger_price is None:
            return False
        if order.side == OrderSide.BUY:
            return current_price >= order.trigger_price
        else:
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
            funds.available_cash -= order_value + fees
        else:
            funds.available_cash += order_value - fees
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
        else:
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
        now = datetime.now(UTC)

        orders_to_remove = []
        for order_id, order in list(self._pending_trigger_orders[user_id].items()):
            if order.status != OrderStatus.OPEN:
                orders_to_remove.append(order_id)
                continue

            # Get current price
            current_price = await self._get_current_price(order.symbol)
            if current_price is None:
                continue
            market_price = Decimal(str(current_price))

            # Extract trigger price from message
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
                exec_price = (
                    market_price
                    if order.order_type == OrderType.STOP_LOSS_MARKET
                    else (order.price or market_price)
                )
                order_value = exec_price * order.quantity
                fees = order_value * self.FEE_PERCENT

                order_request = OrderRequest(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=OrderType.MARKET,
                    quantity=order.quantity,
                    price=exec_price,
                )

                try:
                    result = await self._execute_order(
                        user_id, order_request, exec_price, fees, now
                    )
                    result.message = f"Triggered at {trigger_price}, executed at {exec_price}"
                    executed_orders.append(result)
                    orders_to_remove.append(order_id)

                    order.status = OrderStatus.FILLED
                    order.filled_quantity = order.quantity
                    order.filled_price = exec_price
                    order.filled_at = now
                except Exception as e:
                    logger.error(f"Failed to execute triggered order {order_id}: {e}")

        for order_id in orders_to_remove:
            self._pending_trigger_orders[user_id].pop(order_id, None)

        return executed_orders

    def _extract_trigger_price(self, message: str | None) -> Decimal | None:
        """Extract trigger price from order message."""
        if not message:
            return None

        match = re.search(r"[Tt]rigger(?:\s+(?:price|at))?[:\s]+(\d+(?:\.\d+)?)", message)
        if match:
            return Decimal(match.group(1))
        return None

    async def get_pending_trigger_orders(self, user_id: str) -> list[OrderResponse]:
        """Get all pending trigger orders (SL/GTT) for a user."""
        self._ensure_user(user_id)
        return list(self._pending_trigger_orders[user_id].values())

