"""Trading API routes."""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.modules.data.service import MarketDataService
from app.modules.trading.schemas import (
    OrderCreate,
    OrderFromTemplateCreate,
    OrderListResponse,
    OrderResponse,
    OrderTemplateCreate,
    OrderTemplateListResponse,
    OrderTemplateResponse,
    OrderTemplateUpdate,
)
from app.modules.trading.service import OrderValidationError, TradingService

router = APIRouter()


# Schema for position with SL/TP data
class PositionWithSLTP(BaseModel):
    """Position data for SL/TP/Trailing Stop monitoring."""

    id: str
    user_id: str
    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    trailing_stop_enabled: bool = False
    trailing_stop_pct: Decimal | None = None
    trailing_stop_price: Decimal | None = None
    highest_price_since_entry: Decimal | None = None
    lowest_price_since_entry: Decimal | None = None
    profit_booking_rules: dict | None = None

    model_config = {"from_attributes": True}


class TrailingStopPriceUpdate(BaseModel):
    """Request to update trailing stop price for a position."""

    current_price: Decimal
    is_long: bool = True


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> OrderResponse:
    """Create and execute a new order (paper trading).

    If is_amo=True and market is closed, the order will be queued as an
    After Market Order (AMO) and executed at the next market open.
    """
    from app.modules.trading.models import OrderStatus

    trading_service = TradingService(db)
    market_data_service = MarketDataService()

    # Create the order
    try:
        order = await trading_service.create_order(current_user.id, order_data)
    except OrderValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.detail,
        )

    # For market orders, execute immediately (unless it's an AMO pending order)
    if order_data.order_type.value == "MARKET" and order.status != OrderStatus.AMO_PENDING.value:
        # Get current price
        current_price = await market_data_service.get_current_price(order_data.symbol)
        if current_price is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not get price for {order_data.symbol}",
            )
        order = await trading_service.execute_market_order(order, current_price)

    return OrderResponse.model_validate(order)


@router.get("", response_model=OrderListResponse)
async def get_orders(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> OrderListResponse:
    """Get orders with optional status filter."""
    service = TradingService(db)
    orders, total_count = await service.get_orders(current_user.id, status_filter, page, page_size)

    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.delete("/{order_id}", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> OrderResponse:
    """Cancel a pending or AMO pending order."""
    service = TradingService(db)
    order = await service.cancel_order(current_user.id, order_id)

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or cannot be cancelled",
        )

    return OrderResponse.model_validate(order)


@router.get("/amo", response_model=OrderListResponse)
async def get_amo_orders(
    db: DbSession,
    current_user: CurrentUser,
) -> OrderListResponse:
    """Get all pending AMO (After Market Orders) for the current user."""
    service = TradingService(db)
    orders = await service.get_pending_amo_orders(current_user.id)

    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total_count=len(orders),
        page=1,
        page_size=len(orders),
    )


@router.post("/process-amo-orders")
async def process_amo_orders(
    db: DbSession,
) -> dict:
    """Process all pending AMO orders.

    This endpoint is called by the Celery worker at market open.
    It processes all queued AMO orders for all users.

    Note: This is an internal endpoint, typically called by the scheduler.
    """
    service = TradingService(db)
    result = await service.process_all_amo_orders()
    return result


# ============== SL/TP Monitoring Endpoints (Internal) ==============


@router.get("/positions-with-sl-tp", response_model=list[PositionWithSLTP])
async def get_positions_with_sl_tp(
    db: DbSession,
) -> list[PositionWithSLTP]:
    """Get all positions that have SL/TP, trailing stop, or profit booking rules set.

    This is an internal endpoint used by the Celery worker for SL/TP monitoring.
    Returns positions for all users that need to be monitored.
    """
    from sqlalchemy import or_, select

    from app.modules.portfolio.models import Position

    # Get all positions with SL/TP set, trailing stop enabled, or profit booking rules
    query = select(Position).where(
        Position.quantity > 0,
        or_(
            Position.stop_loss.isnot(None),
            Position.take_profit.isnot(None),
            Position.trailing_stop_enabled == True,  # noqa: E712
            Position.profit_booking_rules.isnot(None),
        ),
    )
    result = await db.execute(query)
    positions = result.scalars().all()

    return [PositionWithSLTP.model_validate(p) for p in positions]


@router.patch("/positions/{position_id}/trailing-stop-price")
async def update_trailing_stop_price(
    db: DbSession,
    position_id: str,
    data: TrailingStopPriceUpdate,
) -> dict:
    """Update the trailing stop price for a position based on current market price.

    This is an internal endpoint used by the Celery worker.
    It updates the trailing stop price (and highest/lowest prices) when the market
    price moves favorably.
    """
    from app.modules.portfolio.service import PortfolioService

    service = PortfolioService(db)
    position = await service.update_trailing_stop_price(
        position_id, data.current_price, data.is_long
    )

    if position:
        await db.commit()
        return {
            "updated": True,
            "trailing_stop_price": str(position.trailing_stop_price),
            "highest_price": str(position.highest_price_since_entry),
            "lowest_price": str(position.lowest_price_since_entry),
        }

    return {"updated": False}


# ============== Order Template Endpoints ==============


@router.post(
    "/templates", response_model=OrderTemplateResponse, status_code=status.HTTP_201_CREATED
)
async def create_template(
    template_data: OrderTemplateCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> OrderTemplateResponse:
    """Create a new order template."""
    service = TradingService(db)
    template = await service.create_template(current_user.id, template_data)
    return OrderTemplateResponse.model_validate(template)


@router.get("/templates", response_model=OrderTemplateListResponse)
async def get_templates(
    db: DbSession,
    current_user: CurrentUser,
    favorites_only: bool = Query(False),
) -> OrderTemplateListResponse:
    """Get all order templates for the current user."""
    service = TradingService(db)
    templates, total_count = await service.get_templates(current_user.id, favorites_only)
    return OrderTemplateListResponse(
        templates=[OrderTemplateResponse.model_validate(t) for t in templates],
        total_count=total_count,
    )


@router.get("/templates/{template_id}", response_model=OrderTemplateResponse)
async def get_template(
    template_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> OrderTemplateResponse:
    """Get a single order template."""
    service = TradingService(db)
    template = await service.get_template(current_user.id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    return OrderTemplateResponse.model_validate(template)


@router.put("/templates/{template_id}", response_model=OrderTemplateResponse)
async def update_template(
    template_id: str,
    template_data: OrderTemplateUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> OrderTemplateResponse:
    """Update an order template."""
    service = TradingService(db)
    template = await service.update_template(current_user.id, template_id, template_data)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    return OrderTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete an order template."""
    service = TradingService(db)
    deleted = await service.delete_template(current_user.id, template_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )


@router.post("/templates/{template_id}/execute", response_model=OrderResponse)
async def execute_template(
    template_id: str,
    data: OrderFromTemplateCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> OrderResponse:
    """Execute an order from a template.

    Creates and executes an order based on the template settings.
    SL/TP are calculated from percentages using the provided current_price.
    """
    from app.modules.trading.service import OrderValidationError

    service = TradingService(db)
    try:
        order = await service.execute_template(
            user_id=current_user.id,
            template_id=template_id,
            current_price=data.current_price,
            quantity_override=data.quantity_override,
        )
        return OrderResponse.model_validate(order)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except OrderValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.detail,
        )
