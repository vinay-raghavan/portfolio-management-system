"""Tests for unified symbol system."""

from app.providers.symbols import (
    Exchange,
    Segment,
    Symbol,
    SymbolMapper,
)


class TestExchange:
    """Tests for Exchange enum."""

    def test_exchange_values(self):
        """Test exchange enum values."""
        assert Exchange.NSE.value == "NSE"
        assert Exchange.BSE.value == "BSE"
        assert Exchange.NYSE.value == "NYSE"
        assert Exchange.NASDAQ.value == "NASDAQ"

    def test_exchange_nfo_mcx(self):
        """Test derivative exchange values."""
        assert Exchange.NFO.value == "NFO"
        assert Exchange.MCX.value == "MCX"


class TestSegment:
    """Tests for Segment enum."""

    def test_segment_values(self):
        """Test segment enum values."""
        assert Segment.EQUITY.value == "EQ"
        assert Segment.FUTURES.value == "FUT"
        assert Segment.OPTIONS.value == "OPT"


class TestSymbol:
    """Tests for Symbol model."""

    def test_symbol_creation(self):
        """Test basic symbol creation."""
        symbol = Symbol(
            symbol="RELIANCE",
            name="Reliance Industries Limited",
            exchange=Exchange.NSE,
        )
        assert symbol.symbol == "RELIANCE"
        assert symbol.exchange == Exchange.NSE
        assert symbol.segment == Segment.EQUITY  # Default

    def test_symbol_to_yahoo_format_nse(self):
        """Test conversion to Yahoo format for NSE."""
        symbol = Symbol(symbol="RELIANCE", exchange=Exchange.NSE)
        assert symbol.to_yahoo_format() == "RELIANCE.NS"

    def test_symbol_to_yahoo_format_bse(self):
        """Test conversion to Yahoo format for BSE."""
        symbol = Symbol(symbol="500325", exchange=Exchange.BSE)
        assert symbol.to_yahoo_format() == "500325.BO"

    def test_symbol_to_yahoo_format_us(self):
        """Test conversion to Yahoo format for US."""
        symbol = Symbol(symbol="AAPL", exchange=Exchange.NYSE)
        assert symbol.to_yahoo_format() == "AAPL"

    def test_symbol_to_broker_format(self):
        """Test conversion to broker format."""
        symbol = Symbol(symbol="RELIANCE", exchange=Exchange.NSE)
        assert symbol.to_broker_format("angelone") == "RELIANCE-EQ"

    def test_symbol_from_yahoo_format_nse(self):
        """Test parsing Yahoo format for NSE."""
        symbol = Symbol.from_yahoo_format("RELIANCE.NS")
        assert symbol.symbol == "RELIANCE"
        assert symbol.exchange == Exchange.NSE

    def test_symbol_from_yahoo_format_bse(self):
        """Test parsing Yahoo format for BSE."""
        symbol = Symbol.from_yahoo_format("500325.BO")
        assert symbol.symbol == "500325"
        assert symbol.exchange == Exchange.BSE

    def test_symbol_from_yahoo_format_us(self):
        """Test parsing Yahoo format for US."""
        symbol = Symbol.from_yahoo_format("AAPL")
        assert symbol.symbol == "AAPL"
        assert symbol.exchange == Exchange.NYSE


class TestSymbolMapper:
    """Tests for SymbolMapper."""

    def test_normalize_symbol_strips_suffix(self):
        """Test symbol normalization."""
        assert SymbolMapper.normalize("RELIANCE.NS") == "RELIANCE"
        assert SymbolMapper.normalize("500325.BO") == "500325"
        assert SymbolMapper.normalize("AAPL") == "AAPL"
        assert SymbolMapper.normalize("RELIANCE-EQ") == "RELIANCE"

    def test_normalize_symbol_uppercase(self):
        """Test symbol normalization uppercases."""
        assert SymbolMapper.normalize("reliance") == "RELIANCE"
        assert SymbolMapper.normalize("aapl") == "AAPL"

    def test_to_yahoo_nse(self):
        """Test conversion to Yahoo format for NSE."""
        result = SymbolMapper.to_yahoo("RELIANCE", Exchange.NSE)
        assert result == "RELIANCE.NS"

    def test_to_yahoo_bse(self):
        """Test conversion to Yahoo format for BSE."""
        result = SymbolMapper.to_yahoo("500325", Exchange.BSE)
        assert result == "500325.BO"

    def test_to_yahoo_us(self):
        """Test conversion to Yahoo format for US stocks."""
        result = SymbolMapper.to_yahoo("AAPL", Exchange.NYSE)
        assert result == "AAPL"

    def test_to_broker_angelone(self):
        """Test conversion to broker format."""
        result = SymbolMapper.to_broker("RELIANCE", Exchange.NSE, "angelone")
        assert result == "RELIANCE-EQ"

    def test_from_any_nse(self):
        """Test parsing any format for NSE."""
        symbol, exchange = SymbolMapper.from_any("RELIANCE.NS")
        assert symbol == "RELIANCE"
        assert exchange == Exchange.NSE

    def test_from_any_bse(self):
        """Test parsing any format for BSE."""
        symbol, exchange = SymbolMapper.from_any("500325.BO")
        assert symbol == "500325"
        assert exchange == Exchange.BSE

    def test_from_any_broker_format(self):
        """Test parsing broker format."""
        symbol, exchange = SymbolMapper.from_any("RELIANCE-EQ")
        assert symbol == "RELIANCE"
        assert exchange == Exchange.NSE

    def test_from_any_plain_symbol(self):
        """Test parsing plain symbol."""
        symbol, exchange = SymbolMapper.from_any("AAPL")
        assert symbol == "AAPL"
        assert exchange is None
