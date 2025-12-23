"""Configuration settings for Trading Engine."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Trading Engine configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/portfolio"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    INTERNAL_API_KEY: str = "internal-worker-key"

    # Data Provider
    DATA_PROVIDER: str = "yahoo"
    DEFAULT_MARKET: str = "IN"

    # Broker
    BROKER_TYPE: str = "paper"
    PAPER_TRADING_INITIAL_BALANCE: float = 1000000.0

    # Logging
    LOG_LEVEL: str = "INFO"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Circuit Breaker
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 300

    # Execution
    MAX_CONCURRENT_EXECUTIONS: int = 10
    EXECUTION_TIMEOUT: int = 300


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
