"""API routes for auto-trade configuration and management."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.modules.algo.auto_trade_service import (
    AutoTradeConfigService,
    AutoTradeService,
    PendingAutoTradeService,
    StrategyTemplateService,
)
from app.modules.algo.models import PendingTradeStatus
from app.modules.algo.schemas import (
    AutoTradeConfigCreate,
    AutoTradeConfigListResponse,
    AutoTradeConfigResponse,
    AutoTradeConfigUpdate,
    PendingAutoTradeAction,
    PendingAutoTradeActionResponse,
    PendingAutoTradeListResponse,
    PendingAutoTradeResponse,
    StrategyTemplateCreate,
    StrategyTemplateListResponse,
    StrategyTemplateResponse,
    StrategyTemplateUpdate,
    WeightConfigResponse,
    WeightConfigUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Internal API Schemas
# =============================================================================


class ProcessAutoTradesRequest(BaseModel):
    """Request to process auto-trades for a category."""

    category: str = Field(..., min_length=1, max_length=50)
    symbols: list[str] = Field(default_factory=list)
    date: str = Field(..., description="ISO format date string")


class ProcessAutoTradesResponse(BaseModel):
    """Response from processing auto-trades."""

    status: str
    category: str
    users_processed: int = 0
    results: dict = Field(default_factory=dict)


class ExpirePendingResponse(BaseModel):
    """Response from expiring pending auto-trades."""

    status: str
    expired_count: int = 0


# =============================================================================
# Internal API Key Verification
# =============================================================================


def verify_internal_key(x_internal_key: Annotated[str | None, Header()] = None) -> str:
    """Verify the internal API key for worker-to-backend calls."""
    internal_key = getattr(settings, "INTERNAL_API_KEY", "internal-worker-key")
    if not x_internal_key or x_internal_key != internal_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )
    return x_internal_key


InternalAuth = Annotated[str, Depends(verify_internal_key)]


# =============================================================================
# Internal Endpoints (Called by Celery Worker)
# =============================================================================


@router.post("/internal/process", response_model=ProcessAutoTradesResponse)
async def process_auto_trades_internal(
    data: ProcessAutoTradesRequest,
    db: DbSession,
    _key: InternalAuth,
) -> ProcessAutoTradesResponse:
    """Process auto-trades for a category after daily recommendations are generated.

    This is an internal endpoint called by the Celery worker.
    It processes recommendations for all users with auto-trade enabled.
    """

    # Parse the date string
    try:
        rec_date = datetime.fromisoformat(data.date)
        if rec_date.tzinfo is None:
            rec_date = rec_date.replace(tzinfo=UTC)
    except ValueError:
        rec_date = datetime.now(UTC)

    service = AutoTradeService(db)
    result = await service.process_recommendations(
        category=data.category,
        symbols=data.symbols,
        recommendation_date=rec_date,
    )

    await db.commit()

    return ProcessAutoTradesResponse(
        status=result.get("status", "processed"),
        category=data.category,
        users_processed=result.get("users_processed", 0),
        results=result.get("results", {}),
    )


@router.post("/internal/expire-pending", response_model=ExpirePendingResponse)
async def expire_pending_auto_trades_internal(
    db: DbSession,
    _key: InternalAuth,
) -> ExpirePendingResponse:
    """Expire pending auto-trades that have passed their expiry time.

    This is an internal endpoint called by the Celery worker hourly.
    """
    service = PendingAutoTradeService(db)
    expired_count = await service.expire_old_trades()
    await db.commit()

    return ExpirePendingResponse(
        status="success",
        expired_count=expired_count,
    )


# =============================================================================
# Strategy Templates
# =============================================================================


@router.get("/templates", response_model=StrategyTemplateListResponse)
async def list_strategy_templates(
    db: DbSession, current_user: CurrentUser
) -> StrategyTemplateListResponse:
    """Get all strategy templates for the current user."""
    service = StrategyTemplateService(db)
    templates = await service.get_templates(str(current_user.id))
    return StrategyTemplateListResponse(
        templates=[StrategyTemplateResponse.model_validate(t) for t in templates],
        total=len(templates),
    )


@router.post("/templates", response_model=StrategyTemplateResponse, status_code=201)
async def create_strategy_template(
    data: StrategyTemplateCreate, db: DbSession, current_user: CurrentUser
) -> StrategyTemplateResponse:
    """Create a new strategy template."""
    service = StrategyTemplateService(db)
    template = await service.create_template(str(current_user.id), data)
    await db.commit()
    return StrategyTemplateResponse.model_validate(template)


@router.get("/templates/{template_id}", response_model=StrategyTemplateResponse)
async def get_strategy_template(
    template_id: str, db: DbSession, current_user: CurrentUser
) -> StrategyTemplateResponse:
    """Get a specific strategy template."""
    service = StrategyTemplateService(db)
    template = await service.get_template(str(current_user.id), template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy template not found",
        )
    return StrategyTemplateResponse.model_validate(template)


@router.patch("/templates/{template_id}", response_model=StrategyTemplateResponse)
async def update_strategy_template(
    template_id: str,
    data: StrategyTemplateUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> StrategyTemplateResponse:
    """Update a strategy template."""
    service = StrategyTemplateService(db)
    template = await service.update_template(str(current_user.id), template_id, data)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy template not found",
        )
    await db.commit()
    return StrategyTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_strategy_template(
    template_id: str, db: DbSession, current_user: CurrentUser
) -> None:
    """Delete a strategy template."""
    service = StrategyTemplateService(db)
    deleted = await service.delete_template(str(current_user.id), template_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy template not found",
        )
    await db.commit()


# =============================================================================
# Auto-Trade Configurations
# =============================================================================


@router.get("/configs", response_model=AutoTradeConfigListResponse)
async def list_auto_trade_configs(
    db: DbSession, current_user: CurrentUser
) -> AutoTradeConfigListResponse:
    """Get all auto-trade configurations for the current user."""
    service = AutoTradeConfigService(db)
    configs = await service.get_configs(str(current_user.id))
    return AutoTradeConfigListResponse(
        configs=[AutoTradeConfigResponse.model_validate(c) for c in configs],
        total=len(configs),
    )


@router.post("/configs", response_model=AutoTradeConfigResponse, status_code=201)
async def create_auto_trade_config(
    data: AutoTradeConfigCreate, db: DbSession, current_user: CurrentUser
) -> AutoTradeConfigResponse:
    """Create a new auto-trade configuration."""
    service = AutoTradeConfigService(db)
    try:
        config = await service.create_config(str(current_user.id), data)
        await db.commit()
        return AutoTradeConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/configs/{config_id}", response_model=AutoTradeConfigResponse)
async def get_auto_trade_config(
    config_id: str, db: DbSession, current_user: CurrentUser
) -> AutoTradeConfigResponse:
    """Get a specific auto-trade configuration."""
    service = AutoTradeConfigService(db)
    config = await service.get_config(str(current_user.id), config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auto-trade config not found",
        )
    return AutoTradeConfigResponse.model_validate(config)


@router.patch("/configs/{config_id}", response_model=AutoTradeConfigResponse)
async def update_auto_trade_config(
    config_id: str,
    data: AutoTradeConfigUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> AutoTradeConfigResponse:
    """Update an auto-trade configuration."""
    service = AutoTradeConfigService(db)
    try:
        config = await service.update_config(str(current_user.id), config_id, data)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auto-trade config not found",
            )
        await db.commit()
        return AutoTradeConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/configs/{config_id}", status_code=204)
async def delete_auto_trade_config(
    config_id: str, db: DbSession, current_user: CurrentUser
) -> None:
    """Delete an auto-trade configuration."""
    service = AutoTradeConfigService(db)
    deleted = await service.delete_config(str(current_user.id), config_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auto-trade config not found",
        )
    await db.commit()


# =============================================================================
# Weight Configuration
# =============================================================================


@router.get("/weights", response_model=WeightConfigResponse)
async def get_weight_config(
    db: DbSession, current_user: CurrentUser, category: str = "momentum"
) -> WeightConfigResponse:
    """Get current multi-factor weight configuration for a category."""
    service = AutoTradeConfigService(db)
    config = await service.get_config_by_category(str(current_user.id), category)
    if not config:
        # Return defaults
        return WeightConfigResponse(
            weight_technical=40,
            weight_fundamental=40,
            weight_sentiment=20,
            min_confidence="medium",
        )
    return WeightConfigResponse(
        weight_technical=config.weight_technical,
        weight_fundamental=config.weight_fundamental,
        weight_sentiment=config.weight_sentiment,
        min_confidence=config.min_confidence,
    )


@router.put("/weights", response_model=WeightConfigResponse)
async def update_weight_config(
    data: WeightConfigUpdate,
    db: DbSession,
    current_user: CurrentUser,
    category: str = "momentum",
) -> WeightConfigResponse:
    """Update multi-factor weight configuration."""
    # Validate weights sum to 100
    total = data.weight_technical + data.weight_fundamental + data.weight_sentiment
    if total != 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weights must sum to 100, got {total}",
        )

    service = AutoTradeConfigService(db)
    config = await service.get_config_by_category(str(current_user.id), category)

    if config:
        config.weight_technical = data.weight_technical
        config.weight_fundamental = data.weight_fundamental
        config.weight_sentiment = data.weight_sentiment
        config.min_confidence = data.min_confidence
        await db.commit()
    else:
        # Create new config with weights
        from app.modules.algo.schemas import AutoTradeConfigCreate

        new_config = AutoTradeConfigCreate(
            category=category,
            preset_category=category,
            weight_technical=data.weight_technical,
            weight_fundamental=data.weight_fundamental,
            weight_sentiment=data.weight_sentiment,
            min_confidence=data.min_confidence,
        )
        config = await service.create_config(str(current_user.id), new_config)
        await db.commit()

    return WeightConfigResponse(
        weight_technical=config.weight_technical,
        weight_fundamental=config.weight_fundamental,
        weight_sentiment=config.weight_sentiment,
        min_confidence=config.min_confidence,
    )


# =============================================================================
# Pending Auto-Trades
# =============================================================================


@router.get("/pending", response_model=PendingAutoTradeListResponse)
async def list_pending_auto_trades(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: str | None = None,
) -> PendingAutoTradeListResponse:
    """Get pending auto-trades for the current user."""
    service = PendingAutoTradeService(db)
    filter_status = None
    if status_filter:
        try:
            filter_status = PendingTradeStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )

    pending = await service.get_pending_trades(str(current_user.id), filter_status)
    # Count only PENDING status trades for the badge
    pending_count = sum(1 for p in pending if p.status == PendingTradeStatus.PENDING)
    return PendingAutoTradeListResponse(
        pending_trades=[PendingAutoTradeResponse.model_validate(p) for p in pending],
        total=len(pending),
        pending_count=pending_count,
    )


@router.get("/pending/{trade_id}", response_model=PendingAutoTradeResponse)
async def get_pending_auto_trade(
    trade_id: str, db: DbSession, current_user: CurrentUser
) -> PendingAutoTradeResponse:
    """Get a specific pending auto-trade."""
    service = PendingAutoTradeService(db)
    pending = await service.get_pending_trade(str(current_user.id), trade_id)
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending auto-trade not found",
        )
    return PendingAutoTradeResponse.model_validate(pending)


@router.post("/pending/{trade_id}/action", response_model=PendingAutoTradeActionResponse)
async def action_pending_auto_trade(
    trade_id: str,
    data: PendingAutoTradeAction,
    db: DbSession,
    current_user: CurrentUser,
) -> PendingAutoTradeActionResponse:
    """Approve or reject a pending auto-trade."""
    service = PendingAutoTradeService(db)

    if data.action == "approve":
        pending, error = await service.approve_pending_trade(str(current_user.id), trade_id)
        if not pending:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error or "Pending auto-trade not found",
            )
        if error:
            return PendingAutoTradeActionResponse(
                id=trade_id,
                status=pending.status.value,
                message=error,
            )
        await db.commit()
        return PendingAutoTradeActionResponse(
            id=trade_id,
            status=pending.status.value,
            created_strategy_id=pending.created_strategy_id,
            message="Trade approved successfully",
        )
    else:  # reject
        pending = await service.reject_pending_trade(
            str(current_user.id), trade_id, reason=data.reason
        )
        if not pending:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending auto-trade not found",
            )
        await db.commit()
        return PendingAutoTradeActionResponse(
            id=trade_id,
            status=pending.status.value,
            message="Trade rejected",
        )
