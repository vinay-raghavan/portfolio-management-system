"""Activity logging service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import desc, func, select, update

from app.modules.activity.models import (
    ActivityCategory,
    ActivityLog,
    ActivitySeverity,
    ActivityType,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ActivityService:
    """Service for managing activity logs."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the activity service.

        Args:
            db: Database session.
        """
        self.db = db

    async def log_activity(
        self,
        user_id: str,
        activity_type: ActivityType,
        category: ActivityCategory,
        title: str,
        description: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        extra_data: dict[str, Any] | None = None,
        severity: ActivitySeverity = ActivitySeverity.INFO,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ActivityLog:
        """Record an activity log entry.

        Args:
            user_id: User ID associated with the activity.
            activity_type: Type of activity.
            category: Category of activity.
            title: Short title for the activity.
            description: Detailed description of the activity.
            entity_type: Type of related entity (e.g., "order", "position").
            entity_id: ID of the related entity.
            extra_data: Additional context data as JSON.
            severity: Severity level of the activity.
            ip_address: Client IP address.
            user_agent: Client user agent string.

        Returns:
            The created ActivityLog entry.
        """
        activity = ActivityLog(
            id=str(uuid4()),
            user_id=user_id,
            activity_type=activity_type.value,
            category=category.value,
            title=title,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            extra_data=extra_data,
            severity=severity.value,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(activity)
        await self.db.flush()

        logger.debug(f"Logged activity: {activity_type.value} for user {user_id}: {title}")
        return activity

    async def get_activities(
        self,
        user_id: str,
        category: str | None = None,
        activity_type: str | None = None,
        severity: str | None = None,
        is_read: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ActivityLog], int, int]:
        """Get paginated activity logs for a user.

        Args:
            user_id: User ID to get activities for.
            category: Optional category filter.
            activity_type: Optional activity type filter.
            severity: Optional severity filter.
            is_read: Optional read status filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Tuple of (activities, total_count, unread_count).
        """
        # Build base query
        query = select(ActivityLog).where(ActivityLog.user_id == user_id)

        # Apply filters
        if category:
            query = query.where(ActivityLog.category == category)
        if activity_type:
            query = query.where(ActivityLog.activity_type == activity_type)
        if severity:
            query = query.where(ActivityLog.severity == severity)
        if is_read is not None:
            query = query.where(ActivityLog.is_read == is_read)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Get unread count
        unread_query = select(func.count()).where(
            ActivityLog.user_id == user_id,
            ActivityLog.is_read == False,  # noqa: E712
        )
        unread_count = await self.db.scalar(unread_query) or 0

        # Apply pagination and ordering
        query = (
            query.order_by(desc(ActivityLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        activities = list(result.scalars().all())

        return activities, total, unread_count

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread activities for a user.

        Args:
            user_id: User ID to get unread count for.

        Returns:
            Number of unread activities.
        """
        query = select(func.count()).where(
            ActivityLog.user_id == user_id,
            ActivityLog.is_read == False,  # noqa: E712
        )
        return await self.db.scalar(query) or 0

    async def mark_as_read(
        self,
        user_id: str,
        activity_ids: list[str] | None = None,
        mark_all: bool = False,
    ) -> int:
        """Mark activities as read.

        Args:
            user_id: User ID owning the activities.
            activity_ids: List of activity IDs to mark as read.
            mark_all: If True, mark all activities as read.

        Returns:
            Number of activities marked as read.
        """
        if mark_all:
            stmt = (
                update(ActivityLog)
                .where(
                    ActivityLog.user_id == user_id,
                    ActivityLog.is_read == False,  # noqa: E712
                )
                .values(is_read=True)
            )
        elif activity_ids:
            stmt = (
                update(ActivityLog)
                .where(
                    ActivityLog.user_id == user_id,
                    ActivityLog.id.in_(activity_ids),
                    ActivityLog.is_read == False,  # noqa: E712
                )
                .values(is_read=True)
            )
        else:
            return 0

        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def get_activities_by_entity(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ActivityLog], int]:
        """Get activities for a specific entity.

        Args:
            user_id: User ID owning the activities.
            entity_type: Type of entity (e.g., "order", "position").
            entity_id: ID of the entity.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Tuple of (activities, total_count).
        """
        query = select(ActivityLog).where(
            ActivityLog.user_id == user_id,
            ActivityLog.entity_type == entity_type,
            ActivityLog.entity_id == entity_id,
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Apply pagination and ordering
        query = (
            query.order_by(desc(ActivityLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        activities = list(result.scalars().all())

        return activities, total
