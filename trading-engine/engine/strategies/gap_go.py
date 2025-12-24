"""Gap and Go Strategy.

An intraday strategy that trades opening gaps in the direction of the gap.
"""

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from enum import Enum

import pandas as pd
from ta.volatility import AverageTrueRange

from engine.models.signals import SignalData, SignalType
from engine.strategies.base import BaseStrategy
from engine.strategies.registry import StrategyRegistry


class GapType(str, Enum):
    """Type of gap."""
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"
    NO_GAP = "no_gap"


@dataclass
class GapInfo:
    """Information about an opening gap."""
    gap_type: GapType
    gap_size: Decimal
    gap_pct: Decimal
    prev_close: Decimal
    open_price: Decimal
    is_full_gap: bool


@StrategyRegistry.register
class GapAndGoStrategy(BaseStrategy):
    """Gap and Go Strategy - Trade in direction of opening gaps."""

    name = "gap_go"
    description = "Gap and Go - Trade in direction of opening gaps"
    default_timeframe = "5m"

    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)

    def __init__(
        self,
        min_gap_pct: float = 1.0,
        max_gap_pct: float = 8.0,
        require_confirmation: bool = True,
        confirmation_candles: int = 1,
        prefer_full_gaps: bool = True,
        volume_confirmation: float = 1.5,
        atr_period: int = 14,
        stop_loss_method: str = "gap_midpoint",
        atr_multiplier: float = 1.5,
        risk_reward_ratio: float = 2.0,
        max_fill_target: bool = True,
        no_trade_after: str = "11:00",
    ):
        """Initialize Gap and Go strategy."""
        self.min_gap_pct = Decimal(str(min_gap_pct))
        self.max_gap_pct = Decimal(str(max_gap_pct))
        self.require_confirmation = require_confirmation
        self.confirmation_candles = confirmation_candles
        self.prefer_full_gaps = prefer_full_gaps
        self.volume_confirmation = volume_confirmation
        self.atr_period = atr_period
        self.stop_loss_method = stop_loss_method
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))
        self.max_fill_target = max_fill_target
        self.no_trade_after = datetime.strptime(no_trade_after, "%H:%M").time()

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "min_gap_pct": float(self.min_gap_pct),
            "max_gap_pct": float(self.max_gap_pct),
            "require_confirmation": self.require_confirmation,
            "confirmation_candles": self.confirmation_candles,
            "prefer_full_gaps": self.prefer_full_gaps,
            "volume_confirmation": self.volume_confirmation,
            "atr_period": self.atr_period,
            "stop_loss_method": self.stop_loss_method,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
            "max_fill_target": self.max_fill_target,
            "no_trade_after": self.no_trade_after.strftime("%H:%M"),
        }

    def _detect_gap(self, df: pd.DataFrame, target_date: datetime) -> GapInfo | None:
        """Detect opening gap for a given date."""
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df.index = pd.to_datetime(df.index)

        target_date = target_date.date() if hasattr(target_date, "date") else target_date
        today_df = df[df.index.date == target_date]

        all_dates = sorted(set(df.index.date))
        try:
            target_idx = all_dates.index(target_date)
            if target_idx == 0:
                return None
            prev_date = all_dates[target_idx - 1]
        except ValueError:
            return None

        prev_df = df[df.index.date == prev_date]
        if today_df.empty or prev_df.empty:
            return None

        prev_close = self._to_decimal(prev_df["Close"].iloc[-1])
        prev_high = self._to_decimal(prev_df["High"].max())
        prev_low = self._to_decimal(prev_df["Low"].min())
        today_open = self._to_decimal(today_df["Open"].iloc[0])

        gap_size = today_open - prev_close
        gap_pct = (gap_size / prev_close) * 100 if prev_close > 0 else Decimal("0")

        if abs(gap_pct) < self.min_gap_pct:
            return GapInfo(
                gap_type=GapType.NO_GAP, gap_size=gap_size, gap_pct=gap_pct,
                prev_close=prev_close, open_price=today_open, is_full_gap=False
            )

        if gap_pct > 0:
            gap_type = GapType.GAP_UP
            is_full_gap = today_open > prev_high
        else:
            gap_type = GapType.GAP_DOWN
            is_full_gap = today_open < prev_low

        return GapInfo(
            gap_type=gap_type, gap_size=abs(gap_size), gap_pct=abs(gap_pct),
            prev_close=prev_close, open_price=today_open, is_full_gap=is_full_gap
        )

    def _check_confirmation(
        self, df: pd.DataFrame, gap: GapInfo, avg_volume: float
    ) -> tuple[bool, Decimal, str]:
        """Check if gap has confirmation from first candle(s)."""
        if len(df) < self.confirmation_candles:
            return False, Decimal("0"), "Insufficient candles"

        confirm_candles = df.iloc[: self.confirmation_candles]
        confirm_volume = confirm_candles["Volume"].sum()
        has_volume = confirm_volume >= (
            avg_volume * self.volume_confirmation * self.confirmation_candles
        )

        first_open = confirm_candles["Open"].iloc[0]
        last_close = confirm_candles["Close"].iloc[-1]

        if gap.gap_type == GapType.GAP_UP:
            is_confirmed = last_close >= first_open
            reason = f"Gap up {gap.gap_pct:.1f}%"
            reason += ", bullish confirmation" if is_confirmed else ", no confirmation"
        else:
            is_confirmed = last_close <= first_open
            reason = f"Gap down {gap.gap_pct:.1f}%"
            reason += ", bearish confirmation" if is_confirmed else ", no confirmation"

        if has_volume:
            reason += " (strong volume)"

        strength = Decimal("0.5")
        if is_confirmed:
            strength += Decimal("0.2")
        if has_volume:
            strength += Decimal("0.15")
        if gap.is_full_gap:
            strength += Decimal("0.15")

        return is_confirmed, min(Decimal("1.0"), strength), reason

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate Gap and Go signals."""
        if df.empty or len(df) < self.atr_period:
            return []

        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df.index = pd.to_datetime(df.index)

        current_time = df.index[-1]
        current_time_only = current_time.time()

        if current_time_only < self.MARKET_OPEN or current_time_only > self.no_trade_after:
            return []

        gap = self._detect_gap(df, current_time)
        if gap is None or gap.gap_type == GapType.NO_GAP:
            return []

        if gap.gap_pct > self.max_gap_pct:
            return []

        today = current_time.date()
        today_df = df[df.index.date == today]

        if len(today_df) < self.confirmation_candles:
            return []

        prev_df = df[df.index.date < today]
        avg_volume = prev_df["Volume"].mean() if not prev_df.empty else today_df["Volume"].mean()

        if self.require_confirmation:
            confirmed, strength, reason = self._check_confirmation(today_df, gap, avg_volume)
            if not confirmed:
                return []
        else:
            strength = Decimal("0.6") if gap.is_full_gap else Decimal("0.5")
            reason = f"Gap {'up' if gap.gap_type == GapType.GAP_UP else 'down'} {gap.gap_pct:.1f}%"

        signal_type = SignalType.BUY if gap.gap_type == GapType.GAP_UP else SignalType.SELL

        atr = None
        if len(df) >= self.atr_period:
            atr_indicator = AverageTrueRange(
                df["High"], df["Low"], df["Close"], window=self.atr_period
            )
            atr_value = atr_indicator.average_true_range().iloc[-1]
            if not pd.isna(atr_value):
                atr = self._to_decimal(atr_value)

        entry_price = self._to_decimal(today_df["Close"].iloc[-1])

        if self.stop_loss_method == "gap_midpoint":
            stop_loss = (gap.open_price + gap.prev_close) / 2
        elif self.stop_loss_method == "prev_close":
            stop_loss = gap.prev_close
        elif self.stop_loss_method == "atr" and atr:
            stop_distance = atr * self.atr_multiplier
            if signal_type == SignalType.BUY:
                stop_loss = entry_price - stop_distance
            else:
                stop_loss = entry_price + stop_distance
        else:
            stop_loss = (gap.open_price + gap.prev_close) / 2

        if self.max_fill_target:
            if signal_type == SignalType.BUY:
                take_profit = entry_price + gap.gap_size
            else:
                take_profit = entry_price - gap.gap_size
        else:
            take_profit = self.calculate_take_profit(
                entry_price, stop_loss, signal_type, self.risk_reward_ratio
            )

        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = reward / risk if risk > 0 else Decimal("0")

        confidence = Decimal("0.5")
        if gap.is_full_gap:
            confidence += Decimal("0.2")
        if gap.gap_pct >= Decimal("2.0"):
            confidence += Decimal("0.1")

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
                "gap_type": gap.gap_type.value,
                "gap_size": float(gap.gap_size),
                "gap_pct": float(gap.gap_pct),
                "prev_close": float(gap.prev_close),
                "open_price": float(gap.open_price),
                "is_full_gap": gap.is_full_gap,
                "atr": float(atr) if atr else None,
            },
            notes=reason,
        )

        return [signal]

