"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str = "Portfolio Management System"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Security - JWT Signing
    # Used for signing JWT tokens. Changing invalidates all active sessions.
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # Security - Credential Encryption (separate from JWT signing)
    # Used for encrypting broker credentials at rest.
    # MUST be different from SECRET_KEY in production!
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    ENCRYPTION_KEY: str = ""
    # Number of PBKDF2 iterations (OWASP 2023 recommends 600,000 for SHA-256)
    ENCRYPTION_ITERATIONS: int = 600_000

    # Database (port 5433 to avoid conflicts with other projects)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/portfolio"
    SKIP_DB_INIT: bool = False  # Skip database initialization on startup

    # Redis (port 6380 to avoid conflicts with other projects)
    REDIS_URL: str = "redis://localhost:6380/0"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # External APIs
    POLYGON_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""

    # Market Data
    DEFAULT_MARKET: str = "IN"  # US | IN
    DATA_REFRESH_INTERVAL_SECONDS: int = 60

    # Provider Configuration
    DATA_PROVIDER: str = "yahoo"  # yahoo | nse | angelone
    BROKER_TYPE: str = "paper"  # paper | angelone | dhan

    # NSE Data Provider Settings
    NSE_RATE_LIMIT_REQUESTS: int = 3  # Max requests per time window
    NSE_RATE_LIMIT_WINDOW: float = 1.0  # Time window in seconds
    NSE_CACHE_TTL_QUOTE: int = 30  # Quote cache TTL in seconds
    NSE_CACHE_TTL_HISTORICAL: int = 3600  # Historical data cache TTL (1 hour)
    NSE_COOKIE_TTL_MINUTES: int = 5  # Cookie refresh interval

    # Paper Trading
    PAPER_TRADING_INITIAL_BALANCE: float = 1000000.0  # ₹10 Lakh default

    # Internal API Key (for worker/service-to-service calls)
    INTERNAL_API_KEY: str = ""

    # Angel One Credentials (for Phase 2)
    ANGEL_API_KEY: str = ""
    ANGEL_CLIENT_ID: str = ""
    ANGEL_PASSWORD: str = ""
    ANGEL_TOTP_SECRET: str = ""

    # Fyers Credentials
    FYERS_CLIENT_ID: str = ""  # APP_ID from Fyers API dashboard (format: XXXXX-100)
    FYERS_SECRET_KEY: str = ""  # Secret key from Fyers API dashboard
    FYERS_REDIRECT_URI: str = (
        "http://localhost:8000/api/v1/auth/fyers/callback"  # OAuth redirect URL
    )
    FYERS_ACCESS_TOKEN: str = ""  # Access token (set after OAuth flow)
    FYERS_LOG_PATH: str = ""  # Optional path for Fyers SDK logs


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
