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
            total_balance=db_funds.cash_balance
            + db_funds.collateral,  # Fixed: was incorrectly adding margin_used
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
            total_balance=funds.cash_balance
            + funds.collateral,  # Fixed: was incorrectly adding margin_used
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
                margin_to_release = min(funds.margin_used, margin_base_value * margin_percent)
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
                logger.info(
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
            logger.info(
                f"MARGIN BUY: Blocked margin ₹{margin_required:.2f} "
                f"for user {user_id[:8]}... Available: ₹{funds.available_cash:.2f}"
            )

        elif product_type == ProductType.SLB:
            # SLB: Similar to INTRADAY but allows multi-day shorting
            # Check if this is closing a short position
            is_closing_short = existing_position_qty is not None and existing_position_qty < 0

            if is_closing_short:
                # Closing short position - release margin and calculate P&L
                margin_base_price = (
                    entry_price if entry_price else trade_value / abs(existing_position_qty)
                )
                margin_base_value = abs(existing_position_qty) * margin_base_price

                if entry_price:
                    short_pnl = (entry_price - (trade_value / abs(existing_position_qty))) * abs(
                        existing_position_qty
                    )
                    funds.cash_balance += short_pnl - fees
                    funds.realized_pnl += short_pnl - fees
                    logger.debug(f"SLB BUY (close short): P&L ₹{short_pnl:.2f} - fees ₹{fees:.2f}")
                else:
                    funds.cash_balance -= total_cost
                    logger.warning("SLB BUY (close short): No entry price provided")

                margin_to_release = min(funds.margin_used, margin_base_value * margin_percent)
                if margin_to_release > 0:
                    funds.margin_used -= margin_to_release
            else:
                # Opening long position - block margin
                margin_required = trade_value * margin_percent + fees
                if funds.available_cash < margin_required:
                    raise ValueError(
                        f"Insufficient margin for SLB buy. "
                        f"Required: ₹{margin_required:.2f}, Available: ₹{funds.available_cash:.2f}"
                    )
                funds.margin_used += margin_required
                logger.info(f"SLB BUY: Blocked margin ₹{margin_required:.2f}")

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

            # Calculate and track P&L if entry_price provided
            if entry_price:
                original_value = quantity * entry_price
                pnl = trade_value - original_value - fees
                funds.realized_pnl += pnl
                logger.debug(
                    f"DELIVERY SELL: Credited ₹{net_proceeds:.2f}, P&L ₹{pnl:.2f} "
                    f"for user {user_id[:8]}... New balance: ₹{funds.cash_balance:.2f}"
                )
            else:
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
                # Also update realized_pnl to keep them in sync
                funds.cash_balance += pnl
                funds.realized_pnl += pnl

                logger.info(
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
            # Also update realized_pnl to keep them in sync
            funds.cash_balance += pnl
            funds.realized_pnl += pnl

            logger.info(
                f"MARGIN SELL: P&L ₹{pnl:.2f}, "
                f"released margin ₹{margin_to_release:.2f} for user {user_id[:8]}..."
            )

        elif product_type == ProductType.SLB:
            # SLB SELL: Check if closing long or opening short
            is_closing_long = existing_position_qty is not None and existing_position_qty > 0

            if is_closing_long:
                # Closing long position - release margin and credit P&L
                if entry_price:
                    original_value = quantity * entry_price
                    margin_to_release = min(funds.margin_used, original_value * margin_percent)
                    pnl = trade_value - original_value - fees
                else:
                    margin_to_release = min(funds.margin_used, trade_value * margin_percent)
                    pnl = -fees
                    logger.warning("SLB SELL (close): No entry price provided")

                if margin_to_release > 0:
                    funds.margin_used -= margin_to_release

                funds.cash_balance += pnl
                funds.realized_pnl += pnl

                logger.info(
                    f"SLB SELL (close): P&L ₹{pnl:.2f}, released margin ₹{margin_to_release:.2f}"
                )
            else:
                # Opening short position via SLB - block margin
                margin_required = trade_value * margin_percent + fees
                if funds.available_cash < margin_required:
                    raise ValueError(
                        f"Insufficient margin for SLB short sell. "
                        f"Required: ₹{margin_required:.2f}, Available: ₹{funds.available_cash:.2f}"
                    )
                funds.margin_used += margin_required
                logger.debug(f"SLB SHORT: Blocked margin ₹{margin_required:.2f}")

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
            total_balance=funds.cash_balance + funds.collateral,
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

    async def recalculate_funds(self, user_id: str) -> Funds:
        """Recalculate funds by deriving values from positions.

        This is the CORRECT way to update funds - derive everything from
        the single source of truth (positions), rather than incremental updates.

        Calculates:
        - margin_used: SUM of margin for OPEN + PARTIAL positions
        - realized_pnl: SUM of realized_pnl from CLOSED + PARTIAL positions
        - cash_balance: starting_balance + realized_pnl

        Args:
            user_id: User identifier

        Returns:
            Updated Funds object
        """
        from sqlalchemy import text

        db_funds = await self._get_or_create_funds(user_id)

        # Calculate margin_used from OPEN and PARTIAL positions
        # margin = entry_price * remaining_quantity * margin_percent
        # Margin percentages:
        # - DELIVERY (CNC): 100% - full payment required
        # - INTRADAY (MIS): 20% - day trading margin
        # - MARGIN (MTF): 50% - leveraged buying
        # - SLB: 30% - short selling with stock borrowing
        margin_result = await self.db.execute(
            text("""
                SELECT COALESCE(SUM(
                    entry_price * remaining_quantity *
                    CASE COALESCE(product_type::text, 'INTRADAY')
                        WHEN 'DELIVERY' THEN 1.0
                        WHEN 'CNC' THEN 1.0
                        WHEN 'INTRADAY' THEN 0.20
                        WHEN 'MIS' THEN 0.20
                        WHEN 'MARGIN' THEN 0.50
                        WHEN 'MTF' THEN 0.50
                        WHEN 'SLB' THEN 0.30
                        ELSE 0.20
                    END
                ), 0) as margin_used
                FROM algo_positions
                WHERE user_id = :user_id AND status IN ('OPEN', 'PARTIAL')
            """),
            {"user_id": user_id},
        )
        new_margin_used = Decimal(str(margin_result.scalar() or 0))

        # Calculate realized_pnl from CLOSED and PARTIAL positions
        pnl_result = await self.db.execute(
            text("""
                SELECT COALESCE(SUM(realized_pnl), 0) as total_pnl
                FROM algo_positions
                WHERE user_id = :user_id AND status IN ('CLOSED', 'PARTIAL')
            """),
            {"user_id": user_id},
        )
        new_realized_pnl = Decimal(str(pnl_result.scalar() or 0))

        # Get starting_balance (default to 100000 if not set)
        starting_balance = db_funds.starting_balance or Decimal("100000")

        # Calculate cash_balance from starting_balance + realized_pnl
        new_cash_balance = starting_balance + new_realized_pnl

        # Only update if values changed
        old_margin = db_funds.margin_used or Decimal("0")
        old_pnl = db_funds.realized_pnl or Decimal("0")
        old_cash = db_funds.cash_balance or starting_balance

        margin_changed = abs(new_margin_used - old_margin) > Decimal("0.01")
        pnl_changed = abs(new_realized_pnl - old_pnl) > Decimal("0.01")
        cash_changed = abs(new_cash_balance - old_cash) > Decimal("0.01")

        if margin_changed or pnl_changed or cash_changed:
            db_funds.margin_used = new_margin_used
            db_funds.realized_pnl = new_realized_pnl
            db_funds.cash_balance = new_cash_balance
            await self.db.flush()

            logger.info(
                f"Recalculated funds for user {user_id[:8]}: "
                f"margin={new_margin_used:.2f}, pnl={new_realized_pnl:.2f}, "
                f"cash={new_cash_balance:.2f}"
            )

        return Funds(
            available_cash=new_cash_balance - new_margin_used,
            used_margin=new_margin_used,
            total_balance=new_cash_balance,
            collateral=db_funds.collateral or Decimal("0"),
            realized_pnl=new_realized_pnl,
            unrealized_pnl=db_funds.unrealized_pnl or Decimal("0"),
        )
