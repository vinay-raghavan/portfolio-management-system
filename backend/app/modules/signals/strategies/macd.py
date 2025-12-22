"""MACD (Moving Average Convergence Divergence) Crossover Strategy."""

from decimal import Decimal

import pandas as pd
from ta.trend import MACD
from ta.volatility import AverageTrueRange

from app.modules.signals.models import SignalType
from app.modules.signals.strategies.base import BaseStrategy, SignalData
from app.modules.signals.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class MACDCrossoverStrategy(BaseStrategy):
    """MACD Crossover Strategy.

    Generates BUY signals when MACD line crosses above the signal line,
    and SELL signals when MACD line crosses below the signal line.

    Optional histogram confirmation: only trigger signals when histogram
    is moving in the direction of the crossover.
    """

    name = "macd_crossover"
    description = "MACD Crossover - Buy on bullish crossover, Sell on bearish crossover"
    default_timeframe = "1d"

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        require_histogram_confirmation: bool = True,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize MACD Crossover strategy.

        Args:
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)
            require_histogram_confirmation: Require histogram direction match (default True)
            atr_period: Period for ATR calculation (default 14)
            atr_multiplier: ATR multiplier for stop loss (default 2.0)
            risk_reward_ratio: Risk/reward ratio for take profit (default 2.0)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.require_histogram_confirmation = require_histogram_confirmation
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
            "require_histogram_confirmation": self.require_histogram_confirmation,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate MACD crossover signals.

        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol

        Returns:
            List of SignalData (0 or 1 signals)
        """
        min_periods = self.slow_period + self.signal_period + 1
        if len(df) < min_periods:
            return []

        close = df["Close"]

        # Calculate MACD
        macd_indicator = MACD(
            close,
            window_slow=self.slow_period,
            window_fast=self.fast_period,
            window_sign=self.signal_period,
        )

        macd_line = macd_indicator.macd()
        signal_line = macd_indicator.macd_signal()
        histogram = macd_indicator.macd_diff()

        # Get current and previous values
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_hist = histogram.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        prev_hist = histogram.iloc[-2]

        current_price = self._to_decimal(close.iloc[-1])

        if any(pd.isna(x) for x in [current_macd, current_signal, prev_macd, prev_signal]):
            return []

        if current_price is None:
            return []

        # Calculate ATR for stop loss
        atr = None
        if len(df) >= self.atr_period:
            atr_indicator = AverageTrueRange(
                df["High"], df["Low"], df["Close"], window=self.atr_period
            )
            atr_value = atr_indicator.average_true_range().iloc[-1]
            if not pd.isna(atr_value):
                atr = self._to_decimal(atr_value)

        signals = []

        # Check for bullish crossover (MACD crosses above signal)
        bullish_crossover = prev_macd <= prev_signal and current_macd > current_signal
        # Check for bearish crossover (MACD crosses below signal)
        bearish_crossover = prev_macd >= prev_signal and current_macd < current_signal

        # Histogram confirmation
        hist_bullish = current_hist > prev_hist if not pd.isna(prev_hist) else True
        hist_bearish = current_hist < prev_hist if not pd.isna(prev_hist) else True

        if bullish_crossover:
            if not self.require_histogram_confirmation or hist_bullish:
                strength = self._calculate_strength(current_macd, current_signal, is_buy=True)
                confidence = self._calculate_confidence(histogram, is_buy=True)

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
                            "histogram": round(current_hist, 4),
                            "atr": float(atr) if atr else None,
                        },
                        notes="MACD bullish crossover",
                    )
                )

        elif bearish_crossover:
            if not self.require_histogram_confirmation or hist_bearish:
                strength = self._calculate_strength(current_macd, current_signal, is_buy=False)
                confidence = self._calculate_confidence(histogram, is_buy=False)

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
                            "histogram": round(current_hist, 4),
                            "atr": float(atr) if atr else None,
                        },
                        notes="MACD bearish crossover",
                    )
                )

        return signals

    def _calculate_strength(
        self, macd: float, signal: float, is_buy: bool
    ) -> Decimal:
        """Calculate signal strength based on MACD divergence from signal line.

        Larger divergence = stronger signal.
        """
        divergence = abs(macd - signal)
        # Normalize divergence (assume typical divergence is 0-2% of signal)
        normalized = min(1.0, divergence / (abs(signal) + 0.001) * 10)
        strength = 0.5 + (normalized * 0.5)  # Scale to 0.5 - 1.0
        return Decimal(str(strength)).quantize(Decimal("0.0001"))

    def _calculate_confidence(self, histogram: pd.Series, is_buy: bool) -> Decimal:
        """Calculate confidence based on histogram momentum.

        Increasing histogram magnitude in direction of trade = higher confidence.
        """
        if len(histogram) < 3:
            return Decimal("0.5")

        recent_hist = histogram.tail(5).dropna()
        if len(recent_hist) < 3:
            return Decimal("0.5")

        # Check histogram trend
        hist_change = recent_hist.iloc[-1] - recent_hist.iloc[-3]

        # For buy, we want histogram increasing (becoming more positive)
        # For sell, we want histogram decreasing (becoming more negative)
        if (is_buy and hist_change > 0) or (not is_buy and hist_change < 0):
            confidence = 0.6 + min(0.3, abs(hist_change) * 5)
        else:
            confidence = 0.4

        return Decimal(str(confidence)).quantize(Decimal("0.0001"))

