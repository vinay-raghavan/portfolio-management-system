"""Tests for instruments module."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.instruments.models import Instrument
from app.modules.instruments.schemas import (
    Exchange,
    InstrumentCreate,
    InstrumentSearchParams,
    InstrumentType,
    Segment,
)


class TestInstrumentSchemas:
    """Tests for instrument Pydantic schemas."""

    def test_instrument_create_minimal(self):
        """Test creating instrument with minimal fields."""
        data = InstrumentCreate(
            symbol="RELIANCE",
            name="Reliance Industries Limited",
            exchange="NSE",
        )
        assert data.symbol == "RELIANCE"
        assert data.segment == "EQ"
        assert data.lot_size == 1
        assert data.tick_size == Decimal("0.05")

    def test_instrument_create_full(self):
        """Test creating instrument with all fields."""
        data = InstrumentCreate(
            symbol="NIFTY24JANFUT",
            name="Nifty January 2024 Futures",
            exchange="NSE",
            segment="FO",
            token="12345",
            lot_size=50,
            tick_size=Decimal("0.05"),
            expiry=date(2024, 1, 25),
            underlying="NIFTY",
            instrument_type="FUT",
        )
        assert data.segment == "FO"
        assert data.lot_size == 50
        assert data.expiry == date(2024, 1, 25)
        assert data.underlying == "NIFTY"

    def test_instrument_create_option(self):
        """Test creating option instrument."""
        data = InstrumentCreate(
            symbol="NIFTY24JAN21500CE",
            name="Nifty 21500 CE",
            exchange="NSE",
            segment="FO",
            lot_size=50,
            expiry=date(2024, 1, 25),
            strike=Decimal("21500"),
            option_type="CE",
            underlying="NIFTY",
            instrument_type="OPT",
        )
        assert data.strike == Decimal("21500")
        assert data.option_type == "CE"

    def test_instrument_search_params_defaults(self):
        """Test search params have correct defaults."""
        params = InstrumentSearchParams()
        assert params.query is None
        assert params.is_active is True
        assert params.limit == 50
        assert params.offset == 0

    def test_instrument_search_params_custom(self):
        """Test search params with custom values."""
        params = InstrumentSearchParams(
            query="NIFTY",
            exchange="NSE",
            segment="FO",
            instrument_type="OPT",
            underlying="NIFTY",
            limit=100,
            offset=50,
        )
        assert params.query == "NIFTY"
        assert params.exchange == "NSE"
        assert params.limit == 100

    def test_exchange_enum(self):
        """Test exchange enum values."""
        assert Exchange.NSE.value == "NSE"
        assert Exchange.BSE.value == "BSE"
        assert Exchange.NFO.value == "NFO"

    def test_segment_enum(self):
        """Test segment enum values."""
        assert Segment.EQ.value == "EQ"
        assert Segment.FO.value == "FO"

    def test_instrument_type_enum(self):
        """Test instrument type enum values."""
        assert InstrumentType.EQ.value == "EQ"
        assert InstrumentType.FUT.value == "FUT"
        assert InstrumentType.OPT.value == "OPT"
        assert InstrumentType.IDX.value == "IDX"


class TestInstrumentModel:
    """Tests for Instrument SQLAlchemy model."""

    def test_instrument_repr(self):
        """Test instrument string representation."""
        instrument = Instrument(
            id="test-id",
            symbol="RELIANCE",
            name="Reliance Industries",
            exchange="NSE",
            segment="EQ",
            lot_size=1,
            tick_size=Decimal("0.05"),
            instrument_type="EQ",
        )
        assert repr(instrument) == "<Instrument NSE:RELIANCE>"

    def test_instrument_with_explicit_values(self):
        """Test instrument with explicit values."""
        instrument = Instrument(
            symbol="TCS",
            name="Tata Consultancy Services",
            exchange="NSE",
            segment="EQ",
            lot_size=1,
            tick_size=Decimal("0.05"),
            instrument_type="EQ",
            is_active=True,
            is_tradeable=True,
        )
        assert instrument.segment == "EQ"
        assert instrument.lot_size == 1
        assert instrument.tick_size == Decimal("0.05")
        assert instrument.is_active is True
        assert instrument.is_tradeable is True

    def test_instrument_fo_fields(self):
        """Test F&O specific fields."""
        instrument = Instrument(
            symbol="NIFTY24JAN21500CE",
            name="Nifty 21500 CE",
            exchange="NSE",
            segment="FO",
            expiry=date(2024, 1, 25),
            strike=Decimal("21500"),
            option_type="CE",
            underlying="NIFTY",
            instrument_type="OPT",
            lot_size=50,
        )
        assert instrument.expiry == date(2024, 1, 25)
        assert instrument.strike == Decimal("21500")
        assert instrument.option_type == "CE"
        assert instrument.underlying == "NIFTY"


class TestInstrumentService:
    """Tests for InstrumentService with mocked database."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create instrument service with mock db."""
        from app.modules.instruments.service import InstrumentService

        return InstrumentService(mock_db)

    @pytest.mark.asyncio
    async def test_create_instrument(self, service, mock_db):
        """Test creating an instrument."""
        data = InstrumentCreate(
            symbol="RELIANCE",
            name="Reliance Industries Limited",
            exchange="NSE",
        )

        await service.create(data)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id(self, service, mock_db):
        """Test getting instrument by ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Instrument(
            id="test-id",
            symbol="RELIANCE",
            name="Reliance Industries",
            exchange="NSE",
        )
        mock_db.execute.return_value = mock_result

        instrument = await service.get_by_id("test-id")

        assert instrument is not None
        assert instrument.symbol == "RELIANCE"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_db):
        """Test getting non-existent instrument."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        instrument = await service.get_by_id("non-existent")

        assert instrument is None

    @pytest.mark.asyncio
    async def test_get_by_symbol(self, service, mock_db):
        """Test getting instrument by symbol."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Instrument(
            id="test-id",
            symbol="TCS",
            name="Tata Consultancy Services",
            exchange="NSE",
        )
        mock_db.execute.return_value = mock_result

        instrument = await service.get_by_symbol("TCS", "NSE")

        assert instrument is not None
        assert instrument.symbol == "TCS"

    @pytest.mark.asyncio
    async def test_search_with_query(self, service, mock_db):
        """Test searching instruments."""
        # Mock count result
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # Mock search results
        mock_search_result = MagicMock()
        mock_search_result.scalars.return_value.all.return_value = [
            Instrument(id="1", symbol="RELIANCE", name="Reliance", exchange="NSE"),
            Instrument(id="2", symbol="RELIANCEPP", name="Reliance PP", exchange="NSE"),
        ]

        # Return different results for count and search
        mock_db.execute.side_effect = [mock_count_result, mock_search_result]

        params = InstrumentSearchParams(query="RELIANCE")
        results, total = await service.search(params)

        assert total == 2
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_filters(self, service, mock_db):
        """Test searching with exchange and segment filters."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_search_result = MagicMock()
        mock_search_result.scalars.return_value.all.return_value = [
            Instrument(
                id="1",
                symbol="NIFTYFUT",
                name="Nifty Futures",
                exchange="NSE",
                segment="FO",
            ),
        ]

        mock_db.execute.side_effect = [mock_count_result, mock_search_result]

        params = InstrumentSearchParams(
            exchange="NSE",
            segment="FO",
            instrument_type="FUT",
        )
        results, total = await service.search(params)

        assert total == 1
        assert results[0].segment == "FO"
