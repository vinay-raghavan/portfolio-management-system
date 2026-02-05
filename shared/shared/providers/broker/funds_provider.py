"""Funds provider protocol for database-backed funds management.

This module defines the protocol for funds providers, allowing PaperBroker
to optionally sync with a database for persistent funds tracking.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from ..schemas import Funds, ProductType


class FundsProvider(ABC):
    """Abstract base class for funds providers.

    Implementations of this protocol provide persistent storage for user funds,
    allowing PaperBroker to sync with a database instead of using in-memory storage.
    """

    @abstractmethod
    async def get_funds(self, user_id: str) -> Funds:
        """Get funds for a user.

        Args:
            user_id: User identifier

        Returns:
            Funds object with current balances
        """
        pass

    @abstractmethod
    async def update_funds_for_trade(
        self,
        user_id: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal,
        product_type: ProductType = ProductType.DELIVERY,
        existing_position_qty: Decimal | None = None,
    ) -> Funds:
        """Update funds after a trade execution.

        Behavior depends on product_type:
        - DELIVERY (CNC): Full payment for BUY, must own shares to SELL
        - INTRADAY (MIS): Block margin (25%) for both BUY and SELL (shorting allowed)
        - MARGIN (MTF): Block margin (50%) for BUY only, no shorting

        Args:
            user_id: User identifier
            side: Trade side ("BUY" or "SELL")
            quantity: Trade quantity
            price: Execution price
            fees: Trading fees
            product_type: Product type (DELIVERY, INTRADAY, MARGIN)
            existing_position_qty: Current position quantity (for SELL validation)

        Returns:
            Updated Funds object

        Raises:
            ValueError: If insufficient funds/margin or invalid operation
        """
        pass

    @abstractmethod
    async def initialize_funds(
        self,
        user_id: str,
        initial_balance: Decimal,
    ) -> Funds:
        """Initialize funds for a new user.

        Args:
            user_id: User identifier
            initial_balance: Starting balance

        Returns:
            Newly created Funds object
        """
        pass

    @abstractmethod
    async def check_buying_power(
        self,
        user_id: str,
        required_amount: Decimal,
    ) -> bool:
        """Check if user has sufficient buying power.

        Args:
            user_id: User identifier
            required_amount: Amount needed for the transaction

        Returns:
            True if user has sufficient funds
        """
        pass

    @abstractmethod
    async def get_position_quantity(
        self,
        user_id: str,
        symbol: str,
    ) -> Decimal:
        """Get existing position quantity for a user and symbol.

        This is used to determine if a SELL order is closing an existing position
        (which releases margin) or opening a short position (which blocks margin).

        Args:
            user_id: User identifier
            symbol: Stock symbol

        Returns:
            Current position quantity (positive for long, negative for short, 0 if no position)
        """
        pass
