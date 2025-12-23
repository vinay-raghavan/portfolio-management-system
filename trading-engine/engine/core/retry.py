"""Retry logic with exponential backoff for transient failures."""

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


# Exception types that should trigger retries
TRANSIENT_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    asyncio.TimeoutError,
    OSError,
)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    exceptions: tuple[type[Exception], ...] = TRANSIENT_EXCEPTIONS,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for adding retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    )


def with_async_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    exceptions: tuple[type[Exception], ...] = TRANSIENT_EXCEPTIONS,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Async decorator for adding retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on

    Returns:
        Decorated async function with retry logic
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_random_exponential(multiplier=min_wait, max=max_wait),
                retry=retry_if_exception_type(exceptions),
                reraise=True,
            ):
                with attempt:
                    result = await func(*args, **kwargs)
                    return result
            # This should never be reached, but satisfies type checker
            raise RuntimeError("Retry loop exited unexpectedly")

        return wrapper

    return decorator


async def retry_async(
    coro_func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    exceptions: tuple[type[Exception], ...] = TRANSIENT_EXCEPTIONS,
    **kwargs: Any,
) -> Any:
    """Execute an async function with retry logic.

    Args:
        coro_func: Async function to execute
        *args: Positional arguments to pass to the function
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Result of the function call

    Raises:
        RetryError: If all retry attempts fail
    """
    last_exception: Exception | None = None

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    ):
        with attempt:
            return await coro_func(*args, **kwargs)

    raise last_exception or RuntimeError("Retry failed")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 60.0,
        exceptions: tuple[type[Exception], ...] = TRANSIENT_EXCEPTIONS,
    ):
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.exceptions = exceptions


# Pre-configured retry configurations
DATA_PROVIDER_RETRY = RetryConfig(max_attempts=3, min_wait=1.0, max_wait=30.0)
BROKER_RETRY = RetryConfig(max_attempts=2, min_wait=0.5, max_wait=10.0)
DATABASE_RETRY = RetryConfig(max_attempts=3, min_wait=0.5, max_wait=15.0)

