"""Broker integration service layer."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.broker.models import BrokerCredential
from app.modules.broker.schemas import BrokerCredentialCreate

logger = logging.getLogger(__name__)


class BrokerService:
    """Service for managing broker credentials and OAuth flows."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_credential(self, user_id: str, broker_type: str) -> BrokerCredential | None:
        """Get broker credential for a user."""
        result = await self.db.execute(
            select(BrokerCredential).where(
                BrokerCredential.user_id == user_id,
                BrokerCredential.broker_type == broker_type,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_credentials(self, user_id: str) -> list[BrokerCredential]:
        """Get all broker credentials for a user."""
        result = await self.db.execute(
            select(BrokerCredential).where(BrokerCredential.user_id == user_id)
        )
        return list(result.scalars().all())

    async def create_or_update_credential(
        self, user_id: str, data: BrokerCredentialCreate
    ) -> BrokerCredential:
        """Create or update broker credentials."""
        existing = await self.get_credential(user_id, data.broker_type.value)

        if existing:
            # Update existing credential
            existing.client_id = data.client_id
            existing.secret_key = data.secret_key  # Uses property setter for encryption
            existing.redirect_uri = data.redirect_uri
            existing.is_active = True
            # Clear access token when credentials change
            existing.access_token = None
            existing.token_expires_at = None
            logger.info(f"Updated {data.broker_type} credentials for user {user_id[:8]}...")
            return existing

        # Create new credential
        credential = BrokerCredential(
            user_id=user_id,
            broker_type=data.broker_type.value,
            client_id=data.client_id,
            secret_key_encrypted="",  # Will be set via property
            redirect_uri=data.redirect_uri,
            is_active=True,
        )
        credential.secret_key = data.secret_key  # Uses property setter for encryption
        self.db.add(credential)
        await self.db.flush()
        logger.info(f"Created {data.broker_type} credentials for user {user_id[:8]}...")
        return credential

    async def update_access_token(
        self,
        user_id: str,
        broker_type: str,
        access_token: str,
        expires_at: datetime | None = None,
    ) -> BrokerCredential | None:
        """Update access token after OAuth callback."""
        credential = await self.get_credential(user_id, broker_type)
        if not credential:
            logger.error(f"No {broker_type} credentials found for user {user_id[:8]}...")
            return None

        credential.access_token = access_token  # Uses property setter for encryption
        credential.token_expires_at = expires_at
        credential.last_used_at = datetime.now(UTC)
        logger.info(f"Updated {broker_type} access token for user {user_id[:8]}...")
        return credential

    async def disconnect_broker(self, user_id: str, broker_type: str) -> bool:
        """Disconnect broker by clearing access token."""
        credential = await self.get_credential(user_id, broker_type)
        if not credential:
            return False

        credential.access_token = None
        credential.token_expires_at = None
        logger.info(f"Disconnected {broker_type} for user {user_id[:8]}...")
        return True

    async def delete_credential(self, user_id: str, broker_type: str) -> bool:
        """Permanently delete broker credentials."""
        credential = await self.get_credential(user_id, broker_type)
        if not credential:
            return False

        await self.db.delete(credential)
        logger.info(f"Deleted {broker_type} credentials for user {user_id[:8]}...")
        return True

    async def mark_last_used(self, user_id: str, broker_type: str) -> None:
        """Update last_used_at timestamp."""
        credential = await self.get_credential(user_id, broker_type)
        if credential:
            credential.last_used_at = datetime.now(UTC)

    async def check_fyers_token_health(self, user_id: str) -> tuple[bool, str]:
        """Check if Fyers access token is still valid.

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        from fyers_apiv3 import fyersModel

        credential = await self.get_credential(user_id, "fyers")
        if not credential:
            return False, "Fyers credentials not configured"

        if not credential.access_token:
            return False, "Not connected - please authenticate"

        try:
            fyers = fyersModel.FyersModel(
                client_id=credential.client_id,
                is_async=False,
                token=credential.access_token,  # Decrypted via property
                log_path="/tmp",  # Use /tmp for Chainguard containers (no write to /app)  # nosec B108
            )

            # Test token by calling get_profile
            response = fyers.get_profile()
            code = response.get("code")

            if code == 200:
                return True, "Token is valid"
            elif code == -16:
                # Invalid or expired token
                return False, "Token expired - please reconnect"
            else:
                return False, f"Token validation failed (code: {code})"

        except Exception as e:
            logger.error(f"Fyers health check error: {e}")
            return False, f"Health check failed: {str(e)}"
