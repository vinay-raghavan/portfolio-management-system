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

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/portfolio"
    SKIP_DB_INIT: bool = False  # Skip database initialization on startup

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # External APIs
    POLYGON_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""

    # Market Data
    DEFAULT_MARKET: str = "US"  # US | IN
    DATA_REFRESH_INTERVAL_SECONDS: int = 60

    # Provider Configuration
    DATA_PROVIDER: str = "yahoo"  # yahoo | nse | angelone
    BROKER_TYPE: str = "paper"  # paper | angelone | dhan

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

