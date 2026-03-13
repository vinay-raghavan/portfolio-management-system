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

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    pass

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
    NIFTY_SYMBOL = "NIFTY 50"
    NIFTY_BANK_SYMBOL = "NIFTY BANK"

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

    def __init__(self, db: AsyncSession):
        """Initialize the detector.

        Args:
            db: Database session for fetching market data
        """
        self.db = db

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

    async def _get_nifty_trend_score(self) -> tuple[float, list[str]]:
        """Get NIFTY 50 trend score based on price vs moving averages.

        Returns:
            Tuple of (score, reasons) where score is -100 to +100
        """
        reasons = []
        score = 0.0

        try:
            # Get NIFTY 50 data with moving averages
            result = await self.db.execute(
                text("""
                    SELECT
                        close,
                        sma_20,
                        sma_50,
                        sma_200,
                        high_52w,
                        low_52w
                    FROM market_data_daily
                    WHERE symbol = :symbol
                    ORDER BY date DESC
                    LIMIT 1
                """),
                {"symbol": self.NIFTY_SYMBOL},
            )
            row = result.fetchone()

            if not row:
                reasons.append("NIFTY 50 data not available")
                return 0.0, reasons

            close = float(row[0]) if row[0] else 0
            sma_20 = float(row[1]) if row[1] else close
            sma_50 = float(row[2]) if row[2] else close
            sma_200 = float(row[3]) if row[3] else close
            high_52w = float(row[4]) if row[4] else close
            low_52w = float(row[5]) if row[5] else close

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
        """Get market breadth score based on advance/decline ratio.

        Returns:
            Tuple of (score, reasons) where score is -100 to +100
        """
        reasons = []
        score = 0.0

        try:
            # Count stocks above/below key moving averages in NIFTY 500
            result = await self.db.execute(
                text("""
                    SELECT
                        COUNT(*) FILTER (WHERE close > sma_50) as above_50dma,
                        COUNT(*) FILTER (WHERE close < sma_50) as below_50dma,
                        COUNT(*) FILTER (WHERE close > sma_200) as above_200dma,
                        COUNT(*) FILTER (WHERE close < sma_200) as below_200dma,
                        COUNT(*) as total
                    FROM market_data_daily md
                    JOIN stocks s ON md.symbol = s.symbol
                    WHERE md.date = (SELECT MAX(date) FROM market_data_daily)
                    AND s.nifty_500 = true
                """)
            )
            row = result.fetchone()

            if not row or row[4] == 0:
                reasons.append("Breadth data not available")
                return 0.0, reasons

            above_50dma = row[0] or 0
            row[1] or 0
            above_200dma = row[2] or 0
            row[3] or 0
            total = row[4]

            # Calculate percentages
            pct_above_50dma = above_50dma / total * 100
            pct_above_200dma = above_200dma / total * 100

            # Score based on 50 DMA breadth (+/- 50 points)
            if pct_above_50dma > 70:
                score += 50
                reasons.append(f"Strong breadth: {pct_above_50dma:.0f}% above 50 DMA")
            elif pct_above_50dma > 50:
                score += 25
                reasons.append(f"Positive breadth: {pct_above_50dma:.0f}% above 50 DMA")
            elif pct_above_50dma < 30:
                score -= 50
                reasons.append(f"Weak breadth: only {pct_above_50dma:.0f}% above 50 DMA")
            elif pct_above_50dma < 50:
                score -= 25
                reasons.append(f"Negative breadth: {pct_above_50dma:.0f}% above 50 DMA")

            # Score based on 200 DMA breadth (+/- 50 points)
            if pct_above_200dma > 70:
                score += 50
                reasons.append(f"Strong LT breadth: {pct_above_200dma:.0f}% above 200 DMA")
            elif pct_above_200dma > 50:
                score += 25
                reasons.append(f"Positive LT breadth: {pct_above_200dma:.0f}% above 200 DMA")
            elif pct_above_200dma < 30:
                score -= 50
                reasons.append(f"Weak LT breadth: only {pct_above_200dma:.0f}% above 200 DMA")
            elif pct_above_200dma < 50:
                score -= 25
                reasons.append(f"Negative LT breadth: {pct_above_200dma:.0f}% above 200 DMA")

        except Exception as e:
            logger.warning(f"Error getting breadth score: {e}")
            reasons.append(f"Error fetching breadth data: {e}")

        return max(-100, min(100, score)), reasons

    async def _get_momentum_score(self) -> tuple[float, list[str]]:
        """Get momentum score based on NIFTY RSI and ROC.

        Returns:
            Tuple of (score, reasons) where score is -100 to +100
        """
        reasons = []
        score = 0.0

        try:
            # Get NIFTY momentum indicators
            result = await self.db.execute(
                text("""
                    SELECT
                        rsi_14,
                        roc_20
                    FROM market_data_daily
                    WHERE symbol = :symbol
                    ORDER BY date DESC
                    LIMIT 1
                """),
                {"symbol": self.NIFTY_SYMBOL},
            )
            row = result.fetchone()

            if not row:
                reasons.append("NIFTY momentum data not available")
                return 0.0, reasons

            rsi = float(row[0]) if row[0] else 50
            roc = float(row[1]) if row[1] else 0

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

    async def _get_volatility_score(self) -> tuple[float, list[str]]:
        """Get volatility score based on India VIX.

        Returns:
            Tuple of (score, reasons) where score is -100 to +100
            High VIX = negative score (bearish/fearful)
        """
        reasons = []
        score = 0.0

        try:
            # Get India VIX
            result = await self.db.execute(
                text("""
                    SELECT close
                    FROM market_data_daily
                    WHERE symbol = 'INDIA VIX'
                    ORDER BY date DESC
                    LIMIT 1
                """)
            )
            row = result.fetchone()

            if not row:
                reasons.append("India VIX data not available")
                return 0.0, reasons

            vix = float(row[0]) if row[0] else 15

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
