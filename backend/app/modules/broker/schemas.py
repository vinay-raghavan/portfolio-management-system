"""Pydantic schemas for broker integration API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class BrokerType(str, Enum):
    """Supported broker types."""

    FYERS = "fyers"
    ANGELONE = "angelone"
    DHAN = "dhan"
    ZERODHA = "zerodha"


class BrokerCredentialCreate(BaseModel):
    """Schema for creating/updating broker credentials."""

    broker_type: BrokerType
    client_id: str = Field(..., min_length=1, max_length=255, description="Broker client/app ID")
    secret_key: str = Field(..., min_length=1, description="Broker secret key (will be encrypted)")
    redirect_uri: str = Field(..., description="OAuth redirect URI")


class BrokerCredentialResponse(BaseModel):
    """Schema for broker credential response (sensitive fields masked)."""

    id: str
    broker_type: str
    client_id: str  # Masked for security
    redirect_uri: str
    is_connected: bool
    is_active: bool
    token_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class BrokerCredentialStatus(BaseModel):
    """Schema for broker connection status."""

    broker_type: str
    is_configured: bool
    is_connected: bool
    is_active: bool
    client_id: str | None = None  # Masked
    last_used_at: datetime | None = None
    token_expires_at: datetime | None = None


class BrokerAuthUrlResponse(BaseModel):
    """Schema for OAuth authorization URL response."""

    auth_url: str
    broker_type: str
    message: str = "Redirect user to auth_url to complete OAuth flow"


class BrokerCallbackRequest(BaseModel):
    """Schema for OAuth callback request."""

    auth_code: str = Field(..., description="Authorization code from OAuth redirect")
    state: str | None = Field(None, description="OAuth state parameter for verification")


class BrokerCallbackResponse(BaseModel):
    """Schema for OAuth callback response."""

    success: bool
    message: str
    broker_type: str
    is_connected: bool


class BrokerDisconnectResponse(BaseModel):
    """Schema for broker disconnect response."""

    success: bool
    message: str
    broker_type: str


class BrokerListResponse(BaseModel):
    """Schema for listing all broker integrations."""

    brokers: list[BrokerCredentialStatus]
