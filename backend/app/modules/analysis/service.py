"""Technical analysis service using ta library."""

from decimal import Decimal
import logging

import pandas as pd
import yfinance as yf
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

from app.modules.analysis.schemas import (
    TechnicalIndicators,
    SignalStrength,
    AnalysisResult,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for technical analysis calculations."""

    async def get_technical_indicators(
        self, symbol: str, period: str = "6mo"
    ) -> TechnicalIndicators | None:
        """Calculate technical indicators for a symbol."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty or len(hist) < 50:
                return None

            close = hist["Close"]
            high = hist["High"]
            low = hist["Low"]
            volume = hist["Volume"]

            # Moving Averages
            sma_20 = SMAIndicator(close, window=20).sma_indicator().iloc[-1]
            sma_50 = SMAIndicator(close, window=50).sma_indicator().iloc[-1]
            sma_200 = SMAIndicator(close, window=200).sma_indicator().iloc[-1] if len(close) >= 200 else None
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
            ticker = yf.Ticker(symbol)
            info = ticker.info
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

    def _calculate_signal(
        self, price: Decimal, indicators: TechnicalIndicators
    ) -> SignalStrength:
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
            strength = Decimal(str(buy_signals / total_signals * 100)) if total_signals else Decimal("50")
        elif sell_signals > buy_signals:
            signal = "SELL"
            strength = Decimal(str(sell_signals / total_signals * 100)) if total_signals else Decimal("50")
        else:
            signal = "HOLD"
            strength = Decimal("50")

        confidence = Decimal(str(abs(buy_signals - sell_signals) / total_signals * 100)) if total_signals else Decimal("0")

        return SignalStrength(signal=signal, strength=strength, confidence=confidence)

    def _determine_trend(
        self, price: Decimal, indicators: TechnicalIndicators
    ) -> str:
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

