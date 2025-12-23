"""Trading strategies for signal generation."""

from engine.strategies.base import BaseStrategy
from engine.strategies.bollinger import BollingerSqueezeStrategy
from engine.strategies.composite import (
    CombineLogic,
    CompositeStrategy,
    CompositeStrategyFactory,
    StrategyComponent,
)
from engine.strategies.macd import MACDCrossoverStrategy
from engine.strategies.moving_average import MovingAverageCrossoverStrategy
from engine.strategies.prebuilt import (
    create_bollinger_rsi_squeeze,
    create_gap_momentum,
    create_intraday_momentum,
    create_rsi_macd_confluence,
    create_trend_momentum_pullback,
    create_triple_confirmation,
    register_all_prebuilt_strategies,
)
from engine.strategies.registry import StrategyRegistry

# Import strategies to register them
from engine.strategies.rsi import RSIStrategy

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
