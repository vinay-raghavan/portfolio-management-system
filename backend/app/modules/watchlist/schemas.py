"""Pydantic schemas for watchlist module."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class WatchlistItemCreate(BaseModel):
    """Schema for adding item to watchlist."""

    symbol: str = Field(min_length=1, max_length=20)
    notes: str | None = None


class WatchlistItemResponse(BaseModel):
    """Schema for watchlist item response."""

    id: str
    symbol: str
    notes: str | None
    sort_order: int = 0
    added_at: datetime
    # Enriched with market data
    current_price: Decimal | None = None
    change: Decimal | None = None
    change_pct: Decimal | None = None

    model_config = {"from_attributes": True}


class WatchlistCreate(BaseModel):
    """Schema for creating a watchlist."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class WatchlistUpdate(BaseModel):
    """Schema for updating a watchlist."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class WatchlistResponse(BaseModel):
    """Schema for watchlist response."""

    id: str
    name: str
    description: str | None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime
    items: list[WatchlistItemResponse] = []
    items_count: int = 0

    model_config = {"from_attributes": True}


class WatchlistListResponse(BaseModel):
    """Schema for list of watchlists."""

    watchlists: list[WatchlistResponse]


class ReorderItemRequest(BaseModel):
    """Schema for reorder request item."""

    id: str
    sort_order: int


class ReorderWatchlistsRequest(BaseModel):
    """Schema for reordering watchlists."""

    items: list[ReorderItemRequest]


class ReorderWatchlistItemsRequest(BaseModel):
    """Schema for reordering items within a watchlist."""

    items: list[ReorderItemRequest]
