"""Fyers data provider implementation.

Provides market data from Fyers API including quotes, historical data,
and instrument information for Indian markets (NSE, BSE).
"""

import asyncio
import logging
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from ..schemas import OHLCV, InstrumentInfo, MarketSession, Quote, SearchResult
from ..symbols import Exchange, SymbolMapper
from .base import DataProvider

logger = logging.getLogger(__name__)

# Rate limiting configuration for Fyers API
# Fyers allows ~10 requests/second for historical data
FYERS_RATE_LIMIT_PER_SECOND = 8  # Stay below limit
FYERS_REQUEST_DELAY = 1.0 / FYERS_RATE_LIMIT_PER_SECOND  # ~0.125 seconds between requests

# Timezone definitions
IST = ZoneInfo("Asia/Kolkata")

# NSE market hours (IST)
NSE_PRE_MARKET_OPEN = time(9, 0)
NSE_PRE_MARKET_CLOSE = time(9, 8)
NSE_MARKET_OPEN = time(9, 15)
NSE_MARKET_CLOSE = time(15, 30)


class FyersDataProvider(DataProvider):
    """Data provider using Fyers API v3.

    Supports NSE and BSE markets with real-time quotes,
    historical data, and option chain data.

    Note: Requires valid Fyers access token obtained via OAuth flow.
    """

    name = "fyers"

    # Class-level rate limiter (shared across all instances)
    _rate_limit_lock: asyncio.Lock | None = None
    _last_request_time: float = 0.0

    def __init__(
        self,
        access_token: str | None = None,
        client_id: str | None = None,
        log_path: str = "",
    ):
        """Initialize Fyers data provider.

        Args:
            access_token: Fyers access token (from OAuth flow)
            client_id: Fyers client/app ID
            log_path: Optional path for Fyers SDK logs
        """
        self.client_id = client_id or ""
        self.access_token = access_token
        self.log_path = log_path
        self._fyers = None
        self.default_exchange = Exchange.NSE

    @classmethod
    async def _rate_limit(cls) -> None:
        """Apply rate limiting to avoid 429 errors from Fyers API."""
        if cls._rate_limit_lock is None:
            cls._rate_limit_lock = asyncio.Lock()

        async with cls._rate_limit_lock:
            import time

            now = time.monotonic()
            elapsed = now - cls._last_request_time
            if elapsed < FYERS_REQUEST_DELAY:
                await asyncio.sleep(FYERS_REQUEST_DELAY - elapsed)
            cls._last_request_time = time.monotonic()

    def _get_fyers_client(self):
        """Lazily create Fyers API client."""
        if self._fyers is None:
            if not self.access_token:
                raise ValueError("Fyers access token not configured. Complete OAuth flow first.")
            try:
                from fyers_apiv3 import fyersModel

                self._fyers = fyersModel.FyersModel(
                    token=self.access_token,
                    is_async=False,
                    client_id=self.client_id,
                    log_path=self.log_path,
                )
            except ImportError as e:
                logger.error(f"fyers-apiv3 package not installed: {e}")
                raise ImportError(
                    "fyers-apiv3 package is required. Install with: pip install fyers-apiv3"
                ) from e
        return self._fyers

    def set_access_token(self, access_token: str) -> None:
        """Set access token and reset client.

        Args:
            access_token: New access token from OAuth flow
        """
        self.access_token = access_token
        self._fyers = None  # Force recreation with new token

    # Mapping from Yahoo index symbols to Fyers format
    # Note: Fyers uses different symbol names than Yahoo
    INDEX_SYMBOL_MAP: dict[str, str] = {
        "^NSEI": "NSE:NIFTY50-INDEX",  # NIFTY 50
        "^BSESN": "BSE:SENSEX-INDEX",
        "^NSEBANK": "NSE:NIFTYBANK-INDEX",
        "^NSMIDCP": "NSE:NIFTYMIDCAP50-INDEX",
        "^NSEMDCP50": "NSE:NIFTYMIDCAP50-INDEX",
        "^CNXIT": "NSE:NIFTYIT-INDEX",
        "^CNX500": "NSE:NIFTY500-INDEX",
        "^CNXAUTO": "NSE:NIFTYAUTO-INDEX",
        "^CNXFIN": "NSE:NIFTYFINSERVICE-INDEX",
        "^CNXMETAL": "NSE:NIFTYMETAL-INDEX",
        "^CNXPHARMA": "NSE:NIFTYPHARMA-INDEX",
        "^CNXPSUBANK": "NSE:NIFTYPSUBANK-INDEX",
        "^CNXREALTY": "NSE:NIFTYREALTY-INDEX",
        "^CNXINFRA": "NSE:NIFTYINFRA-INDEX",
        "^CNXENERGY": "NSE:NIFTYENERGY-INDEX",
        "^CNXFMCG": "NSE:NIFTYFMCG-INDEX",
    }

    def normalize_symbol(self, symbol: str) -> str:
        """Convert symbol to Fyers format (EXCHANGE:SYMBOL-SEGMENT).

        Args:
            symbol: Stock symbol (e.g., "RELIANCE", "SBIN", "^NSEI")

        Returns:
            Fyers format symbol (e.g., "NSE:RELIANCE-EQ", "NSE:NIFTY50-INDEX")
        """
        symbol = symbol.upper().strip()

        # Already in Fyers format
        if ":" in symbol:
            return symbol

        # Handle Yahoo index symbols (start with ^)
        if symbol.startswith("^"):
            if symbol in self.INDEX_SYMBOL_MAP:
                return self.INDEX_SYMBOL_MAP[symbol]
            # Try to derive Fyers format for unknown indices
            # Remove .NS suffix if present and ^ prefix
            base = symbol.lstrip("^").replace(".NS", "")
            return f"NSE:{base}-INDEX"

        # Remove Yahoo .NS/.BO suffix
        if symbol.endswith(".NS"):
            symbol = symbol[:-3]
        elif symbol.endswith(".BO"):
            symbol = symbol[:-3]
            return f"BSE:{symbol}-EQ"

        # Default to NSE equity segment
        return f"NSE:{symbol}-EQ"

    def _parse_fyers_symbol(self, fyers_symbol: str) -> str:
        """Parse Fyers symbol format to base symbol.

        Args:
            fyers_symbol: Fyers format symbol (e.g., "NSE:RELIANCE-EQ")

        Returns:
            Base symbol (e.g., "RELIANCE")
        """
        # Remove exchange prefix and segment suffix
        if ":" in fyers_symbol:
            fyers_symbol = fyers_symbol.split(":")[1]
        if "-" in fyers_symbol:
            fyers_symbol = fyers_symbol.split("-")[0]
        return fyers_symbol

    def get_market_session(self) -> MarketSession:
        """Determine current market session based on IST time."""
        now = datetime.now(IST)
        if now.weekday() >= 5:  # Saturday or Sunday
            return MarketSession.CLOSED
        current_time = now.time()
        if NSE_PRE_MARKET_OPEN <= current_time < NSE_MARKET_OPEN:
            return MarketSession.PRE_MARKET
        elif NSE_MARKET_OPEN <= current_time <= NSE_MARKET_CLOSE:
            return MarketSession.REGULAR
        else:
            return MarketSession.CLOSED

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for a symbol."""
        try:
            # Apply rate limiting to avoid 429 errors
            await self._rate_limit()

            fyers = self._get_fyers_client()
            fyers_symbol = self.normalize_symbol(symbol)

            data = {"symbols": fyers_symbol}
            response = fyers.quotes(data)

            if response.get("code") != 200 or not response.get("d"):
                logger.error(f"Fyers quote error for {symbol}: {response}")
                return None

            quote_data = response["d"][0]["v"]
            base_symbol = self._parse_fyers_symbol(fyers_symbol)

            # Calculate change
            ltp = Decimal(str(quote_data.get("lp", 0)))
            prev_close = Decimal(str(quote_data.get("prev_close_price", 0)))
            change = ltp - prev_close if prev_close else None
            change_pct = (change / prev_close * 100) if change and prev_close else None

            return Quote(
                symbol=SymbolMapper.normalize(base_symbol),
                price=ltp,
                open=Decimal(str(quote_data.get("open_price", 0))) or None,
                high=Decimal(str(quote_data.get("high_price", 0))) or None,
                low=Decimal(str(quote_data.get("low_price", 0))) or None,
                close=prev_close or None,
                previous_close=prev_close or None,
                volume=quote_data.get("volume"),
                change=change,
                change_percent=change_pct,
                bid=Decimal(str(quote_data.get("bid", 0))) or None,
                ask=Decimal(str(quote_data.get("ask", 0))) or None,
                market_session=self.get_market_session(),
            )
        except Exception as e:
            logger.error(f"Error fetching Fyers quote for {symbol}: {e}")
            return None

    async def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[OHLCV]:
        """Get historical OHLCV data for a symbol.

        Args:
            symbol: Stock symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)

        Returns:
            List of OHLCV data points
        """
        try:
            # Apply rate limiting to avoid 429 errors
            await self._rate_limit()

            fyers = self._get_fyers_client()
            fyers_symbol = self.normalize_symbol(symbol)

            # Convert period to date range
            end_date = datetime.now(IST)
            period_days = {
                "1d": 1,
                "5d": 5,
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1y": 365,
                "2y": 730,
                "5y": 1825,
                "10y": 3650,
                "ytd": (end_date - datetime(end_date.year, 1, 1, tzinfo=IST)).days,
                "max": 3650,  # Default to 10 years for max
            }
            days = period_days.get(period, 30)
            start_date = end_date - timedelta(days=days)

            # Map interval to Fyers resolution
            resolution_map = {
                "1m": "1",
                "5m": "5",
                "15m": "15",
                "30m": "30",
                "1h": "60",
                "1d": "D",
                "1wk": "W",
                "1mo": "M",
            }
            resolution = resolution_map.get(interval, "D")

            # Fyers expects date format as YYYY-MM-DD
            data = {
                "symbol": fyers_symbol,
                "resolution": resolution,
                "date_format": "1",  # 0 for epoch, 1 for YYYY-MM-DD
                "range_from": start_date.strftime("%Y-%m-%d"),
                "range_to": end_date.strftime("%Y-%m-%d"),
                "cont_flag": "1",  # Continuous data
            }

            response = fyers.history(data)

            if response.get("code") != 200 or not response.get("candles"):
                logger.error(f"Fyers historical error for {symbol}: {response}")
                return []

            candles = response["candles"]
            result = []

            for candle in candles:
                # Fyers candle format: [timestamp, open, high, low, close, volume]
                timestamp = datetime.fromtimestamp(candle[0], tz=UTC)
                result.append(
                    OHLCV(
                        timestamp=timestamp,
                        open=Decimal(str(candle[1])),
                        high=Decimal(str(candle[2])),
                        low=Decimal(str(candle[3])),
                        close=Decimal(str(candle[4])),
                        volume=int(candle[5]),
                    )
                )

            return result

        except Exception as e:
            logger.error(f"Error fetching Fyers historical for {symbol}: {e}")
            return []

    async def search_symbols(self, query: str) -> list[SearchResult]:
        """Search for symbols matching query.

        Note: Fyers API doesn't have a direct search endpoint.
        This implementation uses the symbol master file approach.
        For now, returns empty list - implement with symbol master if needed.
        """
        logger.warning("Fyers search_symbols not fully implemented - use symbol master")
        return []

    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        """Get instrument information for a symbol."""
        try:
            # Apply rate limiting to avoid 429 errors
            await self._rate_limit()

            fyers = self._get_fyers_client()
            fyers_symbol = self.normalize_symbol(symbol)

            # Get quote data which includes some instrument info
            data = {"symbols": fyers_symbol}
            response = fyers.quotes(data)

            if response.get("code") != 200 or not response.get("d"):
                logger.error(f"Fyers instrument info error for {symbol}: {response}")
                return None

            quote_data = response["d"][0]["v"]
            base_symbol = self._parse_fyers_symbol(fyers_symbol)

            # Determine exchange from symbol
            exchange = Exchange.NSE
            if fyers_symbol.startswith("BSE:"):
                exchange = Exchange.BSE

            return InstrumentInfo(
                symbol=SymbolMapper.normalize(base_symbol),
                name=quote_data.get("short_name", base_symbol),
                exchange=exchange.value,
                instrument_type="EQ",  # Default to equity
                lot_size=1,
                tick_size=Decimal("0.05"),
            )

        except Exception as e:
            logger.error(f"Error fetching Fyers instrument info for {symbol}: {e}")
            return None

    async def get_option_chain(
        self,
        symbol: str,
        expiry_date: datetime | None = None,
    ) -> dict | None:
        """Get option chain data for a symbol.

        Args:
            symbol: Underlying symbol (e.g., "NIFTY", "BANKNIFTY")
            expiry_date: Optional specific expiry date

        Returns:
            Option chain data or None if not available
        """
        try:
            fyers = self._get_fyers_client()

            # Fyers option chain endpoint
            data = {
                "symbol": f"NSE:{symbol}-INDEX",
                "strikecount": 10,  # Number of strikes around ATM
                "timestamp": "",  # Empty for current expiry
            }

            response = fyers.optionchain(data)

            if response.get("code") != 200:
                logger.error(f"Fyers option chain error for {symbol}: {response}")
                return None

            return response.get("data")

        except Exception as e:
            logger.error(f"Error fetching Fyers option chain for {symbol}: {e}")
            return None
