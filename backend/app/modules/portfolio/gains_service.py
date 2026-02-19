"""Service for tracking and reporting capital gains."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portfolio.models import RealizedGain, TaxType


def get_financial_year(date: datetime) -> str:
    """Get financial year string for a date (India: Apr 1 - Mar 31).

    Args:
        date: The date to get FY for

    Returns:
        Financial year in format "YYYY-YY" (e.g., "2024-25")
    """
    year = date.year
    month = date.month

    # In India, FY runs from April 1 to March 31
    # If month is Jan-Mar, we're in the ending year of the FY
    start_year = year - 1 if month < 4 else year

    end_year_short = str(start_year + 1)[-2:]
    return f"{start_year}-{end_year_short}"


def determine_tax_type(purchase_date: datetime, sale_date: datetime) -> TaxType:
    """Determine tax type based on holding period.

    Args:
        purchase_date: When the shares were purchased
        sale_date: When the shares were sold

    Returns:
        TaxType classification
    """
    # Check for intraday (same day)
    if purchase_date.date() == sale_date.date():
        return TaxType.SPECULATIVE

    # Calculate holding period
    holding_days = (sale_date - purchase_date).days

    # In India, LTCG threshold is 365 days for equities
    if holding_days > 365:
        return TaxType.LTCG
    else:
        return TaxType.STCG


class CapitalGainsService:
    """Service for tracking realized capital gains/losses."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def record_realized_gain(
        self,
        user_id: str,
        symbol: str,
        quantity: Decimal,
        cost_basis: Decimal,
        sale_proceeds: Decimal,
        purchase_date: datetime,
        sale_date: datetime,
        fees: Decimal = Decimal("0"),
        cost_lot_id: str | None = None,
        buy_trade_id: str | None = None,
        sell_trade_id: str | None = None,
        portfolio_id: str | None = None,
    ) -> RealizedGain:
        """Record a realized gain/loss from a sale.

        Args:
            user_id: User identifier
            symbol: Stock symbol
            quantity: Number of shares sold
            cost_basis: Total cost of the shares (purchase price * quantity)
            sale_proceeds: Total sale value (sale price * quantity)
            purchase_date: When shares were purchased
            sale_date: When shares were sold
            fees: Total fees (buy + sell)
            cost_lot_id: Reference to the cost lot
            buy_trade_id: Reference to the buy trade
            sell_trade_id: Reference to the sell trade
            portfolio_id: Optional portfolio filter

        Returns:
            Created RealizedGain record
        """
        # Calculate gain/loss
        gain_loss = sale_proceeds - cost_basis - fees

        # Calculate percentage (avoid division by zero)
        gain_loss_pct = (
            (gain_loss / cost_basis) * Decimal("100") if cost_basis > 0 else Decimal("0")
        )

        # Determine holding period and tax type
        holding_days = (sale_date - purchase_date).days
        tax_type = determine_tax_type(purchase_date, sale_date)
        is_long_term = holding_days > 365

        # Get financial year based on sale date
        financial_year = get_financial_year(sale_date)

        # Create the record
        gain = RealizedGain(
            user_id=user_id,
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            quantity=quantity,
            cost_basis=cost_basis,
            sale_proceeds=sale_proceeds,
            fees=fees,
            gain_loss=gain_loss,
            gain_loss_pct=gain_loss_pct,
            purchase_date=purchase_date,
            sale_date=sale_date,
            holding_days=holding_days,
            is_long_term=is_long_term,
            tax_type=tax_type.value,
            cost_lot_id=cost_lot_id,
            buy_trade_id=buy_trade_id,
            sell_trade_id=sell_trade_id,
            financial_year=financial_year,
            created_at=datetime.now(UTC),
        )

        self.db.add(gain)
        await self.db.flush()
        await self.db.refresh(gain)

        return gain

    async def get_realized_gains(
        self,
        user_id: str,
        financial_year: str | None = None,
        symbol: str | None = None,
        tax_type: TaxType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        portfolio_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[RealizedGain], int]:
        """Get realized gains with filters.

        Args:
            user_id: User identifier
            financial_year: Filter by FY (e.g., "2024-25")
            symbol: Filter by symbol
            tax_type: Filter by STCG/LTCG/SPECULATIVE
            start_date: Filter by sale date start
            end_date: Filter by sale date end
            portfolio_id: Filter by portfolio
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Tuple of (list of gains, total count)
        """
        conditions = [RealizedGain.user_id == user_id]

        if financial_year:
            conditions.append(RealizedGain.financial_year == financial_year)
        if symbol:
            conditions.append(RealizedGain.symbol == symbol.upper())
        if tax_type:
            conditions.append(RealizedGain.tax_type == tax_type.value)
        if start_date:
            conditions.append(RealizedGain.sale_date >= start_date)
        if end_date:
            conditions.append(RealizedGain.sale_date <= end_date)
        if portfolio_id:
            conditions.append(RealizedGain.portfolio_id == portfolio_id)

        # Get total count
        count_query = select(func.count(RealizedGain.id)).where(and_(*conditions))
        total_count = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        query = (
            select(RealizedGain)
            .where(and_(*conditions))
            .order_by(RealizedGain.sale_date.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        gains = list(result.scalars().all())

        return gains, total_count

    async def get_gains_summary(
        self,
        user_id: str,
        financial_year: str | None = None,
        portfolio_id: str | None = None,
    ) -> dict:
        """Get summary of capital gains.

        Args:
            user_id: User identifier
            financial_year: Optional FY filter
            portfolio_id: Optional portfolio filter

        Returns:
            Dict with total gains, STCG, LTCG, speculative breakdown
        """
        conditions = [RealizedGain.user_id == user_id]

        if financial_year:
            conditions.append(RealizedGain.financial_year == financial_year)
        if portfolio_id:
            conditions.append(RealizedGain.portfolio_id == portfolio_id)

        # Get aggregated summary by tax type
        query = (
            select(
                RealizedGain.tax_type,
                func.sum(RealizedGain.gain_loss).label("total_gain"),
                func.count(RealizedGain.id).label("count"),
            )
            .where(and_(*conditions))
            .group_by(RealizedGain.tax_type)
        )

        result = await self.db.execute(query)
        rows = result.all()

        # Build summary
        summary = {
            "total_gains": Decimal("0"),
            "total_losses": Decimal("0"),
            "net_gain_loss": Decimal("0"),
            "stcg": Decimal("0"),
            "ltcg": Decimal("0"),
            "speculative": Decimal("0"),
            "stcg_count": 0,
            "ltcg_count": 0,
            "speculative_count": 0,
        }

        for row in rows:
            tax_type = row.tax_type
            total = row.total_gain or Decimal("0")
            count = row.count

            if tax_type == TaxType.STCG.value:
                summary["stcg"] = total
                summary["stcg_count"] = count
            elif tax_type == TaxType.LTCG.value:
                summary["ltcg"] = total
                summary["ltcg_count"] = count
            elif tax_type == TaxType.SPECULATIVE.value:
                summary["speculative"] = total
                summary["speculative_count"] = count

            if total > 0:
                summary["total_gains"] += total
            else:
                summary["total_losses"] += abs(total)

        summary["net_gain_loss"] = summary["stcg"] + summary["ltcg"] + summary["speculative"]

        return summary

    async def get_gains_by_symbol(
        self,
        user_id: str,
        financial_year: str | None = None,
        portfolio_id: str | None = None,
    ) -> list[dict]:
        """Get gains aggregated by symbol.

        Returns:
            List of dicts with symbol, total_gain, trade_count, etc.
        """
        conditions = [RealizedGain.user_id == user_id]

        if financial_year:
            conditions.append(RealizedGain.financial_year == financial_year)
        if portfolio_id:
            conditions.append(RealizedGain.portfolio_id == portfolio_id)

        query = (
            select(
                RealizedGain.symbol,
                func.sum(RealizedGain.gain_loss).label("total_gain"),
                func.sum(RealizedGain.quantity).label("total_quantity"),
                func.count(RealizedGain.id).label("trade_count"),
            )
            .where(and_(*conditions))
            .group_by(RealizedGain.symbol)
            .order_by(func.sum(RealizedGain.gain_loss).desc())
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "symbol": row.symbol,
                "total_gain": row.total_gain or Decimal("0"),
                "total_quantity": row.total_quantity or Decimal("0"),
                "trade_count": row.trade_count,
            }
            for row in rows
        ]
