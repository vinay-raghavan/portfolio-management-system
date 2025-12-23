"""Distributed locking for strategy execution using Redis.

Prevents duplicate strategy executions when multiple workers run concurrently.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import uuid4

from redis.asyncio import Redis

from engine.config import settings
from engine.core.redis import get_redis_context

logger = logging.getLogger(__name__)

# Redis key patterns
STRATEGY_LOCK_KEY = "lock:strategy:{strategy_id}"
EXECUTION_LOCK_KEY = "lock:execution:{execution_id}"
SCHEDULED_RUN_LOCK_KEY = "lock:scheduled_run"

# Default lock settings
DEFAULT_LOCK_TIMEOUT = 300  # 5 minutes
DEFAULT_LOCK_RETRY_DELAY = 0.1  # 100ms
DEFAULT_LOCK_MAX_RETRIES = 50  # 5 seconds max wait


class DistributedLock:
    """Redis-based distributed lock."""

    def __init__(
        self,
        redis: Redis,
        key: str,
        timeout: int = DEFAULT_LOCK_TIMEOUT,
        lock_id: str | None = None,
    ):
        """Initialize a distributed lock.

        Args:
            redis: Redis client
            key: Lock key
            timeout: Lock expiration in seconds
            lock_id: Unique lock identifier (auto-generated if not provided)
        """
        self.redis = redis
        self.key = key
        self.timeout = timeout
        self.lock_id = lock_id or str(uuid4())
        self._acquired = False

    async def acquire(
        self,
        blocking: bool = True,
        max_retries: int = DEFAULT_LOCK_MAX_RETRIES,
        retry_delay: float = DEFAULT_LOCK_RETRY_DELAY,
    ) -> bool:
        """Acquire the lock.

        Args:
            blocking: Whether to wait for the lock
            max_retries: Maximum number of retries (only if blocking)
            retry_delay: Delay between retries in seconds

        Returns:
            True if lock acquired, False otherwise
        """
        for attempt in range(max_retries if blocking else 1):
            # Use SET NX EX for atomic lock acquisition
            acquired = await self.redis.set(
                self.key, self.lock_id, nx=True, ex=self.timeout
            )
            if acquired:
                self._acquired = True
                logger.debug(f"Lock acquired: {self.key}")
                return True

            if not blocking:
                break

            await asyncio.sleep(retry_delay)

        logger.debug(f"Failed to acquire lock: {self.key}")
        return False

    async def release(self) -> bool:
        """Release the lock.

        Only releases if we own the lock (lock_id matches).

        Returns:
            True if lock released, False otherwise
        """
        if not self._acquired:
            return False

        # Lua script for atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self.redis.eval(lua_script, 1, self.key, self.lock_id)
        released = result == 1
        if released:
            self._acquired = False
            logger.debug(f"Lock released: {self.key}")
        return released

    async def extend(self, additional_time: int | None = None) -> bool:
        """Extend the lock's expiration time.

        Args:
            additional_time: Additional seconds (defaults to original timeout)

        Returns:
            True if extended, False if we don't own the lock
        """
        if not self._acquired:
            return False

        extend_time = additional_time or self.timeout

        # Lua script for atomic check-and-extend
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        result = await self.redis.eval(
            lua_script, 1, self.key, self.lock_id, extend_time
        )
        return result == 1

    @property
    def is_acquired(self) -> bool:
        """Check if lock is currently held."""
        return self._acquired


@asynccontextmanager
async def strategy_lock(
    strategy_id: str,
    timeout: int = DEFAULT_LOCK_TIMEOUT,
    blocking: bool = True,
) -> AsyncGenerator[DistributedLock, None]:
    """Context manager for acquiring a strategy execution lock.

    Args:
        strategy_id: Strategy ID to lock
        timeout: Lock expiration in seconds
        blocking: Whether to wait for the lock

    Yields:
        DistributedLock instance

    Raises:
        RuntimeError: If lock cannot be acquired
    """
    async with get_redis_context() as redis:
        key = STRATEGY_LOCK_KEY.format(strategy_id=strategy_id)
        lock = DistributedLock(redis, key, timeout)

        if not await lock.acquire(blocking=blocking):
            raise RuntimeError(f"Could not acquire lock for strategy {strategy_id}")

        try:
            yield lock
        finally:
            await lock.release()


@asynccontextmanager
async def scheduled_run_lock(
    timeout: int = 30,
    blocking: bool = False,
) -> AsyncGenerator[DistributedLock, None]:
    """Context manager for acquiring the scheduled run lock.

    This prevents multiple workers from running scheduled strategies
    at the same time.

    Args:
        timeout: Lock expiration in seconds
        blocking: Whether to wait for the lock

    Yields:
        DistributedLock instance

    Raises:
        RuntimeError: If lock cannot be acquired
    """
    async with get_redis_context() as redis:
        lock = DistributedLock(redis, SCHEDULED_RUN_LOCK_KEY, timeout)

        if not await lock.acquire(blocking=blocking):
            raise RuntimeError("Could not acquire scheduled run lock")

        try:
            yield lock
        finally:
            await lock.release()


async def try_acquire_strategy_lock(
    strategy_id: str,
    timeout: int = DEFAULT_LOCK_TIMEOUT,
) -> tuple[bool, str | None]:
    """Try to acquire a strategy lock without blocking.

    Args:
        strategy_id: Strategy ID to lock
        timeout: Lock expiration in seconds

    Returns:
        Tuple of (acquired, lock_id if acquired else None)
    """
    async with get_redis_context() as redis:
        key = STRATEGY_LOCK_KEY.format(strategy_id=strategy_id)
        lock = DistributedLock(redis, key, timeout)

        if await lock.acquire(blocking=False):
            return True, lock.lock_id
        return False, None


async def release_strategy_lock(strategy_id: str, lock_id: str) -> bool:
    """Release a strategy lock.

    Args:
        strategy_id: Strategy ID
        lock_id: Lock ID from acquisition

    Returns:
        True if released, False otherwise
    """
    async with get_redis_context() as redis:
        key = STRATEGY_LOCK_KEY.format(strategy_id=strategy_id)
        lock = DistributedLock(redis, key, lock_id=lock_id)
        lock._acquired = True  # Mark as acquired so release works
        return await lock.release()

