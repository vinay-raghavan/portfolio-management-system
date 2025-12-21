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
from app.modules.portfolio.models import Position
from app.modules.trading.models import Order

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

        # Add warnings for approaching limits
        if metrics.orders_count >= limits.max_orders_per_day * Decimal("0.8"):
            warnings.append(
                f"Approaching daily order limit ({metrics.orders_count}/{limits.max_orders_per_day})"
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

