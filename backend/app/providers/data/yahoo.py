"""Yahoo Finance data provider implementation."""

import logging
from datetime import datetime
from decimal import Decimal

import yfinance as yf

from app.providers.data.base import DataProvider
from app.providers.schemas import Quote, OHLCV, InstrumentInfo, SearchResult
from app.providers.symbols import SymbolMapper, Exchange

logger = logging.getLogger(__name__)


class YahooDataProvider(DataProvider):
    """Data provider using Yahoo Finance (yfinance).

    Supports global markets including:
    - US stocks (NYSE, NASDAQ)
    - Indian stocks (NSE: .NS suffix, BSE: .BO suffix)
    - Other international markets
    """

    name = "yahoo"

    def __init__(self, default_exchange: Exchange = Exchange.NSE):
        """Initialize Yahoo data provider.

        Args:
            default_exchange: Default exchange for Indian stocks
        """
        self.default_exchange = default_exchange

    def normalize_symbol(self, symbol: str) -> str:
        """Convert symbol to Yahoo Finance format."""
        symbol = symbol.upper().strip()

        # Already in Yahoo format
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            return symbol

        # Check if it's an Indian stock (heuristic)
        # If no suffix and default exchange is Indian, add suffix
        if self.default_exchange == Exchange.NSE:
            return f"{symbol}.NS"
        elif self.default_exchange == Exchange.BSE:
            return f"{symbol}.BO"

        return symbol

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for a symbol."""
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            price = info.get("regularMarketPrice") or info.get("currentPrice")
            if not price:
                return None

            prev_close = info.get("regularMarketPreviousClose", 0)
            change = Decimal(str(price)) - Decimal(str(prev_close)) if prev_close else None
            change_pct = (
                (change / Decimal(str(prev_close)) * 100) if change and prev_close else None
            )

            return Quote(
                symbol=SymbolMapper.normalize(symbol),
                price=Decimal(str(price)),
                open=Decimal(str(info.get("regularMarketOpen", 0))) or None,
                high=Decimal(str(info.get("regularMarketDayHigh", 0))) or None,
                low=Decimal(str(info.get("regularMarketDayLow", 0))) or None,
                close=Decimal(str(prev_close)) if prev_close else None,
                previous_close=Decimal(str(prev_close)) if prev_close else None,
                volume=info.get("regularMarketVolume"),
                change=change,
                change_percent=change_pct,
                bid=Decimal(str(info.get("bid", 0))) or None,
                ask=Decimal(str(info.get("ask", 0))) or None,
            )
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    async def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[OHLCV]:
        """Get historical OHLCV data for a symbol."""
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return []

            data_points = []
            for idx, row in hist.iterrows():
                data_points.append(
                    OHLCV(
                        timestamp=idx.to_pydatetime(),
                        open=Decimal(str(row["Open"])),
                        high=Decimal(str(row["High"])),
                        low=Decimal(str(row["Low"])),
                        close=Decimal(str(row["Close"])),
                        volume=int(row["Volume"]),
                    )
                )

            return data_points
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return []

    async def search_symbols(self, query: str) -> list[SearchResult]:
        """Search for symbols matching a query."""
        try:
            # yfinance doesn't have native search
            # Try to get info for the query as a symbol
            ticker = yf.Ticker(query)
            info = ticker.info

            if info.get("symbol"):
                return [
                    SearchResult(
                        symbol=info.get("symbol", query).replace(".NS", "").replace(".BO", ""),
                        name=info.get("longName") or info.get("shortName") or "",
                        exchange=info.get("exchange", ""),
                        instrument_type=info.get("quoteType", "EQ"),
                    )
                ]
            return []
        except Exception as e:
            logger.debug(f"Search failed for {query}: {e}")
            return []

    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        """Get detailed instrument information."""
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            if not info.get("symbol"):
                return None

            return InstrumentInfo(
                symbol=SymbolMapper.normalize(symbol),
                name=info.get("longName") or info.get("shortName") or "",
                exchange=info.get("exchange", ""),
                instrument_type=info.get("quoteType", "EQ"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                isin=info.get("isin"),
            )
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            return None

