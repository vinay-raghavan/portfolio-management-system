"""Unified symbol system for handling different exchange formats."""

from enum import Enum
from typing import ClassVar

from pydantic import BaseModel


class Exchange(str, Enum):
    """Supported exchanges."""

    NSE = "NSE"
    BSE = "BSE"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    NFO = "NFO"  # NSE F&O
    BFO = "BFO"  # BSE F&O
    MCX = "MCX"  # Commodities


class Segment(str, Enum):
    """Market segments."""

    EQUITY = "EQ"
    FUTURES = "FUT"
    OPTIONS = "OPT"
    INDEX = "IDX"
    COMMODITY = "COM"
    CURRENCY = "CUR"


class Symbol(BaseModel):
    """Unified symbol representation."""

    symbol: str  # Display symbol (e.g., "RELIANCE")
    exchange: Exchange
    segment: Segment = Segment.EQUITY
    token: str | None = None  # Exchange-specific token
    isin: str | None = None  # International Securities Identification Number
    name: str | None = None  # Full company name

    def to_yahoo_format(self) -> str:
        """Convert to Yahoo Finance format."""
        if self.exchange == Exchange.NSE:
            return f"{self.symbol}.NS"
        elif self.exchange == Exchange.BSE:
            return f"{self.symbol}.BO"
        elif self.exchange in (Exchange.NYSE, Exchange.NASDAQ):
            return self.symbol
        return self.symbol

    def to_broker_format(self, broker: str = "angelone") -> str:
        """Convert to broker-specific format."""
        if broker == "angelone":
            if self.exchange == Exchange.NSE and self.segment == Segment.EQUITY:
                return f"{self.symbol}-EQ"
            return self.symbol
        return self.symbol

    @classmethod
    def from_yahoo_format(cls, yahoo_symbol: str) -> "Symbol":
        """Parse Yahoo Finance format symbol."""
        if yahoo_symbol.endswith(".NS"):
            return cls(
                symbol=yahoo_symbol[:-3],
                exchange=Exchange.NSE,
            )
        elif yahoo_symbol.endswith(".BO"):
            return cls(
                symbol=yahoo_symbol[:-3],
                exchange=Exchange.BSE,
            )
        else:
            # Assume US market
            return cls(
                symbol=yahoo_symbol,
                exchange=Exchange.NYSE,
            )


class SymbolMapper:
    """Utility class for symbol format conversions."""

    # Common Indian stock symbol mappings (Yahoo -> Standard)
    YAHOO_TO_STANDARD: ClassVar[dict[str, str]] = {
        "RELIANCE.NS": "RELIANCE",
        "TCS.NS": "TCS",
        "HDFCBANK.NS": "HDFCBANK",
        "INFY.NS": "INFY",
        "ICICIBANK.NS": "ICICIBANK",
    }

    @classmethod
    def normalize(cls, symbol: str) -> str:
        """Normalize symbol to uppercase, remove exchange suffix."""
        symbol = symbol.upper().strip()
        # Remove common suffixes
        for suffix in [".NS", ".BO", "-EQ", "-BE"]:
            if symbol.endswith(suffix):
                symbol = symbol[: -len(suffix)]
        return symbol

    @classmethod
    def to_yahoo(cls, symbol: str, exchange: Exchange = Exchange.NSE) -> str:
        """Convert standard symbol to Yahoo format."""
        symbol = cls.normalize(symbol)
        if exchange == Exchange.NSE:
            return f"{symbol}.NS"
        elif exchange == Exchange.BSE:
            return f"{symbol}.BO"
        return symbol

    @classmethod
    def to_broker(
        cls,
        symbol: str,
        exchange: Exchange = Exchange.NSE,
        broker: str = "angelone",
    ) -> str:
        """Convert standard symbol to broker format."""
        symbol = cls.normalize(symbol)
        if broker == "angelone" and exchange == Exchange.NSE:
            return f"{symbol}-EQ"
        return symbol

    @classmethod
    def from_any(cls, symbol: str) -> tuple[str, Exchange | None]:
        """Parse any format and return (normalized_symbol, exchange)."""
        symbol = symbol.upper().strip()

        if symbol.endswith(".NS"):
            return symbol[:-3], Exchange.NSE
        elif symbol.endswith(".BO"):
            return symbol[:-3], Exchange.BSE
        elif symbol.endswith("-EQ"):
            return symbol[:-3], Exchange.NSE
        else:
            return symbol, None

