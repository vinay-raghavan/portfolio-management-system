"""Database-backed funds provider for paper trading.

This module provides a FundsProvider implementation that directly
interacts with the user_funds table, usable by both backend and trading-engine.
"""

import logging
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.providers.broker.funds_provider import FundsProvider
from shared.providers.schemas import Funds

logger = logging.getLogger(__name__)

# Default initial balance for paper trading (can be overridden)
DEFAULT_INITIAL_BALANCE = Decimal("1000000")


class DatabaseFundsProvider(FundsProvider):
    """Database-backed funds provider.

    Directly interacts with the user_funds table to provide persistent
    funds management for paper trading.

    This provider is designed to work with any SQLAlchemy model class
    that has the user_funds table structure.
    """

    def __init__(
        self,
        db: AsyncSession,
        user_funds_model: Any,
        initial_balance: Decimal = DEFAULT_INITIAL_BALANCE,
    ):
        """Initialize with database session and model class.

        Args:
            db: SQLAlchemy async session
            user_funds_model: The UserFunds model class to use for queries
            initial_balance: Default balance for new users
        """
        self.db = db
        self.user_funds_model = user_funds_model
        self.initial_balance = initial_balance

    async def _get_or_create_funds(self, user_id: str) -> Any:
        """Get existing funds or create with initial balance."""
        result = await self.db.execute(
            select(self.user_funds_model).where(self.user_funds_model.user_id == user_id)
        )
        funds = result.scalar_one_or_none()

        if funds is None:
            funds = self.user_funds_model(
                id=str(uuid4()),
                user_id=user_id,
                cash_balance=self.initial_balance,
                margin_used=Decimal("0"),
                collateral=Decimal("0"),
            )
            self.db.add(funds)
            await self.db.flush()
            await self.db.refresh(funds)
            logger.info(
                f"Initialized funds for user {user_id[:8]}... with balance {self.initial_balance}"
            )

        return funds

    async def get_funds(self, user_id: str) -> Funds:
        """Get funds for a user from the database."""
        db_funds = await self._get_or_create_funds(user_id)
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
        """Update funds after a trade execution."""
        trade_value = quantity * price
        funds = await self._get_or_create_funds(user_id)

        if side.upper() == "BUY":
            total_cost = trade_value + fees
            if funds.available_cash < total_cost:
                raise ValueError(
                    f"Insufficient funds. Required: {total_cost}, Available: {funds.available_cash}"
                )
            funds.cash_balance -= total_cost
            logger.debug(
                f"BUY: Deducted {total_cost} from user {user_id[:8]}... "
                f"New balance: {funds.cash_balance}"
            )
        else:  # SELL
            net_proceeds = trade_value - fees
            funds.cash_balance += net_proceeds
            logger.debug(
                f"SELL: Added {net_proceeds} to user {user_id[:8]}... "
                f"New balance: {funds.cash_balance}"
            )

        await self.db.flush()
        await self.db.refresh(funds)

        return Funds(
            available_cash=funds.available_cash,
            used_margin=funds.margin_used,
            total_balance=funds.cash_balance + funds.margin_used,
            collateral=funds.collateral,
        )

    async def initialize_funds(
        self,
        user_id: str,
        initial_balance: Decimal,
    ) -> Funds:
        """Initialize funds for a new user with a specific balance."""
        # First check if funds already exist
        result = await self.db.execute(
            select(self.user_funds_model).where(self.user_funds_model.user_id == user_id)
        )
        funds = result.scalar_one_or_none()

        if funds is None:
            funds = self.user_funds_model(
                id=str(uuid4()),
                user_id=user_id,
                cash_balance=initial_balance,
                margin_used=Decimal("0"),
                collateral=Decimal("0"),
            )
            self.db.add(funds)
        else:
            # Reset existing funds
            funds.cash_balance = initial_balance
            funds.margin_used = Decimal("0")
            funds.collateral = Decimal("0")

        await self.db.flush()
        await self.db.refresh(funds)

        return Funds(
            available_cash=funds.available_cash,
            used_margin=funds.margin_used,
            total_balance=funds.cash_balance + funds.margin_used,
            collateral=funds.collateral,
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
        funds = await self._get_or_create_funds(user_id)
        return funds.available_cash >= required_amount
