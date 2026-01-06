"""Bollinger Bands trading strategy."""

from decimal import Decimal

import pandas as pd
from ta.volatility import AverageTrueRange, BollingerBands

from shared.models.signals import SignalData, SignalType
from shared.strategies.base import BaseStrategy
from shared.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands Mean Reversion Strategy.

    Generates BUY signals when price touches or crosses below the lower band,
    and SELL signals when price touches or crosses above the upper band.

    Signal strength is based on how far price has moved beyond the bands.
    """

    name = "bollinger"
    description = "Bollinger Bands Mean Reversion - Buy at lower band, Sell at upper band"
    default_timeframe = "1d"

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize Bollinger Bands strategy."""
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "bb_period": self.bb_period,
            "bb_std": self.bb_std,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate Bollinger Bands-based trading signals."""
        if len(df) < self.bb_period + 1:
            return []

        close = df["Close"]
        bb_indicator = BollingerBands(close, window=self.bb_period, window_dev=self.bb_std)

        upper_band = bb_indicator.bollinger_hband()
        middle_band = bb_indicator.bollinger_mavg()
        lower_band = bb_indicator.bollinger_lband()
        _bb_width = bb_indicator.bollinger_wband()
        bb_pband = bb_indicator.bollinger_pband()

        current_price = self._to_decimal(close.iloc[-1])
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_middle = middle_band.iloc[-1]
        current_pband = bb_pband.iloc[-1]

        if pd.isna(current_upper) or pd.isna(current_lower) or current_price is None:
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
        price_float = float(current_price)

        if price_float <= current_lower:
            strength = self._calculate_strength(
                price_float, current_lower, current_upper, is_buy=True
            )
            confidence = self._calculate_confidence(bb_pband, is_buy=True)
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
                        "bb_upper": round(current_upper, 2),
                        "bb_middle": round(current_middle, 2),
                        "bb_lower": round(current_lower, 2),
                        "bb_pband": round(current_pband, 4) if not pd.isna(current_pband) else None,
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"Price at lower Bollinger Band ({current_lower:.2f})",
                )
            )

        elif price_float >= current_upper:
            strength = self._calculate_strength(
                price_float, current_lower, current_upper, is_buy=False
            )
            confidence = self._calculate_confidence(bb_pband, is_buy=False)
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
                        "bb_upper": round(current_upper, 2),
                        "bb_middle": round(current_middle, 2),
                        "bb_lower": round(current_lower, 2),
                        "bb_pband": round(current_pband, 4) if not pd.isna(current_pband) else None,
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"Price at upper Bollinger Band ({current_upper:.2f})",
                )
            )

        else:
            _distance_to_upper = current_upper - price_float
            distance_to_lower = price_float - current_lower
            band_width = current_upper - current_lower
            position_in_band = distance_to_lower / band_width if band_width > 0 else 0.5
            strength = Decimal(str(0.5 + abs(position_in_band - 0.5) * 0.3)).quantize(
                Decimal("0.0001")
            )

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
                        "bb_upper": round(current_upper, 2),
                        "bb_middle": round(current_middle, 2),
                        "bb_lower": round(current_lower, 2),
                        "bb_pband": round(current_pband, 4) if not pd.isna(current_pband) else None,
                        "atr": float(atr) if atr else None,
                    },
                    notes=f"Price within Bollinger Bands (position: {position_in_band:.2%})",
                )
            )

        return signals

    def _calculate_strength(
        self, price: float, lower: float, upper: float, is_buy: bool
    ) -> Decimal:
        """Calculate signal strength based on price position relative to bands."""
        band_width = upper - lower
        if band_width == 0:
            return Decimal("0.5")

        if is_buy:
            # How far below lower band
            overshoot = max(0, lower - price)
            relative_overshoot = overshoot / band_width
            strength = 0.6 + min(0.4, relative_overshoot * 2)
        else:
            # How far above upper band
            overshoot = max(0, price - upper)
            relative_overshoot = overshoot / band_width
            strength = 0.6 + min(0.4, relative_overshoot * 2)

        return Decimal(str(strength)).quantize(Decimal("0.0001"))

    def _calculate_confidence(self, pband_series: pd.Series, is_buy: bool) -> Decimal:
        """Calculate confidence based on %B trend."""
        if len(pband_series) < 5:
            return Decimal("0.5")

        recent_pband = pband_series.tail(5).dropna()
        if len(recent_pband) < 3:
            return Decimal("0.5")

        pband_trend = recent_pband.iloc[-1] - recent_pband.iloc[0]

        # For buy signals, we want %B to be declining (approaching lower band)
        # For sell signals, we want %B to be rising (approaching upper band)
        if (is_buy and pband_trend < 0) or (not is_buy and pband_trend > 0):
            confidence = 0.7
        else:
            confidence = 0.5

        return Decimal(str(confidence)).quantize(Decimal("0.0001"))
