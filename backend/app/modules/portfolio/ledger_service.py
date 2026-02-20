"""Service for managing transaction ledger entries."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheCategory, generate_cache_key, get_cached, set_cached
from app.modules.portfolio.models import TransactionLedger, TransactionType, UserFunds
from app.modules.portfolio.schemas import (
    BalanceHistoryEntry,
    BalanceHistoryResponse,
    LedgerEntryResponse,
    LedgerResponse,
    LedgerStatementResponse,
    LedgerStatementSummary,
)

logger = logging.getLogger(__name__)


class LedgerService:
    """Service class for transaction ledger operations.

    Records all cash flow transactions and provides statement generation.
    """

    def __init__(self, db: AsyncSession, redis: Redis | None = None):
        """Initialize with database session and optional Redis client."""
        self.db = db
        self.redis = redis

    async def record_transaction(
        self,
        user_id: str,
        transaction_type: TransactionType,
        amount: Decimal,
        description: str,
        transaction_date: datetime | None = None,
        portfolio_id: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        symbol: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> TransactionLedger:
        """Record a transaction in the ledger.

        Automatically calculates running balances based on current funds.

        Args:
            user_id: User identifier
            transaction_type: Type of transaction
            amount: Transaction amount (positive for credits, negative for debits)
            description: Human-readable description
            transaction_date: When the transaction occurred (defaults to now)
            portfolio_id: Optional portfolio identifier
            reference_type: Type of source entity (e.g., "trade", "order")
            reference_id: ID of the source entity
            symbol: Symbol for trade-related transactions
            extra_data: Additional context data

        Returns:
            Created TransactionLedger entry
        """
        if transaction_date is None:
            transaction_date = datetime.now()

        # Get current funds for running balance calculation
        funds = await self._get_user_funds(user_id)

        entry = TransactionLedger(
            user_id=user_id,
            portfolio_id=portfolio_id,
            transaction_type=transaction_type.value,
            amount=amount,
            running_cash_balance=funds.cash_balance if funds else Decimal("0"),
            running_margin_used=funds.margin_used if funds else Decimal("0"),
            running_total_balance=funds.total_balance if funds else Decimal("0"),
            reference_type=reference_type,
            reference_id=reference_id,
            symbol=symbol,
            description=description,
            extra_data=extra_data,
            transaction_date=transaction_date,
        )

        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)

        logger.info(
            f"Recorded {transaction_type.value} transaction for user {user_id}: "
            f"{amount} - {description}"
        )
        return entry

    async def get_ledger(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        transaction_types: list[TransactionType] | None = None,
        symbol: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        portfolio_id: str | None = None,
    ) -> LedgerResponse:
        """Get paginated ledger entries with filters.

        Args:
            user_id: User identifier
            page: Page number (1-indexed)
            page_size: Number of entries per page
            transaction_types: Optional filter by transaction types
            symbol: Optional filter by symbol
            start_date: Optional start date filter
            end_date: Optional end date filter
            portfolio_id: Optional portfolio filter

        Returns:
            LedgerResponse with paginated entries and totals
        """
        # Build base query
        conditions = [TransactionLedger.user_id == user_id]

        if transaction_types:
            type_values = [t.value for t in transaction_types]
            conditions.append(TransactionLedger.transaction_type.in_(type_values))
        if symbol:
            conditions.append(TransactionLedger.symbol == symbol)
        if start_date:
            conditions.append(TransactionLedger.transaction_date >= start_date)
        if end_date:
            conditions.append(TransactionLedger.transaction_date <= end_date)
        if portfolio_id:
            conditions.append(TransactionLedger.portfolio_id == portfolio_id)

        # Count total
        count_query = select(func.count(TransactionLedger.id)).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Calculate totals (credits and debits)
        totals_query = select(
            func.sum(case((TransactionLedger.amount > 0, TransactionLedger.amount), else_=0)).label(
                "total_in"
            ),
            func.sum(
                case((TransactionLedger.amount < 0, func.abs(TransactionLedger.amount)), else_=0)
            ).label("total_out"),
        ).where(and_(*conditions))
        totals_result = await self.db.execute(totals_query)
        totals = totals_result.one()

        # Get paginated entries
        offset = (page - 1) * page_size
        query = (
            select(TransactionLedger)
            .where(and_(*conditions))
            .order_by(TransactionLedger.transaction_date.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()

        return LedgerResponse(
            entries=[LedgerEntryResponse.model_validate(e) for e in entries],
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_in=totals.total_in or Decimal("0"),
            total_out=totals.total_out or Decimal("0"),
        )

    async def get_statement(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        transaction_types: list[TransactionType] | None = None,
        symbol: str | None = None,
        portfolio_id: str | None = None,
    ) -> LedgerStatementResponse:
        """Generate account statement for a date range.

        Args:
            user_id: User identifier
            start_date: Statement start date
            end_date: Statement end date
            transaction_types: Optional filter by types
            symbol: Optional filter by symbol
            portfolio_id: Optional portfolio filter

        Returns:
            LedgerStatementResponse with summary and entries
        """
        # Build conditions
        conditions = [
            TransactionLedger.user_id == user_id,
            TransactionLedger.transaction_date >= start_date,
            TransactionLedger.transaction_date <= end_date,
        ]

        if transaction_types:
            type_values = [t.value for t in transaction_types]
            conditions.append(TransactionLedger.transaction_type.in_(type_values))
        if symbol:
            conditions.append(TransactionLedger.symbol == symbol)
        if portfolio_id:
            conditions.append(TransactionLedger.portfolio_id == portfolio_id)

        # Get all entries in period
        query = (
            select(TransactionLedger)
            .where(and_(*conditions))
            .order_by(TransactionLedger.transaction_date.asc())
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()

        # Get opening balance (last entry before start_date)
        opening_query = (
            select(TransactionLedger)
            .where(
                and_(
                    TransactionLedger.user_id == user_id,
                    TransactionLedger.transaction_date < start_date,
                )
            )
            .order_by(TransactionLedger.transaction_date.desc())
            .limit(1)
        )
        opening_result = await self.db.execute(opening_query)
        opening_entry = opening_result.scalar_one_or_none()
        opening_balance = opening_entry.running_cash_balance if opening_entry else Decimal("0")

        # Calculate summaries
        closing_balance = entries[-1].running_cash_balance if entries else opening_balance

        # Sum by type
        type_sums: dict[str, Decimal] = {}
        for entry in entries:
            tx_type = entry.transaction_type
            if tx_type not in type_sums:
                type_sums[tx_type] = Decimal("0")
            type_sums[tx_type] += entry.amount

        summary = LedgerStatementSummary(
            period_start=start_date,
            period_end=end_date,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_deposits=type_sums.get(TransactionType.DEPOSIT.value, Decimal("0")),
            total_withdrawals=abs(type_sums.get(TransactionType.WITHDRAWAL.value, Decimal("0"))),
            total_buys=abs(type_sums.get(TransactionType.BUY.value, Decimal("0"))),
            total_sells=type_sums.get(TransactionType.SELL.value, Decimal("0")),
            total_fees=abs(type_sums.get(TransactionType.FEE.value, Decimal("0"))),
            total_dividends=type_sums.get(TransactionType.DIVIDEND.value, Decimal("0")),
            net_change=closing_balance - opening_balance,
        )

        return LedgerStatementResponse(
            summary=summary,
            entries=[LedgerEntryResponse.model_validate(e) for e in entries],
        )

    async def get_balance_history(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        portfolio_id: str | None = None,
    ) -> BalanceHistoryResponse:
        """Get balance history over time for charts.

        Returns daily closing balances for the date range.

        Args:
            user_id: User identifier
            start_date: History start date
            end_date: History end date
            portfolio_id: Optional portfolio filter

        Returns:
            BalanceHistoryResponse with daily balance points
        """
        # Try cache first - historical data is immutable, good candidate for caching
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        cache_key = generate_cache_key(
            "ledger:balance_history",
            user_id,
            start=start_str,
            end=end_str,
            portfolio=portfolio_id,
        )
        if self.redis:
            cached = await get_cached(self.redis, cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                # Reconstruct response from cached data
                return BalanceHistoryResponse(
                    entries=[
                        BalanceHistoryEntry(
                            date=datetime.fromisoformat(e["date"]),
                            cash_balance=Decimal(str(e["cash_balance"])),
                            margin_used=Decimal(str(e["margin_used"])),
                            total_balance=Decimal(str(e["total_balance"])),
                        )
                        for e in cached["entries"]
                    ],
                    start_date=datetime.fromisoformat(cached["start_date"]),
                    end_date=datetime.fromisoformat(cached["end_date"]),
                )

        conditions = [
            TransactionLedger.user_id == user_id,
            TransactionLedger.transaction_date >= start_date,
            TransactionLedger.transaction_date <= end_date,
        ]

        if portfolio_id:
            conditions.append(TransactionLedger.portfolio_id == portfolio_id)

        # Get all transactions in period ordered by date
        query = (
            select(TransactionLedger)
            .where(and_(*conditions))
            .order_by(TransactionLedger.transaction_date.asc())
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()

        # Group by date and take the last entry of each day
        daily_balances: dict[str, TransactionLedger] = {}
        for entry in entries:
            date_key = entry.transaction_date.strftime("%Y-%m-%d")
            daily_balances[date_key] = entry  # Last entry for each date wins

        history_entries = [
            BalanceHistoryEntry(
                date=entry.transaction_date,
                cash_balance=entry.running_cash_balance,
                margin_used=entry.running_margin_used,
                total_balance=entry.running_total_balance,
            )
            for entry in daily_balances.values()
        ]

        response = BalanceHistoryResponse(
            entries=history_entries,
            start_date=start_date,
            end_date=end_date,
        )

        # Cache the result
        if self.redis:
            cache_data = {
                "entries": [
                    {
                        "date": e.date.isoformat(),
                        "cash_balance": str(e.cash_balance),
                        "margin_used": str(e.margin_used),
                        "total_balance": str(e.total_balance),
                    }
                    for e in history_entries
                ],
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
            await set_cached(self.redis, cache_key, cache_data, CacheCategory.DB_AGGREGATION)

        return response

    async def _get_user_funds(self, user_id: str) -> UserFunds | None:
        """Get user funds for running balance calculation."""
        result = await self.db.execute(select(UserFunds).where(UserFunds.user_id == user_id))
        return result.scalar_one_or_none()
