"""Concrete filter implementations for stock screener."""

import logging

import numpy as np
import pandas as pd

from app.modules.screener.base import BaseFilter, FilterResult, FilterType

logger = logging.getLogger(__name__)


class VolumeFilter(BaseFilter):
    """Filter stocks by volume criteria.

    Checks for minimum average volume and volume spikes.
    """

    filter_type = FilterType.VOLUME
    name = "volume_filter"

    def configure(
        self,
        min_avg_volume: int = 100000,
        volume_lookback: int = 20,
        volume_spike_threshold: float = 1.5,
        require_spike: bool = False,
        **kwargs,
    ) -> None:
        """Configure volume filter.

        Args:
            min_avg_volume: Minimum average daily volume
            volume_lookback: Days to calculate average volume
            volume_spike_threshold: Multiplier for volume spike detection
            require_spike: Require volume spike to pass
        """
        self.min_avg_volume = min_avg_volume
        self.volume_lookback = volume_lookback
        self.volume_spike_threshold = volume_spike_threshold
        self.require_spike = require_spike

    def apply(self, symbol: str, data: pd.DataFrame) -> FilterResult:
        """Apply volume filter."""
        if len(data) < self.volume_lookback:
            return FilterResult(passed=False, reason="Insufficient data")

        if "volume" not in data.columns:
            return FilterResult(passed=False, reason="No volume data")

        try:
            avg_volume = data["volume"].tail(self.volume_lookback).mean()
            latest_volume = data["volume"].iloc[-1]
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0

            has_min_volume = avg_volume >= self.min_avg_volume
            has_spike = volume_ratio >= self.volume_spike_threshold

            if not has_min_volume:
                return FilterResult(
                    passed=False,
                    score=0,
                    reason=f"Avg volume {avg_volume:,.0f} below minimum {self.min_avg_volume:,}",
                )

            if self.require_spike and not has_spike:
                return FilterResult(
                    passed=False,
                    score=30,
                    reason=f"No volume spike (ratio: {volume_ratio:.2f}x)",
                )

            # Score based on volume quality
            vol_score = min(100, (avg_volume / self.min_avg_volume) * 50)
            spike_score = min(50, volume_ratio * 25) if has_spike else 0
            total_score = min(100, vol_score + spike_score)

            return FilterResult(
                passed=True,
                score=total_score,
                reason=f"Volume OK (avg: {avg_volume:,.0f}, ratio: {volume_ratio:.2f}x)",
                metadata={"avg_volume": avg_volume, "volume_ratio": volume_ratio},
            )
        except Exception as e:
            logger.error(f"Volume filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))


class MomentumFilter(BaseFilter):
    """Filter stocks by momentum criteria.

    Checks RSI, rate of change, and proximity to 52-week high/low.
    """

    filter_type = FilterType.MOMENTUM
    name = "momentum_filter"

    def configure(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        momentum_mode: str = "bullish",  # bullish, bearish, neutral
        near_52w_high_pct: float = 10,  # Within X% of 52-week high
        min_roc: float = 0,  # Minimum rate of change
        roc_period: int = 20,
        **kwargs,
    ) -> None:
        """Configure momentum filter."""
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.momentum_mode = momentum_mode
        self.near_52w_high_pct = near_52w_high_pct
        self.min_roc = min_roc
        self.roc_period = roc_period

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

    def apply(self, symbol: str, data: pd.DataFrame) -> FilterResult:
        """Apply momentum filter."""
        if len(data) < max(self.rsi_period, self.roc_period, 252):
            return FilterResult(passed=False, reason="Insufficient data for momentum")

        try:
            close = data["close"]
            current_price = close.iloc[-1]

            # Calculate RSI
            rsi = self._calculate_rsi(close, self.rsi_period)

            # Calculate Rate of Change
            roc = (
                (current_price - close.iloc[-self.roc_period]) / close.iloc[-self.roc_period]
            ) * 100

            # 52-week high/low
            high_52w = data["high"].tail(252).max()
            low_52w = data["low"].tail(252).min()
            pct_from_high = ((high_52w - current_price) / high_52w) * 100
            pct_from_low = ((current_price - low_52w) / low_52w) * 100

            # Evaluate based on momentum mode
            passed = False
            score = 50.0
            reasons = []

            if self.momentum_mode == "bullish":
                # For bullish: prefer high RSI, near 52w high, positive ROC
                if roc >= self.min_roc:
                    passed = True
                    reasons.append(f"ROC {roc:.1f}% >= {self.min_roc}%")
                    score += 20
                if pct_from_high <= self.near_52w_high_pct:
                    passed = True
                    reasons.append(f"Near 52w high ({pct_from_high:.1f}% away)")
                    score += 20
                if rsi > 50:
                    score += 10
                    reasons.append(f"RSI {rsi:.0f} bullish")
            elif self.momentum_mode == "bearish":
                # For bearish: prefer low RSI, near 52w low
                if rsi < self.rsi_oversold:
                    passed = True
                    reasons.append(f"RSI {rsi:.0f} oversold")
                    score += 30
            else:  # neutral
                passed = True
                reasons.append("Neutral momentum mode")

            return FilterResult(
                passed=passed,
                score=min(100, score),
                reason="; ".join(reasons) if reasons else "No momentum signal",
                metadata={
                    "rsi": rsi,
                    "roc": roc,
                    "pct_from_52w_high": pct_from_high,
                    "pct_from_52w_low": pct_from_low,
                },
            )
        except Exception as e:
            logger.error(f"Momentum filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))


class MovingAverageFilter(BaseFilter):
    """Filter stocks by moving average position.

    Checks if price is above/below key moving averages.
    """

    filter_type = FilterType.MOVING_AVERAGE
    name = "moving_average_filter"

    def configure(
        self,
        short_ma: int = 20,
        long_ma: int = 50,
        trend_ma: int = 200,
        require_above_trend: bool = True,
        require_ma_crossover: bool = False,
        **kwargs,
    ) -> None:
        """Configure moving average filter."""
        self.short_ma = short_ma
        self.long_ma = long_ma
        self.trend_ma = trend_ma
        self.require_above_trend = require_above_trend
        self.require_ma_crossover = require_ma_crossover

    def apply(self, symbol: str, data: pd.DataFrame) -> FilterResult:
        """Apply moving average filter."""
        if len(data) < self.trend_ma + 5:
            return FilterResult(passed=False, reason="Insufficient data for MAs")

        try:
            close = data["close"]
            current_price = close.iloc[-1]

            ma_short = close.rolling(self.short_ma).mean().iloc[-1]
            ma_long = close.rolling(self.long_ma).mean().iloc[-1]
            ma_trend = close.rolling(self.trend_ma).mean().iloc[-1]

            above_trend = current_price > ma_trend
            ma_bullish = ma_short > ma_long

            # Check crossover (short MA crossed above long MA recently)
            ma_short_series = close.rolling(self.short_ma).mean()
            ma_long_series = close.rolling(self.long_ma).mean()
            prev_diff = ma_short_series.iloc[-2] - ma_long_series.iloc[-2]
            curr_diff = ma_short_series.iloc[-1] - ma_long_series.iloc[-1]
            crossover = prev_diff < 0 and curr_diff > 0

            passed = True
            score = 50.0
            reasons = []

            if self.require_above_trend:
                if above_trend:
                    score += 25
                    reasons.append(f"Above {self.trend_ma}MA")
                else:
                    passed = False
                    reasons.append(f"Below {self.trend_ma}MA")

            if ma_bullish:
                score += 15
                reasons.append(f"{self.short_ma}MA > {self.long_ma}MA")

            if self.require_ma_crossover and not crossover:
                passed = False
                reasons.append("No recent crossover")
            elif crossover:
                score += 10
                reasons.append("Bullish crossover!")

            return FilterResult(
                passed=passed,
                score=min(100, score),
                reason="; ".join(reasons),
                metadata={
                    "ma_short": ma_short,
                    "ma_long": ma_long,
                    "ma_trend": ma_trend,
                    "above_trend": above_trend,
                    "crossover": crossover,
                },
            )
        except Exception as e:
            logger.error(f"MA filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))


class BreakoutFilter(BaseFilter):
    """Filter stocks showing breakout patterns.

    Detects price breaking out of recent range with volume confirmation.
    """

    filter_type = FilterType.BREAKOUT
    name = "breakout_filter"

    def configure(
        self,
        lookback_period: int = 20,
        breakout_pct: float = 2.0,  # % above range high
        volume_confirmation: float = 1.5,  # Volume multiplier
        **kwargs,
    ) -> None:
        """Configure breakout filter."""
        self.lookback_period = lookback_period
        self.breakout_pct = breakout_pct
        self.volume_confirmation = volume_confirmation

    def apply(self, symbol: str, data: pd.DataFrame) -> FilterResult:
        """Apply breakout filter."""
        if len(data) < self.lookback_period + 5:
            return FilterResult(passed=False, reason="Insufficient data")

        try:
            # Range before today
            range_data = data.iloc[-(self.lookback_period + 1) : -1]
            range_high = range_data["high"].max()
            range_low = range_data["low"].min()

            current_close = data["close"].iloc[-1]
            current_volume = data["volume"].iloc[-1]
            avg_volume = range_data["volume"].mean()

            # Check for breakout
            breakout_level = range_high * (1 + self.breakout_pct / 100)
            is_breakout = current_close >= breakout_level

            # Check volume confirmation
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            has_volume = volume_ratio >= self.volume_confirmation

            if not is_breakout:
                pct_to_breakout = ((breakout_level - current_close) / current_close) * 100
                return FilterResult(
                    passed=False,
                    score=max(0, 50 - pct_to_breakout * 10),
                    reason=f"No breakout ({pct_to_breakout:.1f}% to level)",
                    metadata={"range_high": range_high, "breakout_level": breakout_level},
                )

            score = 60.0
            reasons = [f"Breakout above {range_high:.2f}"]

            if has_volume:
                score += 30
                reasons.append(f"Volume confirmed ({volume_ratio:.1f}x)")
            else:
                score += 10
                reasons.append(f"Weak volume ({volume_ratio:.1f}x)")

            return FilterResult(
                passed=True,
                score=min(100, score),
                reason="; ".join(reasons),
                metadata={
                    "range_high": range_high,
                    "range_low": range_low,
                    "breakout_level": breakout_level,
                    "volume_ratio": volume_ratio,
                },
            )
        except Exception as e:
            logger.error(f"Breakout filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))


class ConsolidationFilter(BaseFilter):
    """Filter stocks in consolidation (potential breakout candidates).

    Detects tight trading ranges indicating potential big moves.
    """

    filter_type = FilterType.CONSOLIDATION
    name = "consolidation_filter"

    def configure(
        self,
        lookback_period: int = 20,
        max_range_pct: float = 10.0,  # Maximum range as % of price
        min_days_in_range: int = 5,
        declining_volume: bool = True,  # Volume should decrease in consolidation
        **kwargs,
    ) -> None:
        """Configure consolidation filter."""
        self.lookback_period = lookback_period
        self.max_range_pct = max_range_pct
        self.min_days_in_range = min_days_in_range
        self.declining_volume = declining_volume

    def apply(self, symbol: str, data: pd.DataFrame) -> FilterResult:
        """Apply consolidation filter."""
        if len(data) < self.lookback_period:
            return FilterResult(passed=False, reason="Insufficient data")

        try:
            recent_data = data.tail(self.lookback_period)
            range_high = recent_data["high"].max()
            range_low = recent_data["low"].min()
            range_pct = ((range_high - range_low) / range_low) * 100

            current_price = data["close"].iloc[-1]

            # Check if range is tight enough
            is_consolidating = range_pct <= self.max_range_pct

            # Check volume trend
            first_half_vol = recent_data["volume"].iloc[: self.lookback_period // 2].mean()
            second_half_vol = recent_data["volume"].iloc[self.lookback_period // 2 :].mean()
            vol_declining = second_half_vol < first_half_vol

            if not is_consolidating:
                return FilterResult(
                    passed=False,
                    score=max(0, 50 - (range_pct - self.max_range_pct) * 5),
                    reason=f"Range too wide ({range_pct:.1f}%)",
                )

            score = 60.0
            reasons = [f"Consolidating ({range_pct:.1f}% range)"]

            if self.declining_volume and vol_declining:
                score += 20
                reasons.append("Volume declining")

            # Bonus if price is near top of range (ready to break out)
            range_position = (current_price - range_low) / (range_high - range_low)
            if range_position > 0.7:
                score += 15
                reasons.append("Near top of range")

            return FilterResult(
                passed=True,
                score=min(100, score),
                reason="; ".join(reasons),
                metadata={
                    "range_high": range_high,
                    "range_low": range_low,
                    "range_pct": range_pct,
                    "range_position": range_position,
                    "volume_declining": vol_declining,
                },
            )
        except Exception as e:
            logger.error(f"Consolidation filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))


class SectorPerformanceFilter(BaseFilter):
    """Filter stocks based on their sector's relative performance.

    Finds stocks in sectors that are outperforming the market,
    then ranks stocks within those sectors.
    """

    filter_type = FilterType.PRICE_ACTION
    name = "sector_performance_filter"

    def configure(
        self,
        lookback_period: int = 20,
        min_sector_roc: float = 0,  # Minimum sector ROC %
        min_stock_vs_sector: float = 0,  # Stock outperformance vs sector
        require_sector_outperformance: bool = True,
        sector: str | None = None,  # Optional: filter specific sector
        **kwargs,
    ) -> None:
        """Configure sector performance filter.

        Args:
            lookback_period: Days to measure performance
            min_sector_roc: Minimum sector rate of change
            min_stock_vs_sector: Minimum stock outperformance vs sector
            require_sector_outperformance: Require sector to be positive
            sector: Optional specific sector to filter for
        """
        self.lookback_period = lookback_period
        self.min_sector_roc = min_sector_roc
        self.min_stock_vs_sector = min_stock_vs_sector
        self.require_sector_outperformance = require_sector_outperformance
        self.sector = sector

    def apply(self, symbol: str, data: pd.DataFrame) -> FilterResult:
        """Apply sector performance filter.

        Note: This filter primarily evaluates stock momentum. Sector data
        should be attached to the result metadata by the screener service
        when aggregating results.
        """
        if len(data) < self.lookback_period:
            return FilterResult(passed=False, reason="Insufficient data")

        try:
            close = data["close"]
            current_price = close.iloc[-1]
            past_price = close.iloc[-self.lookback_period]

            # Calculate stock's rate of change
            stock_roc = ((current_price - past_price) / past_price) * 100

            # Calculate strength relative to lookback
            high_point = close.tail(self.lookback_period).max()
            low_point = close.tail(self.lookback_period).min()
            range_pos = (
                (current_price - low_point) / (high_point - low_point)
                if high_point > low_point
                else 0.5
            )

            # Score based on momentum and range position
            passed = stock_roc > 0  # Basic positive momentum
            score = 50.0

            if stock_roc > 0:
                score += min(30, stock_roc * 3)  # Up to 30 points for ROC
            if range_pos > 0.7:
                score += 15  # Near high of range
            if stock_roc > 5:
                score += 5  # Strong momentum bonus

            reasons = [f"ROC: {stock_roc:.1f}%"]
            if range_pos > 0.7:
                reasons.append(f"Near high (pos: {range_pos:.0%})")

            return FilterResult(
                passed=passed,
                score=min(100, score),
                reason="; ".join(reasons),
                metadata={
                    "stock_roc": stock_roc,
                    "range_position": range_pos,
                    "lookback_period": self.lookback_period,
                },
            )
        except Exception as e:
            logger.error(f"Sector performance filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))
