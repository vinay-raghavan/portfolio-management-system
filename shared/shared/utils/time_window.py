"""Trading time window validation utilities.

This module provides utilities to validate if the current time falls within
a configured trading time window, supporting timezone-aware comparisons.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# Default market timezone for India
DEFAULT_TIMEZONE = "Asia/Kolkata"

# Default active trading days (Monday=0 through Friday=4)
DEFAULT_ACTIVE_DAYS = [0, 1, 2, 3, 4]


class TimeWindowValidator:
    """Validates if current time is within trading window.

    This class provides methods to check if the current time falls within
    a configured trading window, considering:
    - Start and end times
    - Timezone (IANA format)
    - Active trading days (weekday indices)
    """

    def is_within_window(
        self,
        start_time: time | None,
        end_time: time | None,
        timezone: str = DEFAULT_TIMEZONE,
        active_days: list[int] | None = None,
        now: datetime | None = None,
    ) -> tuple[bool, str]:
        """Check if current time is within the trading window.

        Args:
            start_time: Start of trading window (e.g., 09:45:00). None means no start restriction.
            end_time: End of trading window (e.g., 15:15:00). None means no end restriction.
            timezone: IANA timezone string (e.g., "Asia/Kolkata").
            active_days: List of active weekday indices (Monday=0, Sunday=6).
                         None defaults to [0, 1, 2, 3, 4] (Mon-Fri).
            now: Optional current time for testing. If None, uses actual current time.

        Returns:
            Tuple of (is_valid, reason):
            - (True, "") if within window or no window set
            - (False, "Before trading window (HH:MM)") if before start
            - (False, "After trading window (HH:MM)") if after end
            - (False, "Not an active trading day (Day)") if wrong day
        """
        # If no time constraints, always valid
        if start_time is None and end_time is None:
            return True, ""

        # Get current time in the specified timezone
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            # Invalid timezone, fall back to default
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        if now is None:
            now = datetime.now(tz)
        else:
            # Convert provided datetime to target timezone
            now = now.astimezone(tz)

        current_time = now.time()
        current_weekday = now.weekday()

        # Check active days
        if active_days is None:
            active_days = DEFAULT_ACTIVE_DAYS

        if current_weekday not in active_days:
            day_name = now.strftime("%A")
            return False, f"Not an active trading day ({day_name})"

        # Check start time
        if start_time is not None and current_time < start_time:
            return False, f"Before trading window ({start_time.strftime('%H:%M')})"

        # Check end time
        if end_time is not None and current_time > end_time:
            return False, f"After trading window ({end_time.strftime('%H:%M')})"

        return True, ""

    def time_until_window_opens(
        self,
        start_time: time,
        timezone: str = DEFAULT_TIMEZONE,
        now: datetime | None = None,
    ) -> timedelta:
        """Calculate time until the trading window opens.

        Args:
            start_time: Start time of trading window.
            timezone: IANA timezone string.
            now: Optional current time for testing.

        Returns:
            Timedelta until window opens. Returns timedelta(0) if window is already open.
        """
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        if now is None:
            now = datetime.now(tz)
        else:
            now = now.astimezone(tz)

        current_time = now.time()

        if current_time >= start_time:
            # Window is already open (or has passed), calculate time until next day
            tomorrow_start = datetime.combine(now.date() + timedelta(days=1), start_time, tzinfo=tz)
            return tomorrow_start - now

        # Calculate time until window opens today
        today_start = datetime.combine(now.date(), start_time, tzinfo=tz)
        return today_start - now

    def time_until_window_closes(
        self,
        end_time: time,
        timezone: str = DEFAULT_TIMEZONE,
        now: datetime | None = None,
    ) -> timedelta:
        """Calculate time until the trading window closes.

        Args:
            end_time: End time of trading window.
            timezone: IANA timezone string.
            now: Optional current time for testing.

        Returns:
            Timedelta until window closes. Returns timedelta(0) if window is closed.
        """
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        if now is None:
            now = datetime.now(tz)
        else:
            now = now.astimezone(tz)

        current_time = now.time()

        if current_time > end_time:
            # Window already closed
            return timedelta(0)

        # Calculate time until window closes
        today_end = datetime.combine(now.date(), end_time, tzinfo=tz)
        return today_end - now
