"""Health check utilities."""

from engine.core.database import check_db_health
from engine.core.redis import check_redis_health


async def check_all_health() -> dict[str, str]:
    """Check health of all dependencies."""
    db_healthy = await check_db_health()
    redis_healthy = await check_redis_health()

    return {
        "database": "ok" if db_healthy else "error",
        "redis": "ok" if redis_healthy else "error",
    }


async def is_ready() -> bool:
    """Check if service is ready to accept requests."""
    health = await check_all_health()
    return all(status == "ok" for status in health.values())

