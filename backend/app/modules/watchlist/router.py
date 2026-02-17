"""Watchlist API routes."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.modules.watchlist.schemas import (
    ReorderWatchlistItemsRequest,
    ReorderWatchlistsRequest,
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistListResponse,
    WatchlistResponse,
    WatchlistUpdate,
)
from app.modules.watchlist.service import WatchlistService

router = APIRouter()


@router.get("", response_model=WatchlistListResponse)
async def get_watchlists(db: DbSession, current_user: CurrentUser) -> WatchlistListResponse:
    """Get all watchlists for the current user."""
    service = WatchlistService(db)
    watchlists = await service.get_watchlists(current_user.id)

    return WatchlistListResponse(
        watchlists=[
            WatchlistResponse(
                id=w.id,
                name=w.name,
                description=w.description,
                sort_order=w.sort_order,
                created_at=w.created_at,
                updated_at=w.updated_at,
                items=[WatchlistItemResponse.model_validate(i) for i in w.items],
                items_count=len(w.items),
            )
            for w in watchlists
        ]
    )


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    data: WatchlistCreate, db: DbSession, current_user: CurrentUser
) -> WatchlistResponse:
    """Create a new watchlist."""
    service = WatchlistService(db)
    watchlist = await service.create_watchlist(current_user.id, data)

    return WatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        description=watchlist.description,
        sort_order=watchlist.sort_order,
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at,
        items=[],
        items_count=0,
    )


@router.get("/{watchlist_id}", response_model=WatchlistResponse)
async def get_watchlist(
    watchlist_id: str, db: DbSession, current_user: CurrentUser
) -> WatchlistResponse:
    """Get a specific watchlist."""
    service = WatchlistService(db)
    watchlist = await service.get_watchlist(current_user.id, watchlist_id)

    if watchlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found",
        )

    return WatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        description=watchlist.description,
        sort_order=watchlist.sort_order,
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at,
        items=[WatchlistItemResponse.model_validate(i) for i in watchlist.items],
        items_count=len(watchlist.items),
    )


@router.patch("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: str, data: WatchlistUpdate, db: DbSession, current_user: CurrentUser
) -> WatchlistResponse:
    """Update a watchlist."""
    service = WatchlistService(db)
    watchlist = await service.update_watchlist(current_user.id, watchlist_id, data)

    if watchlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found",
        )

    return WatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        description=watchlist.description,
        sort_order=watchlist.sort_order,
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at,
        items=[WatchlistItemResponse.model_validate(i) for i in watchlist.items],
        items_count=len(watchlist.items),
    )


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(watchlist_id: str, db: DbSession, current_user: CurrentUser) -> None:
    """Delete a watchlist."""
    service = WatchlistService(db)
    deleted = await service.delete_watchlist(current_user.id, watchlist_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found",
        )


@router.post(
    "/{watchlist_id}/items",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_watchlist_item(
    watchlist_id: str, data: WatchlistItemCreate, db: DbSession, current_user: CurrentUser
) -> WatchlistItemResponse:
    """Add a symbol to a watchlist."""
    service = WatchlistService(db)
    item = await service.add_item(current_user.id, watchlist_id, data)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found",
        )

    return WatchlistItemResponse.model_validate(item)


@router.delete("/{watchlist_id}/items/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watchlist_item(
    watchlist_id: str, symbol: str, db: DbSession, current_user: CurrentUser
) -> None:
    """Remove a symbol from a watchlist."""
    service = WatchlistService(db)
    removed = await service.remove_item(current_user.id, watchlist_id, symbol)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in watchlist",
        )


@router.put("/reorder", response_model=WatchlistListResponse)
async def reorder_watchlists(
    data: ReorderWatchlistsRequest, db: DbSession, current_user: CurrentUser
) -> WatchlistListResponse:
    """Reorder watchlists for the current user."""
    service = WatchlistService(db)
    watchlists = await service.reorder_watchlists(current_user.id, data.items)

    return WatchlistListResponse(
        watchlists=[
            WatchlistResponse(
                id=w.id,
                name=w.name,
                description=w.description,
                sort_order=w.sort_order,
                created_at=w.created_at,
                updated_at=w.updated_at,
                items=[WatchlistItemResponse.model_validate(i) for i in w.items],
                items_count=len(w.items),
            )
            for w in watchlists
        ]
    )


@router.put("/{watchlist_id}/items/reorder", response_model=WatchlistResponse)
async def reorder_watchlist_items(
    watchlist_id: str,
    data: ReorderWatchlistItemsRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> WatchlistResponse:
    """Reorder items within a watchlist."""
    service = WatchlistService(db)
    watchlist = await service.reorder_items(current_user.id, watchlist_id, data.items)

    if watchlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found",
        )

    return WatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        description=watchlist.description,
        sort_order=watchlist.sort_order,
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at,
        items=[WatchlistItemResponse.model_validate(i) for i in watchlist.items],
        items_count=len(watchlist.items),
    )
