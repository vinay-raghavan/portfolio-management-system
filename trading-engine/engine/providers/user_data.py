"""User-aware data provider selection for the trading engine.

Resolves data provider per-user based on their settings (yahoo, fyers, etc.)
instead of using the hardcoded global DATA_PROVIDER env var.
"""

import logging
import tempfile

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from engine.models.broker import BrokerCredential
from engine.providers.data import DataProvider, get_data_provider

logger = logging.getLogger(__name__)

# Cache resolved providers per user_id (within a single request cycle)
_provider_cache: dict[str, DataProvider] = {}


async def get_user_data_provider(
    db: AsyncSession,
    user_id: str,
) -> DataProvider:
    """Get the appropriate data provider for a user based on their settings.

    Checks user_settings table for data_provider preference.
    If 'fyers', creates a FyersDataProvider with the user's access token.
    Falls back to the global default (yahoo) if not configured or credentials missing.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        DataProvider instance configured for the user
    """
    # Check cache first
    if user_id in _provider_cache:
        return _provider_cache[user_id]

    # Query user's data_provider setting using raw SQL
    # (no UserSettings model in trading engine)
    result = await db.execute(
        text("SELECT data_provider FROM user_settings WHERE user_id = :uid"),
        {"uid": user_id},
    )
    row = result.first()

    if not row or not row.data_provider:
        logger.debug(f"No data_provider setting for user {user_id[:8]}..., using default")
        provider = get_data_provider()
        _provider_cache[user_id] = provider
        return provider

    provider_setting = row.data_provider

    if provider_setting == "fyers":
        provider = await _create_fyers_provider(db, user_id)
        if provider:
            _provider_cache[user_id] = provider
            return provider
        logger.warning(
            f"Fyers selected but not available for user {user_id[:8]}..., falling back to default"
        )

    if provider_setting == "nse":
        provider = get_data_provider("nse")
        _provider_cache[user_id] = provider
        return provider

    # Default: yahoo
    provider = get_data_provider()
    _provider_cache[user_id] = provider
    return provider


async def _create_fyers_provider(
    db: AsyncSession,
    user_id: str,
) -> DataProvider | None:
    """Create a FyersDataProvider from user's broker credentials.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        FyersDataProvider instance or None if credentials not available
    """
    try:
        from shared.providers.data.fyers import FyersDataProvider
    except ImportError:
        logger.error("FyersDataProvider not available - fyers-apiv3 package not installed")
        return None

    result = await db.execute(
        select(BrokerCredential).where(
            BrokerCredential.user_id == user_id,
            BrokerCredential.broker_type == "fyers",
            BrokerCredential.is_active.is_(True),
        )
    )
    cred = result.scalar_one_or_none()

    if not cred or not cred.access_token_encrypted:
        logger.warning(f"No Fyers credentials found for user {user_id[:8]}...")
        return None

    access_token = cred.access_token
    if not access_token:
        logger.warning(f"Failed to decrypt Fyers token for user {user_id[:8]}...")
        return None

    logger.info(f"Using Fyers data provider for user {user_id[:8]}... (real-time)")
    return FyersDataProvider(
        access_token=access_token,
        client_id=cred.client_id,
        log_path=tempfile.gettempdir(),
    )


def clear_provider_cache(user_id: str | None = None) -> None:
    """Clear cached data providers.

    Args:
        user_id: If provided, clear only for this user. If None, clear all.
    """
    if user_id:
        _provider_cache.pop(user_id, None)
    else:
        _provider_cache.clear()
