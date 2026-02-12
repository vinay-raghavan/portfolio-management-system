"""User settings database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class UserSettings(Base):
    """User settings and preferences.

    Stores per-user configuration including data provider preference.
    Each user has exactly one settings record (created on first access).
    """

    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Data provider preference for real-time quotes
    # Options: "yahoo" (default), "fyers", "nse", etc.
    data_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="yahoo")

    # Data provider for research/fundamental data
    # Options: "yahoo" (default - best for fundamentals), "fyers", "nse"
    research_data_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="yahoo")

    # Default market (IN, US, etc.)
    default_market: Mapped[str] = mapped_column(String(10), nullable=False, default="IN")

    # Display preferences (can extend later)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="system")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<UserSettings user_id={self.user_id} provider={self.data_provider}>"
