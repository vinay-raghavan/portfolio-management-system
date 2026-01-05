"""Tests for data provider abstraction and implementations."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.data.service import MarketDataService
from app.providers.data.base import DataProvider
from app.providers.data.yahoo import YahooDataProvider
from app.providers.schemas import MarketSession, Quote


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

    @pytest.mark.asyncio
    async def test_get_quote_with_pre_market_data(self, provider):
        """Test getting quote with pre-market data."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": 150.25,
            "regularMarketPreviousClose": 149.50,
            "preMarketPrice": 151.00,
            "preMarketChange": 1.50,
            "preMarketChangePercent": 0.01,  # 1% as decimal
            "preMarketTime": 1704067200,  # Unix timestamp
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            quote = await provider.get_quote("AAPL")
            assert quote is not None
            assert quote.pre_market_price == Decimal("151")
            assert quote.pre_market_change == Decimal("1.5")
            assert quote.pre_market_change_percent == Decimal("1")  # Converted to percentage
            assert quote.pre_market_time is not None

    @pytest.mark.asyncio
    async def test_get_quote_with_post_market_data(self, provider):
        """Test getting quote with post-market (after-hours) data."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": 150.25,
            "regularMarketPreviousClose": 149.50,
            "postMarketPrice": 149.00,
            "postMarketChange": -1.25,
            "postMarketChangePercent": -0.0083,  # -0.83% as decimal
            "postMarketTime": 1704110400,  # Unix timestamp
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            quote = await provider.get_quote("AAPL")
            assert quote is not None
            assert quote.post_market_price == Decimal("149")
            assert quote.post_market_change == Decimal("-1.25")
            assert quote.post_market_change_percent is not None
            assert quote.post_market_time is not None

    @pytest.mark.asyncio
    async def test_get_quote_without_extended_hours_data(self, provider):
        """Test getting quote when extended hours data is not available."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": 150.25,
            "regularMarketPreviousClose": 149.50,
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            quote = await provider.get_quote("AAPL")
            assert quote is not None
            assert quote.pre_market_price is None
            assert quote.pre_market_change is None
            assert quote.post_market_price is None
            assert quote.post_market_change is None


class TestMarketDataService:
    """Tests for MarketDataService with extended hours support."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock data provider."""
        provider = MagicMock(spec=DataProvider)
        provider.name = "mock"
        return provider

    @pytest.fixture
    def service(self, mock_provider):
        """Create MarketDataService with mock provider."""
        return MarketDataService(provider=mock_provider)

    @pytest.mark.asyncio
    async def test_get_quote_passes_through_extended_hours(self, service, mock_provider):
        """Test that service passes through extended hours data from provider."""
        pre_time = datetime(2024, 1, 1, 8, 0, tzinfo=UTC)
        post_time = datetime(2024, 1, 1, 18, 0, tzinfo=UTC)

        mock_provider.get_quote = AsyncMock(
            return_value=Quote(
                symbol="AAPL",
                price=Decimal("150.25"),
                open=Decimal("149.00"),
                high=Decimal("151.00"),
                low=Decimal("148.50"),
                close=Decimal("150.00"),
                volume=50000000,
                change=Decimal("0.75"),
                change_percent=Decimal("0.50"),
                pre_market_price=Decimal("151.50"),
                pre_market_change=Decimal("1.50"),
                pre_market_change_percent=Decimal("1.00"),
                pre_market_time=pre_time,
                post_market_price=Decimal("149.75"),
                post_market_change=Decimal("-0.50"),
                post_market_change_percent=Decimal("-0.33"),
                post_market_time=post_time,
                market_session=MarketSession.REGULAR,
            )
        )

        result = await service.get_quote("AAPL")

        assert result is not None
        assert result.symbol == "AAPL"
        assert result.price == Decimal("150.25")
        # Verify extended hours fields
        assert result.pre_market_price == Decimal("151.50")
        assert result.pre_market_change == Decimal("1.50")
        assert result.pre_market_change_pct == Decimal("1.00")
        assert result.pre_market_time == pre_time
        assert result.post_market_price == Decimal("149.75")
        assert result.post_market_change == Decimal("-0.50")
        assert result.post_market_change_pct == Decimal("-0.33")
        assert result.post_market_time == post_time
        from app.modules.data.schemas import MarketSession as APIMarketSession

        assert result.market_session == APIMarketSession.REGULAR

    @pytest.mark.asyncio
    async def test_get_quote_handles_null_extended_hours(self, service, mock_provider):
        """Test that service handles null extended hours data gracefully."""
        mock_provider.get_quote = AsyncMock(
            return_value=Quote(
                symbol="RELIANCE",
                price=Decimal("2450.50"),
                # No extended hours data
            )
        )

        result = await service.get_quote("RELIANCE")

        assert result is not None
        assert result.symbol == "RELIANCE"
        assert result.pre_market_price is None
        assert result.post_market_price is None
        assert result.market_session is None

    @pytest.mark.asyncio
    async def test_get_quote_returns_none_when_provider_returns_none(
        self, service, mock_provider
    ):
        """Test that service returns None when provider returns None."""
        mock_provider.get_quote = AsyncMock(return_value=None)

        result = await service.get_quote("INVALID")

        assert result is None
