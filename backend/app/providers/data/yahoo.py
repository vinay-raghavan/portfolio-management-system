"""Yahoo Finance data provider implementation."""

import logging
from datetime import datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import yfinance as yf

from app.providers.data.base import DataProvider
from app.providers.schemas import OHLCV, InstrumentInfo, MarketSession, Quote, SearchResult
from app.providers.symbols import Exchange, SymbolMapper

logger = logging.getLogger(__name__)

# Indian Standard Time timezone
IST = ZoneInfo("Asia/Kolkata")
EST = ZoneInfo("America/New_York")

# NSE market hours (IST)
NSE_PRE_MARKET_OPEN = time(9, 0)  # 9:00 AM IST
NSE_PRE_MARKET_CLOSE = time(9, 8)  # 9:08 AM IST
NSE_MARKET_OPEN = time(9, 15)  # 9:15 AM IST
NSE_MARKET_CLOSE = time(15, 30)  # 3:30 PM IST

# US market hours (EST)
US_PRE_MARKET_OPEN = time(4, 0)  # 4:00 AM EST
US_MARKET_OPEN = time(9, 30)  # 9:30 AM EST
US_MARKET_CLOSE = time(16, 0)  # 4:00 PM EST
US_POST_MARKET_CLOSE = time(20, 0)  # 8:00 PM EST


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

        # Index symbols start with ^ and should be passed as-is
        # e.g., ^NSEI, ^NSEBANK, ^BSESN, ^GSPC, ^DJI, ^IXIC
        if symbol.startswith("^"):
            return symbol

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

    def _get_market_session(self) -> MarketSession:
        """Determine current market session based on exchange and time."""
        if self.default_exchange in (Exchange.NSE, Exchange.BSE):
            now = datetime.now(IST)
            if now.weekday() >= 5:  # Weekend
                return MarketSession.CLOSED
            current_time = now.time()
            if NSE_PRE_MARKET_OPEN <= current_time < NSE_MARKET_OPEN:
                return MarketSession.PRE_MARKET
            elif NSE_MARKET_OPEN <= current_time <= NSE_MARKET_CLOSE:
                return MarketSession.REGULAR
            else:
                return MarketSession.CLOSED
        else:
            # US markets
            now = datetime.now(EST)
            if now.weekday() >= 5:  # Weekend
                return MarketSession.CLOSED
            current_time = now.time()
            if US_PRE_MARKET_OPEN <= current_time < US_MARKET_OPEN:
                return MarketSession.PRE_MARKET
            elif US_MARKET_OPEN <= current_time <= US_MARKET_CLOSE:
                return MarketSession.REGULAR
            elif US_MARKET_CLOSE < current_time <= US_POST_MARKET_CLOSE:
                return MarketSession.POST_MARKET
            else:
                return MarketSession.CLOSED

    def _parse_extended_hours(self, info: dict) -> dict:
        """Extract extended hours data from ticker info."""
        result = {}

        # Pre-market data
        pre_market_price = info.get("preMarketPrice")
        if pre_market_price:
            result["pre_market_price"] = Decimal(str(pre_market_price))
            pre_market_change = info.get("preMarketChange")
            if pre_market_change is not None:
                result["pre_market_change"] = Decimal(str(pre_market_change))
            pre_market_change_pct = info.get("preMarketChangePercent")
            if pre_market_change_pct is not None:
                result["pre_market_change_percent"] = Decimal(str(pre_market_change_pct * 100))
            pre_market_time = info.get("preMarketTime")
            if pre_market_time:
                result["pre_market_time"] = datetime.fromtimestamp(pre_market_time, tz=timezone.utc)

        # Post-market data
        post_market_price = info.get("postMarketPrice")
        if post_market_price:
            result["post_market_price"] = Decimal(str(post_market_price))
            post_market_change = info.get("postMarketChange")
            if post_market_change is not None:
                result["post_market_change"] = Decimal(str(post_market_change))
            post_market_change_pct = info.get("postMarketChangePercent")
            if post_market_change_pct is not None:
                result["post_market_change_percent"] = Decimal(str(post_market_change_pct * 100))
            post_market_time = info.get("postMarketTime")
            if post_market_time:
                result["post_market_time"] = datetime.fromtimestamp(post_market_time, tz=timezone.utc)

        return result

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for a symbol including extended hours data."""
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

            # Parse extended hours data
            extended_hours = self._parse_extended_hours(info)

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
                market_session=self._get_market_session(),
                **extended_hours,
            )
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    async def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
        include_extended_hours: bool = False,
    ) -> list[OHLCV]:
        """Get historical OHLCV data for a symbol.

        Args:
            symbol: Stock symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)
            include_extended_hours: If True, includes pre-market and post-market data
                                   (only applicable for intraday intervals like 1m, 5m, etc.)

        Returns:
            List of OHLCV data points
        """
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period=period, interval=interval, prepost=include_extended_hours)

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

    async def is_market_open(self) -> bool:
        """Check if the market is currently open.

        For Indian markets (NSE/BSE), checks IST market hours.
        For US markets, defaults to True (always open for paper trading).
        """
        if self.default_exchange in (Exchange.NSE, Exchange.BSE):
            now = datetime.now(IST)

            # Check if it's a weekday (Monday = 0, Sunday = 6)
            if now.weekday() >= 5:  # Saturday or Sunday
                return False

            current_time = now.time()
            return NSE_MARKET_OPEN <= current_time <= NSE_MARKET_CLOSE

        # For US markets, default to True (paper trading always works)
        return True
