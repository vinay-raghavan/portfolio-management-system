"""Abstract base class for broker providers."""

from abc import ABC, abstractmethod
from decimal import Decimal

from ..schemas import (
    Funds,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderType,
    Position,
)


class Broker(ABC):
    """Abstract base class for broker providers.

    All broker implementations (Paper, AngelOne, Dhan, etc.) must implement
    this interface. This allows switching between brokers without changing
    business logic.
    """

    name: str = "base"
    is_paper: bool = True  # True for simulated trading

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to broker.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from broker."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if broker is connected.

        Returns:
            True if connected
        """
        pass

    @abstractmethod
    async def place_order(
        self,
        user_id: str,
        order: OrderRequest,
    ) -> OrderResponse:
        """Place a new order.

        Args:
            user_id: User identifier
            order: Order details

        Returns:
            OrderResponse with order ID and status
        """
        pass

    @abstractmethod
    async def cancel_order(
        self,
        user_id: str,
        order_id: str,
    ) -> bool:
        """Cancel a pending order.

        Args:
            user_id: User identifier
            order_id: Order to cancel

        Returns:
            True if cancellation successful
        """
        pass

    @abstractmethod
    async def modify_order(
        self,
        user_id: str,
        order_id: str,
        quantity: int | None = None,
        price: Decimal | None = None,
        trigger_price: Decimal | None = None,
    ) -> OrderResponse:
        """Modify an existing order.

        Args:
            user_id: User identifier
            order_id: Order to modify
            quantity: New quantity (optional)
            price: New price (optional)
            trigger_price: New trigger price (optional)

        Returns:
            Updated OrderResponse
        """
        pass

    @abstractmethod
    async def get_order_status(
        self,
        user_id: str,
        order_id: str,
    ) -> OrderResponse | None:
        """Get current status of an order.

        Args:
            user_id: User identifier
            order_id: Order to check

        Returns:
            OrderResponse with current status, or None if not found
        """
        pass

    @abstractmethod
    async def get_positions(self, user_id: str) -> list[Position]:
        """Get all open positions.

        Args:
            user_id: User identifier

        Returns:
            List of current positions
        """
        pass

    @abstractmethod
    async def get_funds(self, user_id: str) -> Funds:
        """Get account funds/balance.

        Args:
            user_id: User identifier

        Returns:
            Funds with available balance and margins
        """
        pass

    async def get_holdings(self, user_id: str) -> list[Position]:
        """Get delivery holdings (same as positions for paper trading).

        Args:
            user_id: User identifier

        Returns:
            List of holdings
        """
        return await self.get_positions(user_id)

    async def square_off_all(self, user_id: str) -> list[OrderResponse]:
        """Square off all positions (close all).

        Args:
            user_id: User identifier

        Returns:
            List of close order responses
        """
        positions = await self.get_positions(user_id)
        responses = []

        for position in positions:
            if position.quantity > 0:
                order = OrderRequest(
                    symbol=position.symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=int(position.quantity),
                )
                response = await self.place_order(user_id, order)
                responses.append(response)

        return responses
