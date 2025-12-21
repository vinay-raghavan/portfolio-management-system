"""NSE India data provider implementation.

This provider fetches market data from NSE India APIs for Indian stocks.
It handles:
- Live quotes for NSE-listed stocks
- Historical OHLCV data
- Index data (Nifty 50, Bank Nifty, etc.)
- Market hours awareness (9:15 AM - 3:30 PM IST)
"""

import logging
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.providers.data.base import DataProvider
from app.providers.data.rate_limiter import RateLimiter
from app.providers.schemas import Quote, OHLCV, InstrumentInfo, SearchResult

logger = logging.getLogger(__name__)

# Indian Standard Time timezone
IST = ZoneInfo("Asia/Kolkata")

# NSE market hours
MARKET_OPEN = time(9, 15)  # 9:15 AM IST
MARKET_CLOSE = time(15, 30)  # 3:30 PM IST

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive",
        }
        self._cookies: dict[str, str] = {}
        self._last_cookie_refresh: datetime | None = None
        self._cookie_ttl = timedelta(minutes=5)
        # Rate limiter: 3 requests per second to avoid blocks
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
        
        # Refresh cookies if needed
        await self._refresh_cookies()
        return self._session

    async def _refresh_cookies(self) -> None:
        """Refresh NSE cookies by visiting the main page."""
        now = datetime.now(IST)
        if (
            self._last_cookie_refresh is None
            or now - self._last_cookie_refresh > self._cookie_ttl
        ):
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
        """Make a request to NSE API with retry logic and rate limiting.

        Args:
            endpoint: API endpoint path

        Returns:
            JSON response as dict, or None on failure
        """
        # Wait for rate limit token
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
                # Cookie expired, refresh and retry
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
        # Remove common suffixes
        for suffix in [".NS", ".NSE", "-EQ"]:
            if symbol.endswith(suffix):
                symbol = symbol[: -len(suffix)]
        return symbol

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for an NSE stock."""
        symbol = self.normalize_symbol(symbol)
        
        # Check cache first
        if self._redis:
            cached = await self._get_cached_quote(symbol)
            if cached:
                return cached

        data = await self._make_request(f"/quote-equity?symbol={symbol}")
        if not data or "priceInfo" not in data:
            return None

        try:
            price_info = data["priceInfo"]
            return Quote(
                symbol=symbol,
                price=Decimal(str(price_info.get("lastPrice", 0))),
                open=Decimal(str(price_info.get("open", 0))) or None,
                high=Decimal(str(price_info.get("intraDayHighLow", {}).get("max", 0))) or None,
                low=Decimal(str(price_info.get("intraDayHighLow", {}).get("min", 0))) or None,
                close=Decimal(str(price_info.get("close", 0))) or None,
                previous_close=Decimal(str(price_info.get("previousClose", 0))) or None,
                volume=data.get("preOpenMarket", {}).get("totalTradedVolume"),
                change=Decimal(str(price_info.get("change", 0))) or None,
                change_percent=Decimal(str(price_info.get("pChange", 0))) or None,
                timestamp=datetime.now(IST),
            )
        except Exception as e:
            logger.error(f"Error parsing quote for {symbol}: {e}")
            return None

    async def _get_cached_quote(self, symbol: str) -> Quote | None:
        """Get quote from Redis cache."""
        if not self._redis:
            return None
        try:
            import json
            cached = await self._redis.get(f"nse:quote:{symbol}")
            if cached:
                data = json.loads(cached)
                return Quote(**data)
        except Exception as e:
            logger.debug(f"Cache miss for {symbol}: {e}")
        return None

    async def _cache_quote(self, symbol: str, quote: Quote, ttl: int = 60) -> None:
        """Cache quote in Redis."""
        if not self._redis:
            return
        try:
            import json
            await self._redis.setex(
                f"nse:quote:{symbol}",
                ttl,
                quote.model_dump_json(),
            )
        except Exception as e:
            logger.debug(f"Failed to cache quote for {symbol}: {e}")

    async def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[OHLCV]:
        """Get historical OHLCV data for an NSE stock.

        Note: NSE provides limited historical data. For extensive history,
        consider using Yahoo Finance as fallback.
        """
        symbol = self.normalize_symbol(symbol)

        # Calculate date range from period
        end_date = datetime.now(IST)
        period_mapping = {
            "1d": timedelta(days=1),
            "5d": timedelta(days=5),
            "1mo": timedelta(days=30),
            "3mo": timedelta(days=90),
            "6mo": timedelta(days=180),
            "1y": timedelta(days=365),
        }
        delta = period_mapping.get(period, timedelta(days=30))
        start_date = end_date - delta

        # NSE historical data endpoint
        from_date = start_date.strftime("%d-%m-%Y")
        to_date = end_date.strftime("%d-%m-%Y")

        data = await self._make_request(
            f"/historical/cm/equity?symbol={symbol}&from={from_date}&to={to_date}"
        )

        if not data or "data" not in data:
            logger.warning(f"No historical data for {symbol}, trying alternative endpoint")
            return await self._get_historical_fallback(symbol, start_date, end_date)

        try:
            ohlcv_list = []
            for record in data.get("data", []):
                ohlcv_list.append(
                    OHLCV(
                        timestamp=datetime.strptime(record["CH_TIMESTAMP"], "%Y-%m-%d"),
                        open=Decimal(str(record["CH_OPENING_PRICE"])),
                        high=Decimal(str(record["CH_TRADE_HIGH_PRICE"])),
                        low=Decimal(str(record["CH_TRADE_LOW_PRICE"])),
                        close=Decimal(str(record["CH_CLOSING_PRICE"])),
                        volume=int(record.get("CH_TOT_TRADED_QTY", 0)),
                    )
                )
            return sorted(ohlcv_list, key=lambda x: x.timestamp)
        except Exception as e:
            logger.error(f"Error parsing historical data for {symbol}: {e}")
            return []

    async def _get_historical_fallback(
        self, symbol: str, start_date: datetime, end_date: datetime
    ) -> list[OHLCV]:
        """Fallback method for historical data using chart endpoint."""
        # This uses NSE's chart data endpoint as fallback
        data = await self._make_request(f"/chart-databyindex?index={symbol}EQN")
        if not data or "grapthData" not in data:
            return []

        try:
            ohlcv_list = []
            for timestamp_ms, price in data.get("grapthData", []):
                dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=IST)
                if start_date <= dt <= end_date:
                    ohlcv_list.append(
                        OHLCV(
                            timestamp=dt,
                            open=Decimal(str(price)),
                            high=Decimal(str(price)),
                            low=Decimal(str(price)),
                            close=Decimal(str(price)),
                            volume=0,
                        )
                    )
            return ohlcv_list
        except Exception as e:
            logger.error(f"Error in historical fallback for {symbol}: {e}")
            return []

    async def search_symbols(self, query: str) -> list[SearchResult]:
        """Search for NSE symbols matching a query."""
        query = query.upper().strip()

        data = await self._make_request(f"/search/autocomplete?q={query}")
        if not data or "symbols" not in data:
            return []

        try:
            results = []
            for item in data.get("symbols", [])[:10]:  # Limit to 10 results
                results.append(
                    SearchResult(
                        symbol=item.get("symbol", ""),
                        name=item.get("symbol_info", ""),
                        exchange="NSE",
                        instrument_type=item.get("result_type", "EQ"),
                    )
                )
            return results
        except Exception as e:
            logger.error(f"Error searching symbols for {query}: {e}")
            return []

    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        """Get detailed instrument information for an NSE stock."""
        symbol = self.normalize_symbol(symbol)

        data = await self._make_request(f"/quote-equity?symbol={symbol}")
        if not data or "info" not in data:
            return None

        try:
            info = data.get("info", {})
            metadata = data.get("metadata", {})

            return InstrumentInfo(
                symbol=symbol,
                name=info.get("companyName", ""),
                exchange="NSE",
                instrument_type=metadata.get("series", "EQ"),
                sector=info.get("industry", None),
                industry=info.get("industry", None),
                lot_size=1,  # Equity lot size is always 1
                tick_size=Decimal("0.05"),
                isin=metadata.get("isin", None),
                token=data.get("securityInfo", {}).get("tradingSymbol"),
            )
        except Exception as e:
            logger.error(f"Error fetching instrument info for {symbol}: {e}")
            return None

    async def is_market_open(self) -> bool:
        """Check if NSE market is currently open."""
        now = datetime.now(IST)

        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        current_time = now.time()
        return MARKET_OPEN <= current_time <= MARKET_CLOSE

    async def get_index_quote(self, index: str) -> Quote | None:
        """Get quote for NSE indices (NIFTY 50, NIFTY BANK, etc.)."""
        # Map common index names
        index_mapping = {
            "NIFTY": "NIFTY 50",
            "NIFTY50": "NIFTY 50",
            "NIFTY 50": "NIFTY 50",
            "BANKNIFTY": "NIFTY BANK",
            "NIFTYBANK": "NIFTY BANK",
            "NIFTY BANK": "NIFTY BANK",
            "NIFTYIT": "NIFTY IT",
            "NIFTY IT": "NIFTY IT",
        }
        index_name = index_mapping.get(index.upper(), index.upper())

        data = await self._make_request(f"/allIndices")
        if not data or "data" not in data:
            return None

        try:
            for idx_data in data.get("data", []):
                if idx_data.get("index") == index_name:
                    return Quote(
                        symbol=index_name,
                        price=Decimal(str(idx_data.get("last", 0))),
                        open=Decimal(str(idx_data.get("open", 0))) or None,
                        high=Decimal(str(idx_data.get("high", 0))) or None,
                        low=Decimal(str(idx_data.get("low", 0))) or None,
                        previous_close=Decimal(str(idx_data.get("previousClose", 0))) or None,
                        change=Decimal(str(idx_data.get("change", 0))) or None,
                        change_percent=Decimal(str(idx_data.get("percentChange", 0))) or None,
                        timestamp=datetime.now(IST),
                    )
            return None
        except Exception as e:
            logger.error(f"Error fetching index quote for {index}: {e}")
            return None

    async def get_market_status(self) -> dict:
        """Get current NSE market status."""
        data = await self._make_request("/marketStatus")
        if not data:
            return {
                "is_open": await self.is_market_open(),
                "status": "unknown",
            }

        return {
            "is_open": await self.is_market_open(),
            "status": data.get("marketState", [{}])[0].get("marketStatus", "unknown"),
            "timestamp": datetime.now(IST).isoformat(),
        }

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None

