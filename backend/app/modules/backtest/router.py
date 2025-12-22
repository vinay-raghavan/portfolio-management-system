"""API router for backtesting endpoints."""

import logging
import traceback
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.modules.auth.models import User
from app.modules.backtest.schemas import (
    BacktestListResponse,
    BacktestRequest,
    BacktestResponse,
    PerformanceMetrics,
    TradeStatistics,
)
from app.modules.backtest.service import BacktestService
from app.modules.signals.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["backtest"])


@router.post("", response_model=BacktestResponse, status_code=status.HTTP_201_CREATED)
async def create_and_run_backtest(
    request: BacktestRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create and run a new backtest.

    This endpoint creates a backtest record and runs it synchronously.
    For long-running backtests, use the async endpoint instead.
    """
    service = BacktestService(db)

    # Validate strategy exists
    if not StrategyRegistry.has_strategy(request.strategy_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy '{request.strategy_name}' not found. Available: {StrategyRegistry.list_strategies()}",
        )

    try:
        # Create backtest record
        backtest = await service.create_backtest(current_user.id, request)

        # Run backtest
        backtest = await service.run_backtest(backtest.id)

        return _format_backtest_response(backtest)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Backtest failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest failed: {str(e)}",
        )


@router.get("", response_model=list[BacktestListResponse])
async def list_backtests(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all backtests for the current user."""
    service = BacktestService(db)
    backtests = await service.get_user_backtests(current_user.id, limit, offset)

    return [
        BacktestListResponse(
            id=bt.id,
            strategy_name=bt.strategy_name,
            symbol=bt.symbol,
            status=bt.status,
            total_return=bt.total_return,
            sharpe_ratio=bt.sharpe_ratio,
            total_trades=bt.total_trades,
            win_rate=bt.win_rate,
            created_at=bt.created_at,
            completed_at=bt.completed_at,
        )
        for bt in backtests
    ]


@router.get("/strategies", response_model=list[dict])
async def list_available_strategies():
    """List all available strategies for backtesting."""
    strategies = StrategyRegistry.list_strategies()
    return strategies


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    include_trades: bool = Query(default=True),
):
    """Get a specific backtest by ID."""
    service = BacktestService(db)
    backtest = await service.get_backtest(backtest_id)

    if not backtest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found")

    if backtest.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this backtest",
        )

    return _format_backtest_response(backtest, include_trades)


@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest(
    backtest_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Delete a backtest."""
    service = BacktestService(db)
    deleted = await service.delete_backtest(backtest_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found or not authorized",
        )


def _format_backtest_response(backtest, include_trades: bool = True) -> BacktestResponse:
    """Format backtest model to response schema."""
    from app.modules.backtest.schemas import BacktestTradeResponse

    trades = None
    if include_trades and backtest.trades:
        trades = [
            BacktestTradeResponse(
                id=t.id,
                symbol=t.symbol,
                side=t.side,
                entry_date=t.entry_date,
                entry_price=t.entry_price,
                exit_date=t.exit_date,
                exit_price=t.exit_price,
                quantity=t.quantity,
                pnl=t.pnl,
                pnl_pct=t.pnl_pct,
                is_winner=t.is_winner,
                exit_reason=t.exit_reason,
                signal_indicators=t.signal_indicators,
            )
            for t in backtest.trades
        ]

    return BacktestResponse(
        id=backtest.id,
        user_id=backtest.user_id,
        strategy_name=backtest.strategy_name,
        symbol=backtest.symbol,
        timeframe=backtest.timeframe,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        initial_capital=backtest.initial_capital,
        final_capital=backtest.final_capital,
        strategy_params=backtest.strategy_params,
        status=backtest.status,
        error_message=backtest.error_message,
        performance=PerformanceMetrics(
            total_return=backtest.total_return,
            annualized_return=backtest.annualized_return,
            sharpe_ratio=backtest.sharpe_ratio,
            sortino_ratio=backtest.sortino_ratio,
            max_drawdown=backtest.max_drawdown,
            calmar_ratio=backtest.calmar_ratio,
        ),
        trade_stats=TradeStatistics(
            total_trades=backtest.total_trades,
            winning_trades=backtest.winning_trades,
            losing_trades=backtest.losing_trades,
            win_rate=backtest.win_rate,
            profit_factor=backtest.profit_factor,
            avg_win=backtest.avg_win,
            avg_loss=backtest.avg_loss,
            avg_trade=backtest.avg_trade,
            largest_win=backtest.largest_win,
            largest_loss=backtest.largest_loss,
        ),
        equity_curve=backtest.equity_curve,
        drawdown_curve=backtest.drawdown_curve,
        trades=trades,
        created_at=backtest.created_at,
        started_at=backtest.started_at,
        completed_at=backtest.completed_at,
    )
