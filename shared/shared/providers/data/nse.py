"""NSE India data provider implementation.

This provider fetches market data from NSE India APIs for Indian stocks.
It handles:
- Live quotes for NSE-listed stocks
- Historical OHLCV data
- Index data (Nifty 50, Bank Nifty, etc.)
- Market hours awareness (9:15 AM - 3:30 PM IST)
- Caching with Redis
- Rate limiting to avoid blocks
"""

import contextlib
import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from ..schemas import OHLCV, InstrumentInfo, MarketSession, Quote, SearchResult
from .base import DataProvider
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Indian Standard Time timezone
IST = ZoneInfo("Asia/Kolkata")

# NSE market hours
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
PRE_MARKET_OPEN = time(9, 0)
PRE_MARKET_CLOSE = time(9, 8)

# NSE trading holidays (to be updated annually)
NSE_HOLIDAYS_2024 = [
    date(2024, 1, 26),
    date(2024, 3, 8),
    date(2024, 3, 25),
    date(2024, 3, 29),
    date(2024, 4, 11),
    date(2024, 4, 17),
    date(2024, 4, 21),
    date(2024, 5, 1),
    date(2024, 5, 23),
    date(2024, 6, 17),
    date(2024, 7, 17),
    date(2024, 8, 15),
    date(2024, 10, 2),
    date(2024, 11, 1),
    date(2024, 11, 15),
    date(2024, 12, 25),
]

NSE_HOLIDAYS_2025 = [
    date(2025, 1, 26),
    date(2025, 2, 26),
    date(2025, 3, 14),
    date(2025, 3, 31),
    date(2025, 4, 10),
    date(2025, 4, 14),
    date(2025, 4, 18),
    date(2025, 5, 1),
    date(2025, 8, 15),
    date(2025, 8, 27),
    date(2025, 10, 2),
    date(2025, 10, 21),
    date(2025, 10, 22),
    date(2025, 11, 5),
    date(2025, 12, 25),
]

NSE_HOLIDAYS = set(NSE_HOLIDAYS_2024 + NSE_HOLIDAYS_2025)

# NSE API endpoints
NSE_BASE_URL = "https://www.nseindia.com"
NSE_API_BASE = "https://www.nseindia.com/api"


class NSEDataProvider(DataProvider):
    """Data provider for NSE India.

    Uses NSE's public APIs to fetch market data for Indian stocks.
    Implements rate limiting and caching to avoid blocks.
    """

    name = "nse"

    def __init__(self, redis_client: Any = None):
        """Initialize NSE data provider.

        Args:
            redis_client: Optional Redis client for caching
        """
        self._redis = redis_client
        self._session: httpx.AsyncClient | None = None
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive",
        }
        self._cookies: dict[str, str] = {}
        self._last_cookie_refresh: datetime | None = None
        self._cookie_ttl = timedelta(minutes=5)
        self._rate_limiter = RateLimiter(
            max_requests=3,
            time_window=1.0,
            redis_client=redis_client,
            key_prefix="nse",
        )

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session with proper cookies."""
        if self._session is None:
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers=self._headers,
            )
        await self._refresh_cookies()
        return self._session

    async def _refresh_cookies(self) -> None:
        """Refresh NSE cookies by visiting the main page."""
        now = datetime.now(IST)
        if self._last_cookie_refresh is None or now - self._last_cookie_refresh > self._cookie_ttl:
            try:
                session = self._session or httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0),
                    follow_redirects=True,
                    headers=self._headers,
                )
                response = await session.get(NSE_BASE_URL)
                self._cookies = dict(response.cookies)
                self._last_cookie_refresh = now
                logger.debug("NSE cookies refreshed successfully")
            except Exception as e:
                logger.warning(f"Failed to refresh NSE cookies: {e}")

    async def _make_request(self, endpoint: str) -> dict | None:
        """Make a request to NSE API with retry logic and rate limiting."""
        if not await self._rate_limiter.wait_and_acquire("api", timeout=10.0):
            logger.warning(f"Rate limit timeout for {endpoint}")
            return None

        session = await self._get_session()
        url = f"{NSE_API_BASE}{endpoint}"

        try:
            response = await session.get(url, cookies=self._cookies)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self._last_cookie_refresh = None
                await self._refresh_cookies()
                try:
                    response = await session.get(url, cookies=self._cookies)
                    response.raise_for_status()
                    return response.json()
                except Exception as retry_error:
                    logger.error(f"Retry failed for {endpoint}: {retry_error}")
                    return None
            logger.error(f"HTTP error for {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
            return None

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to NSE format."""
        symbol = symbol.upper().strip()
        for suffix in [".NS", ".NSE", "-EQ"]:
            if symbol.endswith(suffix):
                symbol = symbol[: -len(suffix)]
        return symbol

    def is_trading_day(self, check_date: date | None = None) -> bool:
        """Check if a given date is a trading day."""
        if check_date is None:
            check_date = datetime.now(IST).date()
        if check_date.weekday() >= 5:
            return False
        return check_date not in NSE_HOLIDAYS

    async def is_market_open(self) -> bool:
        """Check if NSE market is currently open."""
        now = datetime.now(IST)
        if not self.is_trading_day(now.date()):
            return False
        current_time = now.time()
        return MARKET_OPEN <= current_time <= MARKET_CLOSE

    def get_market_session(self) -> MarketSession:
        """Get the current market session."""
        now = datetime.now(IST)
        if not self.is_trading_day(now.date()):
            return MarketSession.CLOSED
        current_time = now.time()
        if PRE_MARKET_OPEN <= current_time < MARKET_OPEN:
            return MarketSession.PRE_MARKET
        elif MARKET_OPEN <= current_time <= MARKET_CLOSE:
            return MarketSession.REGULAR
        else:
            return MarketSession.CLOSED

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for a symbol."""
        nse_symbol = self.normalize_symbol(symbol)
        cache_key = f"nse:quote:{nse_symbol}"

        if self._redis:
            with contextlib.suppress(Exception):
                cached = await self._redis.get(cache_key)
                if cached:
                    return Quote.model_validate_json(cached)

        data = await self._make_request(f"/quote-equity?symbol={nse_symbol}")
        if not data or "priceInfo" not in data:
            return None

        price_info = data["priceInfo"]

        quote = Quote(
            symbol=nse_symbol,
            price=Decimal(str(price_info.get("lastPrice", 0))),
            open=Decimal(str(price_info.get("open", 0))) or None,
            high=Decimal(str(price_info.get("intraDayHighLow", {}).get("max", 0))) or None,
            low=Decimal(str(price_info.get("intraDayHighLow", {}).get("min", 0))) or None,
            close=Decimal(str(price_info.get("close", 0))) or None,
            previous_close=Decimal(str(price_info.get("previousClose", 0))) or None,
            volume=data.get("preOpenMarket", {}).get("totalTradedVolume"),
            change=Decimal(str(price_info.get("change", 0))) or None,
            change_percent=Decimal(str(price_info.get("pChange", 0))) or None,
            market_session=self.get_market_session(),
        )

        if self._redis:
            with contextlib.suppress(Exception):
                await self._redis.setex(cache_key, 60, quote.model_dump_json())

        return quote

    async def get_index_quote(self, index_name: str) -> Quote | None:
        """Get real-time quote for an index (e.g., NIFTY 50, BANK NIFTY).

        Args:
            index_name: Name of the index (e.g., "NIFTY 50", "NIFTY BANK")

        Returns:
            Quote object with index data, or None if not available
        """
        # Normalize index name
        index_name = index_name.upper().strip()

        # Map common index names to NSE API format
        index_mapping = {
            "NIFTY 50": "NIFTY%2050",
            "NIFTY50": "NIFTY%2050",
            "NIFTY BANK": "NIFTY%20BANK",
            "BANKNIFTY": "NIFTY%20BANK",
            "NIFTY IT": "NIFTY%20IT",
            "NIFTY NEXT 50": "NIFTY%20NEXT%2050",
        }

        api_index = index_mapping.get(index_name, index_name.replace(" ", "%20"))
        cache_key = f"nse:index:{index_name}"

        if self._redis:
            with contextlib.suppress(Exception):
                cached = await self._redis.get(cache_key)
                if cached:
                    return Quote.model_validate_json(cached)

        data = await self._make_request(f"/equity-stockIndices?index={api_index}")
        if not data:
            return None

        # Try to parse index data from response
        try:
            # The API returns data in different formats, handle common cases
            if isinstance(data, dict):
                # Direct index data format
                quote = Quote(
                    symbol=index_name,
                    price=Decimal(str(data.get("last", data.get("lastPrice", 0)))),
                    open=Decimal(str(data.get("open", 0))) or None,
                    high=Decimal(str(data.get("high", data.get("dayHigh", 0)))) or None,
                    low=Decimal(str(data.get("low", data.get("dayLow", 0)))) or None,
                    previous_close=Decimal(str(data.get("previousClose", 0))) or None,
                    change=Decimal(str(data.get("change", 0))) or None,
                    change_percent=Decimal(str(data.get("percChange", data.get("pChange", 0))))
                    or None,
                    market_session=self.get_market_session(),
                )

                if self._redis:
                    with contextlib.suppress(Exception):
                        await self._redis.setex(cache_key, 60, quote.model_dump_json())

                return quote
        except Exception as e:
            logger.error(f"Error parsing index quote for {index_name}: {e}")

        return None

    async def get_index_constituents(self, index_name: str) -> list[dict]:
        """Get constituents of an NSE index.

        Args:
            index_name: Name of the index (e.g., "NIFTY 50", "NIFTY 500", "NIFTY BANK")

        Returns:
            List of constituent stock dictionaries with symbol, name, price data, etc.
        """
        # Normalize index name
        index_name = index_name.upper().strip()

        # Map common index names to NSE API format
        index_mapping = {
            "NIFTY 50": "NIFTY%2050",
            "NIFTY50": "NIFTY%2050",
            "NIFTY 100": "NIFTY%20100",
            "NIFTY100": "NIFTY%20100",
            "NIFTY 200": "NIFTY%20200",
            "NIFTY200": "NIFTY%20200",
            "NIFTY 500": "NIFTY%20500",
            "NIFTY500": "NIFTY%20500",
            "NIFTY BANK": "NIFTY%20BANK",
            "BANKNIFTY": "NIFTY%20BANK",
            "NIFTY IT": "NIFTY%20IT",
            "NIFTYIT": "NIFTY%20IT",
            "NIFTY NEXT 50": "NIFTY%20NEXT%2050",
            "NIFTYNEXT50": "NIFTY%20NEXT%2050",
            "NIFTY MIDCAP 50": "NIFTY%20MIDCAP%2050",
            "NIFTYMIDCAP50": "NIFTY%20MIDCAP%2050",
            "NIFTY MIDCAP 100": "NIFTY%20MIDCAP%20100",
            "NIFTYMIDCAP100": "NIFTY%20MIDCAP%20100",
            "NIFTY MIDCAP 150": "NIFTY%20MIDCAP%20150",
            "NIFTYMIDCAP150": "NIFTY%20MIDCAP%20150",
            "NIFTY SMALLCAP 50": "NIFTY%20SMLCAP%2050",
            "NIFTYSMALLCAP50": "NIFTY%20SMLCAP%2050",
            "NIFTY SMALLCAP 100": "NIFTY%20SMLCAP%20100",
            "NIFTYSMALLCAP100": "NIFTY%20SMLCAP%20100",
            "NIFTY SMALLCAP 250": "NIFTY%20SMLCAP%20250",
            "NIFTYSMALLCAP250": "NIFTY%20SMLCAP%20250",
        }

        api_index = index_mapping.get(index_name, index_name.replace(" ", "%20"))
        cache_key = f"nse:constituents:{index_name}"

        # Check cache first
        if self._redis:
            with contextlib.suppress(Exception):
                import json

                cached = await self._redis.get(cache_key)
                if cached:
                    return json.loads(cached)

        data = await self._make_request(f"/equity-stockIndices?index={api_index}")
        if not data:
            logger.warning(f"No data returned for index: {index_name}")
            return []

        try:
            # The API returns data with a "data" array containing constituents
            constituents_data = data.get("data", [])
            if not constituents_data:
                logger.warning(f"No constituents found in response for: {index_name}")
                return []

            constituents = []
            for item in constituents_data:
                # Skip the index itself (usually first entry)
                symbol = item.get("symbol", "")
                if not symbol or symbol == index_name.replace(" ", ""):
                    continue

                constituent = {
                    "symbol": symbol,
                    "name": item.get("meta", {}).get("companyName", "")
                    if isinstance(item.get("meta"), dict)
                    else "",
                    "industry": item.get("meta", {}).get("industry", "")
                    if isinstance(item.get("meta"), dict)
                    else "",
                    "isin": item.get("meta", {}).get("isin", "")
                    if isinstance(item.get("meta"), dict)
                    else "",
                    "series": item.get("series", "EQ"),
                    "is_fno": item.get("meta", {}).get("isFNOSec", False)
                    if isinstance(item.get("meta"), dict)
                    else False,
                    "last_price": item.get("lastPrice"),
                    "change": item.get("change"),
                    "change_pct": item.get("pChange"),
                    "open": item.get("open"),
                    "high": item.get("dayHigh"),
                    "low": item.get("dayLow"),
                    "previous_close": item.get("previousClose"),
                    "volume": item.get("totalTradedVolume"),
                    "year_high": item.get("yearHigh"),
                    "year_low": item.get("yearLow"),
                }
                constituents.append(constituent)

            # Cache for 5 minutes (index constituents don't change often)
            if self._redis and constituents:
                with contextlib.suppress(Exception):
                    import json

                    await self._redis.setex(cache_key, 300, json.dumps(constituents))

            logger.info(f"Fetched {len(constituents)} constituents for {index_name}")
            return constituents

        except Exception as e:
            logger.error(f"Error parsing index constituents for {index_name}: {e}")
            return []

    async def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[OHLCV]:
        """Get historical OHLCV data for a symbol."""
        nse_symbol = self.normalize_symbol(symbol)

        period_days = {
            "1d": 1,
            "5d": 5,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
        }
        days = period_days.get(period, 30)
        end_date = datetime.now(IST).date()
        start_date = end_date - timedelta(days=days)

        endpoint = (
            f"/historical/cm/equity?symbol={nse_symbol}"
            f"&from={start_date.strftime('%d-%m-%Y')}"
            f"&to={end_date.strftime('%d-%m-%Y')}"
        )

        data = await self._make_request(endpoint)
        if not data or "data" not in data:
            return []

        data_points = []
        for record in data["data"]:
            try:
                data_points.append(
                    OHLCV(
                        timestamp=datetime.strptime(record["CH_TIMESTAMP"], "%Y-%m-%d"),
                        open=Decimal(str(record["CH_OPENING_PRICE"])),
                        high=Decimal(str(record["CH_TRADE_HIGH_PRICE"])),
                        low=Decimal(str(record["CH_TRADE_LOW_PRICE"])),
                        close=Decimal(str(record["CH_CLOSING_PRICE"])),
                        volume=int(record["CH_TOT_TRADED_QTY"]),
                    )
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parsing historical record: {e}")
                continue

        return sorted(data_points, key=lambda x: x.timestamp)

    async def search_symbols(self, query: str) -> list[SearchResult]:
        """Search for symbols matching a query."""
        data = await self._make_request(f"/search/autocomplete?q={query}")
        if not data or "symbols" not in data:
            return []

        results = []
        for item in data["symbols"][:10]:
            results.append(
                SearchResult(
                    symbol=item.get("symbol", ""),
                    name=item.get("symbol_info", ""),
                    exchange="NSE",
                    instrument_type=item.get("result_type", "EQ"),
                )
            )
        return results

    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        """Get detailed instrument information."""
        nse_symbol = self.normalize_symbol(symbol)
        data = await self._make_request(f"/quote-equity?symbol={nse_symbol}")
        if not data:
            return None

        info = data.get("info", {})
        return InstrumentInfo(
            symbol=nse_symbol,
            name=info.get("companyName", ""),
            exchange="NSE",
            instrument_type="EQ",
            sector=info.get("industry"),
            isin=info.get("isin"),
        )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None
