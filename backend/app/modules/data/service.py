"""Market data service using yfinance."""

from datetime import datetime, timedelta
from decimal import Decimal
import logging

import yfinance as yf

from app.modules.data.schemas import (
    StockQuote,
    StockInfo,
    HistoricalDataPoint,
    HistoricalDataResponse,
)

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching market data."""

    async def get_current_price(self, symbol: str) -> Decimal | None:
        """Get current price for a symbol."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            if price:
                return Decimal(str(price))
            return None
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    async def get_quote(self, symbol: str) -> StockQuote | None:
        """Get full quote for a symbol."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            price = info.get("regularMarketPrice") or info.get("currentPrice")
            if not price:
                return None

            prev_close = info.get("regularMarketPreviousClose", 0)
            change = Decimal(str(price)) - Decimal(str(prev_close)) if prev_close else None
            change_pct = (change / Decimal(str(prev_close)) * 100) if change and prev_close else None

            return StockQuote(
                symbol=symbol.upper(),
                price=Decimal(str(price)),
                open=Decimal(str(info.get("regularMarketOpen", 0))) or None,
                high=Decimal(str(info.get("regularMarketDayHigh", 0))) or None,
                low=Decimal(str(info.get("regularMarketDayLow", 0))) or None,
                close=Decimal(str(prev_close)) if prev_close else None,
                volume=info.get("regularMarketVolume"),
                change=change,
                change_pct=change_pct,
            )
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    async def get_stock_info(self, symbol: str) -> StockInfo | None:
        """Get detailed stock information."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return StockInfo(
                symbol=symbol.upper(),
                name=info.get("longName") or info.get("shortName"),
                exchange=info.get("exchange"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                market_cap=Decimal(str(info.get("marketCap", 0))) or None,
                pe_ratio=Decimal(str(info.get("trailingPE", 0))) or None,
                dividend_yield=Decimal(str(info.get("dividendYield", 0) or 0)) * 100 or None,
                fifty_two_week_high=Decimal(str(info.get("fiftyTwoWeekHigh", 0))) or None,
                fifty_two_week_low=Decimal(str(info.get("fiftyTwoWeekLow", 0))) or None,
            )
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            return None

    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> HistoricalDataResponse | None:
        """Get historical price data."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return None

            data_points = []
            for idx, row in hist.iterrows():
                data_points.append(
                    HistoricalDataPoint(
                        date=idx.to_pydatetime(),
                        open=Decimal(str(row["Open"])),
                        high=Decimal(str(row["High"])),
                        low=Decimal(str(row["Low"])),
                        close=Decimal(str(row["Close"])),
                        volume=int(row["Volume"]),
                    )
                )

            return HistoricalDataResponse(
                symbol=symbol.upper(),
                interval=interval,
                data=data_points,
            )
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None

    async def search_symbols(self, query: str) -> list[dict]:
        """Search for symbols by name or ticker."""
        # yfinance doesn't have a native search, so we use a simple approach
        # In production, consider using a dedicated search API
        try:
            ticker = yf.Ticker(query)
            info = ticker.info
            if info.get("symbol"):
                return [{
                    "symbol": info.get("symbol"),
                    "name": info.get("longName") or info.get("shortName"),
                    "exchange": info.get("exchange"),
                    "type": info.get("quoteType"),
                }]
            return []
        except Exception:
            return []

