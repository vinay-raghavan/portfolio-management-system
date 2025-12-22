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

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for technical analysis calculations."""

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
            hist = None

            # If symbol already has a suffix, use as-is
            if "." in symbol_upper:
                hist = self._try_get_history(symbol_upper, period)
            else:
                # Try with Indian suffix first (if default market is Indian)
                default_market = getattr(settings, "DEFAULT_MARKET", "US").upper()
                if default_market in ("NSE", "IN", "INDIA"):
                    hist = self._try_get_history(f"{symbol_upper}.NS", period)
                    if hist is None:
                        # Fallback to US (no suffix)
                        hist = self._try_get_history(symbol_upper, period)
                elif default_market == "BSE":
                    hist = self._try_get_history(f"{symbol_upper}.BO", period)
                    if hist is None:
                        hist = self._try_get_history(symbol_upper, period)
                else:
                    # US market default
                    hist = self._try_get_history(symbol_upper, period)

            if hist is None:
                return None

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

            # Get info with proper market suffix handling
            info = None
            if "." in symbol_upper:
                info = self._try_get_ticker_info(symbol_upper)
            else:
                # Try with Indian suffix first (if default market is Indian)
                default_market = getattr(settings, "DEFAULT_MARKET", "US").upper()
                if default_market in ("NSE", "IN", "INDIA"):
                    info = self._try_get_ticker_info(f"{symbol_upper}.NS")
                    if not info:
                        info = self._try_get_ticker_info(symbol_upper)
                elif default_market == "BSE":
                    info = self._try_get_ticker_info(f"{symbol_upper}.BO")
                    if not info:
                        info = self._try_get_ticker_info(symbol_upper)
                else:
                    info = self._try_get_ticker_info(symbol_upper)

            if not info:
                info = {}

            current_price = Decimal(str(info.get("regularMarketPrice", 0)))

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
        """Get detailed stock information."""
        try:
            symbol_upper = symbol.upper().strip()
            info = None

            # If symbol already has a suffix, use as-is
            if "." in symbol_upper:
                info = self._try_get_ticker_info(symbol_upper)
            else:
                # Try with Indian suffix first (if default market is Indian)
                default_market = getattr(settings, "DEFAULT_MARKET", "US").upper()
                if default_market in ("NSE", "IN", "INDIA"):
                    info = self._try_get_ticker_info(f"{symbol_upper}.NS")
                    if not info:
                        # Fallback to US (no suffix)
                        info = self._try_get_ticker_info(symbol_upper)
                elif default_market == "BSE":
                    info = self._try_get_ticker_info(f"{symbol_upper}.BO")
                    if not info:
                        info = self._try_get_ticker_info(symbol_upper)
                else:
                    # US market default - try without suffix first
                    info = self._try_get_ticker_info(symbol_upper)

            if not info:
                return None

            return StockInfo(
                symbol=symbol_upper,
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
        except Exception as e:
            logger.error(f"Error getting stock info for {symbol}: {e}")
            return None
