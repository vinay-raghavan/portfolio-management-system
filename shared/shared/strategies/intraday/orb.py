"""Opening Range Breakout (ORB) Strategy.

An intraday strategy that trades breakouts from the opening range.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

import pandas as pd
from ta.volatility import AverageTrueRange

from shared.models.signals import SignalData, SignalType
from shared.strategies.base import BaseStrategy
from shared.strategies.registry import StrategyRegistry


@dataclass
class OpeningRange:
    """Opening range data structure."""

    high: Decimal
    low: Decimal
    range_size: Decimal
    range_pct: Decimal
    open_price: Decimal
    start_time: datetime
    end_time: datetime


@StrategyRegistry.register
class ORBStrategy(BaseStrategy):
    """Opening Range Breakout Strategy."""

    name = "orb"
    description = "Opening Range Breakout - Trade breakouts from first N minutes"
    default_timeframe = "5m"

    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)

    def __init__(
        self,
        range_minutes: int = 15,
        breakout_buffer_pct: float = 0.1,
        require_close_breakout: bool = True,
        volume_confirmation: float = 1.2,
        atr_period: int = 14,
        stop_loss_method: str = "range",
        stop_loss_pct: float = 0.5,
        atr_multiplier: float = 1.5,
        risk_reward_ratio: float = 2.0,
        max_entries_per_day: int = 2,
        no_trade_after: str = "14:00",
    ):
        """Initialize ORB strategy."""
        self.range_minutes = range_minutes
        self.breakout_buffer_pct = Decimal(str(breakout_buffer_pct))
        self.require_close_breakout = require_close_breakout
        self.volume_confirmation = volume_confirmation
        self.atr_period = atr_period
        self.stop_loss_method = stop_loss_method
        self.stop_loss_pct = Decimal(str(stop_loss_pct))
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))
        self.max_entries_per_day = max_entries_per_day
        self.no_trade_after = datetime.strptime(no_trade_after, "%H:%M").time()
        self._daily_entries: dict[str, int] = {}

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "range_minutes": self.range_minutes,
            "breakout_buffer_pct": float(self.breakout_buffer_pct),
            "require_close_breakout": self.require_close_breakout,
            "volume_confirmation": self.volume_confirmation,
            "atr_period": self.atr_period,
            "stop_loss_method": self.stop_loss_method,
            "stop_loss_pct": float(self.stop_loss_pct),
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
            "max_entries_per_day": self.max_entries_per_day,
            "no_trade_after": self.no_trade_after.strftime("%H:%M"),
        }

    def _calculate_opening_range(
        self, df: pd.DataFrame, target_date: datetime | None = None
    ) -> OpeningRange | None:
        """Calculate the opening range for a given date."""
        if df.empty:
            return None

        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df.index = pd.to_datetime(df.index)

        if target_date is None:
            target_date = df.index[-1].date()
        else:
            target_date = target_date.date() if hasattr(target_date, "date") else target_date

        day_data = df[df.index.date == target_date]
        if day_data.empty:
            return None

        market_open = datetime.combine(target_date, self.MARKET_OPEN)
        range_end = market_open + timedelta(minutes=self.range_minutes)
        range_candles = day_data[(day_data.index >= market_open) & (day_data.index < range_end)]

        if range_candles.empty:
            return None

        range_high = self._to_decimal(range_candles["High"].max())
        range_low = self._to_decimal(range_candles["Low"].min())
        open_price = self._to_decimal(range_candles["Open"].iloc[0])
        range_size = range_high - range_low
        range_pct = (range_size / open_price) * 100 if open_price > 0 else Decimal("0")

        return OpeningRange(
            high=range_high,
            low=range_low,
            range_size=range_size,
            range_pct=range_pct,
            open_price=open_price,
            start_time=market_open,
            end_time=range_end,
        )

    def _check_breakout(
        self, candle: pd.Series, opening_range: OpeningRange, avg_volume: float
    ) -> tuple[SignalType | None, Decimal, str]:
        """Check if candle represents a breakout."""
        close = self._to_decimal(candle["Close"])
        high = self._to_decimal(candle["High"])
        low = self._to_decimal(candle["Low"])
        volume = candle["Volume"]

        buffer = opening_range.range_size * (self.breakout_buffer_pct / 100)
        breakout_high = opening_range.high + buffer
        breakout_low = opening_range.low - buffer

        volume_ratio = volume / avg_volume if avg_volume > 0 else 0
        has_volume = volume_ratio >= self.volume_confirmation

        if self.require_close_breakout:
            is_upside_breakout = close > breakout_high
            is_downside_breakout = close < breakout_low
        else:
            is_upside_breakout = high > breakout_high
            is_downside_breakout = low < breakout_low

        if is_upside_breakout:
            strength = min(
                Decimal("1.0"), Decimal("0.5") + (close - breakout_high) / opening_range.range_size
            )
            if has_volume:
                strength = min(Decimal("1.0"), strength + Decimal("0.2"))
            reason = f"Upside breakout: Close {close} > Range high {opening_range.high}"
            if has_volume:
                reason += f" (volume {volume_ratio:.1f}x avg)"
            return SignalType.BUY, strength, reason

        if is_downside_breakout:
            strength = min(
                Decimal("1.0"), Decimal("0.5") + (breakout_low - close) / opening_range.range_size
            )
            if has_volume:
                strength = min(Decimal("1.0"), strength + Decimal("0.2"))
            reason = f"Downside breakout: Close {close} < Range low {opening_range.low}"
            if has_volume:
                reason += f" (volume {volume_ratio:.1f}x avg)"
            return SignalType.SELL, strength, reason

        return None, Decimal("0"), ""

    def _calculate_orb_stop_loss(
        self,
        entry_price: Decimal,
        signal_type: SignalType,
        opening_range: OpeningRange,
        atr: Decimal | None = None,
    ) -> Decimal:
        """Calculate stop loss for ORB trade."""
        if self.stop_loss_method == "range":
            if signal_type == SignalType.BUY:
                return opening_range.low
            else:
                return opening_range.high
        elif self.stop_loss_method == "atr" and atr:
            stop_distance = atr * self.atr_multiplier
            if signal_type == SignalType.BUY:
                return entry_price - stop_distance
            else:
                return entry_price + stop_distance
        else:
            stop_distance = entry_price * (self.stop_loss_pct / 100)
            if signal_type == SignalType.BUY:
                return entry_price - stop_distance
            else:
                return entry_price + stop_distance

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate ORB trading signals from intraday OHLCV data."""
        if df.empty or len(df) < self.atr_period:
            return []

        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df.index = pd.to_datetime(df.index)

        current_time = df.index[-1]
        current_time_only = current_time.time()

        if current_time_only > self.no_trade_after:
            return []
        if current_time_only < self.MARKET_OPEN or current_time_only >= self.MARKET_CLOSE:
            return []

        opening_range = self._calculate_opening_range(df)
        if not opening_range:
            return []

        if current_time < opening_range.end_time:
            return []

        date_key = current_time.date().isoformat()
        if self._daily_entries.get(date_key, 0) >= self.max_entries_per_day:
            return []

        post_range_df = df[df.index >= opening_range.end_time]
        if post_range_df.empty:
            return []

        atr = None
        if len(df) >= self.atr_period:
            atr_indicator = AverageTrueRange(
                df["High"], df["Low"], df["Close"], window=self.atr_period
            )
            atr_value = atr_indicator.average_true_range().iloc[-1]
            if not pd.isna(atr_value):
                atr = self._to_decimal(atr_value)

        avg_volume = df["Volume"].tail(20).mean()
        current_candle = df.iloc[-1]
        signal_type, strength, reason = self._check_breakout(
            current_candle, opening_range, avg_volume
        )

        if signal_type is None:
            return []

        entry_price = self._to_decimal(current_candle["Close"])
        stop_loss = self._calculate_orb_stop_loss(entry_price, signal_type, opening_range, atr)
        take_profit = self.calculate_take_profit(
            entry_price, stop_loss, signal_type, self.risk_reward_ratio
        )

        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = reward / risk if risk > 0 else Decimal("0")

        confidence = Decimal("0.5")
        if opening_range.range_pct < Decimal("2.0"):
            confidence += Decimal("0.2")
        volume_ratio = current_candle["Volume"] / avg_volume if avg_volume > 0 else 0
        if volume_ratio >= self.volume_confirmation:
            confidence += Decimal("0.15")
        if atr and opening_range.range_size > atr:
            confidence -= Decimal("0.1")
        confidence = max(Decimal("0.3"), min(Decimal("0.95"), confidence))

        self._daily_entries[date_key] = self._daily_entries.get(date_key, 0) + 1

        signal = SignalData(
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            price_at_signal=entry_price,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            indicators={
                "opening_range_high": float(opening_range.high),
                "opening_range_low": float(opening_range.low),
                "range_size": float(opening_range.range_size),
                "range_pct": float(opening_range.range_pct),
                "volume_ratio": round(volume_ratio, 2),
                "atr": float(atr) if atr else None,
            },
            notes=reason,
        )

        return [signal]

    def reset_daily_entries(self) -> None:
        """Reset daily entry tracking."""
        self._daily_entries.clear()
