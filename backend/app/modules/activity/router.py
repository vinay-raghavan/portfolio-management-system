"""Activity module API routes."""

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.modules.activity.schemas import (
    ActivityLogListResponse,
    ActivityLogResponse,
    ActivityMarkReadRequest,
    ActivityMarkReadResponse,
    ActivityUnreadCountResponse,
)
from app.modules.activity.service import ActivityService

router = APIRouter()


@router.get("", response_model=ActivityLogListResponse)
async def get_activities(
    db: DbSession,
    current_user: CurrentUser,
    category: str | None = Query(None, description="Filter by category"),
    activity_type: str | None = Query(None, description="Filter by activity type"),
    severity: str | None = Query(None, description="Filter by severity"),
    is_read: bool | None = Query(None, description="Filter by read status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> ActivityLogListResponse:
    """Get paginated activity feed for the current user.

    Returns activities sorted by most recent first, with optional filters.
    """
    service = ActivityService(db)
    activities, total, unread_count = await service.get_activities(
        user_id=current_user.id,
        category=category,
        activity_type=activity_type,
        severity=severity,
        is_read=is_read,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return ActivityLogListResponse(
        activities=[ActivityLogResponse.model_validate(a) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=ActivityUnreadCountResponse)
async def get_unread_count(
    db: DbSession,
    current_user: CurrentUser,
) -> ActivityUnreadCountResponse:
    """Get count of unread activities for the current user.

    Useful for notification badges.
    """
    service = ActivityService(db)
    unread_count = await service.get_unread_count(user_id=current_user.id)
    return ActivityUnreadCountResponse(unread_count=unread_count)


@router.post("/mark-read", response_model=ActivityMarkReadResponse)
async def mark_activities_read(
    request: ActivityMarkReadRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ActivityMarkReadResponse:
    """Mark activities as read.

    Either provide specific activity_ids or set mark_all=True.
    """
    service = ActivityService(db)
    marked_count = await service.mark_as_read(
        user_id=current_user.id,
        activity_ids=request.activity_ids,
        mark_all=request.mark_all,
    )
    await db.commit()
    return ActivityMarkReadResponse(marked_count=marked_count)


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=ActivityLogListResponse,
)
async def get_activities_by_entity(
    entity_type: str,
    entity_id: str,
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> ActivityLogListResponse:
    """Get activities for a specific entity.

    Useful for viewing activity history of an order, position, strategy, etc.
    """
    service = ActivityService(db)
    activities, total = await service.get_activities_by_entity(
        user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        page=page,
        page_size=page_size,
    )

    # Get unread count
    unread_count = await service.get_unread_count(user_id=current_user.id)
    total_pages = (total + page_size - 1) // page_size

    return ActivityLogListResponse(
        activities=[ActivityLogResponse.model_validate(a) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        unread_count=unread_count,
    )
