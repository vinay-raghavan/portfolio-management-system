"""Momentum Short Strategy.

Generates SHORT signals based on bearish momentum conditions:
- Price below long-term trend (EMA200)
- Overbought RSI reverting (or oversold in trend)
- Bearish MACD crossover
- Strong downtrend (ADX with -DI dominance)
"""

from decimal import Decimal

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, ADXIndicator, EMAIndicator
from ta.volatility import AverageTrueRange

from shared.models.signals import SignalData, SignalIntent, SignalType
from shared.strategies.base import BaseStrategy
from shared.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class MomentumShortStrategy(BaseStrategy):
    """Momentum-based short selling strategy.

    This strategy identifies bearish momentum setups for short selling:
    1. Price must be below EMA200 (long-term downtrend)
    2. RSI shows overbought condition (>70) or bearish divergence
    3. MACD has bearish crossover (MACD < Signal line)
    4. ADX > 25 with -DI > +DI (strong downtrend)

    Designed for INTRADAY or SLB product types only.

    Risk Management:
    - Stop loss above recent swing high (using ATR)
    - Take profit at risk-reward ratio (default 2:1)
    """

    name = "momentum_short"
    description = "Momentum Short - Bearish momentum signals for short selling"
    default_timeframe = "1h"

    def __init__(
        self,
        ema_fast: int = 21,
        ema_slow: int = 50,
        ema_trend: int = 200,
        rsi_period: int = 14,
        rsi_overbought: int = 70,
        rsi_oversold: int = 30,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        adx_period: int = 14,
        adx_threshold: int = 25,
        atr_period: int = 14,
        atr_stop_multiplier: float = 1.5,
        risk_reward_ratio: float = 2.0,
        min_score: int = 3,
    ):
        """Initialize Momentum Short strategy."""
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.ema_trend = ema_trend
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.atr_period = atr_period
        self.atr_stop_multiplier = Decimal(str(atr_stop_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))
        self.min_score = min_score

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "ema_trend": self.ema_trend,
            "rsi_period": self.rsi_period,
            "rsi_overbought": self.rsi_overbought,
            "rsi_oversold": self.rsi_oversold,
            "macd_fast": self.macd_fast,
            "macd_slow": self.macd_slow,
            "macd_signal": self.macd_signal,
            "adx_period": self.adx_period,
            "adx_threshold": self.adx_threshold,
            "atr_period": self.atr_period,
            "atr_stop_multiplier": float(self.atr_stop_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
            "min_score": self.min_score,
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate short signals based on bearish momentum."""
        if df is None or len(df) < self.ema_trend + 10:
            return []

        # Calculate indicators
        df = df.copy()

        # EMAs
        df["ema_fast"] = EMAIndicator(df["close"], window=self.ema_fast).ema_indicator()
        df["ema_slow"] = EMAIndicator(df["close"], window=self.ema_slow).ema_indicator()
        df["ema_trend"] = EMAIndicator(df["close"], window=self.ema_trend).ema_indicator()

        # RSI
        rsi = RSIIndicator(df["close"], window=self.rsi_period)
        df["rsi"] = rsi.rsi()

        # MACD
        macd = MACD(
            df["close"],
            window_fast=self.macd_fast,
            window_slow=self.macd_slow,
            window_sign=self.macd_signal,
        )
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        # ADX
        adx = ADXIndicator(df["high"], df["low"], df["close"], window=self.adx_period)
        df["adx"] = adx.adx()
        df["di_plus"] = adx.adx_pos()
        df["di_minus"] = adx.adx_neg()

        # ATR for stop loss
        atr = AverageTrueRange(df["high"], df["low"], df["close"], window=self.atr_period)
        df["atr"] = atr.average_true_range()

        # Get latest values
        latest = df.iloc[-1]
        current_price = Decimal(str(latest["close"]))
        atr_value = Decimal(str(latest["atr"])) if pd.notna(latest["atr"]) else Decimal("0")

        # Score bearish conditions (0-5)
        score = 0
        indicators = {}

        # 1. Price below EMA200 (long-term downtrend)
        if pd.notna(latest["ema_trend"]) and latest["close"] < latest["ema_trend"]:
            score += 1
            indicators["below_ema200"] = True

        # 2. EMA bearish alignment (fast < slow)
        if pd.notna(latest["ema_fast"]) and pd.notna(latest["ema_slow"]):
            if latest["ema_fast"] < latest["ema_slow"]:
                score += 1
                indicators["ema_bearish"] = True

        # 3. RSI overbought (potential reversal) or in bearish zone
        if pd.notna(latest["rsi"]):
            if latest["rsi"] > self.rsi_overbought:
                score += 1
                indicators["rsi_overbought"] = float(latest["rsi"])
            elif latest["rsi"] < 50:  # RSI bearish momentum
                score += 0.5
                indicators["rsi_bearish"] = float(latest["rsi"])

        # 4. MACD bearish (MACD < Signal)
        if pd.notna(latest["macd"]) and pd.notna(latest["macd_signal"]):
            if latest["macd"] < latest["macd_signal"]:
                score += 1
                indicators["macd_bearish"] = True

        # 5. ADX strong downtrend (-DI > +DI)
        if pd.notna(latest["adx"]) and latest["adx"] > self.adx_threshold:
            if pd.notna(latest["di_minus"]) and pd.notna(latest["di_plus"]):
                if latest["di_minus"] > latest["di_plus"]:
                    score += 1
                    indicators["adx_downtrend"] = {
                        "adx": float(latest["adx"]),
                        "di_minus": float(latest["di_minus"]),
                        "di_plus": float(latest["di_plus"]),
                    }

        indicators["total_score"] = score

        # Generate SHORT signal if score meets threshold
        if score >= self.min_score:
            # Calculate stop loss (above entry + ATR buffer)
            stop_loss = current_price + (atr_value * self.atr_stop_multiplier)

            # Calculate take profit (below entry at risk-reward ratio)
            risk = stop_loss - current_price
            take_profit = current_price - (risk * self.risk_reward_ratio)

            # Confidence based on score
            confidence = Decimal(str(min(score / 5, 1.0)))
            strength = Decimal(str(min((score - self.min_score + 1) / 3, 1.0)))

            return [
                SignalData(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    intent=SignalIntent.OPEN_SHORT,
                    strength=strength,
                    confidence=confidence,
                    price_at_signal=current_price,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=self.risk_reward_ratio,
                    indicators=indicators,
                    notes=f"Bearish momentum score: {score}/5",
                )
            ]

        return []
