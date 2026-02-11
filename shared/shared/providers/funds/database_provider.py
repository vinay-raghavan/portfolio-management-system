"""Database-backed funds provider for paper trading.

This module provides a FundsProvider implementation that directly
interacts with the user_funds table, usable by both backend and trading-engine.

Supports CNC (Delivery), MIS (Intraday), and MTF (Margin) product types with
proper margin blocking and position validation.
"""

import logging
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.providers.broker.funds_provider import FundsProvider
from shared.providers.schemas import Funds, ProductType

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
        position_model: Any | None = None,
        algo_position_model: Any | None = None,
    ):
        """Initialize with database session and model class.

        Args:
            db: SQLAlchemy async session
            user_funds_model: The UserFunds model class to use for queries
            initial_balance: Default balance for new users
            position_model: Optional Position model for querying portfolio positions
            algo_position_model: Optional AlgoPosition model for querying algo positions
        """
        self.db = db
        self.user_funds_model = user_funds_model
        self.initial_balance = initial_balance
        self.position_model = position_model
        self.algo_position_model = algo_position_model

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
                realized_pnl=Decimal("0"),
                unrealized_pnl=Decimal("0"),
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
            realized_pnl=db_funds.realized_pnl,
            unrealized_pnl=db_funds.unrealized_pnl,
        )

    async def update_funds_for_trade(
        self,
        user_id: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal,
        product_type: ProductType = ProductType.DELIVERY,
        existing_position_qty: Decimal | None = None,
        entry_price: Decimal | None = None,
    ) -> Funds:
        """Update funds after a trade execution with product type rules.

        Product type rules:
        - DELIVERY (CNC): Full payment for BUY, must own shares to SELL
        - INTRADAY (MIS): Block margin (25%) for both BUY and SELL
        - MARGIN (MTF): Block margin (50%) for BUY only, no shorting

        Args:
            user_id: User identifier
            side: Trade side ("BUY" or "SELL")
            quantity: Trade quantity
            price: Execution price
            fees: Trading fees
            product_type: Product type (DELIVERY, INTRADAY, MARGIN)
            existing_position_qty: Current position quantity (for SELL validation)
            entry_price: Original entry price (for correct margin release calculation)
        """
        trade_value = quantity * price
        funds = await self._get_or_create_funds(user_id)
        normalized_type = ProductType.normalize(product_type)
        margin_percent = Decimal(str(ProductType.get_margin_percent(product_type)))

        if side.upper() == "BUY":
            await self._handle_buy(
                funds,
                user_id,
                trade_value,
                fees,
                normalized_type,
                margin_percent,
                existing_position_qty,
                entry_price,
            )
        else:  # SELL
            await self._handle_sell(
                funds,
                user_id,
                trade_value,
                fees,
                quantity,
                normalized_type,
                margin_percent,
                existing_position_qty,
                entry_price,
            )

        await self.db.flush()
        await self.db.refresh(funds)

        return Funds(
            available_cash=funds.available_cash,
            used_margin=funds.margin_used,
            total_balance=funds.cash_balance + funds.margin_used,
            collateral=funds.collateral,
        )

    async def _handle_buy(
        self,
        funds: Any,
        user_id: str,
        trade_value: Decimal,
        fees: Decimal,
        product_type: ProductType,
        margin_percent: Decimal,
        existing_position_qty: Decimal | None,
        entry_price: Decimal | None = None,
    ) -> None:
        """Handle BUY order funds update based on product type.

        Args:
            funds: User funds database record
            user_id: User identifier
            trade_value: quantity * price
            fees: Trading fees
            product_type: DELIVERY, INTRADAY, or MARGIN
            margin_percent: Margin percentage for this product type
            existing_position_qty: Current position qty (negative = short)
            entry_price: Original entry price (for margin release on close)
        """
        total_cost = trade_value + fees

        if product_type == ProductType.DELIVERY:
            # DELIVERY: Full payment required
            if funds.available_cash < total_cost:
                raise ValueError(
                    f"Insufficient funds for DELIVERY buy. "
                    f"Required: ₹{total_cost:.2f}, Available: ₹{funds.available_cash:.2f}"
                )
            funds.cash_balance -= total_cost
            logger.debug(
                f"DELIVERY BUY: Deducted ₹{total_cost:.2f} from user {user_id[:8]}... "
                f"New balance: ₹{funds.cash_balance:.2f}"
            )

        elif product_type == ProductType.INTRADAY:
            # Check if this is closing a short position
            is_closing_short = existing_position_qty is not None and existing_position_qty < 0

            if is_closing_short:
                # Closing short position - calculate P&L and release margin
                # P&L = (short_entry_price - buy_back_price) * qty
                # Use entry_price if provided, otherwise use trade price (less accurate)
                margin_base_price = (
                    entry_price if entry_price else trade_value / abs(existing_position_qty)
                )
                margin_base_value = abs(existing_position_qty) * margin_base_price

                # Calculate P&L: positive if bought back cheaper (profit on short)
                if entry_price:
                    short_pnl = (entry_price - (trade_value / abs(existing_position_qty))) * abs(
                        existing_position_qty
                    )
                    funds.cash_balance += short_pnl - fees
                    logger.debug(
                        f"INTRADAY BUY (close short): P&L ₹{short_pnl:.2f} - fees ₹{fees:.2f} "
                        f"for user {user_id[:8]}..."
                    )
                else:
                    # Fallback: just deduct cost (less accurate, shouldn't happen)
                    funds.cash_balance -= total_cost
                    logger.warning(
                        f"INTRADAY BUY (close short): No entry price provided, "
                        f"deducting cost ₹{total_cost:.2f} for user {user_id[:8]}..."
                    )

                # Release the margin that was blocked for the short (use entry price)
                margin_to_release = min(
                    funds.margin_used, margin_base_value * margin_percent
                )
                if margin_to_release > 0:
                    funds.margin_used -= margin_to_release
                logger.debug(
                    f"INTRADAY BUY (close short): Released margin ₹{margin_to_release:.2f} "
                    f"for user {user_id[:8]}..."
                )
            else:
                # Opening long position - block margin
                # Only add to margin_used, don't deduct from cash_balance
                # (available_cash = cash_balance - margin_used handles the reduction)
                margin_required = trade_value * margin_percent + fees
                if funds.available_cash < margin_required:
                    raise ValueError(
                        f"Insufficient margin for INTRADAY buy. "
                        f"Required: ₹{margin_required:.2f} ({margin_percent * 100:.0f}% margin), "
                        f"Available: ₹{funds.available_cash:.2f}"
                    )
                funds.margin_used += margin_required
                logger.debug(
                    f"INTRADAY BUY: Blocked margin ₹{margin_required:.2f} "
                    f"for user {user_id[:8]}... Available: ₹{funds.available_cash:.2f}"
                )

        elif product_type == ProductType.MARGIN:
            # MARGIN: Block margin instead of full payment
            # Only add to margin_used, don't deduct from cash_balance
            # (available_cash = cash_balance - margin_used handles the reduction)
            margin_required = trade_value * margin_percent + fees
            if funds.available_cash < margin_required:
                raise ValueError(
                    f"Insufficient margin for MARGIN buy. "
                    f"Required: ₹{margin_required:.2f} ({margin_percent * 100:.0f}% margin), "
                    f"Available: ₹{funds.available_cash:.2f}"
                )
            funds.margin_used += margin_required
            logger.debug(
                f"MARGIN BUY: Blocked margin ₹{margin_required:.2f} "
                f"for user {user_id[:8]}... Available: ₹{funds.available_cash:.2f}"
            )

    async def _handle_sell(
        self,
        funds: Any,
        user_id: str,
        trade_value: Decimal,
        fees: Decimal,
        quantity: Decimal,
        product_type: ProductType,
        margin_percent: Decimal,
        existing_position_qty: Decimal | None,
        entry_price: Decimal | None = None,
    ) -> None:
        """Handle SELL order funds update based on product type.

        Args:
            funds: User funds database record
            user_id: User identifier
            trade_value: quantity * price
            fees: Trading fees
            quantity: Trade quantity
            product_type: DELIVERY, INTRADAY, or MARGIN
            margin_percent: Margin percentage for this product type
            existing_position_qty: Current position qty (positive = long)
            entry_price: Original entry price (for margin release on close)
        """

        if product_type == ProductType.DELIVERY:
            # DELIVERY: Must own shares to sell (no shorting)
            if existing_position_qty is None or existing_position_qty < quantity:
                owned = existing_position_qty or Decimal("0")
                raise ValueError(
                    f"Cannot short sell in DELIVERY mode. "
                    f"Trying to sell {quantity} shares but only own {owned}."
                )
            # Credit proceeds to cash
            net_proceeds = trade_value - fees
            funds.cash_balance += net_proceeds
            logger.debug(
                f"DELIVERY SELL: Credited ₹{net_proceeds:.2f} to user {user_id[:8]}... "
                f"New balance: ₹{funds.cash_balance:.2f}"
            )

        elif product_type == ProductType.INTRADAY:
            # INTRADAY: Short selling allowed with margin
            # Check if this is closing an existing position or opening a short
            is_closing = existing_position_qty is not None and existing_position_qty > 0

            if is_closing:
                # Closing long position - release margin and credit P&L only
                # For INTRADAY: we only blocked margin when opening, so we only release margin
                # and credit/debit the P&L (not the full proceeds)

                # Release the margin that was blocked - use entry price if available
                if entry_price:
                    original_value = quantity * entry_price
                    margin_to_release = min(funds.margin_used, original_value * margin_percent)
                    # P&L = (exit_price - entry_price) * quantity
                    pnl = trade_value - original_value - fees
                else:
                    # Fallback: use current trade value (less accurate, assume no P&L)
                    margin_to_release = min(funds.margin_used, trade_value * margin_percent)
                    pnl = -fees  # Only fees as loss if no entry price
                    logger.warning(
                        f"INTRADAY SELL (close): No entry price provided for user {user_id[:8]}..., "
                        f"cannot calculate accurate P&L"
                    )

                if margin_to_release > 0:
                    funds.margin_used -= margin_to_release

                # Credit/debit only the P&L to cash balance (not full proceeds)
                funds.cash_balance += pnl

                logger.debug(
                    f"INTRADAY SELL (close): P&L ₹{pnl:.2f}, "
                    f"released margin ₹{margin_to_release:.2f} for user {user_id[:8]}..."
                )
            else:
                # Opening short position - block margin ONLY
                # DO NOT credit proceeds - we haven't received money yet, just borrowed shares
                # Proceeds will be realized when the short is closed (BUY to cover)
                margin_required = trade_value * margin_percent + fees
                if funds.available_cash < margin_required:
                    raise ValueError(
                        f"Insufficient margin for INTRADAY short sell. "
                        f"Required: ₹{margin_required:.2f} ({margin_percent * 100:.0f}% margin), "
                        f"Available: ₹{funds.available_cash:.2f}"
                    )
                funds.margin_used += margin_required
                logger.debug(
                    f"INTRADAY SHORT: Blocked margin ₹{margin_required:.2f} "
                    f"for user {user_id[:8]}... (no proceeds credited until close)"
                )

        elif product_type == ProductType.MARGIN:
            # MARGIN (MTF): No short selling allowed
            if existing_position_qty is None or existing_position_qty < quantity:
                owned = existing_position_qty or Decimal("0")
                raise ValueError(
                    f"Cannot short sell in MARGIN (MTF) mode. "
                    f"Trying to sell {quantity} shares but only own {owned}."
                )
            # Closing leveraged position - release margin and credit P&L only
            # For MTF: we only blocked margin when opening, so we only release margin
            # and credit/debit the P&L (not the full proceeds)

            # Release the margin that was blocked - use entry price if available
            if entry_price:
                original_value = quantity * entry_price
                margin_to_release = min(funds.margin_used, original_value * margin_percent)
                # P&L = (exit_price - entry_price) * quantity
                pnl = trade_value - original_value - fees
            else:
                # Fallback: use current trade value (less accurate, assume no P&L)
                margin_to_release = min(funds.margin_used, trade_value * margin_percent)
                pnl = -fees  # Only fees as loss if no entry price
                logger.warning(
                    f"MARGIN SELL: No entry price provided for user {user_id[:8]}..., "
                    f"cannot calculate accurate P&L"
                )

            if margin_to_release > 0:
                funds.margin_used -= margin_to_release

            # Credit/debit only the P&L to cash balance (not full proceeds)
            funds.cash_balance += pnl

            logger.debug(
                f"MARGIN SELL: P&L ₹{pnl:.2f}, "
                f"released margin ₹{margin_to_release:.2f} for user {user_id[:8]}..."
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

    async def get_position_quantity(
        self,
        user_id: str,
        symbol: str,
    ) -> Decimal:
        """Get existing position quantity for a user and symbol.

        Checks both portfolio positions and algo positions tables.

        Args:
            user_id: User identifier
            symbol: Stock symbol

        Returns:
            Current position quantity (positive for long, negative for short, 0 if no position)
        """
        symbol = symbol.upper()
        total_qty = Decimal("0")

        # Check portfolio positions table
        if self.position_model is not None:
            result = await self.db.execute(
                select(self.position_model).where(
                    self.position_model.user_id == user_id,
                    self.position_model.symbol == symbol,
                )
            )
            position = result.scalar_one_or_none()
            if position and hasattr(position, "quantity"):
                total_qty += Decimal(str(position.quantity))

        # Check algo positions table (only OPEN/PARTIAL positions)
        if self.algo_position_model is not None:
            # Sum remaining_quantity for all open algo positions for this symbol
            # Note: For LONG positions, quantity is positive; for SHORT, we negate
            result = await self.db.execute(
                select(self.algo_position_model).where(
                    self.algo_position_model.user_id == user_id,
                    self.algo_position_model.symbol == symbol,
                    self.algo_position_model.status.in_(["OPEN", "PARTIAL"]),
                )
            )
            algo_positions = result.scalars().all()
            for pos in algo_positions:
                qty = Decimal(str(pos.remaining_quantity))
                # Check if it's a SHORT position (negate quantity)
                if hasattr(pos, "side") and str(pos.side).upper() == "SHORT":
                    qty = -qty
                total_qty += qty

        return total_qty

    async def update_realized_pnl(
        self,
        user_id: str,
        pnl_amount: Decimal,
    ) -> None:
        """Update cumulative realized P&L for a user.

        This accumulates the P&L amount to the existing realized_pnl.
        """
        db_funds = await self._get_or_create_funds(user_id)
        db_funds.realized_pnl = db_funds.realized_pnl + pnl_amount
        await self.db.flush()
        logger.info(
            f"Updated realized P&L for user {user_id[:8]}...: "
            f"+₹{pnl_amount:.2f} (total: ₹{db_funds.realized_pnl:.2f})"
        )

    async def update_unrealized_pnl(
        self,
        user_id: str,
        unrealized_pnl: Decimal,
    ) -> None:
        """Update current unrealized P&L for a user.

        This replaces the previous unrealized_pnl value.
        """
        db_funds = await self._get_or_create_funds(user_id)
        db_funds.unrealized_pnl = unrealized_pnl
        await self.db.flush()
        logger.info(f"Updated unrealized P&L for user {user_id[:8]}...: ₹{unrealized_pnl:.2f}")
