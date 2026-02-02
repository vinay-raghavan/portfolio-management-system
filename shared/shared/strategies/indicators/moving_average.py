"""Moving Average Crossover trading strategy."""

from decimal import Decimal

import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange

from shared.models.signals import SignalData, SignalType
from shared.strategies.base import BaseStrategy
from shared.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class MovingAverageCrossoverStrategy(BaseStrategy):
    """Moving Average Crossover Strategy.

    Generates BUY signals when fast MA crosses above slow MA (golden cross),
    and SELL signals when fast MA crosses below slow MA (death cross).

    Supports both SMA and EMA.
    """

    name = "ma_crossover"
    description = "Moving Average Crossover - Buy on golden cross, Sell on death cross"
    default_timeframe = "1d"

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 20,
        ma_type: str = "ema",
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize Moving Average Crossover strategy."""
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type.lower()
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "ma_type": self.ma_type,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate Moving Average Crossover-based trading signals."""
        if len(df) < self.slow_period + 1:
            return []

        close = df["Close"]

        if self.ma_type == "ema":
            fast_ma = EMAIndicator(close, window=self.fast_period).ema_indicator()
            slow_ma = EMAIndicator(close, window=self.slow_period).ema_indicator()
        else:
            fast_ma = SMAIndicator(close, window=self.fast_period).sma_indicator()
            slow_ma = SMAIndicator(close, window=self.slow_period).sma_indicator()

        current_fast = fast_ma.iloc[-1]
        current_slow = slow_ma.iloc[-1]
        prev_fast = fast_ma.iloc[-2]
        prev_slow = slow_ma.iloc[-2]
        current_price = self._to_decimal(close.iloc[-1])

        if pd.isna(current_fast) or pd.isna(current_slow) or current_price is None:
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
        golden_cross = prev_fast <= prev_slow and current_fast > current_slow
        death_cross = prev_fast >= prev_slow and current_fast < current_slow

        if golden_cross:
            strength = self._calculate_strength(current_fast, current_slow, fast_ma, slow_ma)
            confidence = self._calculate_confidence(fast_ma, slow_ma, is_bullish=True)
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
                        "fast_ma": round(current_fast, 2),
                        "slow_ma": round(current_slow, 2),
                        "ma_type": self.ma_type.upper(),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"Golden Cross: {self.fast_period} {self.ma_type.upper()} crossed above {self.slow_period} {self.ma_type.upper()}",
                )
            )

        elif death_cross:
            strength = self._calculate_strength(current_fast, current_slow, fast_ma, slow_ma)
            confidence = self._calculate_confidence(fast_ma, slow_ma, is_bullish=False)
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
                        "fast_ma": round(current_fast, 2),
                        "slow_ma": round(current_slow, 2),
                        "ma_type": self.ma_type.upper(),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"Death Cross: {self.fast_period} {self.ma_type.upper()} crossed below {self.slow_period} {self.ma_type.upper()}",
                )
            )

        else:
            ma_diff = current_fast - current_slow
            relative_diff = abs(ma_diff) / current_slow if current_slow != 0 else 0
            strength = Decimal(str(0.5 + min(0.3, relative_diff * 10))).quantize(Decimal("0.0001"))

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
                        "fast_ma": round(current_fast, 2),
                        "slow_ma": round(current_slow, 2),
                        "ma_type": self.ma_type.upper(),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"No crossover. Fast MA {'above' if current_fast > current_slow else 'below'} Slow MA",
                )
            )

        return signals

    def _calculate_strength(
        self, current_fast: float, current_slow: float, fast_ma: pd.Series, slow_ma: pd.Series
    ) -> Decimal:
        """Calculate signal strength based on MA separation."""
        ma_diff = abs(current_fast - current_slow)
        relative_diff = ma_diff / current_slow if current_slow != 0 else 0

        # Stronger signal when MAs are further apart after crossover
        strength = 0.6 + min(0.4, relative_diff * 20)
        return Decimal(str(strength)).quantize(Decimal("0.0001"))

    def _calculate_confidence(
        self, fast_ma: pd.Series, slow_ma: pd.Series, is_bullish: bool
    ) -> Decimal:
        """Calculate confidence based on MA trend consistency."""
        if len(fast_ma) < 5:
            return Decimal("0.5")

        recent_fast = fast_ma.tail(5).dropna()
        recent_slow = slow_ma.tail(5).dropna()

        if len(recent_fast) < 3 or len(recent_slow) < 3:
            return Decimal("0.5")

        fast_trend = recent_fast.iloc[-1] - recent_fast.iloc[0]
        slow_trend = recent_slow.iloc[-1] - recent_slow.iloc[0]

        # Higher confidence when both MAs are trending in the signal direction
        if is_bullish:
            if fast_trend > 0 and slow_trend > 0:
                confidence = 0.8
            elif fast_trend > 0:
                confidence = 0.65
            else:
                confidence = 0.5
        else:
            if fast_trend < 0 and slow_trend < 0:
                confidence = 0.8
            elif fast_trend < 0:
                confidence = 0.65
            else:
                confidence = 0.5

        return Decimal(str(confidence)).quantize(Decimal("0.0001"))
