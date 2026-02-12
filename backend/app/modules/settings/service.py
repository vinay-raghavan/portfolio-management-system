"""User settings service layer."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.broker.models import BrokerCredential
from app.modules.settings.models import UserSettings
from app.modules.settings.schemas import DataProviderType, UserSettingsUpdate

logger = logging.getLogger(__name__)


class UserSettingsService:
    """Service for managing user settings."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_settings(self, user_id: str) -> UserSettings:
        """Get user settings, creating defaults if not exists."""
        result = await self.db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        settings = result.scalar_one_or_none()

        if not settings:
            # Create default settings for user
            settings = UserSettings(user_id=user_id)
            self.db.add(settings)
            await self.db.flush()
            logger.info(f"Created default settings for user {user_id[:8]}...")

        return settings

    async def update_settings(self, user_id: str, data: UserSettingsUpdate) -> UserSettings:
        """Update user settings."""
        settings = await self.get_settings(user_id)

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                # Convert enum to string value for database
                if hasattr(value, "value"):
                    setattr(settings, field, value.value)
                else:
                    setattr(settings, field, value)

        logger.info(f"Updated settings for user {user_id[:8]}...: {list(update_data.keys())}")
        return settings

    async def is_provider_available(
        self, user_id: str, provider: DataProviderType
    ) -> tuple[bool, str | None]:
        """Check if a data provider is available for the user.

        Returns:
            Tuple of (is_available, message)
        """
        if provider == DataProviderType.YAHOO:
            return True, None

        if provider == DataProviderType.NSE:
            return True, None

        if provider == DataProviderType.FYERS:
            # Check if user has Fyers credentials configured and connected
            result = await self.db.execute(
                select(BrokerCredential).where(
                    BrokerCredential.user_id == user_id,
                    BrokerCredential.broker_type == "fyers",
                )
            )
            cred = result.scalar_one_or_none()

            if not cred:
                return (
                    False,
                    "Fyers not configured. Go to Settings → Broker Integrations to set up.",
                )

            if not cred.access_token_encrypted:
                return False, "Fyers not connected. Complete the OAuth flow to use Fyers data."

            return True, "Using your Fyers account for real-time data"

        return False, f"Unknown provider: {provider}"

    async def get_user_data_provider(
        self, user_id: str
    ) -> tuple[DataProviderType, bool, str | None]:
        """Get user's preferred data provider and its availability.

        Returns:
            Tuple of (provider, is_available, message)
        """
        settings = await self.get_settings(user_id)
        provider = DataProviderType(settings.data_provider)
        is_available, message = await self.is_provider_available(user_id, provider)
        return provider, is_available, message

    async def get_user_research_data_provider(
        self, user_id: str
    ) -> tuple[DataProviderType, bool, str | None]:
        """Get user's preferred research/fundamental data provider and its availability.

        Returns:
            Tuple of (provider, is_available, message)
        """
        settings = await self.get_settings(user_id)
        provider = DataProviderType(settings.research_data_provider)
        is_available, message = await self.is_provider_available(user_id, provider)
        return provider, is_available, message
