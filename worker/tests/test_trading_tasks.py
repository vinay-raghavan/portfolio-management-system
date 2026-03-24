"""Tests for trading background tasks."""

from datetime import datetime, time
from unittest.mock import MagicMock, patch

from worker.tasks.trading import (
    INTRADAY_SQUARE_OFF_TIME,
    IST,
    MARKET_CLOSE_TIME,
    MARKET_OPEN_TIME,
    auto_square_off_intraday,
    check_gtt_orders,
    check_sl_tp_orders,
    is_market_hours,
    is_square_off_time,
)


class TestMarketHoursHelpers:
    """Tests for market hours helper functions."""

    def test_market_times_constants(self):
        """Test that market time constants are correctly defined."""
        assert time(9, 15) == MARKET_OPEN_TIME
        assert time(15, 30) == MARKET_CLOSE_TIME
        assert time(15, 10) == INTRADAY_SQUARE_OFF_TIME  # 3:10 PM IST

    def test_is_market_hours_during_trading(self):
        """Test is_market_hours returns True during trading hours."""
        with patch("worker.tasks.trading.datetime") as mock_datetime:
            # 11:00 AM IST - during trading hours
            mock_now = datetime(2024, 1, 15, 11, 0, 0, tzinfo=IST)
            mock_datetime.now.return_value = mock_now

            result = is_market_hours()
            assert result is True

    def test_is_market_hours_before_open(self):
        """Test is_market_hours returns False before market open."""
        with patch("worker.tasks.trading.datetime") as mock_datetime:
            # 8:00 AM IST - before market open
            mock_now = datetime(2024, 1, 15, 8, 0, 0, tzinfo=IST)
            mock_datetime.now.return_value = mock_now

            result = is_market_hours()
            assert result is False

    def test_is_market_hours_after_close(self):
        """Test is_market_hours returns False after market close."""
        with patch("worker.tasks.trading.datetime") as mock_datetime:
            # 4:00 PM IST - after market close
            mock_now = datetime(2024, 1, 15, 16, 0, 0, tzinfo=IST)
            mock_datetime.now.return_value = mock_now

            result = is_market_hours()
            assert result is False

    def test_is_square_off_time_before(self):
        """Test is_square_off_time returns False before 3:15 PM."""
        with patch("worker.tasks.trading.datetime") as mock_datetime:
            # 2:00 PM IST
            mock_now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=IST)
            mock_datetime.now.return_value = mock_now

            result = is_square_off_time()
            assert result is False

    def test_is_square_off_time_after(self):
        """Test is_square_off_time returns True after 3:15 PM."""
        with patch("worker.tasks.trading.datetime") as mock_datetime:
            # 3:20 PM IST
            mock_now = datetime(2024, 1, 15, 15, 20, 0, tzinfo=IST)
            mock_datetime.now.return_value = mock_now

            result = is_square_off_time()
            assert result is True


class TestCheckSLTPOrders:
    """Tests for check_sl_tp_orders task."""

    def test_skips_when_market_closed(self):
        """Test that task skips when market is closed."""
        with patch("worker.tasks.trading.is_market_hours", return_value=False):
            result = check_sl_tp_orders()

            assert result["status"] == "market_closed"
            assert result["checked"] == 0
            assert result["triggered"] == 0

    def test_calls_api_when_market_open(self):
        """Test that task calls API when market is open."""
        with (
            patch("worker.tasks.trading.is_market_hours", return_value=True),
            patch("worker.tasks.trading.httpx.Client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []

            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client.return_value = mock_client_instance

            result = check_sl_tp_orders()

            assert result["status"] == "success"
            assert result["checked"] == 0


class TestAutoSquareOff:
    """Tests for auto_square_off_intraday task."""

    def test_skips_when_not_square_off_time(self):
        """Test that task skips when not at square-off time."""
        with patch("worker.tasks.trading.datetime") as mock_datetime:
            # 2:00 PM IST - not square-off time
            mock_now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=IST)
            mock_datetime.now.return_value = mock_now

            result = auto_square_off_intraday()

            assert result["status"] == "skipped"

    def test_executes_at_square_off_time(self):
        """Test that task executes at square-off time."""
        from unittest.mock import PropertyMock

        # 3:12 PM IST - within square-off window (3:10 - 3:15 PM)
        mock_now = datetime(2024, 1, 15, 15, 12, 0, tzinfo=IST)

        with patch("worker.tasks.trading.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now
            # Preserve the real time() class for comparisons
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            with patch("worker.tasks.trading.httpx.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = []

                mock_client_instance = MagicMock()
                mock_client_instance.get.return_value = mock_response
                mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
                mock_client_instance.__exit__ = MagicMock(return_value=False)
                mock_client.return_value = mock_client_instance

                result = auto_square_off_intraday()

                assert result["status"] == "success"


class TestCheckGTTOrders:
    """Tests for check_gtt_orders task."""

    def test_skips_when_market_closed(self):
        """Test that task skips when market is closed."""
        with patch("worker.tasks.trading.is_market_hours", return_value=False):
            result = check_gtt_orders()

            assert result["status"] == "market_closed"
            assert result["checked"] == 0
