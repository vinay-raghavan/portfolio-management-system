"""Price Action Volume Swing Strategy.

Swing trading strategy combining price action patterns with volume confirmation.
Identifies swing highs/lows, candlestick patterns, and volume expansion for entries.
"""

from decimal import Decimal

import pandas as pd
from ta.volatility import AverageTrueRange

from engine.models.signals import SignalData, SignalType
from engine.strategies.base import BaseStrategy
from engine.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class PriceActionVolumeSwingStrategy(BaseStrategy):
    """Price Action Volume Swing Strategy.

    This strategy combines multiple price action and volume concepts:
    1. Swing detection: Identify swing highs/lows using pivot points
    2. Candlestick patterns: Bullish/bearish engulfing, pin bars, inside bars
    3. Volume confirmation: Require above-average volume for signal validity
    4. Trend filter: Use EMA to filter trades in the direction of the trend

    Signal generation:
    - BUY: Bullish reversal pattern at swing low + volume confirmation + uptrend
    - SELL: Bearish reversal pattern at swing high + volume confirmation + downtrend

    Best suited for:
    - Swing trading on daily charts
    - Trend-following entries on pullbacks
    - Higher timeframe analysis (1D, 4H)
    """

    name = "price_action_volume_swing"
    description = "Price Action Volume Swing - Swing trading with candlestick patterns and volume"
    default_timeframe = "1d"

    def __init__(
        self,
        swing_lookback: int = 5,  # Bars to look back for swing detection
        ema_period: int = 50,  # EMA for trend filter
        volume_lookback: int = 20,  # Periods for average volume
        volume_multiplier: float = 1.2,  # Volume must be > avg * multiplier
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
        require_trend_alignment: bool = True,  # Require EMA trend filter
    ):
        """Initialize Price Action Volume Swing strategy."""
        self.swing_lookback = swing_lookback
        self.ema_period = ema_period
        self.volume_lookback = volume_lookback
        self.volume_multiplier = volume_multiplier
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))
        self.require_trend_alignment = require_trend_alignment

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "swing_lookback": self.swing_lookback,
            "ema_period": self.ema_period,
            "volume_lookback": self.volume_lookback,
            "volume_multiplier": self.volume_multiplier,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
            "require_trend_alignment": self.require_trend_alignment,
        }

    def _is_swing_low(self, df: pd.DataFrame, idx: int, lookback: int) -> bool:
        """Check if the bar at idx is a swing low."""
        if idx < lookback or idx >= len(df) - 1:
            return False
        low = df["Low"].iloc[idx]
        for i in range(1, lookback + 1):
            if df["Low"].iloc[idx - i] <= low:
                return False
        if df["Low"].iloc[idx + 1] <= low:
            return False
        return True

    def _is_swing_high(self, df: pd.DataFrame, idx: int, lookback: int) -> bool:
        """Check if the bar at idx is a swing high."""
        if idx < lookback or idx >= len(df) - 1:
            return False
        high = df["High"].iloc[idx]
        for i in range(1, lookback + 1):
            if df["High"].iloc[idx - i] >= high:
                return False
        if df["High"].iloc[idx + 1] >= high:
            return False
        return True

    def _is_bullish_engulfing(self, df: pd.DataFrame, idx: int) -> bool:
        """Detect bullish engulfing pattern at index idx."""
        if idx < 1:
            return False
        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        prev_bearish = prev["Close"] < prev["Open"]
        curr_bullish = curr["Close"] > curr["Open"]
        engulfs = curr["Close"] > prev["Open"] and curr["Open"] < prev["Close"]
        return prev_bearish and curr_bullish and engulfs

    def _is_bearish_engulfing(self, df: pd.DataFrame, idx: int) -> bool:
        """Detect bearish engulfing pattern at index idx."""
        if idx < 1:
            return False
        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        prev_bullish = prev["Close"] > prev["Open"]
        curr_bearish = curr["Close"] < curr["Open"]
        engulfs = curr["Open"] > prev["Close"] and curr["Close"] < prev["Open"]
        return prev_bullish and curr_bearish and engulfs

    def _is_bullish_pin_bar(self, df: pd.DataFrame, idx: int) -> bool:
        """Detect bullish pin bar (hammer) at index idx."""
        row = df.iloc[idx]
        body = abs(row["Close"] - row["Open"])
        full_range = row["High"] - row["Low"]
        if full_range == 0:
            return False
        lower_wick = min(row["Open"], row["Close"]) - row["Low"]
        upper_wick = row["High"] - max(row["Open"], row["Close"])
        return lower_wick >= 2 * body and upper_wick < body

    def _is_bearish_pin_bar(self, df: pd.DataFrame, idx: int) -> bool:
        """Detect bearish pin bar (shooting star) at index idx."""
        row = df.iloc[idx]
        body = abs(row["Close"] - row["Open"])
        full_range = row["High"] - row["Low"]
        if full_range == 0:
            return False
        lower_wick = min(row["Open"], row["Close"]) - row["Low"]
        upper_wick = row["High"] - max(row["Open"], row["Close"])
        return upper_wick >= 2 * body and lower_wick < body

    def _detect_pattern(self, df: pd.DataFrame, idx: int) -> tuple[str | None, bool]:
        """Detect candlestick pattern at index idx."""
        if self._is_bullish_engulfing(df, idx):
            return "bullish_engulfing", True
        if self._is_bearish_engulfing(df, idx):
            return "bearish_engulfing", False
        if self._is_bullish_pin_bar(df, idx):
            return "bullish_pin_bar", True
        if self._is_bearish_pin_bar(df, idx):
            return "bearish_pin_bar", False
        return None, False

    def _find_recent_swing(
        self, df: pd.DataFrame, is_low: bool, lookback: int = 20
    ) -> int | None:
        """Find the most recent swing high or low within lookback bars."""
        end_idx = len(df) - 2
        start_idx = max(self.swing_lookback, end_idx - lookback)
        for idx in range(end_idx, start_idx, -1):
            if is_low and self._is_swing_low(df, idx, self.swing_lookback):
                return idx
            if not is_low and self._is_swing_high(df, idx, self.swing_lookback):
                return idx
        return None

    def _calculate_strength(self, volume_confirmed: bool, near_swing: bool) -> Decimal:
        """Calculate signal strength based on confirmations."""
        strength = Decimal("0.5")
        if volume_confirmed:
            strength += Decimal("0.2")
        if near_swing:
            strength += Decimal("0.15")
        return strength.quantize(Decimal("0.0001"))

    def _calculate_confidence(self, df: pd.DataFrame, is_bullish: bool) -> Decimal:
        """Calculate confidence based on recent price action consistency."""
        if len(df) < 5:
            return Decimal("0.5")
        recent = df.tail(5)
        bullish_bars = (recent["Close"] > recent["Open"]).sum()
        if is_bullish:
            confidence = 0.4 + bullish_bars * 0.08
        else:
            bearish_bars = 5 - bullish_bars
            confidence = 0.4 + bearish_bars * 0.08
        return Decimal(str(min(0.9, confidence))).quantize(Decimal("0.0001"))

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate price action volume swing signals."""
        min_periods = max(self.ema_period, self.volume_lookback, self.atr_period) + 5
        if len(df) < min_periods:
            return []

        close = df["Close"]
        current_price = self._to_decimal(close.iloc[-1])
        if current_price is None:
            return []

        # Calculate indicators
        ema = close.ewm(span=self.ema_period, adjust=False).mean()
        avg_volume = df["Volume"].rolling(window=self.volume_lookback, min_periods=1).mean()
        current_volume = df["Volume"].iloc[-1]
        current_ema = ema.iloc[-1]

        # Check volume confirmation
        volume_threshold = avg_volume.iloc[-1] * self.volume_multiplier
        volume_confirmed = current_volume > volume_threshold

        # Determine trend
        is_uptrend = close.iloc[-1] > current_ema
        is_downtrend = close.iloc[-1] < current_ema

        # Detect pattern on the current bar
        pattern_name, is_bullish = self._detect_pattern(df, len(df) - 1)

        # Calculate ATR for stop loss
        atr = None
        if len(df) >= self.atr_period:
            atr_indicator = AverageTrueRange(
                df["High"], df["Low"], df["Close"], window=self.atr_period
            )
            atr_value = atr_indicator.average_true_range().iloc[-1]
            if not pd.isna(atr_value):
                atr = self._to_decimal(atr_value)

        # Find recent swing points for context
        recent_swing_low_idx = self._find_recent_swing(df, is_low=True)
        recent_swing_high_idx = self._find_recent_swing(df, is_low=False)
        near_swing_low = recent_swing_low_idx is not None and (len(df) - 1 - recent_swing_low_idx) <= 3
        near_swing_high = recent_swing_high_idx is not None and (len(df) - 1 - recent_swing_high_idx) <= 3

        # Build indicators dict
        indicators = {
            "ema": round(float(current_ema), 2),
            "volume": float(current_volume),
            "avg_volume": round(float(avg_volume.iloc[-1]), 2),
            "volume_confirmed": volume_confirmed,
            "pattern": pattern_name,
            "is_uptrend": is_uptrend,
            "near_swing_low": near_swing_low,
            "near_swing_high": near_swing_high,
            "atr": float(atr) if atr else None,
        }

        signals = []

        # BUY signal conditions
        buy_pattern = pattern_name in ("bullish_engulfing", "bullish_pin_bar")
        trend_ok_buy = not self.require_trend_alignment or is_uptrend
        buy_signal = buy_pattern and volume_confirmed and trend_ok_buy

        # SELL signal conditions
        sell_pattern = pattern_name in ("bearish_engulfing", "bearish_pin_bar")
        trend_ok_sell = not self.require_trend_alignment or is_downtrend
        sell_signal = sell_pattern and volume_confirmed and trend_ok_sell

        if buy_signal:
            strength = self._calculate_strength(volume_confirmed, near_swing_low)
            confidence = self._calculate_confidence(df, is_bullish=True)
            stop_loss = self.calculate_stop_loss(current_price, SignalType.BUY, atr, self.atr_multiplier)
            take_profit = self.calculate_take_profit(current_price, stop_loss, SignalType.BUY, self.risk_reward_ratio)

            signals.append(
                SignalData(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=strength,
                    confidence=confidence,
                    price_at_signal=current_price,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=self.risk_reward_ratio,
                    indicators=indicators,
                    notes=f"Bullish {pattern_name} with volume confirmation",
                )
            )
        elif sell_signal:
            strength = self._calculate_strength(volume_confirmed, near_swing_high)
            confidence = self._calculate_confidence(df, is_bullish=False)
            stop_loss = self.calculate_stop_loss(current_price, SignalType.SELL, atr, self.atr_multiplier)
            take_profit = self.calculate_take_profit(current_price, stop_loss, SignalType.SELL, self.risk_reward_ratio)

            signals.append(
                SignalData(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    strength=strength,
                    confidence=confidence,
                    price_at_signal=current_price,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=self.risk_reward_ratio,
                    indicators=indicators,
                    notes=f"Bearish {pattern_name} with volume confirmation",
                )
            )
        else:
            hold_note = "No actionable pattern"
            if pattern_name and not volume_confirmed:
                hold_note = f"{pattern_name} detected but volume not confirmed"
            elif pattern_name and self.require_trend_alignment:
                hold_note = f"{pattern_name} detected but against trend"

            signals.append(
                SignalData(
                    symbol=symbol,
                    signal_type=SignalType.HOLD,
                    strength=Decimal("0.5"),
                    confidence=Decimal("0.5"),
                    price_at_signal=current_price,
                    entry_price=None,
                    stop_loss=None,
                    take_profit=None,
                    risk_reward_ratio=None,
                    indicators=indicators,
                    notes=hold_note,
                )
            )

        return signals

