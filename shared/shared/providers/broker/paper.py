"""Paper trading broker implementation."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from ..schemas import (
    Funds,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    ProductType,
)
from .base import Broker

if TYPE_CHECKING:
    from .funds_provider import FundsProvider

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
        funds_provider: FundsProvider | None = None,
    ):
        """Initialize paper broker.

        Args:
            initial_balance: Starting balance for new users
            price_fetcher: Function to fetch current price for a symbol
            funds_provider: Optional database-backed funds provider for persistence.
                          When provided, funds are synced with database instead of
                          in-memory storage.
        """
        self._connected = False
        self._initial_balance = initial_balance or _default_initial_balance
        self._price_fetcher = price_fetcher
        self._funds_provider = funds_provider

        # In-memory storage per user
        self._positions: dict[str, dict[str, Position]] = {}
        self._funds: dict[str, Funds] = {}
        self._orders: dict[str, dict[str, OrderResponse]] = {}
        self._pending_trigger_orders: dict[str, dict[str, OrderResponse]] = {}

    def set_funds_provider(self, provider: FundsProvider) -> None:
        """Set a database-backed funds provider.

        When set, all funds operations will be persisted to the database.

        Args:
            provider: FundsProvider implementation (e.g., DatabaseFundsProvider)
        """
        self._funds_provider = provider
        logger.info("Paper broker configured with database funds provider")

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

        # Get current position for validation
        positions = self._positions.get(user_id, {})
        existing_position = positions.get(order.symbol.upper())
        existing_qty = existing_position.quantity if existing_position else Decimal("0")

        # Normalize product type
        product_type = ProductType.normalize(order.product_type)
        margin_percent = Decimal(str(ProductType.get_margin_percent(order.product_type)))

        # Validate order based on product type
        funds = await self.get_funds(user_id)
        validation_error = self._validate_order_for_product_type(
            order=order,
            product_type=product_type,
            margin_percent=margin_percent,
            order_value=order_value,
            fees=fees,
            funds=funds,
            existing_qty=existing_qty,
        )
        if validation_error:
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                message=validation_error,
                placed_at=now,
            )

        # Handle different order types
        return await self._process_order(user_id, order, order_id, now, market_price, price, fees)

    def _validate_order_for_product_type(
        self,
        order: OrderRequest,
        product_type: ProductType,
        margin_percent: Decimal,
        order_value: Decimal,
        fees: Decimal,
        funds: Funds,
        existing_qty: Decimal,
    ) -> str | None:
        """Validate order based on product type rules.

        Returns:
            Error message if validation fails, None if valid.
        """
        if order.side == OrderSide.BUY:
            return self._validate_buy_order(
                product_type, margin_percent, order_value, fees, funds
            )
        else:  # SELL
            return self._validate_sell_order(
                order, product_type, margin_percent, order_value, fees, funds, existing_qty
            )

    def _validate_buy_order(
        self,
        product_type: ProductType,
        margin_percent: Decimal,
        order_value: Decimal,
        fees: Decimal,
        funds: Funds,
    ) -> str | None:
        """Validate BUY order based on product type."""
        if product_type == ProductType.DELIVERY:
            # DELIVERY: Full payment required
            total_cost = order_value + fees
            if total_cost > funds.available_cash:
                return (
                    f"Insufficient funds for DELIVERY buy. "
                    f"Required: ₹{total_cost:.2f}, Available: ₹{funds.available_cash:.2f}"
                )
        else:
            # INTRADAY/MARGIN: Margin required
            margin_required = order_value * margin_percent + fees
            if margin_required > funds.available_cash:
                return (
                    f"Insufficient margin for {product_type.value} buy. "
                    f"Required: ₹{margin_required:.2f} ({margin_percent*100:.0f}% margin), "
                    f"Available: ₹{funds.available_cash:.2f}"
                )
        return None

    def _validate_sell_order(
        self,
        order: OrderRequest,
        product_type: ProductType,
        margin_percent: Decimal,
        order_value: Decimal,
        fees: Decimal,
        funds: Funds,
        existing_qty: Decimal,
    ) -> str | None:
        """Validate SELL order based on product type."""
        if product_type == ProductType.DELIVERY:
            # DELIVERY: Must own shares to sell (no shorting)
            if existing_qty < order.quantity:
                return (
                    f"Cannot short sell in DELIVERY mode. "
                    f"Trying to sell {order.quantity} shares but only own {existing_qty}."
                )

        elif product_type == ProductType.INTRADAY:
            # INTRADAY: Short selling allowed with margin
            # If opening a short (not closing existing long), check margin
            if existing_qty <= 0:
                margin_required = order_value * margin_percent + fees
                if margin_required > funds.available_cash:
                    return (
                        f"Insufficient margin for INTRADAY short sell. "
                        f"Required: ₹{margin_required:.2f} ({margin_percent*100:.0f}% margin), "
                        f"Available: ₹{funds.available_cash:.2f}"
                    )

        elif product_type == ProductType.MARGIN:
            # MARGIN (MTF): No short selling allowed
            if existing_qty < order.quantity:
                return (
                    f"Cannot short sell in MARGIN (MTF) mode. "
                    f"Trying to sell {order.quantity} shares but only own {existing_qty}."
                )

        return None

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
            return await self._process_gtt_order(user_id, order, order_id, now, market_price, fees)

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

        # Get existing position for funds update
        positions = self._positions.get(user_id, {})
        existing_position = positions.get(order.symbol.upper())
        existing_qty = existing_position.quantity if existing_position else Decimal("0")

        # Update funds - use provider if available for database sync
        if self._funds_provider is not None:
            await self._funds_provider.update_funds_for_trade(
                user_id=user_id,
                side=order.side.value,
                quantity=Decimal(str(order.quantity)),
                price=price,
                fees=fees,
                product_type=order.product_type,
                existing_position_qty=existing_qty,
            )
        else:
            # In-memory funds update (no persistence) - simplified, no product type logic
            order_value = price * order.quantity
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
        """Get account funds.

        If a funds provider is configured, retrieves funds from the database.
        Otherwise, returns in-memory funds.

        Args:
            user_id: User identifier

        Returns:
            Funds object with current balances
        """
        if self._funds_provider is not None:
            return await self._funds_provider.get_funds(user_id)

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
