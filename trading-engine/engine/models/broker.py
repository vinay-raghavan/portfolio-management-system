"""Broker credential database model.

Mirrors the backend model for reading encrypted broker credentials.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.core.database import Base
from engine.core.encryption import decrypt_value


class BrokerType(str, Enum):
    """Supported broker types."""

    FYERS = "fyers"
    ANGELONE = "angelone"
    DHAN = "dhan"
    ZERODHA = "zerodha"


class BrokerCredential(Base):
    """Encrypted broker credentials for a user.

    Stores OAuth credentials and access tokens for broker integrations.
    Sensitive fields are encrypted at rest using AES-128-CBC (Fernet).
    """

    __tablename__ = "broker_credentials"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    broker_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Client ID (not encrypted - used for identification)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Encrypted sensitive fields
    secret_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # OAuth configuration
    redirect_uri: Mapped[str] = mapped_column(String(500), nullable=False)

    # Token metadata
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BrokerCredential {self.broker_type} for user {self.user_id[:8]}...>"

    @property
    def access_token(self) -> str | None:
        """Decrypt and return the access token."""
        if not self.access_token_encrypted:
            return None
        return decrypt_value(self.access_token_encrypted)

    @property
    def is_connected(self) -> bool:
        """Check if broker has valid access token."""
        if not self.access_token_encrypted:
            return False
        if self.token_expires_at and self.token_expires_at < datetime.now(
            self.token_expires_at.tzinfo
        ):
            return False
        return True
