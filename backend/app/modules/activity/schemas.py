"""Activity module schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.modules.activity.models import ActivityCategory, ActivitySeverity, ActivityType


class ActivityLogBase(BaseModel):
    """Base schema for activity logs."""

    activity_type: ActivityType
    category: ActivityCategory
    title: str
    description: str
    entity_type: str | None = None
    entity_id: str | None = None
    extra_data: dict[str, Any] | None = None
    severity: ActivitySeverity = ActivitySeverity.INFO


class ActivityLogCreate(ActivityLogBase):
    """Schema for creating an activity log entry."""

    ip_address: str | None = None
    user_agent: str | None = None


class ActivityLogResponse(BaseModel):
    """Schema for a single activity log response."""

    id: str
    user_id: str
    activity_type: str
    category: str
    title: str
    description: str
    entity_type: str | None = None
    entity_id: str | None = None
    extra_data: dict[str, Any] | None = None
    severity: str
    is_read: bool
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityLogListResponse(BaseModel):
    """Schema for paginated activity log list."""

    activities: list[ActivityLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    unread_count: int


class ActivityUnreadCountResponse(BaseModel):
    """Schema for unread count response."""

    unread_count: int


class ActivityMarkReadRequest(BaseModel):
    """Schema for marking activities as read."""

    activity_ids: list[str] | None = None
    mark_all: bool = False


class ActivityMarkReadResponse(BaseModel):
    """Schema for mark read response."""

    marked_count: int
