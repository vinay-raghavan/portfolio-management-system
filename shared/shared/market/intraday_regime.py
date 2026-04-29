"""Intraday Regime Detector.

Detects the intraday market direction by analyzing real-time signals
that the daily regime detector misses:
  1. Gap direction  — today's open vs yesterday's close
  2. VIX rate of change — VIX crush/spike signals risk-on/risk-off
  3. Opening price action — whether Nifty is extending or fading the gap

Returns an IntradayRegime that can override the daily regime for
INTRADAY (MIS) strategies.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class IntradayDirection(str, Enum):
    """Intraday regime classification."""

    BULLISH = "bullish"  # Favor LONG entries
    BEARISH = "bearish"  # Favor SHORT entries
    NEUTRAL = "neutral"  # No strong intraday bias — defer to daily regime


@dataclass
class IntradayRegimeData:
    """Result of intraday regime detection."""

    direction: IntradayDirection
    confidence: float  # 0-100
    gap_score: float  # -100 to +100
    vix_change_score: float  # -100 to +100
    price_action_score: float  # -100 to +100
    composite_score: float  # -100 to +100
    reasons: list[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)


# Thresholds
_BULLISH_THRESHOLD = 25
_BEARISH_THRESHOLD = -25


class IntradayRegimeDetector:
    """Detects intraday market direction using real-time signals.

    Designed to run inside the StrategyExecutor before signal generation
    for INTRADAY product-type strategies. Uses the same DataProvider
    already available in the executor.
    """

    def __init__(self, data_provider):
        """Initialize with a shared DataProvider instance."""
        self._provider = data_provider

    async def detect(self) -> IntradayRegimeData:
        """Run all intraday checks and return the regime."""
        gap_score, gap_reasons = await self._gap_score()
        vix_score, vix_reasons = await self._vix_change_score()
        pa_score, pa_reasons = await self._price_action_score()

        # Weights: gap(40%) + VIX change(35%) + price action(25%)
        composite = gap_score * 0.40 + vix_score * 0.35 + pa_score * 0.25

        if composite >= _BULLISH_THRESHOLD:
            direction = IntradayDirection.BULLISH
        elif composite <= _BEARISH_THRESHOLD:
            direction = IntradayDirection.BEARISH
        else:
            direction = IntradayDirection.NEUTRAL

        reasons = gap_reasons + vix_reasons + pa_reasons
        confidence = min(abs(composite), 100)

        data = IntradayRegimeData(
            direction=direction,
            confidence=confidence,
            gap_score=gap_score,
            vix_change_score=vix_score,
            price_action_score=pa_score,
            composite_score=round(composite, 1),
            reasons=reasons,
        )
        logger.info(
            f"Intraday regime: {direction.value} "
            f"(score={composite:.1f}, gap={gap_score:.0f}, "
            f"vix_chg={vix_score:.0f}, pa={pa_score:.0f})"
        )
        return data

    # ------------------------------------------------------------------
    # Signal 1 — Gap direction (today open vs yesterday close)
    # ------------------------------------------------------------------
    async def _gap_score(self) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 0.0
        try:
            bars = await self._provider.get_historical(
                symbol="^NSEI",
                interval="1d",
                period="5d",
            )
            if not bars or len(bars) < 2:
                reasons.append("Insufficient Nifty data for gap calc")
                return 0.0, reasons

            prev_close = float(bars[-2].close)
            today_open = float(bars[-1].open)
            gap_pct = ((today_open - prev_close) / prev_close) * 100

            if gap_pct >= 0.75:
                score = 100
            elif gap_pct >= 0.3:
                score = 60
            elif gap_pct > 0:
                score = 25
            elif gap_pct <= -0.75:
                score = -100
            elif gap_pct <= -0.3:
                score = -60
            elif gap_pct < 0:
                score = -25

            reasons.append(f"Gap: {gap_pct:+.2f}% (open {today_open:.0f} vs prev {prev_close:.0f})")
        except Exception as e:
            logger.warning(f"Gap score error: {e}")
            reasons.append(f"Gap calc error: {e}")
        return score, reasons

    # ------------------------------------------------------------------
    # Signal 2 — VIX rate of change (today vs yesterday)
    # ------------------------------------------------------------------
    async def _vix_change_score(self) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 0.0
        try:
            bars = await self._provider.get_historical(
                symbol="^INDIAVIX",
                interval="1d",
                period="5d",
            )
            if not bars or len(bars) < 2:
                reasons.append("VIX data insufficient for rate-of-change")
                return 0.0, reasons

            vix_prev = float(bars[-2].close)
            vix_now = float(bars[-1].close)
            vix_chg_pct = ((vix_now - vix_prev) / vix_prev) * 100

            # VIX crush = bullish; VIX spike = bearish
            if vix_chg_pct <= -15:
                score = 100  # Massive VIX crush — very bullish
            elif vix_chg_pct <= -8:
                score = 60
            elif vix_chg_pct <= -3:
                score = 30
            elif vix_chg_pct >= 15:
                score = -100  # Massive VIX spike — very bearish
            elif vix_chg_pct >= 8:
                score = -60
            elif vix_chg_pct >= 3:
                score = -30

            reasons.append(f"VIX change: {vix_chg_pct:+.1f}% ({vix_prev:.1f} → {vix_now:.1f})")
        except Exception as e:
            logger.warning(f"VIX change score error: {e}")
            reasons.append(f"VIX rate-of-change error: {e}")
        return score, reasons

    # ------------------------------------------------------------------
    # Signal 3 — Price action (is Nifty extending or fading the gap?)
    # ------------------------------------------------------------------
    async def _price_action_score(self) -> tuple[float, list[str]]:
        """Compare current price vs today's open to detect gap extension/fade."""
        reasons: list[str] = []
        score = 0.0
        try:
            bars = await self._provider.get_historical(
                symbol="^NSEI",
                interval="1d",
                period="5d",
            )
            if not bars or len(bars) < 2:
                reasons.append("Insufficient data for price action")
                return 0.0, reasons

            today = bars[-1]
            today_open = float(today.open)
            today_close = float(today.close)  # Latest available price
            today_high = float(today.high)
            today_low = float(today.low)
            prev_close = float(bars[-2].close)

            # Day range position: where is price within today's range?
            day_range = today_high - today_low
            if day_range > 0:
                range_pos = (today_close - today_low) / day_range
            else:
                range_pos = 0.5

            # Is the gap extending or fading?
            gap_up = today_open > prev_close
            extending = (gap_up and today_close > today_open) or (
                not gap_up and today_close < today_open
            )

            move_from_open = ((today_close - today_open) / today_open) * 100

            if extending and abs(move_from_open) > 0.3:
                # Gap is extending — strong trend day
                score = 80 if move_from_open > 0 else -80
                reasons.append(f"Gap extending: {move_from_open:+.2f}% from open")
            elif extending:
                score = 30 if move_from_open > 0 else -30
                reasons.append(f"Gap holding: {move_from_open:+.2f}% from open")
            else:
                # Gap fading
                score = -40 if gap_up else 40
                reasons.append(f"Gap fading: {move_from_open:+.2f}% from open")

            # Range position bonus
            if range_pos > 0.75:
                score += 20
                reasons.append(f"Trading near highs ({range_pos:.0%})")
            elif range_pos < 0.25:
                score -= 20
                reasons.append(f"Trading near lows ({range_pos:.0%})")

        except Exception as e:
            logger.warning(f"Price action score error: {e}")
            reasons.append(f"Price action error: {e}")
        return max(-100, min(100, score)), reasons
