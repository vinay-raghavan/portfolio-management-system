"""API routes for risk management."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.modules.risk.schemas import (
    DailyRiskMetricsResponse,
    RiskLimitsResponse,
    RiskLimitsUpdate,
    RiskSummary,
)
from app.modules.risk.service import RiskService

router = APIRouter()


@router.get("/limits", response_model=RiskLimitsResponse)
async def get_risk_limits(
    db: DbSession,
    current_user: CurrentUser,
) -> RiskLimitsResponse:
    """Get current user's risk limits."""
    service = RiskService(db)
    limits = await service.get_limits(current_user.id)
    return RiskLimitsResponse.model_validate(limits)


@router.put("/limits", response_model=RiskLimitsResponse)
async def update_risk_limits(
    updates: RiskLimitsUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> RiskLimitsResponse:
    """Update current user's risk limits."""
    service = RiskService(db)
    limits = await service.update_limits(current_user.id, updates)
    await db.commit()
    return RiskLimitsResponse.model_validate(limits)


@router.get("/summary", response_model=RiskSummary)
async def get_risk_summary(
    db: DbSession,
    current_user: CurrentUser,
) -> RiskSummary:
    """Get current risk status summary.

    Returns daily P&L, remaining limits, and trading status.
    """
    service = RiskService(db)
    return await service.get_risk_summary(current_user.id)


@router.get("/metrics/today", response_model=DailyRiskMetricsResponse)
async def get_today_metrics(
    db: DbSession,
    current_user: CurrentUser,
) -> DailyRiskMetricsResponse:
    """Get today's risk metrics."""
    service = RiskService(db)
    metrics = await service.get_daily_metrics(current_user.id)
    return DailyRiskMetricsResponse.model_validate(metrics)


@router.post("/reset-daily", response_model=DailyRiskMetricsResponse)
async def reset_daily_metrics(
    db: DbSession,
    current_user: CurrentUser,
) -> DailyRiskMetricsResponse:
    """Reset daily risk metrics (admin/testing only).

    This clears the daily loss limit breach flag and resets counters.
    """
    service = RiskService(db)
    metrics = await service.get_daily_metrics(current_user.id)

    # Reset metrics
    metrics.orders_count = 0
    metrics.trades_count = 0
    metrics.realized_pnl = 0
    metrics.unrealized_pnl = 0
    metrics.total_traded_value = 0
    metrics.daily_loss_limit_breached = False
    metrics.position_limit_breached = False

    await db.commit()
    await db.refresh(metrics)

    return DailyRiskMetricsResponse.model_validate(metrics)
