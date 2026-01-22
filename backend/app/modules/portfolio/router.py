"""Portfolio API routes."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.modules.portfolio.funds_service import FundsService
from app.modules.portfolio.schemas import (
    FundsDepositRequest,
    FundsResetRequest,
    FundsResponse,
    FundsWithdrawRequest,
    PortfolioCreate,
    PortfolioDetailResponse,
    PortfolioInfo,
    PortfolioListResponse,
    PortfolioResponse,
    PortfolioUpdate,
    ProfitBookingRules,
    TradeHistoryResponse,
    TradeResponse,
    TrailingStopConfig,
    TrailingStopUpdate,
)
from app.modules.portfolio.service import PortfolioService

router = APIRouter()


# ============== Portfolio Management ==============


@router.post("/portfolios", response_model=PortfolioInfo, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    db: DbSession,
    current_user: CurrentUser,
    data: PortfolioCreate,
) -> PortfolioInfo:
    """Create a new portfolio."""
    service = PortfolioService(db)
    portfolio = await service.create_portfolio(current_user.id, data)
    await db.commit()
    return PortfolioInfo.model_validate(portfolio)


@router.get("/portfolios", response_model=PortfolioListResponse)
async def list_portfolios(
    db: DbSession,
    current_user: CurrentUser,
) -> PortfolioListResponse:
    """List all portfolios for the current user."""
    service = PortfolioService(db)
    portfolios = await service.get_portfolios(current_user.id)
    return PortfolioListResponse(
        portfolios=[PortfolioInfo.model_validate(p) for p in portfolios],
        total_count=len(portfolios),
    )


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioDetailResponse)
async def get_portfolio_detail(
    db: DbSession,
    current_user: CurrentUser,
    portfolio_id: str,
) -> PortfolioDetailResponse:
    """Get detailed portfolio with positions and summary."""
    service = PortfolioService(db)
    result = await service.get_portfolio_detail(current_user.id, portfolio_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )
    return result


@router.patch("/portfolios/{portfolio_id}", response_model=PortfolioInfo)
async def update_portfolio(
    db: DbSession,
    current_user: CurrentUser,
    portfolio_id: str,
    data: PortfolioUpdate,
) -> PortfolioInfo:
    """Update a portfolio."""
    service = PortfolioService(db)
    portfolio = await service.update_portfolio(current_user.id, portfolio_id, data)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )
    await db.commit()
    return PortfolioInfo.model_validate(portfolio)


@router.delete("/portfolios/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    db: DbSession,
    current_user: CurrentUser,
    portfolio_id: str,
) -> None:
    """Delete a portfolio."""
    service = PortfolioService(db)
    try:
        deleted = await service.delete_portfolio(current_user.id, portfolio_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found",
            )
        await db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============== Legacy Portfolio Endpoints ==============


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(db: DbSession, current_user: CurrentUser) -> PortfolioResponse:
    """Get portfolio summary and positions (all portfolios combined)."""
    service = PortfolioService(db)
    return await service.get_portfolio(current_user.id)


@router.get("/trades", response_model=TradeHistoryResponse)
async def get_trade_history(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> TradeHistoryResponse:
    """Get trade history with pagination."""
    service = PortfolioService(db)
    trades, total_count = await service.get_trades(current_user.id, page, page_size)

    trade_responses = [
        TradeResponse(
            id=t.id,
            portfolio_id=t.portfolio_id,
            symbol=t.symbol,
            side=t.side,
            quantity=t.quantity,
            price=t.price,
            fees=t.fees,
            total_value=t.quantity * t.price,
            executed_at=t.executed_at,
        )
        for t in trades
    ]

    return TradeHistoryResponse(
        trades=trade_responses,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


# ============== Profit Booking Endpoints ==============


@router.get("/positions/{position_id}/profit-booking", response_model=ProfitBookingRules | None)
async def get_profit_booking_rules(
    db: DbSession,
    current_user: CurrentUser,
    position_id: str,
) -> ProfitBookingRules | None:
    """Get profit booking rules for a position."""
    service = PortfolioService(db)
    rules = await service.get_profit_booking_rules(current_user.id, position_id)
    return rules


@router.patch("/positions/{position_id}/profit-booking", response_model=ProfitBookingRules)
async def update_profit_booking_rules(
    db: DbSession,
    current_user: CurrentUser,
    position_id: str,
    rules: ProfitBookingRules,
) -> ProfitBookingRules:
    """Set or update profit booking rules for a position."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Updating profit booking rules - user_id: {current_user.id}, position_id: {position_id}"
    )
    logger.info(f"Rules: {rules}")

    service = PortfolioService(db)
    updated_rules = await service.update_profit_booking_rules(current_user.id, position_id, rules)
    if updated_rules is None:
        logger.error(f"Position not found - user_id: {current_user.id}, position_id: {position_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found",
        )
    await db.commit()
    return updated_rules


# ============== Trailing Stop Endpoints ==============


@router.get("/positions/{position_id}/trailing-stop", response_model=TrailingStopConfig | None)
async def get_trailing_stop_config(
    db: DbSession,
    current_user: CurrentUser,
    position_id: str,
) -> TrailingStopConfig | None:
    """Get trailing stop configuration for a position."""
    service = PortfolioService(db)
    config = await service.get_trailing_stop_config(current_user.id, position_id)
    return config


@router.patch("/positions/{position_id}/trailing-stop", response_model=TrailingStopConfig)
async def update_trailing_stop(
    db: DbSession,
    current_user: CurrentUser,
    position_id: str,
    config: TrailingStopUpdate,
) -> TrailingStopConfig:
    """Set or update trailing stop configuration for a position.

    When enabled, the stop loss will automatically adjust upward (for LONG positions)
    or downward (for SHORT positions) as the price moves favorably, while never
    moving in the unfavorable direction.
    """
    service = PortfolioService(db)
    try:
        updated_config = await service.update_trailing_stop(current_user.id, position_id, config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if updated_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found",
        )
    await db.commit()
    return updated_config


# ============== Funds Management Endpoints ==============


@router.get("/funds", response_model=FundsResponse)
async def get_funds(
    db: DbSession,
    current_user: CurrentUser,
) -> FundsResponse:
    """Get current user funds/balance."""
    service = FundsService(db)
    funds = await service.get_or_create_funds(current_user.id)
    return FundsResponse(
        id=funds.id,
        user_id=funds.user_id,
        cash_balance=funds.cash_balance,
        margin_used=funds.margin_used,
        collateral=funds.collateral,
        available_cash=funds.available_cash,
        total_balance=funds.total_balance,
        available_margin=funds.available_margin,
    )


@router.post("/funds/deposit", response_model=FundsResponse)
async def deposit_funds(
    db: DbSession,
    current_user: CurrentUser,
    request: FundsDepositRequest,
) -> FundsResponse:
    """Add funds to account (simulated deposit for paper trading)."""
    service = FundsService(db)
    note = request.note or "Manual deposit"
    funds = await service.add_cash(current_user.id, request.amount, reason=note)
    await db.commit()
    return FundsResponse(
        id=funds.id,
        user_id=funds.user_id,
        cash_balance=funds.cash_balance,
        margin_used=funds.margin_used,
        collateral=funds.collateral,
        available_cash=funds.available_cash,
        total_balance=funds.total_balance,
        available_margin=funds.available_margin,
    )


@router.post("/funds/withdraw", response_model=FundsResponse)
async def withdraw_funds(
    db: DbSession,
    current_user: CurrentUser,
    request: FundsWithdrawRequest,
) -> FundsResponse:
    """Withdraw funds from account (simulated withdrawal for paper trading)."""
    service = FundsService(db)
    note = request.note or "Manual withdrawal"
    try:
        funds = await service.deduct_cash(current_user.id, request.amount, reason=note)
        await db.commit()
        return FundsResponse(
            id=funds.id,
            user_id=funds.user_id,
            cash_balance=funds.cash_balance,
            margin_used=funds.margin_used,
            collateral=funds.collateral,
            available_cash=funds.available_cash,
            total_balance=funds.total_balance,
            available_margin=funds.available_margin,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/funds/reset", response_model=FundsResponse)
async def reset_funds(
    db: DbSession,
    current_user: CurrentUser,
    request: FundsResetRequest | None = None,
) -> FundsResponse:
    """Reset funds to initial balance (for paper trading).

    This will reset the balance to the specified amount or the default
    initial balance configured for paper trading.
    """
    service = FundsService(db)

    # Get existing funds or create new
    existing_funds = await service.get_funds(current_user.id)

    initial_balance = request.initial_balance if request else None

    if existing_funds:
        # Reset existing funds
        from decimal import Decimal

        from app.core.config import settings

        if initial_balance is None:
            initial_balance = Decimal(str(settings.PAPER_TRADING_INITIAL_BALANCE))

        existing_funds.cash_balance = initial_balance
        existing_funds.margin_used = Decimal("0")
        existing_funds.collateral = Decimal("0")
        await db.flush()
        await db.refresh(existing_funds)
        funds = existing_funds
    else:
        # Create new funds
        funds = await service.initialize_funds(current_user.id, initial_balance)

    await db.commit()
    return FundsResponse(
        id=funds.id,
        user_id=funds.user_id,
        cash_balance=funds.cash_balance,
        margin_used=funds.margin_used,
        collateral=funds.collateral,
        available_cash=funds.available_cash,
        total_balance=funds.total_balance,
        available_margin=funds.available_margin,
    )
