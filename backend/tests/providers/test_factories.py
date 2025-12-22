"""Tests for provider factories."""

from unittest.mock import patch

import pytest

from app.providers.broker.base import Broker
from app.providers.broker.factory import BrokerFactory
from app.providers.broker.paper import PaperBroker
from app.providers.data.base import DataProvider
from app.providers.data.factory import DataProviderFactory, get_data_provider
from app.providers.data.yahoo import YahooDataProvider


class TestDataProviderFactory:
    """Tests for DataProviderFactory."""

    def test_get_yahoo_provider(self):
        """Test getting Yahoo provider."""
        provider = DataProviderFactory.get_provider("yahoo")
        assert isinstance(provider, YahooDataProvider)

    def test_get_provider_case_insensitive(self):
        """Test provider name is case insensitive."""
        provider1 = DataProviderFactory.get_provider("YAHOO")
        provider2 = DataProviderFactory.get_provider("yahoo")
        # Both should be YahooDataProvider (not singleton since factory creates new each time)
        assert isinstance(provider1, YahooDataProvider)
        assert isinstance(provider2, YahooDataProvider)

    def test_get_unknown_provider_raises(self):
        """Test unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown data provider"):
            DataProviderFactory.get_provider("unknown")

    def test_list_providers(self):
        """Test listing available providers."""
        providers = DataProviderFactory.list_providers()
        assert "yahoo" in providers

    def test_register_custom_provider(self):
        """Test registering custom provider."""

        class CustomProvider(DataProvider):
            name = "custom"

            async def get_quote(self, symbol):
                return None

            async def get_historical(self, symbol, period, interval):
                return []

            async def search_symbols(self, query):
                return []

            async def get_instrument_info(self, symbol):
                return None

        DataProviderFactory.register("custom", CustomProvider)
        assert "custom" in DataProviderFactory.list_providers()

        provider = DataProviderFactory.get_provider("custom")
        assert isinstance(provider, CustomProvider)

    def test_get_data_provider_uses_settings(self):
        """Test get_data_provider uses settings."""
        with patch("app.providers.data.factory.settings") as mock_settings:
            mock_settings.DATA_PROVIDER = "yahoo"
            mock_settings.DEFAULT_MARKET = "IN"
            # Clear cache
            get_data_provider.cache_clear()
            provider = get_data_provider()
            assert isinstance(provider, YahooDataProvider)


class TestBrokerFactory:
    """Tests for BrokerFactory."""

    def setup_method(self):
        """Reset factory state before each test."""
        BrokerFactory._instances.clear()

    def test_get_paper_broker(self):
        """Test getting paper broker."""
        broker = BrokerFactory.get_broker("paper")
        assert isinstance(broker, PaperBroker)

    def test_get_broker_case_insensitive(self):
        """Test broker name is case insensitive."""
        broker1 = BrokerFactory.get_broker("PAPER")
        broker2 = BrokerFactory.get_broker("paper")
        assert broker1 is broker2

    def test_get_broker_singleton(self):
        """Test broker returns same instance."""
        broker1 = BrokerFactory.get_broker("paper")
        broker2 = BrokerFactory.get_broker("paper")
        assert broker1 is broker2

    def test_get_unknown_broker_raises(self):
        """Test unknown broker raises ValueError."""
        with pytest.raises(ValueError, match="Unknown broker"):
            BrokerFactory.get_broker("unknown")

    def test_list_brokers(self):
        """Test listing available brokers."""
        brokers = BrokerFactory.list_brokers()
        assert "paper" in brokers

    def test_is_paper_trading(self):
        """Test paper trading detection."""
        with patch("app.providers.broker.factory.settings") as mock_settings:
            mock_settings.BROKER_TYPE = "paper"
            assert BrokerFactory.is_paper_trading() is True

            mock_settings.BROKER_TYPE = "angelone"
            assert BrokerFactory.is_paper_trading() is False

    def test_register_custom_broker(self):
        """Test registering custom broker."""

        class CustomBroker(Broker):
            name = "custom"

            async def connect(self):
                return True

            async def disconnect(self):
                pass

            async def is_connected(self):
                return False

            async def place_order(self, user_id, order):
                return None

            async def cancel_order(self, user_id, order_id):
                return None

            async def modify_order(self, user_id, order_id, modifications):
                return None

            async def get_order_status(self, user_id, order_id):
                return None

            async def get_orders(self, user_id, status):
                return []

            async def get_positions(self, user_id):
                return []

            async def get_funds(self, user_id):
                return None

        BrokerFactory.register("custom", CustomBroker)
        assert "custom" in BrokerFactory.list_brokers()

        broker = BrokerFactory.get_broker("custom")
        assert isinstance(broker, CustomBroker)
