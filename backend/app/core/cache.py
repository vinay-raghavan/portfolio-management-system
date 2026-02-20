"""Redis caching utilities for the portfolio management system.

Provides reusable caching functions with market-hours-aware TTL strategies.
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class CacheCategory(str, Enum):
    """Cache categories with different TTL strategies."""

    # Database aggregations - moderate staleness OK
    DB_AGGREGATION = "db_aggregation"  # 15min market, 1hr off

    # External API calls - expensive, cache longer
    EXTERNAL_API = "external_api"  # 5min market, 30min off

    # Fundamental data - changes infrequently
    FUNDAMENTALS = "fundamentals"  # 1hr always

    # Dividend data - changes very infrequently
    DIVIDENDS = "dividends"  # 6hr always

    # Reference data - rarely changes
    REFERENCE = "reference"  # 24hr always

    # Screener results - existing pattern
    SCREENER = "screener"  # 5min market, 1hr off


# TTL values in seconds: (market_hours, off_market)
TTL_CONFIG: dict[CacheCategory, tuple[int, int]] = {
    CacheCategory.DB_AGGREGATION: (900, 3600),  # 15min, 1hr
    CacheCategory.EXTERNAL_API: (300, 1800),  # 5min, 30min
    CacheCategory.FUNDAMENTALS: (3600, 3600),  # 1hr always
    CacheCategory.DIVIDENDS: (21600, 21600),  # 6hr always
    CacheCategory.REFERENCE: (86400, 86400),  # 24hr always
    CacheCategory.SCREENER: (300, 3600),  # 5min, 1hr
}


def is_market_hours() -> bool:
    """Check if we're in Indian market hours (9:15 AM - 3:30 PM IST, weekdays)."""
    now = datetime.now(UTC)

    # Convert to IST (UTC+5:30)
    ist_hour = (now.hour + 5) % 24
    ist_minute = now.minute + 30
    if ist_minute >= 60:
        ist_hour = (ist_hour + 1) % 24
        ist_minute -= 60

    # Check weekday (0=Monday, 6=Sunday)
    if now.weekday() >= 5:  # Weekend
        return False

    # Market: 9:15 AM - 3:30 PM IST
    current_minutes = ist_hour * 60 + ist_minute
    market_open = 9 * 60 + 15  # 9:15 AM = 555 minutes
    market_close = 15 * 60 + 30  # 3:30 PM = 930 minutes

    return market_open <= current_minutes <= market_close


def get_ttl(category: CacheCategory) -> int:
    """Get TTL in seconds based on cache category and market hours."""
    market_ttl, off_market_ttl = TTL_CONFIG[category]
    return market_ttl if is_market_hours() else off_market_ttl


def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """Generate a cache key from prefix and arguments.

    Args:
        prefix: Cache key prefix (e.g., "gains:summary")
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key (sorted)

    Returns:
        Cache key string like "cache:gains:summary:user123:2025-26"
    """
    parts = [str(arg) for arg in args if arg is not None]

    if kwargs:
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())
        parts.extend(f"{k}={v}" for k, v in sorted_kwargs if v is not None)

    key_suffix = ":".join(parts) if parts else ""
    return f"cache:{prefix}:{key_suffix}" if key_suffix else f"cache:{prefix}"


def generate_hash_key(prefix: str, data: dict | list | BaseModel) -> str:
    """Generate a cache key with MD5 hash for complex data structures.

    Args:
        prefix: Cache key prefix
        data: Data to hash (dict, list, or Pydantic model)

    Returns:
        Cache key with hash suffix
    """
    if isinstance(data, BaseModel):
        data_str = data.model_dump_json(exclude_none=True)
    else:
        data_str = json.dumps(data, sort_keys=True, default=str)

    # MD5 used only for cache key generation, not security
    hash_val = hashlib.md5(data_str.encode(), usedforsecurity=False).hexdigest()[:12]
    return f"cache:{prefix}:{hash_val}"


async def get_cached(redis: Redis, key: str) -> Any | None:
    """Get cached value, returns None if not found or on error."""
    try:
        data = await redis.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Cache get error for {key}: {e}")
    return None


async def set_cached(
    redis: Redis,
    key: str,
    value: Any,
    category: CacheCategory,
) -> bool:
    """Set cached value with category-based TTL."""
    try:
        ttl = get_ttl(category)
        data = json.dumps(value, default=str)
        await redis.setex(key, ttl, data)
        return True
    except Exception as e:
        logger.warning(f"Cache set error for {key}: {e}")
        return False


async def invalidate_pattern(redis: Redis, pattern: str) -> int:
    """Invalidate all keys matching a pattern. Returns count deleted."""
    try:
        keys = []
        async for key in redis.scan_iter(match=f"cache:{pattern}*"):
            keys.append(key)
        if keys:
            return await redis.delete(*keys)
    except Exception as e:
        logger.warning(f"Cache invalidation error for {pattern}: {e}")
    return 0
