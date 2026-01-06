"""MACD (Moving Average Convergence Divergence) trading strategy."""

from decimal import Decimal

import pandas as pd
from ta.trend import MACD
from ta.volatility import AverageTrueRange

from shared.models.signals import SignalData, SignalType
from shared.strategies.base import BaseStrategy
from shared.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class MACDStrategy(BaseStrategy):
    """MACD Crossover Strategy.

    Generates BUY signals when MACD line crosses above signal line,
    and SELL signals when MACD line crosses below signal line.

    Signal strength is based on the magnitude of the crossover.
    """

    name = "macd"
    description = "MACD Crossover - Buy on bullish crossover, Sell on bearish crossover"
    default_timeframe = "1d"

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize MACD strategy."""
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate MACD-based trading signals."""
        min_periods = self.slow_period + self.signal_period
        if len(df) < min_periods + 1:
            return []

        close = df["Close"]
        macd_indicator = MACD(
            close,
            window_slow=self.slow_period,
            window_fast=self.fast_period,
            window_sign=self.signal_period,
        )

        macd_line = macd_indicator.macd()
        signal_line = macd_indicator.macd_signal()
        histogram = macd_indicator.macd_diff()

        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        prev_histogram = histogram.iloc[-2]
        current_price = self._to_decimal(close.iloc[-1])

        if pd.isna(current_macd) or pd.isna(current_signal) or current_price is None:
            return []

        atr = None
        if len(df) >= self.atr_period:
            atr_indicator = AverageTrueRange(
                df["High"], df["Low"], df["Close"], window=self.atr_period
            )
            atr_value = atr_indicator.average_true_range().iloc[-1]
            if not pd.isna(atr_value):
                atr = self._to_decimal(atr_value)

        signals = []
        bullish_crossover = prev_histogram < 0 and current_histogram > 0
        bearish_crossover = prev_histogram > 0 and current_histogram < 0

        if bullish_crossover:
            strength = self._calculate_strength(current_histogram, histogram)
            confidence = self._calculate_confidence(macd_line, signal_line, is_bullish=True)
            stop_loss = self.calculate_stop_loss(
                current_price, SignalType.BUY, atr, self.atr_multiplier
            )
            take_profit = self.calculate_take_profit(
                current_price, stop_loss, SignalType.BUY, self.risk_reward_ratio
            )

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
                    indicators={
                        "macd": round(current_macd, 4),
                        "signal": round(current_signal, 4),
                        "histogram": round(current_histogram, 4),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"MACD bullish crossover (histogram: {current_histogram:.4f})",
                )
            )

        elif bearish_crossover:
            strength = self._calculate_strength(current_histogram, histogram)
            confidence = self._calculate_confidence(macd_line, signal_line, is_bullish=False)
            stop_loss = self.calculate_stop_loss(
                current_price, SignalType.SELL, atr, self.atr_multiplier
            )
            take_profit = self.calculate_take_profit(
                current_price, stop_loss, SignalType.SELL, self.risk_reward_ratio
            )

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
                    indicators={
                        "macd": round(current_macd, 4),
                        "signal": round(current_signal, 4),
                        "histogram": round(current_histogram, 4),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"MACD bearish crossover (histogram: {current_histogram:.4f})",
                )
            )

        else:
            strength = Decimal("0.5")
            signals.append(
                SignalData(
                    symbol=symbol,
                    signal_type=SignalType.HOLD,
                    strength=strength,
                    confidence=Decimal("0.6"),
                    price_at_signal=current_price,
                    entry_price=None,
                    stop_loss=None,
                    take_profit=None,
                    risk_reward_ratio=None,
                    indicators={
                        "macd": round(current_macd, 4),
                        "signal": round(current_signal, 4),
                        "histogram": round(current_histogram, 4),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"MACD no crossover (histogram: {current_histogram:.4f})",
                )
            )

        return signals

    def _calculate_strength(self, current_histogram: float, histogram_series: pd.Series) -> Decimal:
        """Calculate signal strength based on histogram magnitude."""
        recent_hist = histogram_series.tail(20).dropna()
        if len(recent_hist) < 5:
            return Decimal("0.5")
        max_hist = recent_hist.abs().max()
        if max_hist == 0:
            return Decimal("0.5")
        relative_strength = abs(current_histogram) / max_hist
        strength = 0.5 + relative_strength * 0.5
        return Decimal(str(min(1.0, strength))).quantize(Decimal("0.0001"))

    def _calculate_confidence(
        self, macd_line: pd.Series, signal_line: pd.Series, is_bullish: bool
    ) -> Decimal:
        """Calculate confidence based on MACD trend."""
        if len(macd_line) < 5:
            return Decimal("0.5")
        recent_macd = macd_line.tail(5).dropna()
        if len(recent_macd) < 3:
            return Decimal("0.5")
        macd_trend = recent_macd.iloc[-1] - recent_macd.iloc[0]
        if (is_bullish and macd_trend > 0) or (not is_bullish and macd_trend < 0):
            confidence = 0.7
        else:
            confidence = 0.5
        return Decimal(str(confidence)).quantize(Decimal("0.0001"))
