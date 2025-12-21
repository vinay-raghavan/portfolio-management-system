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

    # Security
    SECRET_KEY: str = "change-this-in-production-use-a-real-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

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

    # Angel One Credentials (for Phase 2)
    ANGEL_API_KEY: str = ""
    ANGEL_CLIENT_ID: str = ""
    ANGEL_PASSWORD: str = ""
    ANGEL_TOTP_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

