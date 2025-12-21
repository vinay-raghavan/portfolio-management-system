"""Portfolio API routes."""

from fastapi import APIRouter, Query

from app.api.deps import DbSession, CurrentUser
from app.modules.portfolio.schemas import PortfolioResponse, TradeHistoryResponse, TradeResponse
from app.modules.portfolio.service import PortfolioService

router = APIRouter()


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(db: DbSession, current_user: CurrentUser) -> PortfolioResponse:
    """Get portfolio summary and positions."""
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

