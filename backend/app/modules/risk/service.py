"""Risk management service for enforcing trading limits."""

import logging
from datetime import datetime, date, timezone
from decimal import Decimal
from dataclasses import dataclass, field

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.risk.models import RiskLimits, DailyRiskMetrics
from app.modules.risk.schemas import RiskCheckResult, RiskSummary, RiskLimitsUpdate
from app.modules.portfolio.funds_service import FundsService
from app.modules.portfolio.models import Position, ProductType
from app.modules.trading.models import Order
from app.modules.instruments.models import Instrument

logger = logging.getLogger(__name__)


@dataclass
class RiskCheck:
    """Individual risk check result."""
    
    name: str
    passed: bool
    current_value: str
    limit_value: str
    message: str | None = None


class RiskService:
    """Service for risk management and limit enforcement.
    
    Provides pre-trade risk checks and daily limit tracking.
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.funds_service = FundsService(db)

    async def get_limits(self, user_id: str) -> RiskLimits:
        """Get risk limits for a user, creating defaults if needed."""
        result = await self.db.execute(
            select(RiskLimits).where(RiskLimits.user_id == user_id)
        )
        limits = result.scalar_one_or_none()
        
        if limits is None:
            limits = RiskLimits(user_id=user_id)
            self.db.add(limits)
            await self.db.flush()
            await self.db.refresh(limits)
            logger.info(f"Created default risk limits for user {user_id}")
        
        return limits

    async def update_limits(
        self, 
        user_id: str, 
        updates: RiskLimitsUpdate
    ) -> RiskLimits:
        """Update risk limits for a user."""
        limits = await self.get_limits(user_id)
        
        update_data = updates.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(limits, field_name, value)
        
        await self.db.flush()
        await self.db.refresh(limits)
        
        logger.info(f"Updated risk limits for user {user_id}: {update_data}")
        return limits

    async def get_daily_metrics(self, user_id: str) -> DailyRiskMetrics:
        """Get today's risk metrics, creating if needed."""
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        result = await self.db.execute(
            select(DailyRiskMetrics).where(
                DailyRiskMetrics.user_id == user_id,
                func.date(DailyRiskMetrics.date) == today.date()
            )
        )
        metrics = result.scalar_one_or_none()
        
        if metrics is None:
            metrics = DailyRiskMetrics(user_id=user_id, date=today)
            self.db.add(metrics)
            await self.db.flush()
            await self.db.refresh(metrics)
        
        return metrics

    async def check_order_risk(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
    ) -> RiskCheckResult:
        """Run all risk checks for a proposed order.
        
        Args:
            user_id: User placing the order
            symbol: Symbol to trade
            side: BUY or SELL
            quantity: Order quantity
            price: Order price
            
        Returns:
            RiskCheckResult with pass/fail and details
        """
        limits = await self.get_limits(user_id)
        metrics = await self.get_daily_metrics(user_id)
        
        checks: list[RiskCheck] = []
        warnings: list[str] = []
        order_value = quantity * price
        
        # 1. Check daily loss limit
        if metrics.realized_pnl < 0:
            daily_loss = abs(metrics.realized_pnl)
            loss_check = RiskCheck(
                name="daily_loss_limit",
                passed=daily_loss < limits.max_daily_loss,
                current_value=f"₹{daily_loss:.2f}",
                limit_value=f"₹{limits.max_daily_loss:.2f}",
            )
            if not loss_check.passed:
                loss_check.message = "Daily loss limit exceeded"
            checks.append(loss_check)
        
        # 2. Check order value limit
        order_check = RiskCheck(
            name="max_order_value",
            passed=order_value <= limits.max_order_value,
            current_value=f"₹{order_value:.2f}",
            limit_value=f"₹{limits.max_order_value:.2f}",
        )
        if not order_check.passed:
            order_check.message = "Order value exceeds limit"
        checks.append(order_check)
        
        # 3. Check daily order count
        orders_check = RiskCheck(
            name="max_orders_per_day",
            passed=metrics.orders_count < limits.max_orders_per_day,
            current_value=str(metrics.orders_count),
            limit_value=str(limits.max_orders_per_day),
        )
        if not orders_check.passed:
            orders_check.message = "Daily order limit reached"
        checks.append(orders_check)
        
        # 4. Check position count (for new positions)
        if side == "BUY":
            positions_count = await self._get_positions_count(user_id)
            existing_position = await self._get_position(user_id, symbol)

            if existing_position is None:  # New position
                positions_check = RiskCheck(
                    name="max_positions",
                    passed=positions_count < limits.max_positions,
                    current_value=str(positions_count),
                    limit_value=str(limits.max_positions),
                )
                if not positions_check.passed:
                    positions_check.message = "Maximum positions limit reached"
                checks.append(positions_check)

        # 5. Check position size limit
        position_size_check = RiskCheck(
            name="max_position_size",
            passed=order_value <= limits.max_position_size,
            current_value=f"₹{order_value:.2f}",
            limit_value=f"₹{limits.max_position_size:.2f}",
        )
        if not position_size_check.passed:
            position_size_check.message = "Position size exceeds limit"
        checks.append(position_size_check)

        # 6. Check sector concentration limit (for BUY orders)
        if side == "BUY":
            sector_check = await self._check_sector_concentration(
                user_id, symbol, order_value, limits
            )
            if sector_check:
                checks.append(sector_check)
                if not sector_check.passed:
                    warnings.append(f"Sector concentration warning: {sector_check.message}")

        # 7. Check intraday exposure limit
        intraday_exposure = await self._get_intraday_exposure(user_id)
        intraday_check = RiskCheck(
            name="max_intraday_exposure",
            passed=intraday_exposure + order_value <= limits.max_intraday_exposure,
            current_value=f"₹{intraday_exposure:.2f}",
            limit_value=f"₹{limits.max_intraday_exposure:.2f}",
        )
        if not intraday_check.passed:
            intraday_check.message = "Intraday exposure limit exceeded"
        checks.append(intraday_check)

        # Add warnings for approaching limits
        if metrics.orders_count >= limits.max_orders_per_day * Decimal("0.8"):
            warnings.append(
                f"Approaching daily order limit ({metrics.orders_count}/{limits.max_orders_per_day})"
            )

        # Warn if sector concentration is approaching limit
        sector_concentration = await self._get_sector_concentration(user_id, symbol)
        if sector_concentration and sector_concentration >= limits.max_sector_concentration * Decimal("0.8"):
            warnings.append(
                f"Approaching sector concentration limit ({sector_concentration:.1f}%/{limits.max_sector_concentration}%)"
            )

        # Determine overall result
        all_passed = all(check.passed for check in checks)
        blocked_reason = None
        if not all_passed:
            failed_checks = [c for c in checks if not c.passed]
            blocked_reason = failed_checks[0].message if failed_checks else "Risk check failed"

        return RiskCheckResult(
            passed=all_passed,
            checks=[
                {
                    "name": c.name,
                    "passed": c.passed,
                    "current": c.current_value,
                    "limit": c.limit_value,
                    "message": c.message,
                }
                for c in checks
            ],
            warnings=warnings,
            blocked_reason=blocked_reason,
        )

    async def record_order(self, user_id: str, order_value: Decimal) -> None:
        """Record an order for daily metrics tracking."""
        metrics = await self.get_daily_metrics(user_id)
        metrics.orders_count += 1
        metrics.total_traded_value += order_value
        await self.db.flush()

    async def record_trade_pnl(self, user_id: str, pnl: Decimal) -> None:
        """Record realized P&L from a trade."""
        metrics = await self.get_daily_metrics(user_id)
        metrics.realized_pnl += pnl
        metrics.trades_count += 1

        # Check if daily loss limit is breached
        limits = await self.get_limits(user_id)
        if metrics.realized_pnl < 0 and abs(metrics.realized_pnl) >= limits.max_daily_loss:
            metrics.daily_loss_limit_breached = True
            logger.warning(f"Daily loss limit breached for user {user_id}")

        await self.db.flush()

    async def get_risk_summary(self, user_id: str) -> RiskSummary:
        """Get current risk status summary."""
        limits = await self.get_limits(user_id)
        metrics = await self.get_daily_metrics(user_id)
        funds = await self.funds_service.get_or_create_funds(user_id)

        positions_count = await self._get_positions_count(user_id)
        largest_position_pct = await self._get_largest_position_pct(user_id, funds.total_balance)

        daily_pnl_pct = Decimal("0")
        if funds.total_balance > 0:
            daily_pnl_pct = (metrics.realized_pnl / funds.total_balance) * 100

        daily_loss_remaining = limits.max_daily_loss
        if metrics.realized_pnl < 0:
            daily_loss_remaining = limits.max_daily_loss - abs(metrics.realized_pnl)

        is_blocked = metrics.daily_loss_limit_breached
        block_reason = "Daily loss limit exceeded" if is_blocked else None

        return RiskSummary(
            daily_pnl=metrics.realized_pnl,
            daily_pnl_pct=daily_pnl_pct,
            daily_loss_remaining=daily_loss_remaining,
            orders_today=metrics.orders_count,
            orders_remaining=limits.max_orders_per_day - metrics.orders_count,
            positions_count=positions_count,
            positions_remaining=limits.max_positions - positions_count,
            largest_position_pct=largest_position_pct,
            is_trading_blocked=is_blocked,
            block_reason=block_reason,
        )

    async def _get_positions_count(self, user_id: str) -> int:
        """Get count of open positions."""
        result = await self.db.execute(
            select(func.count(Position.id)).where(
                Position.user_id == user_id,
                Position.quantity > 0
            )
        )
        return result.scalar() or 0

    async def _get_position(self, user_id: str, symbol: str) -> Position | None:
        """Get a specific position."""
        result = await self.db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.symbol == symbol
            )
        )
        return result.scalar_one_or_none()

    async def _get_largest_position_pct(
        self,
        user_id: str,
        total_balance: Decimal
    ) -> Decimal:
        """Get the largest position as percentage of portfolio."""
        if total_balance <= 0:
            return Decimal("0")

        result = await self.db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.quantity > 0
            )
        )
        positions = result.scalars().all()

        if not positions:
            return Decimal("0")

        largest_value = max(p.quantity * p.avg_cost for p in positions)
        return (largest_value / total_balance) * 100

    async def _get_sector_for_symbol(self, symbol: str) -> str | None:
        """Get sector for a symbol from instruments table."""
        result = await self.db.execute(
            select(Instrument.sector).where(
                Instrument.symbol == symbol.upper(),
                Instrument.exchange == "NSE"
            )
        )
        return result.scalar_one_or_none()

    async def _get_sector_concentration(
        self,
        user_id: str,
        symbol: str,
    ) -> Decimal | None:
        """Get current sector concentration for a symbol's sector.

        Returns:
            Sector concentration as percentage, or None if sector unknown
        """
        sector = await self._get_sector_for_symbol(symbol)
        if not sector:
            return None

        # Get all positions with their sectors
        result = await self.db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.quantity > 0
            )
        )
        positions = list(result.scalars().all())

        if not positions:
            return Decimal("0")

        total_value = Decimal("0")
        sector_value = Decimal("0")

        for pos in positions:
            pos_value = pos.quantity * pos.avg_cost
            total_value += pos_value

            # Get sector for this position
            pos_sector = pos.sector or await self._get_sector_for_symbol(pos.symbol)
            if pos_sector == sector:
                sector_value += pos_value

        if total_value == 0:
            return Decimal("0")

        return (sector_value / total_value) * 100

    async def _check_sector_concentration(
        self,
        user_id: str,
        symbol: str,
        order_value: Decimal,
        limits: RiskLimits,
    ) -> RiskCheck | None:
        """Check if order would exceed sector concentration limit."""
        sector = await self._get_sector_for_symbol(symbol)
        if not sector:
            # Unknown sector, skip check
            return None

        current_concentration = await self._get_sector_concentration(user_id, symbol)
        if current_concentration is None:
            return None

        # Estimate new concentration after this order
        funds = await self.funds_service.get_or_create_funds(user_id)
        total_value = funds.total_balance
        if total_value <= 0:
            return None

        # Get current sector value
        result = await self.db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.quantity > 0
            )
        )
        positions = list(result.scalars().all())

        sector_value = Decimal("0")
        for pos in positions:
            pos_sector = pos.sector or await self._get_sector_for_symbol(pos.symbol)
            if pos_sector == sector:
                sector_value += pos.quantity * pos.avg_cost

        new_sector_value = sector_value + order_value
        new_total = total_value  # Assuming cash available covers the order
        new_concentration = (new_sector_value / new_total) * 100 if new_total > 0 else Decimal("0")

        return RiskCheck(
            name="max_sector_concentration",
            passed=new_concentration <= limits.max_sector_concentration,
            current_value=f"{new_concentration:.1f}%",
            limit_value=f"{limits.max_sector_concentration}%",
            message=f"Sector '{sector}' concentration would reach {new_concentration:.1f}%" if new_concentration > limits.max_sector_concentration else None,
        )

    async def _get_intraday_exposure(self, user_id: str) -> Decimal:
        """Get current intraday exposure (value of all INTRADAY positions)."""
        result = await self.db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.quantity > 0,
                Position.product_type == ProductType.INTRADAY.value
            )
        )
        positions = list(result.scalars().all())

        return sum(p.quantity * p.avg_cost for p in positions)

