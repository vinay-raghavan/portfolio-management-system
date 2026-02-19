"""Activity log database models."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ActivityType(str, Enum):
    """Types of activities that can be logged."""

    # Auth
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"  # nosec B105 - enum value, not a password

    # Trading
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_MODIFIED = "ORDER_MODIFIED"

    # Portfolio
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"

    # Algo
    STRATEGY_CREATED = "STRATEGY_CREATED"
    STRATEGY_STARTED = "STRATEGY_STARTED"
    STRATEGY_STOPPED = "STRATEGY_STOPPED"
    STRATEGY_DELETED = "STRATEGY_DELETED"
    KILL_SWITCH_ACTIVATED = "KILL_SWITCH_ACTIVATED"
    CIRCUIT_BREAKER_TRIGGERED = "CIRCUIT_BREAKER_TRIGGERED"

    # Risk
    RISK_LIMIT_BREACHED = "RISK_LIMIT_BREACHED"
    RISK_LIMIT_UPDATED = "RISK_LIMIT_UPDATED"
    MARGIN_CALL = "MARGIN_CALL"

    # Broker
    BROKER_CONNECTED = "BROKER_CONNECTED"
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"
    BROKER_ERROR = "BROKER_ERROR"

    # Settings
    SETTINGS_UPDATED = "SETTINGS_UPDATED"
    WATCHLIST_UPDATED = "WATCHLIST_UPDATED"
    ALERT_CREATED = "ALERT_CREATED"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"


class ActivityCategory(str, Enum):
    """Categories for grouping activities."""

    AUTH = "auth"
    TRADING = "trading"
    PORTFOLIO = "portfolio"
    ALGO = "algo"
    RISK = "risk"
    BROKER = "broker"
    SETTINGS = "settings"


class ActivitySeverity(str, Enum):
    """Severity levels for activities."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActivityLog(Base):
    """Activity log model for user-facing activity feed.

    Records all significant user actions and system events for auditing
    and user notification purposes.
    """

    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        index=True,
    )

    # Activity details
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Entity reference
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Additional context
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Severity/importance
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ActivitySeverity.INFO.value
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Client info
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_activity_logs_user_created", "user_id", "created_at"),
        Index("ix_activity_logs_user_type", "user_id", "activity_type"),
        Index("ix_activity_logs_user_category", "user_id", "category"),
        Index("ix_activity_logs_entity", "entity_type", "entity_id"),
        Index("ix_activity_logs_user_unread", "user_id", "is_read"),
    )
