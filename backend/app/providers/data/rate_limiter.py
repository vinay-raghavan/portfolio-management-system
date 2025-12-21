"""Rate limiter for API requests.

Provides a simple token bucket rate limiter to avoid hitting API rate limits.
Supports both in-memory and Redis-based rate limiting.
"""

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter.
    
    Limits requests to a maximum number per time window.
    Uses a simple in-memory implementation by default.
    """

    def __init__(
        self,
        max_requests: int = 3,
        time_window: float = 1.0,
        redis_client: Any = None,
        key_prefix: str = "rate_limit",
    ):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per time window
            time_window: Time window in seconds
            redis_client: Optional Redis client for distributed rate limiting
            key_prefix: Prefix for Redis keys
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._tokens: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str = "default") -> bool:
        """Acquire a rate limit token.
        
        Args:
            key: Rate limit bucket key (e.g., endpoint or symbol)
            
        Returns:
            True if token acquired, False if rate limited
        """
        if self._redis:
            return await self._acquire_redis(key)
        return await self._acquire_memory(key)

    async def _acquire_memory(self, key: str) -> bool:
        """In-memory rate limiting."""
        async with self._lock:
            now = time.time()
            
            # Get or create token bucket
            if key not in self._tokens:
                self._tokens[key] = []
            
            # Remove expired tokens
            self._tokens[key] = [
                t for t in self._tokens[key]
                if now - t < self.time_window
            ]
            
            # Check if we can add a new request
            if len(self._tokens[key]) < self.max_requests:
                self._tokens[key].append(now)
                return True
            
            return False

    async def _acquire_redis(self, key: str) -> bool:
        """Redis-based distributed rate limiting."""
        try:
            redis_key = f"{self._key_prefix}:{key}"
            now = time.time()
            window_start = now - self.time_window
            
            # Use Redis sorted set for sliding window
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {str(now): now})
            pipe.expire(redis_key, int(self.time_window) + 1)
            
            results = await pipe.execute()
            count = results[1]
            
            if count < self.max_requests:
                return True
            
            # Remove the just-added entry since we're rate limited
            await self._redis.zrem(redis_key, str(now))
            return False
            
        except Exception as e:
            logger.warning(f"Redis rate limit error: {e}, falling back to allow")
            return True

    async def wait_and_acquire(self, key: str = "default", timeout: float = 10.0) -> bool:
        """Wait until a token is available and acquire it.
        
        Args:
            key: Rate limit bucket key
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if token acquired, False if timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if await self.acquire(key):
                return True
            # Wait a fraction of the time window before retrying
            await asyncio.sleep(self.time_window / self.max_requests)
        return False

    def reset(self, key: str | None = None) -> None:
        """Reset rate limit counters.
        
        Args:
            key: Specific key to reset, or None to reset all
        """
        if key:
            self._tokens.pop(key, None)
        else:
            self._tokens.clear()


# Default rate limiter for NSE (3 requests per second)
nse_rate_limiter = RateLimiter(max_requests=3, time_window=1.0, key_prefix="nse")

