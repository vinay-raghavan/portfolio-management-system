"""VWAP Reversion Strategy.

Volume Weighted Average Price (VWAP) mean reversion strategy.
Trades pullbacks to VWAP in trending markets.
"""

from datetime import datetime, time
from decimal import Decimal

import pandas as pd
from ta.volatility import AverageTrueRange

from engine.models.signals import SignalData, SignalType
from engine.strategies.base import BaseStrategy
from engine.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class VWAPReversionStrategy(BaseStrategy):
    """VWAP Mean Reversion Strategy.

    This strategy trades pullbacks to VWAP in trending markets.
    """

    name = "vwap_reversion"
    description = "VWAP Mean Reversion - Trade pullbacks to VWAP in trends"
    default_timeframe = "5m"

    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)

    def __init__(
        self,
        band_std_dev: float = 1.5,
        entry_zone_pct: float = 0.3,
        trend_lookback: int = 20,
        min_trend_strength: float = 0.3,
        require_band_touch: bool = True,
        atr_period: int = 14,
        atr_multiplier: float = 1.5,
        risk_reward_ratio: float = 2.0,
        max_distance_from_vwap_pct: float = 2.0,
        no_trade_after: str = "14:30",
    ):
        """Initialize VWAP Reversion strategy."""
        self.band_std_dev = band_std_dev
        self.entry_zone_pct = Decimal(str(entry_zone_pct))
        self.trend_lookback = trend_lookback
        self.min_trend_strength = min_trend_strength
        self.require_band_touch = require_band_touch
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))
        self.max_distance_pct = Decimal(str(max_distance_from_vwap_pct))
        self.no_trade_after = datetime.strptime(no_trade_after, "%H:%M").time()

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "band_std_dev": self.band_std_dev,
            "entry_zone_pct": float(self.entry_zone_pct),
            "trend_lookback": self.trend_lookback,
            "min_trend_strength": self.min_trend_strength,
            "require_band_touch": self.require_band_touch,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
            "max_distance_from_vwap_pct": float(self.max_distance_pct),
            "no_trade_after": self.no_trade_after.strftime("%H:%M"),
        }

    def _calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate VWAP and bands for intraday data."""
        df = df.copy()
        typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
        cumulative_tp_vol = (typical_price * df["Volume"]).cumsum()
        cumulative_vol = df["Volume"].cumsum()
        df["vwap"] = cumulative_tp_vol / cumulative_vol
        df["squared_diff"] = (typical_price - df["vwap"]) ** 2
        df["cumsum_sq_diff"] = df["squared_diff"].cumsum()
        df["variance"] = df["cumsum_sq_diff"] / (range(1, len(df) + 1))
        df["std_dev"] = df["variance"] ** 0.5
        df["upper_band"] = df["vwap"] + (self.band_std_dev * df["std_dev"])
        df["lower_band"] = df["vwap"] - (self.band_std_dev * df["std_dev"])
        return df

    def _detect_trend(self, df: pd.DataFrame) -> tuple[str, float]:
        """Detect intraday trend direction and strength."""
        if len(df) < self.trend_lookback:
            return "neutral", 0.0

        recent_df = df.tail(self.trend_lookback)
        vwap = recent_df["vwap"]
        close = recent_df["Close"]
        above_vwap = (close > vwap).sum()
        below_vwap = (close < vwap).sum()
        total = len(recent_df)

        if above_vwap > below_vwap:
            direction = "up"
            strength = (above_vwap - below_vwap) / total
        elif below_vwap > above_vwap:
            direction = "down"
            strength = (below_vwap - above_vwap) / total
        else:
            direction = "neutral"
            strength = 0.0

        return direction, min(1.0, strength)

    def _check_vwap_signal(
        self, df: pd.DataFrame, trend: str, trend_strength: float
    ) -> tuple[SignalType | None, Decimal, str]:
        """Check for VWAP reversion signal."""
        if trend == "neutral" or trend_strength < self.min_trend_strength:
            return None, Decimal("0"), "No clear trend"

        current = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else current
        close = self._to_decimal(current["Close"])
        vwap = self._to_decimal(current["vwap"])
        distance_pct = abs((close - vwap) / vwap) * 100

        if distance_pct > self.max_distance_pct:
            return None, Decimal("0"), f"Too far from VWAP ({distance_pct:.1f}%)"

        recent_low = df.tail(3)["Low"].min()
        recent_high = df.tail(3)["High"].max()
        touched_lower = recent_low <= current["lower_band"]
        touched_upper = recent_high >= current["upper_band"]

        if trend == "up":
            near_vwap = close <= vwap * (1 + self.entry_zone_pct / 100)
            bouncing = close > prev["Close"]
            if near_vwap and bouncing:
                if self.require_band_touch and not touched_lower:
                    return None, Decimal("0"), "No lower band touch"
                strength = Decimal(str(min(0.5 + trend_strength * 0.5, 1.0)))
                reason = f"Uptrend pullback to VWAP ({vwap:.2f}), bouncing"
                return SignalType.BUY, strength, reason

        if trend == "down":
            near_vwap = close >= vwap * (1 - self.entry_zone_pct / 100)
            rejecting = close < prev["Close"]
            if near_vwap and rejecting:
                if self.require_band_touch and not touched_upper:
                    return None, Decimal("0"), "No upper band touch"
                strength = Decimal(str(min(0.5 + trend_strength * 0.5, 1.0)))
                reason = f"Downtrend retrace to VWAP ({vwap:.2f}), rejecting"
                return SignalType.SELL, strength, reason

        return None, Decimal("0"), ""

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate VWAP reversion signals."""
        if df.empty or len(df) < max(self.trend_lookback, self.atr_period):
            return []

        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df.index = pd.to_datetime(df.index)

        current_time = df.index[-1].time()
        if current_time < self.MARKET_OPEN or current_time > self.no_trade_after:
            return []

        today = df.index[-1].date()
        today_df = df[df.index.date == today].copy()

        if len(today_df) < self.trend_lookback:
            return []

        today_df = self._calculate_vwap(today_df)
        trend, trend_strength = self._detect_trend(today_df)
        signal_type, strength, reason = self._check_vwap_signal(today_df, trend, trend_strength)

        if signal_type is None:
            return []

        atr = None
        if len(df) >= self.atr_period:
            atr_indicator = AverageTrueRange(
                df["High"], df["Low"], df["Close"], window=self.atr_period
            )
            atr_value = atr_indicator.average_true_range().iloc[-1]
            if not pd.isna(atr_value):
                atr = self._to_decimal(atr_value)

        current = today_df.iloc[-1]
        entry_price = self._to_decimal(current["Close"])
        vwap = self._to_decimal(current["vwap"])

        if atr:
            stop_distance = atr * self.atr_multiplier
        else:
            stop_distance = abs(entry_price - vwap) * Decimal("1.5")

        if signal_type == SignalType.BUY:
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance

        take_profit = self.calculate_take_profit(
            entry_price, stop_loss, signal_type, self.risk_reward_ratio
        )

        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = reward / risk if risk > 0 else Decimal("0")
        confidence = Decimal(str(0.4 + trend_strength * 0.4))

        signal = SignalData(
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            confidence=min(Decimal("0.9"), confidence),
            price_at_signal=entry_price,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            indicators={
                "vwap": float(vwap),
                "upper_band": float(current["upper_band"]),
                "lower_band": float(current["lower_band"]),
                "trend": trend,
                "trend_strength": round(trend_strength, 2),
                "atr": float(atr) if atr else None,
            },
            notes=reason,
        )

        return [signal]

