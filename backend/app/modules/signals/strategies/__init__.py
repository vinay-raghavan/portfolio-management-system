"""Trading strategies for signal generation."""

from app.modules.signals.strategies.base import BaseStrategy, SignalData
from app.modules.signals.strategies.bollinger import BollingerSqueezeStrategy
from app.modules.signals.strategies.composite import (
    CombineLogic,
    CompositeStrategy,
    CompositeStrategyFactory,
    StrategyComponent,
)
from app.modules.signals.strategies.macd import MACDCrossoverStrategy
from app.modules.signals.strategies.moving_average import MovingAverageCrossoverStrategy
from app.modules.signals.strategies.orb import ORBStrategy
from app.modules.signals.strategies.registry import StrategyRegistry
from app.modules.signals.strategies.rsi import RSIStrategy

__all__ = [
    "BaseStrategy",
    "SignalData",
    "StrategyRegistry",
    "RSIStrategy",
    "MACDCrossoverStrategy",
    "MovingAverageCrossoverStrategy",
    "BollingerSqueezeStrategy",
    "ORBStrategy",
    # Composite strategies
    "CompositeStrategy",
    "CompositeStrategyFactory",
    "StrategyComponent",
    "CombineLogic",
]
