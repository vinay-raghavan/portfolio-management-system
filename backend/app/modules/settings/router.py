"""User settings API routes."""

import logging

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.modules.settings.schemas import (
    AvailableProvidersResponse,
    CurrencyType,
    DataProviderInfo,
    DataProviderType,
    MarketType,
    ThemeType,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.modules.settings.service import UserSettingsService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=UserSettingsResponse)
async def get_user_settings(
    db: DbSession,
    current_user: CurrentUser,
) -> UserSettingsResponse:
    """Get current user's settings."""
    service = UserSettingsService(db)
    settings = await service.get_settings(current_user.id)

    # Check if selected provider is available
    is_available, message = await service.is_provider_available(
        current_user.id, DataProviderType(settings.data_provider)
    )

    return UserSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        data_provider=DataProviderType(settings.data_provider),
        default_market=MarketType(settings.default_market),
        currency=CurrencyType(settings.currency),
        theme=ThemeType(settings.theme),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
        data_provider_available=is_available,
        data_provider_message=message,
    )


@router.patch("", response_model=UserSettingsResponse)
async def update_user_settings(
    data: UserSettingsUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> UserSettingsResponse:
    """Update current user's settings."""
    service = UserSettingsService(db)
    settings = await service.update_settings(current_user.id, data)

    # Check if selected provider is available
    is_available, message = await service.is_provider_available(
        current_user.id, DataProviderType(settings.data_provider)
    )

    return UserSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        data_provider=DataProviderType(settings.data_provider),
        default_market=MarketType(settings.default_market),
        currency=CurrencyType(settings.currency),
        theme=ThemeType(settings.theme),
        created_at=settings.created_at,
        updated_at=settings.updated_at,
        data_provider_available=is_available,
        data_provider_message=message,
    )


@router.get("/providers", response_model=AvailableProvidersResponse)
async def get_available_providers(
    db: DbSession,
    current_user: CurrentUser,
) -> AvailableProvidersResponse:
    """Get list of available data providers for current user."""
    service = UserSettingsService(db)
    settings = await service.get_settings(current_user.id)

    providers = []

    # Yahoo Finance - always available
    providers.append(
        DataProviderInfo(
            id=DataProviderType.YAHOO,
            name="Yahoo Finance",
            description="Free market data with 15-minute delay for Indian markets",
            requires_auth=False,
            is_available=True,
            message=None,
        )
    )

    # Fyers - requires OAuth
    fyers_available, fyers_message = await service.is_provider_available(
        current_user.id, DataProviderType.FYERS
    )
    providers.append(
        DataProviderInfo(
            id=DataProviderType.FYERS,
            name="Fyers",
            description="Real-time market data via your Fyers trading account",
            requires_auth=True,
            is_available=fyers_available,
            message=fyers_message,
        )
    )

    # NSE - available but limited
    providers.append(
        DataProviderInfo(
            id=DataProviderType.NSE,
            name="NSE India",
            description="Direct NSE data (may have rate limits)",
            requires_auth=False,
            is_available=True,
            message=None,
        )
    )

    return AvailableProvidersResponse(
        providers=providers,
        current=DataProviderType(settings.data_provider),
    )
