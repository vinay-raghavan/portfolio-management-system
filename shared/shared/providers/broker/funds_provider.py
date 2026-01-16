"""Funds provider protocol for database-backed funds management.

This module defines the protocol for funds providers, allowing PaperBroker
to optionally sync with a database for persistent funds tracking.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from ..schemas import Funds


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
    ) -> Funds:
        """Update funds after a trade execution.

        For BUY: Deduct (quantity * price + fees) from available cash
        For SELL: Add (quantity * price - fees) to available cash

        Args:
            user_id: User identifier
            side: Trade side ("BUY" or "SELL")
            quantity: Trade quantity
            price: Execution price
            fees: Trading fees

        Returns:
            Updated Funds object
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
