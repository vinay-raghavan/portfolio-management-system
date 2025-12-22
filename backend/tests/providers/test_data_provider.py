"""Tests for data provider abstraction and implementations."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.providers.data.base import DataProvider
from app.providers.data.yahoo import YahooDataProvider


class TestDataProviderABC:
    """Tests for DataProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that DataProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DataProvider()

    def test_concrete_class_must_implement_methods(self):
        """Test that concrete class must implement all abstract methods."""

        class IncompleteProvider(DataProvider):
            name = "incomplete"

        with pytest.raises(TypeError):
            IncompleteProvider()


class TestYahooDataProvider:
    """Tests for Yahoo Finance data provider."""

    @pytest.fixture
    def provider(self):
        """Create Yahoo provider instance."""
        from app.providers.symbols import Exchange

        return YahooDataProvider(default_exchange=Exchange.NYSE)

    def test_provider_name(self, provider):
        """Test provider name."""
        assert provider.name == "yahoo"

    @pytest.mark.asyncio
    async def test_get_current_price_success(self, provider):
        """Test getting current price."""
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 150.25}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            price = await provider.get_current_price("AAPL")
            assert price == 150.25

    @pytest.mark.asyncio
    async def test_get_current_price_fallback(self, provider):
        """Test fallback to currentPrice field."""
        mock_ticker = MagicMock()
        mock_ticker.info = {"currentPrice": 148.50}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            price = await provider.get_current_price("AAPL")
            assert price == 148.5

    @pytest.mark.asyncio
    async def test_get_current_price_not_found(self, provider):
        """Test price not found returns None."""
        mock_ticker = MagicMock()
        mock_ticker.info = {}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            price = await provider.get_current_price("INVALID")
            assert price is None

    @pytest.mark.asyncio
    async def test_get_current_price_error(self, provider):
        """Test error handling returns None."""
        with patch("yfinance.Ticker", side_effect=Exception("API Error")):
            price = await provider.get_current_price("AAPL")
            assert price is None

    @pytest.mark.asyncio
    async def test_get_quote_success(self, provider):
        """Test getting full quote."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": 150.25,
            "regularMarketOpen": 149.00,
            "regularMarketDayHigh": 151.00,
            "regularMarketDayLow": 148.50,
            "regularMarketPreviousClose": 149.50,
            "regularMarketVolume": 50000000,
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            quote = await provider.get_quote("AAPL")
            assert quote is not None
            assert quote.symbol == "AAPL"
            assert quote.price == Decimal("150.25")
            assert quote.open == Decimal("149")
            assert quote.high == Decimal("151")
            assert quote.low == Decimal("148.5")
            assert quote.volume == 50000000

    @pytest.mark.asyncio
    async def test_get_quote_calculates_change(self, provider):
        """Test quote calculates price change."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": 150.00,
            "regularMarketPreviousClose": 145.00,
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            quote = await provider.get_quote("AAPL")
            assert quote.change == Decimal("5")
            # Change percent: (5 / 145) * 100 ≈ 3.45%
            assert quote.change_percent is not None

    @pytest.mark.asyncio
    async def test_get_instrument_info(self, provider):
        """Test getting instrument info."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "symbol": "AAPL",  # Required field for the provider
            "longName": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "quoteType": "EQUITY",
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            info = await provider.get_instrument_info("AAPL")
            assert info is not None
            assert info.symbol == "AAPL"
            assert info.name == "Apple Inc."
            assert info.exchange == "NASDAQ"
            assert info.sector == "Technology"

    @pytest.mark.asyncio
    async def test_search_symbols(self, provider):
        """Test symbol search."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "symbol": "AAPL",
            "longName": "Apple Inc.",
            "exchange": "NASDAQ",
            "quoteType": "EQUITY",
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            results = await provider.search_symbols("AAPL")
            assert len(results) == 1
            assert results[0].symbol == "AAPL"
            assert results[0].name == "Apple Inc."
