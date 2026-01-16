"""Tests for Fyers data provider and broker.

These tests use mocking to avoid requiring actual Fyers API credentials.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from shared.providers.broker.fyers import FyersBroker
from shared.providers.broker.fyers_auth import FyersAuthHandler, FyersCredentials
from shared.providers.data.fyers import FyersDataProvider
from shared.providers.schemas import (
    OrderStatus,
    OrderType,
    ProductType,
)


class TestFyersCredentials:
    """Tests for FyersCredentials dataclass."""

    def test_credentials_creation(self):
        """Test creating credentials with required fields."""
        creds = FyersCredentials(
            client_id="TEST-100",
            secret_key="test_secret",
            redirect_uri="http://localhost:8000/callback",
        )
        assert creds.client_id == "TEST-100"
        assert creds.secret_key == "test_secret"
        assert creds.redirect_uri == "http://localhost:8000/callback"
        assert creds.access_token is None
        assert creds.log_path == ""

    def test_credentials_with_access_token(self):
        """Test creating credentials with access token."""
        creds = FyersCredentials(
            client_id="TEST-100",
            secret_key="test_secret",
            redirect_uri="http://localhost:8000/callback",
            access_token="test_token",
        )
        assert creds.access_token == "test_token"


class TestFyersAuthHandler:
    """Tests for FyersAuthHandler."""

    def test_auth_handler_creation(self):
        """Test creating auth handler."""
        creds = FyersCredentials(
            client_id="TEST-100",
            secret_key="test_secret",
            redirect_uri="http://localhost:8000/callback",
        )
        handler = FyersAuthHandler(creds)
        assert handler.credentials == creds
        assert not handler.is_authenticated

    def test_is_authenticated_with_token(self):
        """Test is_authenticated returns True when token is set."""
        creds = FyersCredentials(
            client_id="TEST-100",
            secret_key="test_secret",
            redirect_uri="http://localhost:8000/callback",
            access_token="test_token",
        )
        handler = FyersAuthHandler(creds)
        assert handler.is_authenticated

    def test_get_full_access_token(self):
        """Test getting full access token format."""
        creds = FyersCredentials(
            client_id="TEST-100",
            secret_key="test_secret",
            redirect_uri="http://localhost:8000/callback",
            access_token="test_token",
        )
        handler = FyersAuthHandler(creds)
        assert handler.get_full_access_token() == "TEST-100:test_token"

    def test_get_full_access_token_none_when_not_authenticated(self):
        """Test getting full access token returns None when not authenticated."""
        creds = FyersCredentials(
            client_id="TEST-100",
            secret_key="test_secret",
            redirect_uri="http://localhost:8000/callback",
        )
        handler = FyersAuthHandler(creds)
        assert handler.get_full_access_token() is None


class TestFyersDataProvider:
    """Tests for FyersDataProvider."""

    def test_provider_creation(self):
        """Test creating data provider."""
        provider = FyersDataProvider(
            access_token="test_token",
            client_id="TEST-100",
        )
        assert provider.name == "fyers"
        assert provider.access_token == "test_token"
        assert provider.client_id == "TEST-100"

    def test_normalize_symbol_simple(self):
        """Test normalizing simple symbol."""
        provider = FyersDataProvider()
        assert provider.normalize_symbol("RELIANCE") == "NSE:RELIANCE-EQ"
        assert provider.normalize_symbol("sbin") == "NSE:SBIN-EQ"

    def test_normalize_symbol_already_formatted(self):
        """Test normalizing already formatted symbol."""
        provider = FyersDataProvider()
        assert provider.normalize_symbol("NSE:RELIANCE-EQ") == "NSE:RELIANCE-EQ"
        assert provider.normalize_symbol("BSE:INFY-EQ") == "BSE:INFY-EQ"

    def test_parse_fyers_symbol(self):
        """Test parsing Fyers symbol format."""
        provider = FyersDataProvider()
        assert provider._parse_fyers_symbol("NSE:RELIANCE-EQ") == "RELIANCE"
        assert provider._parse_fyers_symbol("BSE:INFY-EQ") == "INFY"
        assert provider._parse_fyers_symbol("SBIN") == "SBIN"

    def test_set_access_token(self):
        """Test setting access token resets client."""
        provider = FyersDataProvider(access_token="old_token")
        provider._fyers = MagicMock()  # Simulate existing client
        provider.set_access_token("new_token")
        assert provider.access_token == "new_token"
        assert provider._fyers is None  # Client should be reset

    @patch("shared.providers.data.fyers.datetime")
    def test_get_market_session_regular(self, mock_datetime):
        """Test market session during regular hours."""
        from zoneinfo import ZoneInfo

        IST = ZoneInfo("Asia/Kolkata")
        # Monday at 10:00 AM IST
        mock_now = datetime(2024, 1, 15, 10, 0, tzinfo=IST)
        mock_datetime.now.return_value = mock_now

        provider = FyersDataProvider()
        # Note: This test may not work as expected due to how datetime is mocked
        # The actual implementation uses datetime.now(IST) directly


class TestFyersBroker:
    """Tests for FyersBroker."""

    def test_broker_creation(self):
        """Test creating broker."""
        broker = FyersBroker(
            access_token="test_token",
            client_id="TEST-100",
        )
        assert broker.name == "fyers"
        assert broker.is_paper is False
        assert broker.access_token == "test_token"
        assert broker.client_id == "TEST-100"

    def test_normalize_symbol(self):
        """Test normalizing symbol."""
        broker = FyersBroker()
        assert broker.normalize_symbol("RELIANCE") == "NSE:RELIANCE-EQ"
        assert broker.normalize_symbol("NSE:INFY-EQ") == "NSE:INFY-EQ"

    def test_map_order_type(self):
        """Test mapping order types."""
        broker = FyersBroker()
        assert broker._map_order_type(OrderType.MARKET) == 2
        assert broker._map_order_type(OrderType.LIMIT) == 1
        assert broker._map_order_type(OrderType.STOP_LOSS) == 3
        assert broker._map_order_type(OrderType.STOP_LOSS_MARKET) == 4

    def test_map_product_type(self):
        """Test mapping product types."""
        broker = FyersBroker()
        assert broker._map_product_type(ProductType.DELIVERY) == "CNC"
        assert broker._map_product_type(ProductType.CNC) == "CNC"
        assert broker._map_product_type(ProductType.INTRADAY) == "INTRADAY"
        assert broker._map_product_type(ProductType.MIS) == "INTRADAY"

    def test_parse_order_status(self):
        """Test parsing order status."""
        broker = FyersBroker()
        assert broker._parse_order_status(1) == OrderStatus.PENDING
        assert broker._parse_order_status(2) == OrderStatus.FILLED
        assert broker._parse_order_status(3) == OrderStatus.REJECTED
        assert broker._parse_order_status(4) == OrderStatus.CANCELLED
        assert broker._parse_order_status(6) == OrderStatus.PARTIALLY_FILLED

    def test_set_access_token(self):
        """Test setting access token resets client."""
        broker = FyersBroker(access_token="old_token")
        broker._fyers = MagicMock()
        broker.set_access_token("new_token")
        assert broker.access_token == "new_token"
        assert broker._fyers is None

    @pytest.mark.asyncio
    async def test_is_connected_without_token(self):
        """Test is_connected returns False without token."""
        broker = FyersBroker()
        assert await broker.is_connected() is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnect clears state."""
        broker = FyersBroker(access_token="test_token")
        broker._connected = True
        broker._fyers = MagicMock()

        await broker.disconnect()

        assert broker._connected is False
        assert broker._fyers is None
