"""Watchlist service layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.watchlist.models import Watchlist, WatchlistItem
from app.modules.watchlist.schemas import (
    ReorderItemRequest,
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistUpdate,
)


class WatchlistService:
    """Service class for watchlist operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_watchlists(self, user_id: str) -> list[Watchlist]:
        """Get all watchlists for a user."""
        result = await self.db.execute(
            select(Watchlist)
            .where(Watchlist.user_id == user_id)
            .options(selectinload(Watchlist.items))
            .order_by(Watchlist.sort_order, Watchlist.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_watchlist(self, user_id: str, watchlist_id: str) -> Watchlist | None:
        """Get a specific watchlist."""
        result = await self.db.execute(
            select(Watchlist)
            .where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
            .options(selectinload(Watchlist.items))
        )
        return result.scalar_one_or_none()

    async def create_watchlist(self, user_id: str, data: WatchlistCreate) -> Watchlist:
        """Create a new watchlist."""
        watchlist = Watchlist(
            user_id=user_id,
            name=data.name,
            description=data.description,
        )
        self.db.add(watchlist)
        await self.db.flush()
        await self.db.refresh(watchlist)
        return watchlist

    async def update_watchlist(
        self, user_id: str, watchlist_id: str, data: WatchlistUpdate
    ) -> Watchlist | None:
        """Update a watchlist."""
        watchlist = await self.get_watchlist(user_id, watchlist_id)
        if watchlist is None:
            return None

        if data.name is not None:
            watchlist.name = data.name
        if data.description is not None:
            watchlist.description = data.description

        await self.db.flush()
        await self.db.refresh(watchlist)
        return watchlist

    async def delete_watchlist(self, user_id: str, watchlist_id: str) -> bool:
        """Delete a watchlist."""
        watchlist = await self.get_watchlist(user_id, watchlist_id)
        if watchlist is None:
            return False

        await self.db.delete(watchlist)
        await self.db.flush()
        return True

    async def add_item(
        self, user_id: str, watchlist_id: str, data: WatchlistItemCreate
    ) -> WatchlistItem | None:
        """Add an item to a watchlist."""
        watchlist = await self.get_watchlist(user_id, watchlist_id)
        if watchlist is None:
            return None

        # Check if item already exists
        for item in watchlist.items:
            if item.symbol == data.symbol.upper():
                return item  # Already exists

        item = WatchlistItem(
            watchlist_id=watchlist_id,
            symbol=data.symbol.upper(),
            notes=data.notes,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def remove_item(self, user_id: str, watchlist_id: str, symbol: str) -> bool:
        """Remove an item from a watchlist."""
        watchlist = await self.get_watchlist(user_id, watchlist_id)
        if watchlist is None:
            return False

        for item in watchlist.items:
            if item.symbol == symbol.upper():
                await self.db.delete(item)
                await self.db.flush()
                return True

        return False

    async def reorder_watchlists(
        self, user_id: str, items: list[ReorderItemRequest]
    ) -> list[Watchlist]:
        """Reorder watchlists for a user."""
        # Get all watchlists for the user
        watchlists = await self.get_watchlists(user_id)
        watchlist_map = {w.id: w for w in watchlists}

        # Update sort_order for each watchlist
        for item in items:
            if item.id in watchlist_map:
                watchlist_map[item.id].sort_order = item.sort_order

        await self.db.flush()
        # Return updated list
        return await self.get_watchlists(user_id)

    async def reorder_items(
        self, user_id: str, watchlist_id: str, items: list[ReorderItemRequest]
    ) -> Watchlist | None:
        """Reorder items within a watchlist."""
        watchlist = await self.get_watchlist(user_id, watchlist_id)
        if watchlist is None:
            return None

        item_map = {i.id: i for i in watchlist.items}

        # Update sort_order for each item
        for item in items:
            if item.id in item_map:
                item_map[item.id].sort_order = item.sort_order

        await self.db.flush()
        await self.db.refresh(watchlist)
        return watchlist
