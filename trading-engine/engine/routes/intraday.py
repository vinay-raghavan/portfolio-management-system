"""Intraday position management routes.

This module provides endpoints for:
- Auto square-off of INTRADAY positions before market close
- Checking remaining intraday positions
- Manual square-off triggers
"""

import logging
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.config import settings
from engine.core.database import get_db
from engine.models.algo import AlgoPosition, PositionStatus, StrategyProductType
from engine.providers.data import DataProvider, get_data_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["intraday"])


def verify_internal_api_key(x_internal_key: Annotated[str, Header()]) -> str:
    """Verify the internal API key for worker-to-engine communication."""
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )
    return x_internal_key


class SquareOffResult(BaseModel):
    """Result of intraday square-off operation."""

    positions_closed: int
    total_pnl: float
    positions: list[dict]
    errors: list[str]


class IntradayPositionCount(BaseModel):
    """Count of remaining intraday positions."""

    count: int
    positions: list[dict]


@router.post("/square-off-intraday", response_model=SquareOffResult)
async def square_off_intraday_positions(
    db: Annotated[AsyncSession, Depends(get_db)],
    data_provider: Annotated[DataProvider, Depends(get_data_provider)],
    _api_key: Annotated[str, Depends(verify_internal_api_key)],
) -> SquareOffResult:
    """Auto square-off all INTRADAY positions.

    This endpoint is called by the Celery worker at 3:15 PM IST to close
    all INTRADAY positions before market close.

    Steps:
    1. Find all OPEN positions with product_type=INTRADAY
    2. Fetch current prices for each symbol
    3. Close each position at market price
    4. Update funds (release margin, credit/debit P&L)
    5. Return summary of closed positions
    """
    from engine.algo.position_tracker import PositionTracker

    logger.info("Starting intraday auto square-off")

    # Query all OPEN or PARTIAL intraday positions (PARTIAL = partially closed)
    query = select(AlgoPosition).where(
        AlgoPosition.status.in_([PositionStatus.OPEN, PositionStatus.PARTIAL]),
        AlgoPosition.product_type == StrategyProductType.INTRADAY,
    )
    result = await db.execute(query)
    intraday_positions = result.scalars().all()

    if not intraday_positions:
        logger.info("No intraday positions to square off")
        return SquareOffResult(
            positions_closed=0,
            total_pnl=0.0,
            positions=[],
            errors=[],
        )

    logger.info(f"Found {len(intraday_positions)} intraday positions to square off")

    # Group positions by user
    positions_by_user: dict[str, list[AlgoPosition]] = {}
    for pos in intraday_positions:
        if pos.user_id not in positions_by_user:
            positions_by_user[pos.user_id] = []
        positions_by_user[pos.user_id].append(pos)

    closed_positions = []
    errors = []
    total_pnl = Decimal("0")

    # Get current prices for all symbols
    symbols = list({pos.symbol for pos in intraday_positions})
    current_prices: dict[str, Decimal] = {}
    try:
        for symbol in symbols:
            quote = await data_provider.get_quote(symbol)
            if quote and quote.price:
                current_prices[symbol] = Decimal(str(quote.price))
    except Exception as e:
        logger.error(f"Failed to fetch prices for square-off: {e}")
        return SquareOffResult(
            positions_closed=0,
            total_pnl=0.0,
            positions=[],
            errors=[f"Failed to fetch prices: {e!s}"],
        )

    # Close positions for each user
    position_tracker = PositionTracker(db)

    for user_id, user_positions in positions_by_user.items():
        for position in user_positions:
            try:
                current_price = current_prices.get(position.symbol)
                if not current_price:
                    errors.append(f"No price for {position.symbol}")
                    continue

                # Close the position
                close_result = await position_tracker.close_position(
                    strategy_id=position.strategy_id,
                    user_id=user_id,
                    symbol=position.symbol,
                    quantity=position.remaining_quantity,
                    exit_price=current_price,
                )

                if close_result is None:
                    errors.append(f"No open position found for {position.symbol}")
                    continue

                closed_positions.append(
                    {
                        "symbol": position.symbol,
                        "quantity": position.remaining_quantity,
                        "entry_price": float(position.entry_price),
                        "exit_price": float(current_price),
                        "pnl": float(close_result.realized_pnl),
                        "user_id": user_id[:8],
                    }
                )
                total_pnl += close_result.realized_pnl

                logger.info(
                    f"Squared off {position.symbol}: "
                    f"qty={position.remaining_quantity}, pnl={close_result.realized_pnl}"
                )

            except Exception as e:
                error_msg = f"Failed to close {position.symbol}: {e!s}"
                logger.error(error_msg)
                errors.append(error_msg)

    await db.commit()

    logger.info(
        f"Intraday square-off complete: "
        f"{len(closed_positions)} positions closed, total P&L: {total_pnl}"
    )

    return SquareOffResult(
        positions_closed=len(closed_positions),
        total_pnl=float(total_pnl),
        positions=closed_positions,
        errors=errors,
    )


@router.get("/intraday-positions-count", response_model=IntradayPositionCount)
async def get_intraday_positions_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    _api_key: Annotated[str, Depends(verify_internal_api_key)],
) -> IntradayPositionCount:
    """Get count of remaining INTRADAY positions.

    This endpoint is used for safety checks after market close
    to verify all intraday positions have been squared off.
    """
    query = select(AlgoPosition).where(
        AlgoPosition.status.in_([PositionStatus.OPEN, PositionStatus.PARTIAL]),
        AlgoPosition.product_type == StrategyProductType.INTRADAY,
    )
    result = await db.execute(query)
    positions = result.scalars().all()

    position_list = [
        {
            "symbol": pos.symbol,
            "quantity": pos.remaining_quantity,
            "entry_price": float(pos.entry_price),
            "user_id": pos.user_id[:8],
        }
        for pos in positions
    ]

    return IntradayPositionCount(
        count=len(positions),
        positions=position_list,
    )
