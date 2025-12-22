"""Signals API routes."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.modules.signals.models import SignalStatus, SignalType
from app.modules.signals.schemas import (
    SignalGenerateRequest,
    SignalGenerateResponse,
    SignalListResponse,
    SignalResponse,
    SignalUpdate,
    StrategyListResponse,
)
from app.modules.signals.service import SignalService

router = APIRouter()


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies(db: DbSession) -> StrategyListResponse:
    """List all available trading strategies."""
    service = SignalService(db)
    strategies = service.get_available_strategies()
    return StrategyListResponse(strategies=strategies)


@router.post("/generate", response_model=SignalGenerateResponse)
async def generate_signals(
    request: SignalGenerateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> SignalGenerateResponse:
    """Generate trading signals for given symbols.

    Runs the specified strategy (or all strategies) on the provided symbols
    and creates signal records.
    """
    service = SignalService(db)
    signals = await service.generate_signals(
        symbols=request.symbols,
        user_id=current_user.id,
        strategy_name=request.strategy_name,
        timeframe=request.timeframe,
    )

    return SignalGenerateResponse(
        signals_generated=len(signals),
        signals=[SignalResponse.model_validate(s) for s in signals],
    )


@router.get("", response_model=SignalListResponse)
async def list_signals(
    db: DbSession,
    current_user: CurrentUser,
    symbol: str | None = None,
    status: SignalStatus | None = None,
    signal_type: SignalType | None = None,
    strategy_name: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SignalListResponse:
    """List signals for the current user with optional filters."""
    service = SignalService(db)
    offset = (page - 1) * page_size

    signals, total = await service.get_signals(
        user_id=current_user.id,
        symbol=symbol,
        status=status,
        signal_type=signal_type,
        strategy_name=strategy_name,
        limit=page_size,
        offset=offset,
    )

    return SignalListResponse(
        signals=[SignalResponse.model_validate(s) for s in signals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> SignalResponse:
    """Get a specific signal by ID."""
    service = SignalService(db)
    signal = await service.get_signal(signal_id, current_user.id)

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal not found: {signal_id}",
        )

    return SignalResponse.model_validate(signal)


@router.patch("/{signal_id}", response_model=SignalResponse)
async def update_signal(
    signal_id: str,
    update: SignalUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> SignalResponse:
    """Update a signal's status or execution info."""
    service = SignalService(db)
    signal = await service.update_signal(
        signal_id=signal_id,
        user_id=current_user.id,
        status=update.status,
        is_executed=update.is_executed,
        executed_order_id=update.executed_order_id,
        notes=update.notes,
    )

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal not found: {signal_id}",
        )

    return SignalResponse.model_validate(signal)


@router.post("/{signal_id}/cancel", response_model=SignalResponse)
async def cancel_signal(
    signal_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> SignalResponse:
    """Cancel a pending signal."""
    service = SignalService(db)
    signal = await service.cancel_signal(signal_id, current_user.id)

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal not found or not pending: {signal_id}",
        )

    return SignalResponse.model_validate(signal)


@router.post("/expire", status_code=status.HTTP_200_OK)
async def expire_signals(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Expire signals past their expiration date."""
    service = SignalService(db)
    count = await service.expire_old_signals(current_user.id)
    return {"expired_count": count, "message": f"Expired {count} signals"}

