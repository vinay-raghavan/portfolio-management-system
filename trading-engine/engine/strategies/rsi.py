"""RSI (Relative Strength Index) trading strategy."""

from decimal import Decimal

import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

from engine.models.signals import SignalData, SignalType
from engine.strategies.base import BaseStrategy
from engine.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class RSIStrategy(BaseStrategy):
    """RSI Oversold/Overbought Strategy.

    Generates BUY signals when RSI drops below oversold threshold (default 30),
    and SELL signals when RSI rises above overbought threshold (default 70).

    Signal strength is based on how extreme the RSI reading is.
    """

    name = "rsi"
    description = "RSI Oversold/Overbought - Buy when RSI < 30, Sell when RSI > 70"
    default_timeframe = "1d"

    def __init__(
        self,
        rsi_period: int = 14,
        oversold_threshold: int = 30,
        overbought_threshold: int = 70,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize RSI strategy."""
        self.rsi_period = rsi_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "rsi_period": self.rsi_period,
            "oversold_threshold": self.oversold_threshold,
            "overbought_threshold": self.overbought_threshold,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate RSI-based trading signals."""
        if len(df) < self.rsi_period + 1:
            return []

        # Calculate RSI
        close = df["Close"]
        rsi_indicator = RSIIndicator(close, window=self.rsi_period)
        rsi_values = rsi_indicator.rsi()

        # Get latest values
        current_rsi = rsi_values.iloc[-1]
        current_price = self._to_decimal(close.iloc[-1])

        if pd.isna(current_rsi) or current_price is None:
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

        # Check for oversold (BUY signal)
        if current_rsi < self.oversold_threshold:
            strength = self._calculate_strength(current_rsi, is_buy=True)
            confidence = self._calculate_confidence(current_rsi, rsi_values)

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
                    indicators={"rsi": round(current_rsi, 2), "atr": float(atr) if atr else None},
                    notes=f"RSI oversold at {current_rsi:.2f}",
                )
            )

        # Check for overbought (SELL signal)
        elif current_rsi > self.overbought_threshold:
            strength = self._calculate_strength(current_rsi, is_buy=False)
            confidence = self._calculate_confidence(current_rsi, rsi_values)

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
                    indicators={"rsi": round(current_rsi, 2), "atr": float(atr) if atr else None},
                    notes=f"RSI overbought at {current_rsi:.2f}",
                )
            )

        return signals

    def _calculate_strength(self, rsi: float, is_buy: bool) -> Decimal:
        """Calculate signal strength based on RSI extremity."""
        if is_buy:
            strength = 1.0 - (rsi / (self.oversold_threshold * 2))
        else:
            strength = (rsi - self.overbought_threshold) / (
                100 - self.overbought_threshold
            ) * 0.5 + 0.5
        return Decimal(str(max(0.0, min(1.0, strength)))).quantize(Decimal("0.0001"))

    def _calculate_confidence(self, current_rsi: float, rsi_series: pd.Series) -> Decimal:
        """Calculate confidence based on RSI trend consistency."""
        if len(rsi_series) < 3:
            return Decimal("0.5")

        recent_rsi = rsi_series.tail(5).dropna()
        if len(recent_rsi) < 3:
            return Decimal("0.5")

        rsi_change = recent_rsi.iloc[-1] - recent_rsi.iloc[0]

        if (
            current_rsi < self.oversold_threshold
            and rsi_change < 0
            or current_rsi > self.overbought_threshold
            and rsi_change > 0
        ):
            confidence = 0.6 + min(0.3, abs(rsi_change) / 30)
        else:
            confidence = 0.5

        return Decimal(str(confidence)).quantize(Decimal("0.0001"))
