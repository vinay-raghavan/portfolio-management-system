"""Research notes service for CRUD operations."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.models import ResearchNote
from app.modules.research.schemas import ResearchNoteCreate, ResearchNoteUpdate

logger = logging.getLogger(__name__)


class ResearchNoteService:
    """Service for managing user research notes."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_notes(
        self,
        user_id: str,
        symbol: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ResearchNote], int]:
        """Get research notes for a user.

        Args:
            user_id: User ID
            symbol: Optional symbol to filter by
            limit: Maximum number of notes
            offset: Offset for pagination

        Returns:
            Tuple of (notes list, total count)
        """
        query = select(ResearchNote).where(ResearchNote.user_id == user_id)

        if symbol:
            query = query.where(ResearchNote.symbol == symbol.upper())

        # Get total count
        count_result = await self.db.execute(query)
        total_count = len(count_result.scalars().all())

        # Get paginated results
        query = query.order_by(ResearchNote.updated_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        notes = list(result.scalars().all())

        return notes, total_count

    async def get_note(self, user_id: str, note_id: str) -> ResearchNote | None:
        """Get a specific research note.

        Args:
            user_id: User ID
            note_id: Note ID

        Returns:
            ResearchNote or None if not found
        """
        result = await self.db.execute(
            select(ResearchNote).where(
                ResearchNote.id == note_id,
                ResearchNote.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_note(self, user_id: str, data: ResearchNoteCreate) -> ResearchNote:
        """Create a new research note.

        Args:
            user_id: User ID
            data: Note creation data

        Returns:
            Created ResearchNote
        """
        note = ResearchNote(
            user_id=user_id,
            symbol=data.symbol.upper(),
            title=data.title,
            content=data.content,
            rating=data.rating,
            target_price=data.target_price,
            tags=data.tags,
        )
        self.db.add(note)
        await self.db.flush()
        await self.db.refresh(note)
        logger.info(f"Created research note {note.id} for {note.symbol}")
        return note

    async def update_note(
        self,
        user_id: str,
        note_id: str,
        data: ResearchNoteUpdate,
    ) -> ResearchNote | None:
        """Update a research note.

        Args:
            user_id: User ID
            note_id: Note ID
            data: Note update data

        Returns:
            Updated ResearchNote or None if not found
        """
        note = await self.get_note(user_id, note_id)
        if note is None:
            return None

        if data.title is not None:
            note.title = data.title
        if data.content is not None:
            note.content = data.content
        if data.rating is not None:
            note.rating = data.rating
        if data.target_price is not None:
            note.target_price = data.target_price
        if data.tags is not None:
            note.tags = data.tags

        await self.db.flush()
        await self.db.refresh(note)
        logger.info(f"Updated research note {note_id}")
        return note

    async def delete_note(self, user_id: str, note_id: str) -> bool:
        """Delete a research note.

        Args:
            user_id: User ID
            note_id: Note ID

        Returns:
            True if deleted, False if not found
        """
        note = await self.get_note(user_id, note_id)
        if note is None:
            return False

        await self.db.delete(note)
        await self.db.flush()
        logger.info(f"Deleted research note {note_id}")
        return True
