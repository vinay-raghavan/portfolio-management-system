"""Concrete filter implementations for stock screener."""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.modules.screener.base import BaseFilter, FilterResult, FilterType, sanitize_for_json
from shared.providers.schemas import FundamentalData

logger = logging.getLogger(__name__)


@dataclass
class FundamentalCriteria:
    """Criteria for fundamental filter."""

    # Valuation
    max_pe: float | None = None
    min_pe: float | None = None
    max_pb: float | None = None
    min_pb: float | None = None
    max_ps: float | None = None
    max_peg: float | None = None
    # Growth
    min_eps_growth: float | None = None
    min_revenue_growth: float | None = None
    # Profitability
    min_profit_margin: float | None = None
    min_operating_margin: float | None = None
    min_roe: float | None = None
    min_roa: float | None = None
    # Dividends
    min_dividend_yield: float | None = None
    max_payout_ratio: float | None = None
    # Balance sheet
    max_debt_to_equity: float | None = None
    min_current_ratio: float | None = None
    # Other
    min_market_cap: float | None = None
    max_market_cap: float | None = None
    sectors: list[str] | None = None
    industries: list[str] | None = None


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
                metadata=sanitize_for_json(
                    {"avg_volume": avg_volume, "volume_ratio": volume_ratio}
                ),
            )
        except Exception as e:
            logger.error(f"Volume filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))


class MomentumFilter(BaseFilter):
    """Filter stocks by momentum criteria.

    Checks RSI, rate of change, and proximity to 52-week high/low.
    Supports Minervini Trend Template criteria.
    """

    filter_type = FilterType.MOMENTUM
    name = "momentum_filter"

    def configure(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        momentum_mode: str = "bullish",  # bullish, bearish, neutral
        near_52w_high_pct: float = 25,  # Within X% of 52-week high (Minervini: 25%)
        min_pct_above_52w_low: float = 0,  # Min % above 52-week low (Minervini: 30%)
        min_roc: float = 0,  # Minimum rate of change
        roc_period: int = 20,
        **kwargs,
    ) -> None:
        """Configure momentum filter.

        Args:
            rsi_period: RSI calculation period
            rsi_oversold: RSI level considered oversold
            rsi_overbought: RSI level considered overbought
            momentum_mode: 'bullish', 'bearish', or 'neutral'
            near_52w_high_pct: Max % below 52-week high (Minervini uses 25%)
            min_pct_above_52w_low: Min % above 52-week low (Minervini uses 30%)
            min_roc: Minimum rate of change percentage
            roc_period: Period for ROC calculation
        """
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.momentum_mode = momentum_mode
        self.near_52w_high_pct = near_52w_high_pct
        self.min_pct_above_52w_low = min_pct_above_52w_low
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
        # Need at least 200 days for reasonable 52-week calculations
        min_required = max(self.rsi_period, self.roc_period, 200)
        if len(data) < min_required:
            return FilterResult(
                passed=False,
                reason=f"Insufficient data for momentum ({len(data)} < {min_required})",
            )

        try:
            close = data["close"]
            current_price = close.iloc[-1]

            # Calculate RSI
            rsi = self._calculate_rsi(close, self.rsi_period)

            # Calculate Rate of Change
            roc = (
                (current_price - close.iloc[-self.roc_period]) / close.iloc[-self.roc_period]
            ) * 100

            # 52-week high/low (use all available data, up to 252 days)
            lookback_days = min(252, len(data))
            high_52w = data["high"].tail(lookback_days).max()
            low_52w = data["low"].tail(lookback_days).min()
            pct_from_high = ((high_52w - current_price) / high_52w) * 100
            pct_above_low = ((current_price - low_52w) / low_52w) * 100

            # Evaluate based on momentum mode
            passed = False
            score = 50.0
            reasons = []

            if self.momentum_mode == "bullish":
                # For bullish: prefer high RSI, near 52w high, positive ROC
                checks_passed = 0
                total_checks = 0

                # Check ROC
                if self.min_roc > 0:
                    total_checks += 1
                    if roc >= self.min_roc:
                        checks_passed += 1
                        reasons.append(f"ROC {roc:.1f}%")
                        score += 15

                # Check near 52-week high
                total_checks += 1
                if pct_from_high <= self.near_52w_high_pct:
                    checks_passed += 1
                    reasons.append(f"Near 52w high ({pct_from_high:.1f}% away)")
                    score += 15

                # Check above 52-week low (Minervini criteria)
                if self.min_pct_above_52w_low > 0:
                    total_checks += 1
                    if pct_above_low >= self.min_pct_above_52w_low:
                        checks_passed += 1
                        reasons.append(f"{pct_above_low:.0f}% above 52w low")
                        score += 10

                # RSI bonus
                if rsi > 50:
                    score += 10
                    reasons.append(f"RSI {rsi:.0f}")

                # Pass if at least one key check passes
                passed = checks_passed > 0

            elif self.momentum_mode == "bearish":
                # For bearish/pullback: prefer low RSI (oversold)
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
                metadata=sanitize_for_json(
                    {
                        "rsi": rsi,
                        "roc": roc,
                        "pct_from_52w_high": pct_from_high,
                        "pct_above_52w_low": pct_above_low,
                    }
                ),
            )
        except Exception as e:
            logger.error(f"Momentum filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))


class MovingAverageFilter(BaseFilter):
    """Filter stocks by moving average position.

    Checks if price is above/below key moving averages.
    Supports Minervini Trend Template with stacked MA verification.
    """

    filter_type = FilterType.MOVING_AVERAGE
    name = "moving_average_filter"

    def configure(
        self,
        short_ma: int = 50,
        mid_ma: int = 150,
        trend_ma: int = 200,
        require_above_trend: bool = True,
        require_stacked_ma: bool = False,
        require_trend_up: bool = False,
        trend_up_days: int = 22,
        require_ma_crossover: bool = False,
        **kwargs,
    ) -> None:
        """Configure moving average filter.

        Args:
            short_ma: Short-term MA period (default 50 for Minervini)
            mid_ma: Mid-term MA period (default 150 for Minervini)
            trend_ma: Long-term trend MA period (default 200)
            require_above_trend: Price must be above trend MA
            require_stacked_ma: Require 50 > 150 > 200 SMA stacking (Minervini)
            require_trend_up: Require 200 SMA to be trending upward
            trend_up_days: Days to check for 200 SMA uptrend (default ~1 month)
            require_ma_crossover: Require recent bullish crossover
        """
        self.short_ma = short_ma
        self.mid_ma = mid_ma
        self.trend_ma = trend_ma
        self.require_above_trend = require_above_trend
        self.require_stacked_ma = require_stacked_ma
        self.require_trend_up = require_trend_up
        self.trend_up_days = trend_up_days
        self.require_ma_crossover = require_ma_crossover

    def apply(self, symbol: str, data: pd.DataFrame) -> FilterResult:
        """Apply moving average filter."""
        min_data_needed = max(self.trend_ma, self.mid_ma) + self.trend_up_days + 5
        if len(data) < min_data_needed:
            return FilterResult(passed=False, reason="Insufficient data for MAs")

        try:
            close = data["close"]
            current_price = close.iloc[-1]

            # Calculate all MAs
            ma_short = close.rolling(self.short_ma).mean().iloc[-1]
            ma_mid = close.rolling(self.mid_ma).mean().iloc[-1]
            ma_trend = close.rolling(self.trend_ma).mean().iloc[-1]

            # Check price above all MAs
            above_short = current_price > ma_short
            above_mid = current_price > ma_mid
            above_trend = current_price > ma_trend

            # Check stacked MAs (Minervini: 50 > 150 > 200)
            stacked_ma = ma_short > ma_mid > ma_trend

            # Check 200 SMA trend direction
            ma_trend_series = close.rolling(self.trend_ma).mean()
            ma_trend_now = ma_trend_series.iloc[-1]
            ma_trend_past = ma_trend_series.iloc[-self.trend_up_days]
            trend_up = ma_trend_now > ma_trend_past

            # Check crossover (short MA crossed above mid MA recently)
            ma_short_series = close.rolling(self.short_ma).mean()
            ma_mid_series = close.rolling(self.mid_ma).mean()
            prev_diff = ma_short_series.iloc[-2] - ma_mid_series.iloc[-2]
            curr_diff = ma_short_series.iloc[-1] - ma_mid_series.iloc[-1]
            crossover = prev_diff < 0 and curr_diff > 0

            passed = True
            score = 50.0
            reasons = []

            # Check required conditions
            if self.require_above_trend:
                if above_trend:
                    score += 15
                    reasons.append(f"Above {self.trend_ma}MA")
                else:
                    passed = False
                    reasons.append(f"Below {self.trend_ma}MA")

            if self.require_stacked_ma:
                if stacked_ma:
                    score += 20
                    reasons.append(f"{self.short_ma}>{self.mid_ma}>{self.trend_ma} stacked")
                else:
                    passed = False
                    reasons.append("MAs not stacked")

            if self.require_trend_up:
                if trend_up:
                    score += 15
                    reasons.append(f"{self.trend_ma}MA trending up")
                else:
                    passed = False
                    reasons.append(f"{self.trend_ma}MA not trending up")

            # Bonus points for additional bullish signals
            if above_short and above_mid and above_trend:
                score += 10
                if f"Above {self.trend_ma}MA" not in reasons:
                    reasons.append("Above all MAs")

            if self.require_ma_crossover and not crossover:
                passed = False
                reasons.append("No recent crossover")
            elif crossover:
                score += 10
                reasons.append("Bullish crossover!")

            return FilterResult(
                passed=passed,
                score=min(100, score),
                reason="; ".join(reasons) if reasons else "MA check passed",
                metadata=sanitize_for_json(
                    {
                        "ma_short": ma_short,
                        "ma_mid": ma_mid,
                        "ma_trend": ma_trend,
                        "above_short": above_short,
                        "above_mid": above_mid,
                        "above_trend": above_trend,
                        "stacked_ma": stacked_ma,
                        "trend_up": trend_up,
                        "crossover": crossover,
                    }
                ),
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
                    metadata=sanitize_for_json(
                        {"range_high": range_high, "breakout_level": breakout_level}
                    ),
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
                metadata=sanitize_for_json(
                    {
                        "range_high": range_high,
                        "range_low": range_low,
                        "breakout_level": breakout_level,
                        "volume_ratio": volume_ratio,
                    }
                ),
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
                metadata=sanitize_for_json(
                    {
                        "range_high": range_high,
                        "range_low": range_low,
                        "range_pct": range_pct,
                        "range_position": range_position,
                        "volume_declining": vol_declining,
                    }
                ),
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
                metadata=sanitize_for_json(
                    {
                        "stock_roc": stock_roc,
                        "range_position": range_pos,
                        "lookback_period": self.lookback_period,
                    }
                ),
            )
        except Exception as e:
            logger.error(f"Sector performance filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))


class FundamentalFilter(BaseFilter):
    """Filter stocks by fundamental criteria.

    Evaluates stocks based on valuation, growth, profitability, dividends,
    and balance sheet metrics. This filter requires fundamental data to be
    passed via the metadata field of the DataFrame or as a separate parameter.
    """

    filter_type = FilterType.FUNDAMENTAL
    name = "fundamental_filter"

    def configure(
        self,
        criteria: FundamentalCriteria | None = None,
        # Valuation thresholds
        max_pe: float | None = None,
        min_pe: float | None = None,
        max_pb: float | None = None,
        min_pb: float | None = None,
        max_ps: float | None = None,
        max_peg: float | None = None,
        # Growth thresholds
        min_eps_growth: float | None = None,
        min_revenue_growth: float | None = None,
        # Profitability thresholds
        min_profit_margin: float | None = None,
        min_operating_margin: float | None = None,
        min_roe: float | None = None,
        min_roa: float | None = None,
        # Dividend thresholds
        min_dividend_yield: float | None = None,
        max_payout_ratio: float | None = None,
        # Balance sheet thresholds
        max_debt_to_equity: float | None = None,
        min_current_ratio: float | None = None,
        # Market cap filters
        min_market_cap: float | None = None,
        max_market_cap: float | None = None,
        # Sector/industry filters
        sectors: list[str] | None = None,
        industries: list[str] | None = None,
        **kwargs,
    ) -> None:
        """Configure fundamental filter.

        Can be configured with a FundamentalCriteria object or individual parameters.
        """
        if criteria:
            self.criteria = criteria
        else:
            self.criteria = FundamentalCriteria(
                max_pe=max_pe,
                min_pe=min_pe,
                max_pb=max_pb,
                min_pb=min_pb,
                max_ps=max_ps,
                max_peg=max_peg,
                min_eps_growth=min_eps_growth,
                min_revenue_growth=min_revenue_growth,
                min_profit_margin=min_profit_margin,
                min_operating_margin=min_operating_margin,
                min_roe=min_roe,
                min_roa=min_roa,
                min_dividend_yield=min_dividend_yield,
                max_payout_ratio=max_payout_ratio,
                max_debt_to_equity=max_debt_to_equity,
                min_current_ratio=min_current_ratio,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap,
                sectors=sectors,
                industries=industries,
            )

    def apply(self, symbol: str, data: pd.DataFrame) -> FilterResult:
        """Apply fundamental filter.

        Note: This filter requires fundamental data to be passed via apply_with_fundamentals().
        When called with just OHLCV data, it will return a neutral result.
        """
        return FilterResult(
            passed=True,
            score=50,
            reason="Use apply_with_fundamentals() for fundamental screening",
        )

    def apply_with_fundamentals(
        self, symbol: str, fundamentals: FundamentalData
    ) -> FilterResult:
        """Apply fundamental filter with fundamental data.

        Args:
            symbol: Stock symbol
            fundamentals: FundamentalData with valuation ratios and metrics

        Returns:
            FilterResult with pass/fail and score
        """
        try:
            checks_passed = 0
            total_checks = 0
            reasons = []
            score = 50.0
            metadata = {}

            # Valuation checks
            if self.criteria.max_pe is not None and fundamentals.pe_ratio is not None:
                total_checks += 1
                if fundamentals.pe_ratio <= self.criteria.max_pe:
                    checks_passed += 1
                    score += 5
                    reasons.append(f"P/E {fundamentals.pe_ratio:.1f} ≤ {self.criteria.max_pe}")
                else:
                    reasons.append(f"P/E {fundamentals.pe_ratio:.1f} > {self.criteria.max_pe}")
                metadata["pe_ratio"] = fundamentals.pe_ratio

            if self.criteria.min_pe is not None and fundamentals.pe_ratio is not None:
                total_checks += 1
                if fundamentals.pe_ratio >= self.criteria.min_pe:
                    checks_passed += 1
                else:
                    reasons.append(f"P/E {fundamentals.pe_ratio:.1f} < {self.criteria.min_pe}")

            if self.criteria.max_pb is not None and fundamentals.pb_ratio is not None:
                total_checks += 1
                if fundamentals.pb_ratio <= self.criteria.max_pb:
                    checks_passed += 1
                    score += 5
                    reasons.append(f"P/B {fundamentals.pb_ratio:.1f} ≤ {self.criteria.max_pb}")
                else:
                    reasons.append(f"P/B {fundamentals.pb_ratio:.1f} > {self.criteria.max_pb}")
                metadata["pb_ratio"] = fundamentals.pb_ratio

            if self.criteria.max_peg is not None and fundamentals.peg_ratio is not None:
                total_checks += 1
                if fundamentals.peg_ratio <= self.criteria.max_peg:
                    checks_passed += 1
                    score += 5
                metadata["peg_ratio"] = fundamentals.peg_ratio

            # Growth checks
            if self.criteria.min_eps_growth is not None and fundamentals.eps_growth_yoy is not None:
                total_checks += 1
                if fundamentals.eps_growth_yoy >= self.criteria.min_eps_growth:
                    checks_passed += 1
                    score += 10
                    reasons.append(f"EPS growth {fundamentals.eps_growth_yoy:.1f}%")
                metadata["eps_growth_yoy"] = fundamentals.eps_growth_yoy

            if self.criteria.min_revenue_growth is not None and fundamentals.revenue_growth_yoy is not None:
                total_checks += 1
                if fundamentals.revenue_growth_yoy >= self.criteria.min_revenue_growth:
                    checks_passed += 1
                    score += 10
                    reasons.append(f"Revenue growth {fundamentals.revenue_growth_yoy:.1f}%")
                metadata["revenue_growth_yoy"] = fundamentals.revenue_growth_yoy

            # Profitability checks
            if self.criteria.min_roe is not None and fundamentals.roe is not None:
                total_checks += 1
                if fundamentals.roe >= self.criteria.min_roe:
                    checks_passed += 1
                    score += 10
                    reasons.append(f"ROE {fundamentals.roe:.1f}%")
                metadata["roe"] = fundamentals.roe

            if self.criteria.min_profit_margin is not None and fundamentals.profit_margin is not None:
                total_checks += 1
                if fundamentals.profit_margin >= self.criteria.min_profit_margin:
                    checks_passed += 1
                    score += 5
                metadata["profit_margin"] = fundamentals.profit_margin

            # Dividend checks
            if self.criteria.min_dividend_yield is not None and fundamentals.dividend_yield is not None:
                total_checks += 1
                if fundamentals.dividend_yield >= self.criteria.min_dividend_yield:
                    checks_passed += 1
                    score += 10
                    reasons.append(f"Yield {fundamentals.dividend_yield:.2f}%")
                metadata["dividend_yield"] = fundamentals.dividend_yield

            # Balance sheet checks
            if self.criteria.max_debt_to_equity is not None and fundamentals.debt_to_equity is not None:
                total_checks += 1
                if fundamentals.debt_to_equity <= self.criteria.max_debt_to_equity:
                    checks_passed += 1
                    score += 5
                metadata["debt_to_equity"] = fundamentals.debt_to_equity

            if self.criteria.min_current_ratio is not None and fundamentals.current_ratio is not None:
                total_checks += 1
                if fundamentals.current_ratio >= self.criteria.min_current_ratio:
                    checks_passed += 1
                    score += 5
                metadata["current_ratio"] = fundamentals.current_ratio

            # Market cap checks
            if self.criteria.min_market_cap is not None and fundamentals.market_cap is not None:
                total_checks += 1
                if fundamentals.market_cap >= self.criteria.min_market_cap:
                    checks_passed += 1
                metadata["market_cap"] = fundamentals.market_cap

            if self.criteria.max_market_cap is not None and fundamentals.market_cap is not None:
                total_checks += 1
                if fundamentals.market_cap <= self.criteria.max_market_cap:
                    checks_passed += 1

            # Sector/industry checks
            if self.criteria.sectors is not None and fundamentals.sector is not None:
                total_checks += 1
                if fundamentals.sector in self.criteria.sectors:
                    checks_passed += 1
                    reasons.append(f"Sector: {fundamentals.sector}")
                metadata["sector"] = fundamentals.sector

            if self.criteria.industries is not None and fundamentals.industry is not None:
                total_checks += 1
                if fundamentals.industry in self.criteria.industries:
                    checks_passed += 1
                metadata["industry"] = fundamentals.industry

            # Determine pass/fail
            if total_checks == 0:
                return FilterResult(
                    passed=True,
                    score=50,
                    reason="No fundamental criteria specified",
                )

            passed = checks_passed == total_checks
            pass_rate = checks_passed / total_checks

            return FilterResult(
                passed=passed,
                score=min(100, score),
                reason="; ".join(reasons[:5]) if reasons else f"Passed {checks_passed}/{total_checks} checks",
                metadata=sanitize_for_json(metadata),
            )
        except Exception as e:
            logger.error(f"Fundamental filter error for {symbol}: {e}")
            return FilterResult(passed=False, reason=str(e))
