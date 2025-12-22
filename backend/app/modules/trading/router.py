"""Trading API routes."""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession, CurrentUser
from app.modules.trading.schemas import OrderCreate, OrderResponse, OrderListResponse
from app.modules.trading.service import TradingService, OrderValidationError
from app.modules.data.service import MarketDataService

router = APIRouter()


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
    orders, total_count = await service.get_orders(
        current_user.id, status_filter, page, page_size
    )

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
