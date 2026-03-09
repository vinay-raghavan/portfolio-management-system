"""Abstract base class for broker providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from ..schemas import (
    Funds,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderType,
    Position,
)


@dataclass
class SLBAvailability:
    """SLB availability information for a symbol."""

    symbol: str
    available_quantity: int
    borrow_rate: Decimal  # Annualized rate, e.g., 0.05 = 5%
    min_tenure_days: int
    max_tenure_days: int


@dataclass
class SLBBorrowResponse:
    """Response from borrowing securities via SLB."""

    success: bool
    slb_id: str | None  # Broker's SLB reference ID
    symbol: str
    quantity: int
    borrow_rate: Decimal
    tenure_days: int
    daily_fee: Decimal
    total_estimated_fee: Decimal
    error_message: str | None = None


@dataclass
class SLBReturnResponse:
    """Response from returning borrowed securities."""

    success: bool
    slb_id: str
    symbol: str
    quantity_returned: int
    total_fee_paid: Decimal
    error_message: str | None = None


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

    # =========================================================================
    # SLB (Securities Lending & Borrowing) Methods
    # =========================================================================
    # These methods support multi-day short selling via SLB.
    # Not all brokers support SLB - default implementations return not-supported.

    async def get_slb_availability(self, symbol: str) -> SLBAvailability | None:
        """Check SLB availability and rates for a symbol.

        Args:
            symbol: Stock symbol to check

        Returns:
            SLBAvailability if available, None if not supported or unavailable
        """
        # Default: SLB not supported
        return None

    async def borrow_securities(
        self,
        user_id: str,
        symbol: str,
        quantity: int,
        tenure_days: int,
    ) -> SLBBorrowResponse:
        """Borrow securities via SLB for short selling.

        Args:
            user_id: User identifier
            symbol: Stock symbol to borrow
            quantity: Number of shares to borrow
            tenure_days: Borrowing period in days

        Returns:
            SLBBorrowResponse with borrowing details or error
        """
        # Default: SLB not supported
        return SLBBorrowResponse(
            success=False,
            slb_id=None,
            symbol=symbol,
            quantity=0,
            borrow_rate=Decimal("0"),
            tenure_days=0,
            daily_fee=Decimal("0"),
            total_estimated_fee=Decimal("0"),
            error_message="SLB not supported by this broker",
        )

    async def return_securities(
        self,
        user_id: str,
        slb_id: str,
    ) -> SLBReturnResponse:
        """Return borrowed securities to close SLB position.

        Args:
            user_id: User identifier
            slb_id: SLB position ID from borrow_securities

        Returns:
            SLBReturnResponse with return details or error
        """
        # Default: SLB not supported
        return SLBReturnResponse(
            success=False,
            slb_id=slb_id,
            symbol="",
            quantity_returned=0,
            total_fee_paid=Decimal("0"),
            error_message="SLB not supported by this broker",
        )
