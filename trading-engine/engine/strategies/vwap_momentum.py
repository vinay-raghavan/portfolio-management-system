"""VWAP Momentum Strategy.

Intraday momentum strategy combining VWAP, EMAs, RSI, and volume analysis.
Based on the intradaysignalAPI scoring approach.
"""

from decimal import Decimal

import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

from engine.models.signals import SignalData, SignalType
from engine.strategies.base import BaseStrategy
from engine.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class VWAPMomentumStrategy(BaseStrategy):
    """VWAP Momentum Scoring Strategy.

    This strategy combines multiple intraday indicators to generate a momentum score:
    1. Price vs VWAP: Bullish if price > VWAP
    2. EMA alignment: Bullish if EMA5 > EMA9 > EMA21 (short-term momentum)
    3. RSI position: Bullish if RSI > 50
    4. Volume confirmation: Bullish if current volume > average volume

    Signal generation:
    - Score >= 4/5: Strong BUY signal
    - Score >= 3/5: BUY signal
    - Score <= 1/5: Strong SELL signal
    - Score <= 2/5: SELL signal
    - Otherwise: HOLD

    Best suited for:
    - Intraday trading on 5-minute charts
    - Momentum-driven stocks
    - High liquidity environments
    """

    name = "vwap_momentum"
    description = "VWAP Momentum - Multi-indicator scoring for intraday momentum"
    default_timeframe = "5m"

    def __init__(
        self,
        ema_fast: int = 5,
        ema_medium: int = 9,
        ema_slow: int = 21,
        rsi_period: int = 14,
        rsi_threshold: int = 50,
        volume_lookback: int = 10,
        buy_threshold: int = 3,
        strong_buy_threshold: int = 4,
        sell_threshold: int = 2,
        strong_sell_threshold: int = 1,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize VWAP Momentum strategy."""
        self.ema_fast = ema_fast
        self.ema_medium = ema_medium
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
        self.volume_lookback = volume_lookback
        self.buy_threshold = buy_threshold
        self.strong_buy_threshold = strong_buy_threshold
        self.sell_threshold = sell_threshold
        self.strong_sell_threshold = strong_sell_threshold
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "ema_fast": self.ema_fast,
            "ema_medium": self.ema_medium,
            "ema_slow": self.ema_slow,
            "rsi_period": self.rsi_period,
            "rsi_threshold": self.rsi_threshold,
            "volume_lookback": self.volume_lookback,
            "buy_threshold": self.buy_threshold,
            "strong_buy_threshold": self.strong_buy_threshold,
            "sell_threshold": self.sell_threshold,
            "strong_sell_threshold": self.strong_sell_threshold,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
        }

    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP for the DataFrame."""
        typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
        cumulative_tp_vol = (typical_price * df["Volume"]).cumsum()
        cumulative_vol = df["Volume"].cumsum()
        return cumulative_tp_vol / cumulative_vol

    def _calculate_indicators(self, df: pd.DataFrame) -> dict:
        """Calculate all indicators for scoring."""
        close = df["Close"]
        vwap = self._calculate_vwap(df)
        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_medium = close.ewm(span=self.ema_medium, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()
        rsi_indicator = RSIIndicator(close, window=self.rsi_period)
        rsi = rsi_indicator.rsi()
        avg_volume = df["Volume"].rolling(window=self.volume_lookback, min_periods=1).mean()

        return {
            "vwap": vwap.iloc[-1],
            "ema_fast": ema_fast.iloc[-1],
            "ema_medium": ema_medium.iloc[-1],
            "ema_slow": ema_slow.iloc[-1],
            "rsi": rsi.iloc[-1],
            "volume": df["Volume"].iloc[-1],
            "avg_volume": avg_volume.iloc[-1],
            "close": close.iloc[-1],
        }

    def _calculate_score(self, indicators: dict) -> tuple[int, list[str]]:
        """Calculate momentum score based on indicators."""
        score = 0
        bullish_factors = []
        bearish_factors = []

        close = indicators["close"]
        vwap = indicators["vwap"]
        ema_fast = indicators["ema_fast"]
        ema_medium = indicators["ema_medium"]
        ema_slow = indicators["ema_slow"]
        rsi = indicators["rsi"]
        volume = indicators["volume"]
        avg_volume = indicators["avg_volume"]

        if close > vwap:
            score += 1
            bullish_factors.append(f"Price ({close:.2f}) > VWAP ({vwap:.2f})")
        else:
            bearish_factors.append(f"Price ({close:.2f}) < VWAP ({vwap:.2f})")

        if ema_fast > ema_medium:
            score += 1
            bullish_factors.append(f"EMA{self.ema_fast} > EMA{self.ema_medium}")
        else:
            bearish_factors.append(f"EMA{self.ema_fast} < EMA{self.ema_medium}")

        if ema_medium > ema_slow:
            score += 1
            bullish_factors.append(f"EMA{self.ema_medium} > EMA{self.ema_slow}")
        else:
            bearish_factors.append(f"EMA{self.ema_medium} < EMA{self.ema_slow}")

        if not pd.isna(rsi):
            if rsi > self.rsi_threshold:
                score += 1
                bullish_factors.append(f"RSI ({rsi:.1f}) > {self.rsi_threshold}")
            else:
                bearish_factors.append(f"RSI ({rsi:.1f}) < {self.rsi_threshold}")

        if volume > avg_volume:
            score += 1
            bullish_factors.append(f"Volume ({volume:.0f}) > Avg ({avg_volume:.0f})")
        else:
            bearish_factors.append(f"Volume ({volume:.0f}) < Avg ({avg_volume:.0f})")

        return score, bullish_factors if score >= 3 else bearish_factors

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate VWAP momentum signals based on multi-indicator scoring."""
        min_periods = max(self.ema_slow, self.rsi_period, self.volume_lookback) + 1
        if len(df) < min_periods:
            return []

        # Filter to today's data for intraday VWAP
        if isinstance(df.index, pd.DatetimeIndex):
            today = df.index[-1].date()
            today_df = df[df.index.date == today].copy()
            if len(today_df) < min_periods:
                today_df = df.tail(min_periods).copy()
        else:
            today_df = df.tail(min_periods).copy()

        indicators = self._calculate_indicators(today_df)
        current_price = self._to_decimal(indicators["close"])

        if pd.isna(indicators["rsi"]) or pd.isna(indicators["vwap"]):
            return []

        score, factors = self._calculate_score(indicators)

        atr = None
        if len(df) >= self.atr_period:
            atr_indicator = AverageTrueRange(
                df["High"], df["Low"], df["Close"], window=self.atr_period
            )
            atr_value = atr_indicator.average_true_range().iloc[-1]
            if not pd.isna(atr_value):
                atr = self._to_decimal(atr_value)

        if score >= self.buy_threshold:
            signal_type = SignalType.BUY
            is_strong = score >= self.strong_buy_threshold
            strength = (
                Decimal(str(0.6 + (score / 5) * 0.4))
                if is_strong
                else Decimal(str(0.5 + (score / 5) * 0.3))
            )
            confidence = Decimal(str(0.5 + (score / 5) * 0.4))
            notes = f"Momentum score {score}/5 ({'Strong ' if is_strong else ''}BUY): " + ", ".join(
                factors[:3]
            )
            stop_loss = self.calculate_stop_loss(
                current_price, signal_type, atr, self.atr_multiplier
            )
            take_profit = self.calculate_take_profit(
                current_price, stop_loss, signal_type, self.risk_reward_ratio
            )

        elif score <= self.sell_threshold:
            signal_type = SignalType.SELL
            is_strong = score <= self.strong_sell_threshold
            strength = (
                Decimal(str(0.6 + ((5 - score) / 5) * 0.4))
                if is_strong
                else Decimal(str(0.5 + ((5 - score) / 5) * 0.3))
            )
            confidence = Decimal(str(0.5 + ((5 - score) / 5) * 0.4))
            notes = (
                f"Momentum score {score}/5 ({'Strong ' if is_strong else ''}SELL): "
                + ", ".join(factors[:3])
            )
            stop_loss = self.calculate_stop_loss(
                current_price, signal_type, atr, self.atr_multiplier
            )
            take_profit = self.calculate_take_profit(
                current_price, stop_loss, signal_type, self.risk_reward_ratio
            )

        else:
            signal_type = SignalType.HOLD
            strength = Decimal("0.5")
            confidence = Decimal("0.5")
            notes = f"Momentum score {score}/5 - Neutral, waiting for clearer signal"
            stop_loss = None
            take_profit = None

        indicators_out = {
            "score": score,
            "vwap": round(float(indicators["vwap"]), 2),
            "ema_fast": round(float(indicators["ema_fast"]), 2),
            "ema_medium": round(float(indicators["ema_medium"]), 2),
            "ema_slow": round(float(indicators["ema_slow"]), 2),
            "rsi": round(float(indicators["rsi"]), 2) if not pd.isna(indicators["rsi"]) else None,
            "volume": float(indicators["volume"]),
            "avg_volume": round(float(indicators["avg_volume"]), 2),
            "atr": float(atr) if atr else None,
        }

        signal = SignalData(
            symbol=symbol,
            signal_type=signal_type,
            strength=strength.quantize(Decimal("0.0001")),
            confidence=confidence.quantize(Decimal("0.0001")),
            price_at_signal=current_price,
            entry_price=current_price if signal_type != SignalType.HOLD else None,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=self.risk_reward_ratio if signal_type != SignalType.HOLD else None,
            indicators=indicators_out,
            notes=notes,
        )

        return [signal]

