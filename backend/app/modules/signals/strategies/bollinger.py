"""Bollinger Band Squeeze Strategy."""

from decimal import Decimal

import pandas as pd
from ta.volatility import AverageTrueRange, BollingerBands

from app.modules.signals.models import SignalType
from app.modules.signals.strategies.base import BaseStrategy, SignalData
from app.modules.signals.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class BollingerSqueezeStrategy(BaseStrategy):
    """Bollinger Band Squeeze Strategy.

    Detects when Bollinger Bands squeeze (low volatility) and then expand,
    signaling potential breakout moves.

    BUY signal: Price breaks above upper band after squeeze
    SELL signal: Price breaks below lower band after squeeze
    """

    name = "bollinger_squeeze"
    description = "Bollinger Squeeze - Breakout signals after low volatility periods"
    default_timeframe = "1d"

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        squeeze_percentile: int = 20,  # Band width below this percentile = squeeze
        lookback_periods: int = 50,  # Periods to calculate bandwidth percentile
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize Bollinger Squeeze strategy.

        Args:
            bb_period: Bollinger Band period (default 20)
            bb_std: Standard deviation multiplier (default 2.0)
            squeeze_percentile: Band width percentile threshold (default 20)
            lookback_periods: Periods for percentile calculation (default 50)
            atr_period: Period for ATR calculation (default 14)
            atr_multiplier: ATR multiplier for stop loss (default 2.0)
            risk_reward_ratio: Risk/reward ratio for take profit (default 2.0)
        """
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.squeeze_percentile = squeeze_percentile
        self.lookback_periods = lookback_periods
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "bb_period": self.bb_period,
            "bb_std": self.bb_std,
            "squeeze_percentile": self.squeeze_percentile,
            "lookback_periods": self.lookback_periods,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate Bollinger Squeeze breakout signals.

        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol

        Returns:
            List of SignalData (0 or 1 signals)
        """
        min_periods = max(self.bb_period, self.lookback_periods) + 2
        if len(df) < min_periods:
            return []

        close = df["Close"]

        # Calculate Bollinger Bands
        bb = BollingerBands(close, window=self.bb_period, window_dev=self.bb_std)
        upper_band = bb.bollinger_hband()
        lower_band = bb.bollinger_lband()
        middle_band = bb.bollinger_mavg()

        # Calculate bandwidth (normalized)
        bandwidth = (upper_band - lower_band) / middle_band * 100

        # Get current values
        current_price = self._to_decimal(close.iloc[-1])
        prev_price = self._to_decimal(close.iloc[-2])
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        prev_upper = upper_band.iloc[-2]
        prev_lower = lower_band.iloc[-2]
        current_bw = bandwidth.iloc[-1]
        prev_bw = bandwidth.iloc[-2] if len(bandwidth) > 2 else None

        if current_price is None or prev_price is None:
            return []

        if any(pd.isna(x) for x in [current_upper, current_lower, current_bw]):
            return []

        # Calculate bandwidth percentile
        recent_bw = bandwidth.tail(self.lookback_periods).dropna()
        if len(recent_bw) < 10:
            return []

        bw_percentile = (recent_bw < prev_bw).sum() / len(recent_bw) * 100 if prev_bw else 50

        # Check for squeeze condition (was in squeeze, now expanding)
        was_in_squeeze = bw_percentile < self.squeeze_percentile
        is_expanding = current_bw > prev_bw if prev_bw else False

        if not (was_in_squeeze and is_expanding):
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

        # Breakout above upper band - BUY
        if float(prev_price) <= prev_upper and float(current_price) > current_upper:
            strength = self._calculate_strength(current_bw, recent_bw)
            confidence = self._calculate_confidence(bandwidth, is_buy=True)

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
                        "bb_upper": round(current_upper, 4),
                        "bb_lower": round(current_lower, 4),
                        "bandwidth": round(current_bw, 4),
                        "bw_percentile": round(bw_percentile, 2),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"Bollinger squeeze breakout (upside), BW percentile: {bw_percentile:.0f}%",
                )
            )

        # Breakout below lower band - SELL
        elif float(prev_price) >= prev_lower and float(current_price) < current_lower:
            strength = self._calculate_strength(current_bw, recent_bw)
            confidence = self._calculate_confidence(bandwidth, is_buy=False)

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
                        "bb_upper": round(current_upper, 4),
                        "bb_lower": round(current_lower, 4),
                        "bandwidth": round(current_bw, 4),
                        "bw_percentile": round(bw_percentile, 2),
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"Bollinger squeeze breakout (downside), BW percentile: {bw_percentile:.0f}%",
                )
            )

        return signals

    def _calculate_strength(self, current_bw: float, bw_series: pd.Series) -> Decimal:
        """Calculate signal strength based on squeeze intensity.

        Tighter squeeze (lower bandwidth percentile) = stronger potential breakout.
        """
        # Lower bandwidth percentile = tighter squeeze = stronger signal
        bw_percentile = (bw_series < current_bw).sum() / len(bw_series) * 100
        # Invert: lower percentile = higher strength
        strength = 0.5 + (1 - bw_percentile / 100) * 0.5
        return Decimal(str(strength)).quantize(Decimal("0.0001"))

    def _calculate_confidence(self, bandwidth: pd.Series, is_buy: bool) -> Decimal:
        """Calculate confidence based on bandwidth expansion rate.

        Faster expansion = higher confidence in the breakout.
        """
        if len(bandwidth) < 3:
            return Decimal("0.5")

        recent_bw = bandwidth.tail(3).dropna()
        if len(recent_bw) < 3:
            return Decimal("0.5")

        # Check expansion rate
        expansion_rate = (recent_bw.iloc[-1] - recent_bw.iloc[0]) / recent_bw.iloc[0]

        if expansion_rate > 0.1:  # More than 10% expansion
            confidence = 0.7
        elif expansion_rate > 0.05:  # 5-10% expansion
            confidence = 0.6
        else:
            confidence = 0.5

        return Decimal(str(confidence)).quantize(Decimal("0.0001"))
