"""Fyers OAuth2 authentication handler.

Fyers uses OAuth2 for authentication. The flow is:
1. Generate auth URL and redirect user to Fyers login
2. User logs in and Fyers redirects back with auth_code
3. Exchange auth_code for access_token
4. Use access_token for API calls
"""

import logging
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class FyersCredentials:
    """Fyers API credentials configuration."""

    client_id: str  # APP_ID from Fyers API dashboard (format: XXXXX-100)
    secret_key: str  # Secret key from Fyers API dashboard
    redirect_uri: str  # OAuth redirect URL registered in Fyers dashboard
    access_token: str | None = None  # Access token (set after OAuth flow)
    log_path: str = ""  # Optional path for Fyers SDK logs


class FyersAuthHandler:
    """Handles Fyers OAuth2 authentication flow.

    Usage:
        1. Create handler with credentials
        2. Call generate_auth_url() to get login URL
        3. Redirect user to login URL
        4. After redirect, call exchange_auth_code(auth_code) to get access token
        5. Use access_token for API calls
    """

    def __init__(
        self,
        credentials: FyersCredentials,
        on_token_received: Callable[[str], None] | None = None,
    ):
        """Initialize Fyers auth handler.

        Args:
            credentials: Fyers API credentials
            on_token_received: Optional callback when access token is received
        """
        self.credentials = credentials
        self.on_token_received = on_token_received
        self._session_model = None

    def _get_session_model(self):
        """Lazily create Fyers SessionModel."""
        if self._session_model is None:
            try:
                from fyers_apiv3 import fyersModel

                self._session_model = fyersModel.SessionModel(
                    client_id=self.credentials.client_id,
                    redirect_uri=self.credentials.redirect_uri,
                    response_type="code",
                    state="portfolio_management_system",
                    secret_key=self.credentials.secret_key,
                    grant_type="authorization_code",
                )
            except ImportError as e:
                logger.error(f"fyers-apiv3 package not installed: {e}")
                raise ImportError(
                    "fyers-apiv3 package is required. Install with: pip install fyers-apiv3"
                ) from e
        return self._session_model

    def generate_auth_url(self) -> str:
        """Generate OAuth2 authorization URL.

        Returns:
            URL to redirect user for Fyers login
        """
        session = self._get_session_model()
        auth_url = session.generate_authcode()
        logger.info(f"Generated Fyers auth URL: {auth_url}")
        return auth_url

    def exchange_auth_code(self, auth_code: str) -> str:
        """Exchange authorization code for access token.

        Args:
            auth_code: Authorization code received from Fyers redirect

        Returns:
            Access token for API calls

        Raises:
            ValueError: If token exchange fails
        """
        session = self._get_session_model()
        session.set_token(auth_code)
        response = session.generate_token()

        if "access_token" not in response:
            error_msg = response.get("message", "Unknown error during token exchange")
            logger.error(f"Fyers token exchange failed: {response}")
            raise ValueError(f"Failed to get access token: {error_msg}")

        access_token = response["access_token"]
        self.credentials.access_token = access_token

        if self.on_token_received:
            self.on_token_received(access_token)

        logger.info("Successfully obtained Fyers access token")
        return access_token

    def get_full_access_token(self) -> str | None:
        """Get full access token in format required by Fyers API.

        Returns:
            Access token in format "client_id:access_token", or None if not authenticated
        """
        if not self.credentials.access_token:
            return None
        return f"{self.credentials.client_id}:{self.credentials.access_token}"

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid access token."""
        return bool(self.credentials.access_token)


def create_auth_handler_from_env() -> FyersAuthHandler:
    """Create FyersAuthHandler from environment variables.

    Expected environment variables:
        - FYERS_CLIENT_ID: APP_ID from Fyers dashboard
        - FYERS_SECRET_KEY: Secret key from Fyers dashboard
        - FYERS_REDIRECT_URI: OAuth redirect URL
        - FYERS_ACCESS_TOKEN: (Optional) Pre-existing access token
        - FYERS_LOG_PATH: (Optional) Path for Fyers SDK logs

    Returns:
        Configured FyersAuthHandler
    """
    import os

    credentials = FyersCredentials(
        client_id=os.getenv("FYERS_CLIENT_ID", ""),
        secret_key=os.getenv("FYERS_SECRET_KEY", ""),
        redirect_uri=os.getenv("FYERS_REDIRECT_URI", "http://localhost:8000/api/v1/auth/fyers/callback"),
        access_token=os.getenv("FYERS_ACCESS_TOKEN", "") or None,
        log_path=os.getenv("FYERS_LOG_PATH", ""),
    )

    if not credentials.client_id or not credentials.secret_key:
        logger.warning(
            "Fyers credentials not configured. Set FYERS_CLIENT_ID and FYERS_SECRET_KEY environment variables."
        )

    return FyersAuthHandler(credentials)

