"""Trading strategies for signal generation."""

from engine.strategies.base import BaseStrategy
from engine.strategies.registry import StrategyRegistry

# Import strategies to register them
from engine.strategies.rsi import RSIStrategy
from engine.strategies.macd import MACDCrossoverStrategy
from engine.strategies.bollinger import BollingerSqueezeStrategy
from engine.strategies.moving_average import MovingAverageCrossoverStrategy
from engine.strategies.composite import (
    CompositeStrategy,
    CompositeStrategyFactory,
    CombineLogic,
    StrategyComponent,
)
from engine.strategies.prebuilt import (
    create_rsi_macd_confluence,
    create_trend_momentum_pullback,
    create_bollinger_rsi_squeeze,
    create_triple_confirmation,
    create_intraday_momentum,
    create_gap_momentum,
    register_all_prebuilt_strategies,
)

__all__ = [
    "BaseStrategy",
    "StrategyRegistry",
    "RSIStrategy",
    "MACDCrossoverStrategy",
    "BollingerSqueezeStrategy",
    "MovingAverageCrossoverStrategy",
    "CompositeStrategy",
    "CompositeStrategyFactory",
    "CombineLogic",
    "StrategyComponent",
    "create_rsi_macd_confluence",
    "create_trend_momentum_pullback",
    "create_bollinger_rsi_squeeze",
    "create_triple_confirmation",
    "create_intraday_momentum",
    "create_gap_momentum",
    "register_all_prebuilt_strategies",
]
