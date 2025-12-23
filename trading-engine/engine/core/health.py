"""Health check utilities."""

from engine.core.database import check_db_health
from engine.core.redis import check_redis_health
from engine.providers.data.factory import check_data_provider_health


async def check_all_health() -> dict[str, str | dict]:
    """Check health of all dependencies."""
    db_healthy = await check_db_health()
    redis_healthy = await check_redis_health()
    data_provider_health = await check_data_provider_health()

    return {
        "database": "ok" if db_healthy else "error",
        "redis": "ok" if redis_healthy else "error",
        "data_provider": data_provider_health,
    }


async def check_critical_health() -> dict[str, str]:
    """Check health of critical dependencies (database and redis only).

    This is used for readiness checks where data provider
    health is not strictly required.
    """
    db_healthy = await check_db_health()
    redis_healthy = await check_redis_health()

    return {
        "database": "ok" if db_healthy else "error",
        "redis": "ok" if redis_healthy else "error",
    }


async def is_ready() -> bool:
    """Check if service is ready to accept requests.

    This only checks critical dependencies (database and redis).
    Data provider health is checked separately.
    """
    health = await check_critical_health()
    return all(status == "ok" for status in health.values())

