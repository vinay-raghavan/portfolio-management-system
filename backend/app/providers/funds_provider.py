"""Database-backed funds provider for PaperBroker.

This module provides a FundsProvider implementation that wraps FundsService,
enabling PaperBroker to persist funds to the database.
"""

from decimal import Decimal

from shared.providers.broker.funds_provider import FundsProvider
from shared.providers.schemas import Funds
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portfolio.funds_service import FundsService


class DatabaseFundsProvider(FundsProvider):
    """Database-backed funds provider.

    Wraps FundsService to implement the FundsProvider protocol,
    allowing PaperBroker to sync funds with the database.
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session.

        Args:
            db: SQLAlchemy async session
        """
        self._funds_service = FundsService(db)

    async def get_funds(self, user_id: str) -> Funds:
        """Get funds for a user from the database.

        Args:
            user_id: User identifier

        Returns:
            Funds object with current balances
        """
        db_funds = await self._funds_service.get_or_create_funds(user_id)
        return Funds(
            available_cash=db_funds.available_cash,
            used_margin=db_funds.margin_used,
            total_balance=db_funds.cash_balance + db_funds.margin_used,
            collateral=db_funds.collateral,
        )

    async def update_funds_for_trade(
        self,
        user_id: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal,
    ) -> Funds:
        """Update funds after a trade execution.

        Args:
            user_id: User identifier
            side: Trade side ("BUY" or "SELL")
            quantity: Trade quantity
            price: Execution price
            fees: Trading fees

        Returns:
            Updated Funds object
        """
        total_value = quantity * price

        if side == "BUY":
            # Debit funds for purchase
            db_funds = await self._funds_service.debit_funds(
                user_id=user_id,
                amount=total_value + fees,
                description=f"Buy order: {quantity} @ {price}",
            )
        else:
            # Credit funds for sale
            db_funds = await self._funds_service.credit_funds(
                user_id=user_id,
                amount=total_value - fees,
                description=f"Sell order: {quantity} @ {price}",
            )

        return Funds(
            available_cash=db_funds.available_cash,
            used_margin=db_funds.margin_used,
            total_balance=db_funds.cash_balance + db_funds.margin_used,
            collateral=db_funds.collateral,
        )

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
        db_funds = await self._funds_service.initialize_funds(user_id, initial_balance)
        return Funds(
            available_cash=db_funds.available_cash,
            used_margin=db_funds.margin_used,
            total_balance=db_funds.cash_balance + db_funds.margin_used,
            collateral=db_funds.collateral,
        )

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
        return await self._funds_service.check_buying_power(user_id, required_amount)
