"""Tests for TimeWindowValidator."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from shared.utils.time_window import TimeWindowValidator


class TestTimeWindowValidator:
    """Test cases for TimeWindowValidator."""

    @pytest.fixture
    def validator(self) -> TimeWindowValidator:
        """Create a validator instance."""
        return TimeWindowValidator()

    @pytest.fixture
    def india_tz(self) -> ZoneInfo:
        """Return India timezone."""
        return ZoneInfo("Asia/Kolkata")

    # Tests for is_within_window

    def test_no_time_window_always_valid(self, validator: TimeWindowValidator):
        """If no time window is set, should always be valid."""
        is_valid, reason = validator.is_within_window(start_time=None, end_time=None)
        assert is_valid is True
        assert reason == ""

    def test_within_window(self, validator: TimeWindowValidator, india_tz: ZoneInfo):
        """Test time within trading window."""
        # Set window from 09:45 to 15:15
        start_time = time(9, 45)
        end_time = time(15, 15)

        # Mock time at 11:00 on a Tuesday (weekday=1)
        mock_now = datetime(2026, 2, 24, 11, 0, 0, tzinfo=india_tz)  # Tuesday

        is_valid, reason = validator.is_within_window(
            start_time=start_time,
            end_time=end_time,
            timezone="Asia/Kolkata",
            active_days=[0, 1, 2, 3, 4],
            now=mock_now,
        )
        assert is_valid is True
        assert reason == ""

    def test_before_window(self, validator: TimeWindowValidator, india_tz: ZoneInfo):
        """Test time before trading window opens."""
        start_time = time(9, 45)
        end_time = time(15, 15)

        # Mock time at 09:00 (before window)
        mock_now = datetime(2026, 2, 24, 9, 0, 0, tzinfo=india_tz)

        is_valid, reason = validator.is_within_window(
            start_time=start_time,
            end_time=end_time,
            now=mock_now,
        )
        assert is_valid is False
        assert "Before trading window" in reason
        assert "09:45" in reason

    def test_after_window(self, validator: TimeWindowValidator, india_tz: ZoneInfo):
        """Test time after trading window closes."""
        start_time = time(9, 45)
        end_time = time(15, 15)

        # Mock time at 16:00 (after window)
        mock_now = datetime(2026, 2, 24, 16, 0, 0, tzinfo=india_tz)

        is_valid, reason = validator.is_within_window(
            start_time=start_time,
            end_time=end_time,
            now=mock_now,
        )
        assert is_valid is False
        assert "After trading window" in reason
        assert "15:15" in reason

    def test_inactive_day(self, validator: TimeWindowValidator, india_tz: ZoneInfo):
        """Test time on an inactive trading day (Saturday)."""
        start_time = time(9, 45)
        end_time = time(15, 15)

        # Mock time on Saturday (weekday=5)
        mock_now = datetime(2026, 2, 28, 11, 0, 0, tzinfo=india_tz)  # Saturday

        is_valid, reason = validator.is_within_window(
            start_time=start_time,
            end_time=end_time,
            active_days=[0, 1, 2, 3, 4],  # Mon-Fri
            now=mock_now,
        )
        assert is_valid is False
        assert "Not an active trading day" in reason
        assert "Saturday" in reason

    def test_only_start_time(self, validator: TimeWindowValidator, india_tz: ZoneInfo):
        """Test with only start time set."""
        start_time = time(9, 45)

        # Before start
        mock_now = datetime(2026, 2, 24, 9, 0, 0, tzinfo=india_tz)
        is_valid, _ = validator.is_within_window(start_time=start_time, end_time=None, now=mock_now)
        assert is_valid is False

        # After start
        mock_now = datetime(2026, 2, 24, 10, 0, 0, tzinfo=india_tz)
        is_valid, _ = validator.is_within_window(start_time=start_time, end_time=None, now=mock_now)
        assert is_valid is True

    def test_only_end_time(self, validator: TimeWindowValidator, india_tz: ZoneInfo):
        """Test with only end time set."""
        end_time = time(15, 15)

        # Before end
        mock_now = datetime(2026, 2, 24, 14, 0, 0, tzinfo=india_tz)
        is_valid, _ = validator.is_within_window(start_time=None, end_time=end_time, now=mock_now)
        assert is_valid is True

        # After end
        mock_now = datetime(2026, 2, 24, 16, 0, 0, tzinfo=india_tz)
        is_valid, _ = validator.is_within_window(start_time=None, end_time=end_time, now=mock_now)
        assert is_valid is False

    def test_invalid_timezone_falls_back(self, validator: TimeWindowValidator):
        """Test that invalid timezone falls back to default."""
        is_valid, _ = validator.is_within_window(
            start_time=None,
            end_time=None,
            timezone="Invalid/Timezone",
        )
        assert is_valid is True  # No window set, should still be valid

    # Tests for time_until_window_opens

    def test_time_until_window_opens_before_start(
        self, validator: TimeWindowValidator, india_tz: ZoneInfo
    ):
        """Test time until window opens when before start time."""
        start_time = time(9, 45)
        mock_now = datetime(2026, 2, 24, 9, 0, 0, tzinfo=india_tz)

        result = validator.time_until_window_opens(start_time=start_time, now=mock_now)
        assert result == timedelta(minutes=45)

    def test_time_until_window_opens_after_start(
        self, validator: TimeWindowValidator, india_tz: ZoneInfo
    ):
        """Test time until window opens when window is already open."""
        start_time = time(9, 45)
        mock_now = datetime(2026, 2, 24, 10, 0, 0, tzinfo=india_tz)

        result = validator.time_until_window_opens(start_time=start_time, now=mock_now)
        # Should calculate time until next day's start
        expected = timedelta(hours=23, minutes=45)
        assert result == expected

    # Tests for time_until_window_closes

    def test_time_until_window_closes_within_window(
        self, validator: TimeWindowValidator, india_tz: ZoneInfo
    ):
        """Test time until window closes when within window."""
        end_time = time(15, 15)
        mock_now = datetime(2026, 2, 24, 14, 0, 0, tzinfo=india_tz)

        result = validator.time_until_window_closes(end_time=end_time, now=mock_now)
        assert result == timedelta(hours=1, minutes=15)

    def test_time_until_window_closes_after_close(
        self, validator: TimeWindowValidator, india_tz: ZoneInfo
    ):
        """Test time until window closes when already closed."""
        end_time = time(15, 15)
        mock_now = datetime(2026, 2, 24, 16, 0, 0, tzinfo=india_tz)

        result = validator.time_until_window_closes(end_time=end_time, now=mock_now)
        assert result == timedelta(0)

    # Edge cases

    def test_at_exact_start_time(self, validator: TimeWindowValidator, india_tz: ZoneInfo):
        """Test at exact start time boundary."""
        start_time = time(9, 45)
        end_time = time(15, 15)
        mock_now = datetime(2026, 2, 24, 9, 45, 0, tzinfo=india_tz)

        is_valid, _ = validator.is_within_window(
            start_time=start_time, end_time=end_time, now=mock_now
        )
        assert is_valid is True

    def test_at_exact_end_time(self, validator: TimeWindowValidator, india_tz: ZoneInfo):
        """Test at exact end time boundary."""
        start_time = time(9, 45)
        end_time = time(15, 15)
        mock_now = datetime(2026, 2, 24, 15, 15, 0, tzinfo=india_tz)

        is_valid, _ = validator.is_within_window(
            start_time=start_time, end_time=end_time, now=mock_now
        )
        assert is_valid is True

    def test_weekend_trading_active(self, validator: TimeWindowValidator, india_tz: ZoneInfo):
        """Test weekend trading when explicitly enabled."""
        # Enable weekend trading (Saturday=5, Sunday=6)
        mock_now = datetime(2026, 2, 28, 11, 0, 0, tzinfo=india_tz)  # Saturday

        is_valid, _ = validator.is_within_window(
            start_time=time(9, 0),
            end_time=time(17, 0),
            active_days=[5, 6],  # Weekend only
            now=mock_now,
        )
        assert is_valid is True
