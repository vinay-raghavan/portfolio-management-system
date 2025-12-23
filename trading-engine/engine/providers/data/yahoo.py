"""Yahoo Finance data provider implementation."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time
from decimal import Decimal
from functools import partial
from zoneinfo import ZoneInfo

import yfinance as yf

from engine.core.retry import DATA_PROVIDER_RETRY, with_async_retry
from engine.providers.data.base import DataProvider
from engine.providers.schemas import OHLCV, InstrumentInfo, Quote, SearchResult
from engine.providers.symbols import Exchange, SymbolMapper

logger = logging.getLogger(__name__)

# Indian Standard Time timezone
IST = ZoneInfo("Asia/Kolkata")

# NSE market hours
NSE_MARKET_OPEN = time(9, 15)  # 9:15 AM IST
NSE_MARKET_CLOSE = time(15, 30)  # 3:30 PM IST

# Thread pool for running synchronous yfinance calls
_executor = ThreadPoolExecutor(max_workers=4)


async def _run_in_executor(func, *args, **kwargs):
    """Run a synchronous function in a thread pool executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, partial(func, *args, **kwargs))


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

    def _fetch_ticker_info(self, yahoo_symbol: str) -> dict:
        """Synchronous helper to fetch ticker info (runs in thread pool)."""
        ticker = yf.Ticker(yahoo_symbol)
        return ticker.info

    def _fetch_history(self, yahoo_symbol: str, period: str, interval: str):
        """Synchronous helper to fetch history (runs in thread pool)."""
        ticker = yf.Ticker(yahoo_symbol)
        return ticker.history(period=period, interval=interval)

    @with_async_retry(
        max_attempts=DATA_PROVIDER_RETRY.max_attempts,
        min_wait=DATA_PROVIDER_RETRY.min_wait,
        max_wait=DATA_PROVIDER_RETRY.max_wait,
    )
    async def _get_quote_with_retry(self, symbol: str) -> Quote | None:
        """Get quote with retry logic for transient failures."""
        yahoo_symbol = self.normalize_symbol(symbol)
        info = await _run_in_executor(self._fetch_ticker_info, yahoo_symbol)

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if not price:
            return None

        prev_close = info.get("regularMarketPreviousClose", 0)
        change = Decimal(str(price)) - Decimal(str(prev_close)) if prev_close else None
        change_pct = (change / Decimal(str(prev_close)) * 100) if change and prev_close else None

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

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for a symbol."""
        try:
            return await self._get_quote_with_retry(symbol)
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol} after retries: {e}")
            return None

    @with_async_retry(
        max_attempts=DATA_PROVIDER_RETRY.max_attempts,
        min_wait=DATA_PROVIDER_RETRY.min_wait,
        max_wait=DATA_PROVIDER_RETRY.max_wait,
    )
    async def _get_historical_with_retry(
        self, symbol: str, period: str, interval: str
    ) -> list[OHLCV]:
        """Get historical data with retry logic for transient failures."""
        yahoo_symbol = self.normalize_symbol(symbol)
        hist = await _run_in_executor(self._fetch_history, yahoo_symbol, period, interval)

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

    async def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[OHLCV]:
        """Get historical OHLCV data for a symbol."""
        try:
            return await self._get_historical_with_retry(symbol, period, interval)
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} after retries: {e}")
            return []

    @with_async_retry(
        max_attempts=DATA_PROVIDER_RETRY.max_attempts,
        min_wait=DATA_PROVIDER_RETRY.min_wait,
        max_wait=DATA_PROVIDER_RETRY.max_wait,
    )
    async def _search_symbols_with_retry(self, query: str) -> list[SearchResult]:
        """Search symbols with retry logic."""
        yahoo_symbol = self.normalize_symbol(query)
        info = await _run_in_executor(self._fetch_ticker_info, yahoo_symbol)

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

    async def search_symbols(self, query: str) -> list[SearchResult]:
        """Search for symbols matching a query."""
        try:
            return await self._search_symbols_with_retry(query)
        except Exception as e:
            logger.debug(f"Search failed for {query} after retries: {e}")
            return []

    @with_async_retry(
        max_attempts=DATA_PROVIDER_RETRY.max_attempts,
        min_wait=DATA_PROVIDER_RETRY.min_wait,
        max_wait=DATA_PROVIDER_RETRY.max_wait,
    )
    async def _get_instrument_info_with_retry(self, symbol: str) -> InstrumentInfo | None:
        """Get instrument info with retry logic."""
        yahoo_symbol = self.normalize_symbol(symbol)
        info = await _run_in_executor(self._fetch_ticker_info, yahoo_symbol)

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

    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        """Get detailed instrument information."""
        try:
            return await self._get_instrument_info_with_retry(symbol)
        except Exception as e:
            logger.error(f"Error fetching info for {symbol} after retries: {e}")
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
