"""
Indicator-based trading strategies.
"""

from shared.strategies.indicators.bollinger import BollingerBandsStrategy
from shared.strategies.indicators.macd import MACDStrategy
from shared.strategies.indicators.moving_average import MovingAverageStrategy
from shared.strategies.indicators.rsi import RSIStrategy

__all__ = [
    "RSIStrategy",
    "MACDStrategy",
    "MovingAverageStrategy",
    "BollingerBandsStrategy",
]
