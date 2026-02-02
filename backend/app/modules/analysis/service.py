"""Technical analysis service using ta library."""

import logging
from decimal import Decimal

import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands

from app.core.config import settings
from app.modules.analysis.schemas import (
    AnalysisResult,
    SignalStrength,
    StockInfo,
    TechnicalIndicators,
)
from app.providers.data import DataProvider, get_data_provider

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for technical analysis calculations."""

    def __init__(self, provider: DataProvider | None = None):
        """Initialize with optional custom data provider.

        Args:
            provider: Data provider instance. If None, uses default from config.
        """
        self._provider = provider or get_data_provider()

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Yahoo Finance.

        For Indian market (NSE/BSE), adds the appropriate suffix.
        For other markets, returns the symbol as-is.
        """
        symbol = symbol.upper().strip()

        # Already has Yahoo Finance suffix (international)
        if "." in symbol:
            return symbol

        # Check if default market is Indian
        default_market = getattr(settings, "DEFAULT_MARKET", "US").upper()
        if default_market in ("NSE", "IN", "INDIA"):
            # First try to check if it's a valid US stock by testing without suffix
            # Common US stocks don't need suffix - return as-is if it looks like US stock
            return f"{symbol}.NS"
        elif default_market == "BSE":
            return f"{symbol}.BO"

        return symbol

    def _normalize_symbol_with_fallback(self, symbol: str) -> tuple[str, bool]:
        """Normalize symbol with fallback detection.

        Returns:
            Tuple of (normalized_symbol, is_indian_stock)
        """
        symbol = symbol.upper().strip()

        # Already has Yahoo Finance suffix
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            return symbol, True

        # Other international suffix
        if "." in symbol:
            return symbol, False

        # For Indian market default, we need to try Indian first, then US
        default_market = getattr(settings, "DEFAULT_MARKET", "US").upper()
        if default_market in ("NSE", "IN", "INDIA"):
            return f"{symbol}.NS", True
        elif default_market == "BSE":
            return f"{symbol}.BO", True

        return symbol, False

    def _try_get_history(self, yahoo_symbol: str, period: str) -> pd.DataFrame | None:
        """Try to get ticker history, returns None if not found or empty."""
        try:
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period=period)
            if not hist.empty and len(hist) >= 50:
                return hist
        except Exception:
            pass
        return None

    async def get_technical_indicators(
        self, symbol: str, period: str = "6mo"
    ) -> TechnicalIndicators | None:
        """Calculate technical indicators for a symbol."""
        try:
            symbol_upper = symbol.upper().strip()

            # Use the configured data provider to fetch historical data
            ohlcv_list = await self._provider.get_historical(symbol_upper, period=period)

            if not ohlcv_list or len(ohlcv_list) < 50:
                logger.warning(
                    f"Insufficient data for {symbol}: got {len(ohlcv_list) if ohlcv_list else 0} bars"
                )
                return None

            # Convert OHLCV list to pandas DataFrame
            # Note: Convert Decimal to float for ta library compatibility
            hist = pd.DataFrame(
                [
                    {
                        "Open": float(bar.open),
                        "High": float(bar.high),
                        "Low": float(bar.low),
                        "Close": float(bar.close),
                        "Volume": int(bar.volume or 0),
                    }
                    for bar in ohlcv_list
                ]
            )

            close = hist["Close"]
            high = hist["High"]
            low = hist["Low"]
            volume = hist["Volume"]

            # Moving Averages
            sma_20 = SMAIndicator(close, window=20).sma_indicator().iloc[-1]
            sma_50 = SMAIndicator(close, window=50).sma_indicator().iloc[-1]
            sma_200 = (
                SMAIndicator(close, window=200).sma_indicator().iloc[-1]
                if len(close) >= 200
                else None
            )
            ema_12 = EMAIndicator(close, window=12).ema_indicator().iloc[-1]
            ema_26 = EMAIndicator(close, window=26).ema_indicator().iloc[-1]

            # MACD
            macd_indicator = MACD(close)
            macd = macd_indicator.macd().iloc[-1]
            macd_signal = macd_indicator.macd_signal().iloc[-1]
            macd_hist = macd_indicator.macd_diff().iloc[-1]

            # RSI
            rsi = RSIIndicator(close, window=14).rsi().iloc[-1]

            # Bollinger Bands
            bb = BollingerBands(close, window=20, window_dev=2)
            bb_upper = bb.bollinger_hband().iloc[-1]
            bb_middle = bb.bollinger_mavg().iloc[-1]
            bb_lower = bb.bollinger_lband().iloc[-1]

            # ATR
            atr = AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]

            # Volume SMA
            vol_sma = SMAIndicator(volume.astype(float), window=20).sma_indicator().iloc[-1]

            return TechnicalIndicators(
                symbol=symbol.upper(),
                sma_20=self._to_decimal(sma_20),
                sma_50=self._to_decimal(sma_50),
                sma_200=self._to_decimal(sma_200),
                ema_12=self._to_decimal(ema_12),
                ema_26=self._to_decimal(ema_26),
                macd=self._to_decimal(macd),
                macd_signal=self._to_decimal(macd_signal),
                macd_histogram=self._to_decimal(macd_hist),
                rsi_14=self._to_decimal(rsi),
                bb_upper=self._to_decimal(bb_upper),
                bb_middle=self._to_decimal(bb_middle),
                bb_lower=self._to_decimal(bb_lower),
                atr_14=self._to_decimal(atr),
                volume_sma_20=self._to_decimal(vol_sma),
            )
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return None

    async def get_analysis(self, symbol: str) -> AnalysisResult | None:
        """Get complete technical analysis for a symbol."""
        indicators = await self.get_technical_indicators(symbol)
        if indicators is None:
            return None

        try:
            symbol_upper = symbol.upper().strip()

            # Get current price from the configured data provider
            current_price = Decimal("0")
            price = await self._provider.get_current_price(symbol_upper)
            if price is not None:
                current_price = Decimal(str(price))

            # Determine signal based on indicators
            signal = self._calculate_signal(current_price, indicators)

            # Determine trend
            trend = self._determine_trend(current_price, indicators)

            # Calculate support/resistance (simplified)
            support_levels = []
            resistance_levels = []
            if indicators.bb_lower:
                support_levels.append(indicators.bb_lower)
            if indicators.sma_50:
                support_levels.append(indicators.sma_50)
            if indicators.bb_upper:
                resistance_levels.append(indicators.bb_upper)

            return AnalysisResult(
                symbol=symbol.upper(),
                current_price=current_price,
                indicators=indicators,
                signal=signal,
                support_levels=sorted(support_levels),
                resistance_levels=sorted(resistance_levels),
                trend=trend,
            )
        except Exception as e:
            logger.error(f"Error getting analysis for {symbol}: {e}")
            return None

    def _to_decimal(self, value) -> Decimal | None:
        """Convert value to Decimal, handling NaN."""
        if value is None or pd.isna(value):
            return None
        return Decimal(str(round(value, 4)))

    def _format_timestamp(self, value) -> str | None:
        """Convert Unix timestamp to ISO date string."""
        if value is None or pd.isna(value):
            return None
        try:
            from datetime import datetime

            return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            return None

    def _calculate_signal(self, price: Decimal, indicators: TechnicalIndicators) -> SignalStrength:
        """Calculate trading signal based on indicators."""
        buy_signals = 0
        sell_signals = 0
        total_signals = 0

        # RSI signals
        if indicators.rsi_14:
            total_signals += 1
            if indicators.rsi_14 < 30:
                buy_signals += 1
            elif indicators.rsi_14 > 70:
                sell_signals += 1

        # MACD signals
        if indicators.macd and indicators.macd_signal:
            total_signals += 1
            if indicators.macd > indicators.macd_signal:
                buy_signals += 1
            else:
                sell_signals += 1

        # Price vs SMA signals
        if indicators.sma_20:
            total_signals += 1
            if price > indicators.sma_20:
                buy_signals += 1
            else:
                sell_signals += 1

        # Calculate overall signal
        if buy_signals > sell_signals:
            signal = "BUY"
            strength = (
                Decimal(str(buy_signals / total_signals * 100)) if total_signals else Decimal("50")
            )
        elif sell_signals > buy_signals:
            signal = "SELL"
            strength = (
                Decimal(str(sell_signals / total_signals * 100)) if total_signals else Decimal("50")
            )
        else:
            signal = "HOLD"
            strength = Decimal("50")

        confidence = (
            Decimal(str(abs(buy_signals - sell_signals) / total_signals * 100))
            if total_signals
            else Decimal("0")
        )

        return SignalStrength(signal=signal, strength=strength, confidence=confidence)

    def _determine_trend(self, price: Decimal, indicators: TechnicalIndicators) -> str:
        """Determine overall trend."""
        bullish = 0
        bearish = 0

        if indicators.sma_20 and indicators.sma_50:
            if indicators.sma_20 > indicators.sma_50:
                bullish += 1
            else:
                bearish += 1

        if indicators.sma_50 and price > indicators.sma_50:
            bullish += 1
        elif indicators.sma_50:
            bearish += 1

        if bullish > bearish:
            return "BULLISH"
        elif bearish > bullish:
            return "BEARISH"
        return "NEUTRAL"

    def _try_get_ticker_info(self, yahoo_symbol: str) -> dict | None:
        """Try to get ticker info, returns None if not found."""
        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            if info and info.get("regularMarketPrice") is not None:
                return info
        except Exception:
            pass
        return None

    async def get_stock_info(self, symbol: str) -> StockInfo | None:
        """Get detailed stock information.

        Uses the configured data provider for quote data, with Yahoo Finance
        as fallback for fundamental data (P/E, market cap, analyst ratings).
        """
        try:
            symbol_upper = symbol.upper().strip()

            # Get basic info and quote from the configured data provider
            instrument_info = await self._provider.get_instrument_info(symbol_upper)
            quote = await self._provider.get_quote(symbol_upper)

            if not instrument_info and not quote:
                logger.warning(f"No data from provider for {symbol}, trying Yahoo fallback")
                # Fall back to Yahoo Finance for fundamental data
                return await self._get_stock_info_from_yahoo(symbol_upper)

            # Build StockInfo from provider data
            stock_info = StockInfo(
                symbol=symbol_upper,
                name=instrument_info.name if instrument_info else None,
                exchange=instrument_info.exchange if instrument_info else None,
                sector=instrument_info.sector if instrument_info else None,
                industry=instrument_info.industry if instrument_info else None,
                current_price=self._to_decimal(quote.price) if quote else None,
                previous_close=self._to_decimal(quote.close) if quote else None,
                open=self._to_decimal(quote.open) if quote else None,
                day_high=self._to_decimal(quote.high) if quote else None,
                day_low=self._to_decimal(quote.low) if quote else None,
                volume=quote.volume if quote else None,
            )

            # Try to enrich with Yahoo Finance fundamental data (P/E, market cap, etc.)
            # This is optional enrichment - provider data takes precedence for price info
            yahoo_info = await self._get_yahoo_fundamentals(symbol_upper)
            if yahoo_info:
                # Only add fields not already set from provider
                if stock_info.name is None:
                    stock_info.name = yahoo_info.get("longName") or yahoo_info.get("shortName")
                if stock_info.currency is None:
                    stock_info.currency = yahoo_info.get("currency")
                # Add fundamental data (provider doesn't have this)
                stock_info.week_52_high = self._to_decimal(yahoo_info.get("fiftyTwoWeekHigh"))
                stock_info.week_52_low = self._to_decimal(yahoo_info.get("fiftyTwoWeekLow"))
                stock_info.avg_volume = yahoo_info.get("averageVolume")
                stock_info.avg_volume_10d = yahoo_info.get("averageVolume10days")
                stock_info.market_cap = self._to_decimal(yahoo_info.get("marketCap"))
                stock_info.shares_outstanding = yahoo_info.get("sharesOutstanding")
                stock_info.float_shares = yahoo_info.get("floatShares")
                stock_info.pe_ratio = self._to_decimal(yahoo_info.get("trailingPE"))
                stock_info.forward_pe = self._to_decimal(yahoo_info.get("forwardPE"))
                stock_info.peg_ratio = self._to_decimal(yahoo_info.get("pegRatio"))
                stock_info.price_to_book = self._to_decimal(yahoo_info.get("priceToBook"))
                stock_info.eps = self._to_decimal(yahoo_info.get("trailingEps"))
                stock_info.forward_eps = self._to_decimal(yahoo_info.get("forwardEps"))
                stock_info.dividend_yield = self._to_decimal(yahoo_info.get("dividendYield"))
                stock_info.dividend_rate = self._to_decimal(yahoo_info.get("dividendRate"))
                stock_info.ex_dividend_date = self._format_timestamp(
                    yahoo_info.get("exDividendDate")
                )
                stock_info.target_mean_price = self._to_decimal(yahoo_info.get("targetMeanPrice"))
                stock_info.target_high_price = self._to_decimal(yahoo_info.get("targetHighPrice"))
                stock_info.target_low_price = self._to_decimal(yahoo_info.get("targetLowPrice"))
                stock_info.recommendation = yahoo_info.get("recommendationKey")
                stock_info.num_analyst_opinions = yahoo_info.get("numberOfAnalystOpinions")
                stock_info.beta = self._to_decimal(yahoo_info.get("beta"))
                stock_info.trailing_annual_return = self._to_decimal(
                    yahoo_info.get("trailingAnnualDividendYield")
                )

            return stock_info

        except Exception as e:
            logger.error(f"Error getting stock info for {symbol}: {e}")
            return None

    async def _get_yahoo_fundamentals(self, symbol: str) -> dict | None:
        """Get fundamental data from Yahoo Finance (for enrichment)."""
        default_market = getattr(settings, "DEFAULT_MARKET", "US").upper()
        yahoo_symbol = symbol

        if "." not in symbol:
            if default_market in ("NSE", "IN", "INDIA"):
                yahoo_symbol = f"{symbol}.NS"
            elif default_market == "BSE":
                yahoo_symbol = f"{symbol}.BO"

        info = self._try_get_ticker_info(yahoo_symbol)
        if not info and yahoo_symbol != symbol:
            # Try without suffix as fallback
            info = self._try_get_ticker_info(symbol)
        return info

    async def _get_stock_info_from_yahoo(self, symbol: str) -> StockInfo | None:
        """Full stock info from Yahoo Finance (fallback when provider fails)."""
        default_market = getattr(settings, "DEFAULT_MARKET", "US").upper()
        info = None

        if "." in symbol:
            info = self._try_get_ticker_info(symbol)
        else:
            if default_market in ("NSE", "IN", "INDIA"):
                info = self._try_get_ticker_info(f"{symbol}.NS")
                if not info:
                    info = self._try_get_ticker_info(symbol)
            elif default_market == "BSE":
                info = self._try_get_ticker_info(f"{symbol}.BO")
                if not info:
                    info = self._try_get_ticker_info(symbol)
            else:
                info = self._try_get_ticker_info(symbol)

        if not info:
            return None

        return StockInfo(
            symbol=symbol,
            name=info.get("longName") or info.get("shortName"),
            exchange=info.get("exchange"),
            currency=info.get("currency"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            current_price=self._to_decimal(info.get("regularMarketPrice")),
            previous_close=self._to_decimal(info.get("previousClose")),
            open=self._to_decimal(info.get("open")),
            day_high=self._to_decimal(info.get("dayHigh")),
            day_low=self._to_decimal(info.get("dayLow")),
            week_52_high=self._to_decimal(info.get("fiftyTwoWeekHigh")),
            week_52_low=self._to_decimal(info.get("fiftyTwoWeekLow")),
            volume=info.get("volume"),
            avg_volume=info.get("averageVolume"),
            avg_volume_10d=info.get("averageVolume10days"),
            market_cap=self._to_decimal(info.get("marketCap")),
            shares_outstanding=info.get("sharesOutstanding"),
            float_shares=info.get("floatShares"),
            pe_ratio=self._to_decimal(info.get("trailingPE")),
            forward_pe=self._to_decimal(info.get("forwardPE")),
            peg_ratio=self._to_decimal(info.get("pegRatio")),
            price_to_book=self._to_decimal(info.get("priceToBook")),
            eps=self._to_decimal(info.get("trailingEps")),
            forward_eps=self._to_decimal(info.get("forwardEps")),
            dividend_yield=self._to_decimal(info.get("dividendYield")),
            dividend_rate=self._to_decimal(info.get("dividendRate")),
            ex_dividend_date=self._format_timestamp(info.get("exDividendDate")),
            target_mean_price=self._to_decimal(info.get("targetMeanPrice")),
            target_high_price=self._to_decimal(info.get("targetHighPrice")),
            target_low_price=self._to_decimal(info.get("targetLowPrice")),
            recommendation=info.get("recommendationKey"),
            num_analyst_opinions=info.get("numberOfAnalystOpinions"),
            beta=self._to_decimal(info.get("beta")),
            trailing_annual_return=self._to_decimal(info.get("trailingAnnualDividendYield")),
        )
