"""Tests for rate limiter."""

import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from app.providers.data.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for token bucket rate limiter."""

    @pytest.fixture
    def limiter(self):
        """Create rate limiter with 5 requests per second."""
        return RateLimiter(max_requests=5, time_window=1.0)

    @pytest.fixture
    def slow_limiter(self):
        """Create rate limiter with 2 requests per second."""
        return RateLimiter(max_requests=2, time_window=1.0)

    def test_limiter_initialization(self, limiter):
        """Test limiter is initialized correctly."""
        assert limiter.max_requests == 5
        assert limiter.time_window == 1.0
        assert limiter._redis is None
        assert limiter._key_prefix == "rate_limit"

    def test_limiter_with_custom_prefix(self):
        """Test limiter with custom key prefix."""
        limiter = RateLimiter(max_requests=5, time_window=1.0, key_prefix="nse")
        assert limiter._key_prefix == "nse"

    @pytest.mark.asyncio
    async def test_acquire_within_limit(self, limiter):
        """Test acquiring tokens within limit."""
        # Should be able to acquire 5 tokens quickly
        for _ in range(5):
            result = await limiter.acquire("test")
            assert result is True

    @pytest.mark.asyncio
    async def test_acquire_exceeds_limit(self, slow_limiter):
        """Test acquiring more tokens than allowed."""
        # Acquire all tokens
        for _ in range(2):
            await slow_limiter.acquire("test")

        # Third should fail
        result = await slow_limiter.acquire("test")
        assert result is False

    @pytest.mark.asyncio
    async def test_tokens_replenish(self, slow_limiter):
        """Test tokens replenish after time window."""
        # Use all tokens
        for _ in range(2):
            await slow_limiter.acquire("test")

        # Wait for replenishment (slightly more than time window)
        await asyncio.sleep(1.1)

        # Should be able to acquire again
        result = await slow_limiter.acquire("test")
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_and_acquire_immediate(self, limiter):
        """Test wait_and_acquire returns immediately when tokens available."""
        start = time.time()
        result = await limiter.wait_and_acquire("test", timeout=5.0)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 0.5  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_wait_and_acquire_waits(self, slow_limiter):
        """Test wait_and_acquire waits when no tokens available."""
        # Use all tokens
        for _ in range(2):
            await slow_limiter.acquire("test")

        start = time.time()
        result = await slow_limiter.wait_and_acquire("test", timeout=5.0)
        elapsed = time.time() - start

        assert result is True
        assert elapsed >= 0.4  # Should have waited for replenishment

    @pytest.mark.asyncio
    async def test_wait_and_acquire_timeout(self, slow_limiter):
        """Test wait_and_acquire times out."""
        # Use all tokens
        for _ in range(2):
            await slow_limiter.acquire("test")

        # Set very short timeout
        result = await slow_limiter.wait_and_acquire("test", timeout=0.1)
        assert result is False

    @pytest.mark.asyncio
    async def test_different_keys_independent(self, slow_limiter):
        """Test different keys have independent limits."""
        # Use all tokens for key1
        for _ in range(2):
            await slow_limiter.acquire("key1")

        # key2 should still have tokens
        result = await slow_limiter.acquire("key2")
        assert result is True

    def test_reset_specific_key(self, slow_limiter):
        """Test resetting rate limiter for a specific key."""
        # Add some tokens to track
        slow_limiter._tokens["test"] = [time.time()]
        slow_limiter._tokens["other"] = [time.time()]

        # Reset specific key
        slow_limiter.reset("test")

        # test key should be removed
        assert "test" not in slow_limiter._tokens
        # other key should still exist
        assert "other" in slow_limiter._tokens

    def test_reset_all_keys(self, slow_limiter):
        """Test resetting all rate limiter keys."""
        # Add some tokens to track
        slow_limiter._tokens["test1"] = [time.time()]
        slow_limiter._tokens["test2"] = [time.time()]

        # Reset all
        slow_limiter.reset()

        assert len(slow_limiter._tokens) == 0


class TestRateLimiterWithRedis:
    """Tests for rate limiter with Redis backend.

    Note: These tests verify the limiter is initialized correctly with Redis.
    The actual Redis operations are complex to mock due to pipeline patterns,
    so we verify the fallback behavior works correctly.
    """

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        return MagicMock()

    @pytest.fixture
    def redis_limiter(self, mock_redis):
        """Create rate limiter with mock Redis."""
        return RateLimiter(
            max_requests=5,
            time_window=1.0,
            redis_client=mock_redis,
            key_prefix="test",
        )

    def test_redis_limiter_initialization(self, redis_limiter, mock_redis):
        """Test Redis limiter is initialized correctly."""
        assert redis_limiter._redis is mock_redis
        assert redis_limiter._key_prefix == "test"

    @pytest.mark.asyncio
    async def test_redis_fallback_on_error(self, redis_limiter, mock_redis):
        """Test Redis limiter falls back to allow on error."""
        # Mock pipeline that raises an error
        mock_redis.pipeline.side_effect = Exception("Redis connection error")

        # Should fall back to allowing the request
        result = await redis_limiter.acquire("api")

        assert result is True  # Falls back to allow

    @pytest.mark.asyncio
    async def test_redis_uses_pipeline(self, redis_limiter, mock_redis):
        """Test Redis limiter uses pipeline for atomic operations."""
        # Set up mock pipeline that will eventually fail (triggering fallback)
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock(return_value=mock_pipe)
        mock_pipe.zcard = MagicMock(return_value=mock_pipe)
        mock_pipe.zadd = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = MagicMock(side_effect=Exception("Pipe error"))
        mock_redis.pipeline.return_value = mock_pipe

        result = await redis_limiter.acquire("api")

        # Should have tried to use pipeline
        mock_redis.pipeline.assert_called()
        # Should fall back to allow on error
        assert result is True

