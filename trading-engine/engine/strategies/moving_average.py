"""Moving Average Crossover Strategy."""

from decimal import Decimal

import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange

from engine.models.signals import SignalData, SignalType
from engine.strategies.base import BaseStrategy
from engine.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class MovingAverageCrossoverStrategy(BaseStrategy):
    """Moving Average Crossover Strategy.

    Generates BUY signals when the fast MA crosses above the slow MA (golden cross),
    and SELL signals when the fast MA crosses below the slow MA (death cross).

    Supports both SMA and EMA.
    """

    name = "ma_crossover"
    description = "Moving Average Crossover - Buy on golden cross, Sell on death cross"
    default_timeframe = "1d"

    def __init__(
        self,
        fast_period: int = 20,
        slow_period: int = 50,
        ma_type: str = "SMA",  # SMA or EMA
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize Moving Average Crossover strategy.

        Args:
            fast_period: Fast MA period (default 20)
            slow_period: Slow MA period (default 50)
            ma_type: Type of moving average - "SMA" or "EMA" (default SMA)
            atr_period: Period for ATR calculation (default 14)
            atr_multiplier: ATR multiplier for stop loss (default 2.0)
            risk_reward_ratio: Risk/reward ratio for take profit (default 2.0)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type.upper()
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
        """Generate MA crossover signals.

        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol

        Returns:
            List of SignalData (0 or 1 signals)
        """
        if len(df) < self.slow_period + 1:
            return []

        close = df["Close"]

        # Calculate moving averages
        if self.ma_type == "EMA":
            fast_ma = EMAIndicator(close, window=self.fast_period).ema_indicator()
            slow_ma = EMAIndicator(close, window=self.slow_period).ema_indicator()
        else:  # SMA
            fast_ma = SMAIndicator(close, window=self.fast_period).sma_indicator()
            slow_ma = SMAIndicator(close, window=self.slow_period).sma_indicator()

        # Get current and previous values
        current_fast = fast_ma.iloc[-1]
        current_slow = slow_ma.iloc[-1]
        prev_fast = fast_ma.iloc[-2]
        prev_slow = slow_ma.iloc[-2]

        current_price = self._to_decimal(close.iloc[-1])

        if any(pd.isna(x) for x in [current_fast, current_slow, prev_fast, prev_slow]):
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

        # Golden cross (fast crosses above slow) - BUY
        golden_cross = prev_fast <= prev_slow and current_fast > current_slow
        # Death cross (fast crosses below slow) - SELL
        death_cross = prev_fast >= prev_slow and current_fast < current_slow

        if golden_cross:
            strength = self._calculate_strength(current_fast, current_slow, current_price)
            confidence = self._calculate_confidence(fast_ma, slow_ma, is_buy=True)

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
                        f"fast_{self.ma_type.lower()}_{self.fast_period}": round(current_fast, 4),
                        f"slow_{self.ma_type.lower()}_{self.slow_period}": round(current_slow, 4),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"{self.ma_type} Golden Cross ({self.fast_period}/{self.slow_period})",
                )
            )

        elif death_cross:
            strength = self._calculate_strength(current_fast, current_slow, current_price)
            confidence = self._calculate_confidence(fast_ma, slow_ma, is_buy=False)

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
                        f"fast_{self.ma_type.lower()}_{self.fast_period}": round(current_fast, 4),
                        f"slow_{self.ma_type.lower()}_{self.slow_period}": round(current_slow, 4),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"{self.ma_type} Death Cross ({self.fast_period}/{self.slow_period})",
                )
            )

        # HOLD signal - no crossover detected
        else:
            # Determine trend direction from MA positions
            if current_fast > current_slow:
                trend_note = f"Fast {self.ma_type} above slow (bullish trend)"
            else:
                trend_note = f"Fast {self.ma_type} below slow (bearish trend)"

            # Strength based on how far apart MAs are (further = stronger trend)
            separation_pct = abs(current_fast - current_slow) / current_slow * 100
            strength = Decimal(str(min(0.8, 0.5 + separation_pct / 10))).quantize(Decimal("0.0001"))

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
                        f"fast_{self.ma_type.lower()}_{self.fast_period}": round(current_fast, 4),
                        f"slow_{self.ma_type.lower()}_{self.slow_period}": round(current_slow, 4),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"No {self.ma_type} crossover - {trend_note}",
                )
            )

        return signals

    def _calculate_strength(self, fast_ma: float, slow_ma: float, price: Decimal) -> Decimal:
        """Calculate signal strength based on MA separation.

        Larger separation between MAs = stronger trend.
        """
        separation = abs(fast_ma - slow_ma) / slow_ma * 100  # As percentage
        # Normalize: 0% = 0.5, 2%+ = 1.0
        normalized = min(1.0, 0.5 + (separation / 4))
        return Decimal(str(normalized)).quantize(Decimal("0.0001"))

    def _calculate_confidence(
        self, fast_ma: pd.Series, slow_ma: pd.Series, is_buy: bool
    ) -> Decimal:
        """Calculate confidence based on MA trend alignment.

        Higher confidence if both MAs are trending in same direction.
        """
        if len(fast_ma) < 5 or len(slow_ma) < 5:
            return Decimal("0.5")

        # Check if MAs are both trending in the signal direction
        fast_trend = fast_ma.iloc[-1] - fast_ma.iloc[-5]
        slow_trend = slow_ma.iloc[-1] - slow_ma.iloc[-5]

        if is_buy:
            # For buy, we want both MAs trending up
            if fast_trend > 0 and slow_trend > 0:
                confidence = 0.7
            elif fast_trend > 0:
                confidence = 0.6
            else:
                confidence = 0.5
        else:
            # For sell, we want both MAs trending down
            if fast_trend < 0 and slow_trend < 0:
                confidence = 0.7
            elif fast_trend < 0:
                confidence = 0.6
            else:
                confidence = 0.5

        return Decimal(str(confidence)).quantize(Decimal("0.0001"))
