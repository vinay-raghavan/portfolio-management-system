"""Broker credential database models.

Stores encrypted broker credentials per user for OAuth-based broker integrations.
Sensitive fields (secret_key, access_token) are encrypted at rest using Fernet.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.encryption import decrypt_value, encrypt_value, mask_sensitive_value


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

    Security:
    - client_id is stored in plaintext (not sensitive, used for identification)
    - secret_key_encrypted is AES-encrypted at rest
    - access_token_encrypted is AES-encrypted at rest
    - Encryption uses app SECRET_KEY - ensure it's strong in production
    """

    __tablename__ = "broker_credentials"

    __table_args__ = (UniqueConstraint("user_id", "broker_type", name="uq_user_broker"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BrokerCredential {self.broker_type} for user {self.user_id[:8]}...>"

    # Property accessors for encrypted fields

    @property
    def secret_key(self) -> str:
        """Decrypt and return the secret key."""
        return decrypt_value(self.secret_key_encrypted)

    @secret_key.setter
    def secret_key(self, value: str) -> None:
        """Encrypt and store the secret key."""
        self.secret_key_encrypted = encrypt_value(value)

    @property
    def access_token(self) -> str | None:
        """Decrypt and return the access token."""
        if not self.access_token_encrypted:
            return None
        return decrypt_value(self.access_token_encrypted)

    @access_token.setter
    def access_token(self, value: str | None) -> None:
        """Encrypt and store the access token."""
        if value is None:
            self.access_token_encrypted = None
        else:
            self.access_token_encrypted = encrypt_value(value)

    @property
    def is_connected(self) -> bool:
        """Check if broker has valid access token."""
        if not self.access_token_encrypted:
            return False
        return not (
            self.token_expires_at
            and self.token_expires_at < datetime.now(self.token_expires_at.tzinfo)
        )

    @property
    def masked_client_id(self) -> str:
        """Get masked client ID for display."""
        return mask_sensitive_value(self.client_id, visible_chars=4)

    @property
    def masked_secret_key(self) -> str:
        """Get masked secret key for display (never expose full value)."""
        return "*" * 12  # Never show any part of secret key


class BrokerAPILog(Base):
    """Log of all broker API interactions for debugging and audit.

    Records request/response details, latency, and outcome for each API call.
    Sensitive data (tokens, secrets) is masked before logging.
    """

    __tablename__ = "broker_api_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Broker info
    broker_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Request details
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)  # GET, POST, etc.
    request_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Response details
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Performance
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Context
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # place_order, cancel, etc.
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # order, position
    reference_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Timestamps
    request_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_broker_api_logs_user_date", "user_id", "request_at"),
        Index("ix_broker_api_logs_broker_action", "broker_type", "action"),
        Index("ix_broker_api_logs_reference", "reference_type", "reference_id"),
    )

    def __repr__(self) -> str:
        status = "OK" if self.is_success else "FAIL"
        return f"<BrokerAPILog {self.broker_type}.{self.action} [{status}]>"
