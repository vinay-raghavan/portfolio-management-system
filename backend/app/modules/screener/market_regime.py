"""Market Regime Detection Module.

Detects whether the market is in a bullish, bearish, or neutral regime
based on multiple indicators:
- NIFTY 50 trend (price vs moving averages)
- Market breadth (advance/decline ratio)
- Momentum indicators (RSI, ROC)
- Volatility (India VIX levels)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from shared.providers.data.base import DataProviderBase

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Market regime classification."""

    STRONGLY_BULLISH = "strongly_bullish"  # Strong uptrend, buy aggressively
    BULLISH = "bullish"  # Uptrend, favor longs
    NEUTRAL = "neutral"  # Choppy/sideways, reduce exposure
    BEARISH = "bearish"  # Downtrend, favor shorts
    STRONGLY_BEARISH = "strongly_bearish"  # Strong downtrend, short aggressively


@dataclass
class MarketRegimeData:
    """Market regime detection result."""

    regime: MarketRegime
    confidence: float  # 0-100
    nifty_trend_score: float  # -100 to +100
    breadth_score: float  # -100 to +100
    momentum_score: float  # -100 to +100
    volatility_score: float  # -100 to +100 (negative = high VIX = bearish)
    composite_score: float  # -100 to +100
    reasons: list[str]
    detected_at: datetime


class MarketRegimeDetector:
    """Detects current market regime based on multiple factors."""

    # Index symbol for regime detection
    NIFTY_SYMBOL = "NIFTY"  # Use NIFTY for Yahoo Finance
    NIFTY_SYMBOL_ALT = "^NSEI"  # Yahoo Finance symbol for NIFTY 50
    NIFTY_BANK_SYMBOL = "^NSEBANK"

    # Thresholds for regime classification
    STRONGLY_BULLISH_THRESHOLD = 50
    BULLISH_THRESHOLD = 20
    BEARISH_THRESHOLD = -20
    STRONGLY_BEARISH_THRESHOLD = -50

    # VIX thresholds
    VIX_LOW = 12  # Low volatility, bullish
    VIX_MEDIUM = 18  # Normal volatility
    VIX_HIGH = 25  # High volatility, bearish
    VIX_EXTREME = 35  # Extreme fear

    def __init__(self, db: AsyncSession, data_provider: "DataProviderBase | None" = None):
        """Initialize the detector.

        Args:
            db: Database session for fetching market data
            data_provider: Optional data provider for fetching market data
        """
        self.db = db
        self._data_provider = data_provider

    async def detect_regime(self) -> MarketRegimeData:
        """Detect current market regime.

        Returns:
            MarketRegimeData with regime classification and scores
        """
        reasons = []

        # 1. Get NIFTY 50 trend score
        nifty_trend_score, trend_reasons = await self._get_nifty_trend_score()
        reasons.extend(trend_reasons)

        # 2. Get market breadth score
        breadth_score, breadth_reasons = await self._get_breadth_score()
        reasons.extend(breadth_reasons)

        # 3. Get momentum score
        momentum_score, momentum_reasons = await self._get_momentum_score()
        reasons.extend(momentum_reasons)

        # 4. Get volatility score (VIX)
        volatility_score, vix_reasons = await self._get_volatility_score()
        reasons.extend(vix_reasons)

        # 5. Calculate composite score (weighted average)
        composite_score = (
            nifty_trend_score * 0.35  # Trend is most important
            + breadth_score * 0.25  # Breadth confirms trend
            + momentum_score * 0.25  # Momentum shows strength
            + volatility_score * 0.15  # VIX as fear gauge
        )

        # 6. Classify regime
        regime = self._classify_regime(composite_score)

        # 7. Calculate confidence
        confidence = min(abs(composite_score), 100)

        return MarketRegimeData(
            regime=regime,
            confidence=confidence,
            nifty_trend_score=nifty_trend_score,
            breadth_score=breadth_score,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            composite_score=composite_score,
            reasons=reasons,
            detected_at=datetime.now(),
        )

    def _classify_regime(self, composite_score: float) -> MarketRegime:
        """Classify regime based on composite score."""
        if composite_score >= self.STRONGLY_BULLISH_THRESHOLD:
            return MarketRegime.STRONGLY_BULLISH
        elif composite_score >= self.BULLISH_THRESHOLD:
            return MarketRegime.BULLISH
        elif composite_score <= self.STRONGLY_BEARISH_THRESHOLD:
            return MarketRegime.STRONGLY_BEARISH
        elif composite_score <= self.BEARISH_THRESHOLD:
            return MarketRegime.BEARISH
        else:
            return MarketRegime.NEUTRAL

    async def _get_data_provider(self) -> "DataProviderBase":
        """Get or create a data provider."""
        if self._data_provider:
            return self._data_provider

        from shared.providers.data import get_data_provider

        self._data_provider = get_data_provider("yahoo")
        return self._data_provider

    async def _get_nifty_trend_score(self) -> tuple[float, list[str]]:
        """Get NIFTY 50 trend score based on price vs moving averages.

        Returns:
            Tuple of (score, reasons) where score is -100 to +100
        """
        reasons = []
        score = 0.0

        try:
            provider = await self._get_data_provider()

            # Fetch NIFTY historical data (250 days for 200 DMA + buffer)
            history = await provider.get_historical(
                symbol=self.NIFTY_SYMBOL_ALT,  # ^NSEI for Yahoo
                interval="1d",
                days=300,
            )

            if not history or len(history) < 50:
                reasons.append("NIFTY 50 data not available or insufficient")
                return 0.0, reasons

            # Calculate current price and moving averages
            closes = [float(bar.close) for bar in history]
            close = closes[-1]

            # Calculate SMAs
            sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else close
            sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else close
            sma_200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else close

            # Calculate 52-week high/low (252 trading days)
            prices_52w = closes[-252:] if len(closes) >= 252 else closes
            high_52w = max(prices_52w)
            low_52w = min(prices_52w)

            # Score components
            # 1. Price vs 50 DMA (+/- 30 points)
            if close > sma_50 * 1.02:
                score += 30
                reasons.append(f"NIFTY above 50 DMA ({close:.0f} > {sma_50:.0f})")
            elif close < sma_50 * 0.98:
                score -= 30
                reasons.append(f"NIFTY below 50 DMA ({close:.0f} < {sma_50:.0f})")

            # 2. Price vs 200 DMA (+/- 30 points)
            if close > sma_200 * 1.02:
                score += 30
                reasons.append(f"NIFTY above 200 DMA ({close:.0f} > {sma_200:.0f})")
            elif close < sma_200 * 0.98:
                score -= 30
                reasons.append(f"NIFTY below 200 DMA ({close:.0f} < {sma_200:.0f})")

            # 3. MA alignment (+/- 20 points)
            if sma_20 > sma_50 > sma_200:
                score += 20
                reasons.append("Bullish MA alignment (20 > 50 > 200)")
            elif sma_20 < sma_50 < sma_200:
                score -= 20
                reasons.append("Bearish MA alignment (20 < 50 < 200)")

            # 4. Distance from 52-week high/low (+/- 20 points)
            range_52w = high_52w - low_52w if high_52w > low_52w else 1
            position_in_range = (close - low_52w) / range_52w

            if position_in_range > 0.8:
                score += 20
                reasons.append(f"NIFTY near 52-week high ({position_in_range:.0%})")
            elif position_in_range < 0.2:
                score -= 20
                reasons.append(f"NIFTY near 52-week low ({position_in_range:.0%})")

        except Exception as e:
            logger.warning(f"Error getting NIFTY trend score: {e}")
            reasons.append(f"Error fetching NIFTY data: {e}")

        return max(-100, min(100, score)), reasons

    async def _get_breadth_score(self) -> tuple[float, list[str]]:
        """Get market breadth score.

        Note: Since we don't have a breadth database, we use NIFTY trend
        as a proxy. Breadth analysis requires individual stock data which
        is expensive to fetch for regime detection.

        Returns:
            Tuple of (score, reasons) where score is -100 to +100
        """
        reasons = []
        # For now, return neutral score until we have breadth data
        # TODO: Implement proper breadth analysis with cached stock data
        reasons.append("Breadth analysis skipped (using NIFTY trend as proxy)")
        return 0.0, reasons

    async def _get_momentum_score(self) -> tuple[float, list[str]]:
        """Get momentum score based on NIFTY RSI and ROC.

        Returns:
            Tuple of (score, reasons) where score is -100 to +100
        """
        reasons = []
        score = 0.0

        try:
            provider = await self._get_data_provider()

            # Fetch NIFTY historical data for momentum calculation
            history = await provider.get_historical(
                symbol=self.NIFTY_SYMBOL_ALT,  # ^NSEI for Yahoo
                interval="1d",
                days=30,
            )

            if not history or len(history) < 20:
                reasons.append("NIFTY momentum data not available")
                return 0.0, reasons

            closes = [float(bar.close) for bar in history]

            # Calculate RSI (14-period)
            rsi = self._calculate_rsi(closes, 14)

            # Calculate ROC (20-period)
            roc = ((closes[-1] - closes[-20]) / closes[-20]) * 100 if len(closes) >= 20 else 0

            # RSI score (+/- 50 points)
            if rsi > 70:
                score += 30  # Overbought but still bullish
                reasons.append(f"NIFTY RSI overbought ({rsi:.0f})")
            elif rsi > 55:
                score += 50
                reasons.append(f"NIFTY RSI bullish ({rsi:.0f})")
            elif rsi < 30:
                score -= 30  # Oversold but still bearish
                reasons.append(f"NIFTY RSI oversold ({rsi:.0f})")
            elif rsi < 45:
                score -= 50
                reasons.append(f"NIFTY RSI bearish ({rsi:.0f})")

            # ROC score (+/- 50 points)
            if roc > 5:
                score += 50
                reasons.append(f"Strong NIFTY momentum (ROC: +{roc:.1f}%)")
            elif roc > 0:
                score += 25
                reasons.append(f"Positive NIFTY momentum (ROC: +{roc:.1f}%)")
            elif roc < -5:
                score -= 50
                reasons.append(f"Strong negative momentum (ROC: {roc:.1f}%)")
            elif roc < 0:
                score -= 25
                reasons.append(f"Negative NIFTY momentum (ROC: {roc:.1f}%)")

        except Exception as e:
            logger.warning(f"Error getting momentum score: {e}")
            reasons.append(f"Error fetching momentum data: {e}")

        return max(-100, min(100, score)), reasons

    def _calculate_rsi(self, closes: list[float], period: int = 14) -> float:
        """Calculate RSI from close prices."""
        if len(closes) < period + 1:
            return 50.0  # Default to neutral

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    async def _get_volatility_score(self) -> tuple[float, list[str]]:
        """Get volatility score based on India VIX.

        Returns:
            Tuple of (score, reasons) where score is -100 to +100
            High VIX = negative score (bearish/fearful)
        """
        reasons = []
        score = 0.0

        try:
            provider = await self._get_data_provider()

            # Try to fetch India VIX
            try:
                history = await provider.get_historical(
                    symbol="^INDIAVIX",  # Yahoo Finance symbol
                    interval="1d",
                    days=5,
                )

                if history and len(history) > 0:
                    vix = float(history[-1].close)
                else:
                    # VIX data not available, return neutral
                    reasons.append("India VIX data not available")
                    return 0.0, reasons
            except Exception:
                # VIX data not available, return neutral
                reasons.append("India VIX data not available")
                return 0.0, reasons

            # VIX score (inverted - low VIX = bullish)
            if vix < self.VIX_LOW:
                score += 50
                reasons.append(f"Low VIX ({vix:.1f}) - complacency/bullish")
            elif vix < self.VIX_MEDIUM:
                score += 25
                reasons.append(f"Normal VIX ({vix:.1f}) - stable conditions")
            elif vix > self.VIX_EXTREME:
                score -= 75
                reasons.append(f"Extreme VIX ({vix:.1f}) - panic/highly bearish")
            elif vix > self.VIX_HIGH:
                score -= 50
                reasons.append(f"High VIX ({vix:.1f}) - fear/bearish")
            else:
                score -= 25
                reasons.append(f"Elevated VIX ({vix:.1f}) - caution")

        except Exception as e:
            logger.warning(f"Error getting volatility score: {e}")
            reasons.append(f"Error fetching VIX data: {e}")

        return max(-100, min(100, score)), reasons
