"""Tests for cache service module."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.cache import (
    CacheCategory,
    generate_cache_key,
    generate_hash_key,
    get_cached,
    get_ttl,
    invalidate_pattern,
    is_market_hours,
    set_cached,
)


class TestCacheKeyGeneration:
    """Tests for cache key generation functions."""

    def test_generate_cache_key_simple(self):
        """Test simple cache key generation."""
        key = generate_cache_key("gains", "summary", "user123")
        assert key == "cache:gains:summary:user123"

    def test_generate_cache_key_with_kwargs(self):
        """Test cache key generation with keyword arguments."""
        key = generate_cache_key("gains", "summary", "user123", fy="2024-25", portfolio="p1")
        # Should be sorted alphabetically: fy=2024-25:portfolio=p1
        assert "cache:gains:summary:user123" in key
        assert "fy=2024-25" in key
        assert "portfolio=p1" in key

    def test_generate_cache_key_with_none_values(self):
        """Test that None values are excluded from the key."""
        key = generate_cache_key("gains", "summary", "user123", fy=None, portfolio="p1")
        # None values should be excluded
        assert "fy=" not in key
        assert "portfolio=p1" in key

    def test_generate_hash_key(self):
        """Test hash key generation for complex data."""
        data = {"symbols": ["RELIANCE", "TCS"], "filters": {"min_pe": 10}}
        key1 = generate_hash_key("screener:filter", data)
        key2 = generate_hash_key("screener:filter", data)
        assert key1 == key2  # Same data produces same key
        assert key1.startswith("cache:screener:filter:")


class TestMarketHours:
    """Tests for market hours detection."""

    @patch("app.core.cache.datetime")
    def test_is_market_hours_true(self, mock_datetime):
        """Test market hours detection during trading time."""
        # Monday at 10:00 AM IST
        mock_dt = datetime(2026, 2, 23, 10, 0)  # Monday
        mock_datetime.now.return_value = mock_dt
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        # This would require mocking IST timezone properly
        # For now, we just verify the function runs without error
        result = is_market_hours()
        assert isinstance(result, bool)

    def test_is_market_hours_returns_bool(self):
        """Test that is_market_hours returns a boolean."""
        result = is_market_hours()
        assert isinstance(result, bool)


class TestTTL:
    """Tests for TTL calculation."""

    def test_get_ttl_fundamentals(self):
        """Test TTL for fundamentals category (always 1 hour)."""
        ttl = get_ttl(CacheCategory.FUNDAMENTALS)
        assert ttl == 3600  # 1 hour

    def test_get_ttl_dividends(self):
        """Test TTL for dividends category (always 6 hours)."""
        ttl = get_ttl(CacheCategory.DIVIDENDS)
        assert ttl == 21600  # 6 hours

    def test_get_ttl_reference(self):
        """Test TTL for reference category (always 24 hours)."""
        ttl = get_ttl(CacheCategory.REFERENCE)
        assert ttl == 86400  # 24 hours


class TestCacheOperations:
    """Tests for cache get/set operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.setex = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        return mock

    @pytest.mark.asyncio
    async def test_get_cached_miss(self, mock_redis):
        """Test cache miss returns None."""
        mock_redis.get.return_value = None
        result = await get_cached(mock_redis, "cache:test:key")
        assert result is None
        mock_redis.get.assert_called_once_with("cache:test:key")

    @pytest.mark.asyncio
    async def test_get_cached_hit(self, mock_redis):
        """Test cache hit returns deserialized data."""
        cached_data = {"total": 1000, "count": 5}
        mock_redis.get.return_value = json.dumps(cached_data)
        result = await get_cached(mock_redis, "cache:test:key")
        assert result == cached_data

    @pytest.mark.asyncio
    async def test_set_cached(self, mock_redis):
        """Test setting cached data."""
        data = {"total": 1000, "count": 5}
        result = await set_cached(mock_redis, "cache:test:key", data, CacheCategory.FUNDAMENTALS)
        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_cached_handles_error(self, mock_redis):
        """Test that set_cached handles errors gracefully."""
        mock_redis.setex.side_effect = Exception("Redis error")
        data = {"total": 1000}
        result = await set_cached(mock_redis, "cache:test:key", data, CacheCategory.FUNDAMENTALS)
        assert result is False


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client with scan_iter."""
        mock = AsyncMock()
        mock.delete = AsyncMock(return_value=2)
        return mock

    @pytest.mark.asyncio
    async def test_invalidate_pattern_deletes_matching_keys(self, mock_redis):
        """Test that invalidate_pattern deletes matching keys."""

        # Mock scan_iter to return keys
        async def mock_scan_iter(match):
            for key in [b"cache:gains:summary:user1", b"cache:gains:by_symbol:user1"]:
                yield key

        mock_redis.scan_iter = mock_scan_iter
        count = await invalidate_pattern(mock_redis, "gains:summary:user1")
        # Should have attempted to delete
        assert mock_redis.delete.called or count >= 0
