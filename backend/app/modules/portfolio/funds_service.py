"""Service for managing user funds and balances."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.portfolio.models import TransactionType, UserFunds
from app.modules.portfolio.schemas import FundsSummary

if TYPE_CHECKING:
    from app.modules.portfolio.ledger_service import LedgerService

logger = logging.getLogger(__name__)


class FundsService:
    """Service class for user funds operations.

    Handles fund initialization, balance updates, and queries.
    """

    def __init__(self, db: AsyncSession, ledger_service: LedgerService | None = None):
        """Initialize with database session.

        Args:
            db: Database session
            ledger_service: Optional ledger service for transaction recording
        """
        self.db = db
        self._ledger_service = ledger_service

    @property
    def ledger_service(self) -> LedgerService | None:
        """Get ledger service, creating lazily if needed."""
        return self._ledger_service

    def set_ledger_service(self, ledger_service: LedgerService) -> None:
        """Set the ledger service for transaction recording."""
        self._ledger_service = ledger_service

    async def get_funds(self, user_id: str) -> UserFunds | None:
        """Get funds for a user.

        Args:
            user_id: User identifier

        Returns:
            UserFunds model or None if not found
        """
        result = await self.db.execute(select(UserFunds).where(UserFunds.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create_funds(self, user_id: str) -> UserFunds:
        """Get existing funds or create with initial balance.

        Args:
            user_id: User identifier

        Returns:
            UserFunds model (existing or newly created)
        """
        funds = await self.get_funds(user_id)
        if funds is None:
            funds = await self.initialize_funds(user_id)
        return funds

    async def initialize_funds(
        self, user_id: str, initial_balance: Decimal | None = None
    ) -> UserFunds:
        """Initialize funds for a new user.

        Args:
            user_id: User identifier
            initial_balance: Optional custom initial balance.
                           Uses PAPER_TRADING_INITIAL_BALANCE from config if not provided.

        Returns:
            Newly created UserFunds model
        """
        if initial_balance is None:
            initial_balance = Decimal(str(settings.PAPER_TRADING_INITIAL_BALANCE))

        funds = UserFunds(
            user_id=user_id,
            cash_balance=initial_balance,
            margin_used=Decimal("0"),
            collateral=Decimal("0"),
        )
        self.db.add(funds)
        await self.db.flush()
        await self.db.refresh(funds)

        logger.info(f"Initialized funds for user {user_id} with balance {initial_balance}")
        return funds

    async def add_cash(self, user_id: str, amount: Decimal, reason: str = "deposit") -> UserFunds:
        """Add cash to user's balance (deposit).

        Args:
            user_id: User identifier
            amount: Amount to add (must be positive)
            reason: Reason for the deposit

        Returns:
            Updated UserFunds model

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Amount must be positive for deposits")

        funds = await self.get_or_create_funds(user_id)
        funds.cash_balance += amount

        await self.db.flush()
        await self.db.refresh(funds)

        # Record in ledger if service is available
        if self._ledger_service:
            await self._ledger_service.record_transaction(
                user_id=user_id,
                transaction_type=TransactionType.DEPOSIT,
                amount=amount,  # Positive for credit
                description=f"Cash deposit: {reason}",
                transaction_date=datetime.now(),
            )

        logger.info(f"Added {amount} to user {user_id} funds. Reason: {reason}")
        return funds

    async def deduct_cash(
        self, user_id: str, amount: Decimal, reason: str = "withdrawal"
    ) -> UserFunds:
        """Deduct cash from user's balance (withdrawal or purchase).

        Args:
            user_id: User identifier
            amount: Amount to deduct (must be positive)
            reason: Reason for the deduction

        Returns:
            Updated UserFunds model

        Raises:
            ValueError: If amount is not positive or insufficient balance
        """
        if amount <= 0:
            raise ValueError("Amount must be positive for deductions")

        funds = await self.get_or_create_funds(user_id)

        if funds.available_cash < amount:
            raise ValueError(
                f"Insufficient funds. Available: {funds.available_cash}, Required: {amount}"
            )

        funds.cash_balance -= amount

        await self.db.flush()
        await self.db.refresh(funds)

        # Record in ledger if service is available
        if self._ledger_service:
            await self._ledger_service.record_transaction(
                user_id=user_id,
                transaction_type=TransactionType.WITHDRAWAL,
                amount=-amount,  # Negative for debit
                description=f"Cash withdrawal: {reason}",
                transaction_date=datetime.now(),
            )

        logger.info(f"Deducted {amount} from user {user_id} funds. Reason: {reason}")
        return funds

    async def block_margin(self, user_id: str, amount: Decimal) -> UserFunds:
        """Block margin for an order/position.

        Args:
            user_id: User identifier
            amount: Amount to block

        Returns:
            Updated UserFunds model

        Raises:
            ValueError: If insufficient margin available
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        funds = await self.get_or_create_funds(user_id)

        if funds.available_margin < amount:
            raise ValueError(
                f"Insufficient margin. Available: {funds.available_margin}, Required: {amount}"
            )

        funds.margin_used += amount

        await self.db.flush()
        await self.db.refresh(funds)

        logger.debug(f"Blocked margin {amount} for user {user_id}")
        return funds

    async def release_margin(self, user_id: str, amount: Decimal) -> UserFunds:
        """Release blocked margin.

        Args:
            user_id: User identifier
            amount: Amount to release

        Returns:
            Updated UserFunds model
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        funds = await self.get_or_create_funds(user_id)

        # Don't release more than what's blocked
        release_amount = min(amount, funds.margin_used)
        funds.margin_used -= release_amount

        await self.db.flush()
        await self.db.refresh(funds)

        logger.debug(f"Released margin {release_amount} for user {user_id}")
        return funds

    async def process_trade_settlement(
        self,
        user_id: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal = Decimal("0"),
        symbol: str | None = None,
        trade_id: str | None = None,
    ) -> UserFunds:
        """Process funds settlement after a trade execution.

        For BUY: Deduct (quantity * price + fees) from cash
        For SELL: Add (quantity * price - fees) to cash

        Args:
            user_id: User identifier
            side: Trade side ("BUY" or "SELL")
            quantity: Trade quantity
            price: Execution price
            fees: Trading fees
            symbol: Symbol being traded (for ledger)
            trade_id: Trade ID for reference (for ledger)

        Returns:
            Updated UserFunds model
        """
        trade_value = quantity * price

        funds = await self.get_or_create_funds(user_id)

        if side.upper() == "BUY":
            total_cost = trade_value + fees
            if funds.available_cash < total_cost:
                raise ValueError(
                    f"Insufficient funds for trade. "
                    f"Required: {total_cost}, Available: {funds.available_cash}"
                )
            funds.cash_balance -= total_cost
            logger.info(f"BUY settlement: Deducted {total_cost} from user {user_id}")
        else:  # SELL
            net_proceeds = trade_value - fees
            funds.cash_balance += net_proceeds
            logger.info(f"SELL settlement: Added {net_proceeds} to user {user_id}")

        await self.db.flush()
        await self.db.refresh(funds)

        # Record in ledger if service is available
        if self._ledger_service:
            now = datetime.now()
            tx_type = TransactionType.BUY if side.upper() == "BUY" else TransactionType.SELL

            if side.upper() == "BUY":
                # Record BUY (debit) and FEE separately for clarity
                await self._ledger_service.record_transaction(
                    user_id=user_id,
                    transaction_type=tx_type,
                    amount=-trade_value,  # Negative for debit
                    description=f"Buy {quantity} {symbol or 'shares'} @ {price}",
                    transaction_date=now,
                    reference_type="trade",
                    reference_id=trade_id,
                    symbol=symbol,
                    metadata={"quantity": str(quantity), "price": str(price)},
                )
                if fees > 0:
                    await self._ledger_service.record_transaction(
                        user_id=user_id,
                        transaction_type=TransactionType.FEE,
                        amount=-fees,  # Negative for debit
                        description=f"Trading fees for {symbol or 'trade'}",
                        transaction_date=now,
                        reference_type="trade",
                        reference_id=trade_id,
                        symbol=symbol,
                    )
            else:  # SELL
                await self._ledger_service.record_transaction(
                    user_id=user_id,
                    transaction_type=tx_type,
                    amount=trade_value,  # Positive for credit
                    description=f"Sell {quantity} {symbol or 'shares'} @ {price}",
                    transaction_date=now,
                    reference_type="trade",
                    reference_id=trade_id,
                    symbol=symbol,
                    metadata={"quantity": str(quantity), "price": str(price)},
                )
                if fees > 0:
                    await self._ledger_service.record_transaction(
                        user_id=user_id,
                        transaction_type=TransactionType.FEE,
                        amount=-fees,  # Negative for debit
                        description=f"Trading fees for {symbol or 'trade'}",
                        transaction_date=now,
                        reference_type="trade",
                        reference_id=trade_id,
                        symbol=symbol,
                    )

        return funds

    async def get_funds_summary(self, user_id: str) -> FundsSummary:
        """Get funds summary for portfolio view.

        Args:
            user_id: User identifier

        Returns:
            FundsSummary schema
        """
        funds = await self.get_or_create_funds(user_id)

        return FundsSummary(
            cash_balance=funds.cash_balance,
            margin_used=funds.margin_used,
            available_margin=funds.available_margin,
            collateral=funds.collateral,
        )

    async def check_buying_power(self, user_id: str, required_amount: Decimal) -> bool:
        """Check if user has sufficient buying power.

        Args:
            user_id: User identifier
            required_amount: Amount needed for the transaction

        Returns:
            True if user has sufficient funds
        """
        funds = await self.get_or_create_funds(user_id)
        return funds.available_cash >= required_amount

    async def reset_funds(self, user_id: str, new_balance: Decimal | None = None) -> UserFunds:
        """Reset user funds (for paper trading reset).

        Args:
            user_id: User identifier
            new_balance: New balance. Uses initial balance from config if not provided.

        Returns:
            Reset UserFunds model
        """
        if new_balance is None:
            new_balance = Decimal(str(settings.PAPER_TRADING_INITIAL_BALANCE))

        funds = await self.get_or_create_funds(user_id)
        funds.cash_balance = new_balance
        funds.margin_used = Decimal("0")
        funds.collateral = Decimal("0")

        await self.db.flush()
        await self.db.refresh(funds)

        logger.info(f"Reset funds for user {user_id} to {new_balance}")
        return funds
