"""User settings Pydantic schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DataProviderType(str, Enum):
    """Available data provider types."""

    YAHOO = "yahoo"
    FYERS = "fyers"
    NSE = "nse"


class ThemeType(str, Enum):
    """Available theme options."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class CurrencyType(str, Enum):
    """Available currency options."""

    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class MarketType(str, Enum):
    """Available market options."""

    IN = "IN"
    US = "US"


class UserSettingsResponse(BaseModel):
    """User settings response schema."""

    id: str
    user_id: str
    data_provider: DataProviderType
    default_market: MarketType
    currency: CurrencyType
    theme: ThemeType
    created_at: datetime
    updated_at: datetime

    # Additional computed fields
    data_provider_available: bool = Field(
        default=True,
        description="Whether the selected data provider is available (e.g., Fyers needs OAuth)",
    )
    data_provider_message: str | None = Field(
        default=None,
        description="Message about the data provider status",
    )

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings."""

    data_provider: DataProviderType | None = None
    default_market: MarketType | None = None
    currency: CurrencyType | None = None
    theme: ThemeType | None = None


class DataProviderInfo(BaseModel):
    """Information about a data provider."""

    id: DataProviderType
    name: str
    description: str
    requires_auth: bool
    is_available: bool
    message: str | None = None


class AvailableProvidersResponse(BaseModel):
    """Response with list of available data providers."""

    providers: list[DataProviderInfo]
    current: DataProviderType
