"""Redis connection management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as redis

from engine.config import settings

# Create Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Dependency to get Redis client."""
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.aclose()


@asynccontextmanager
async def get_redis_context() -> AsyncGenerator[redis.Redis, None]:
    """Context manager for Redis client."""
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.aclose()


async def check_redis_health() -> bool:
    """Check Redis connectivity."""
    try:
        client = redis.Redis(connection_pool=redis_pool)
        await client.ping()
        await client.aclose()
        return True
    except Exception:
        return False


async def close_redis_pool() -> None:
    """Close the Redis connection pool."""
    await redis_pool.disconnect()

