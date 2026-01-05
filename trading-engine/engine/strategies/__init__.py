"""Trading strategies for signal generation."""

from engine.strategies.base import BaseStrategy
from engine.strategies.bollinger import BollingerSqueezeStrategy
from engine.strategies.composite import (
    CombineLogic,
    CompositeStrategy,
    CompositeStrategyFactory,
    StrategyComponent,
)
from engine.strategies.gap_go import GapAndGoStrategy
from engine.strategies.macd import MACDCrossoverStrategy
from engine.strategies.moving_average import MovingAverageCrossoverStrategy
from engine.strategies.orb import ORBStrategy
from engine.strategies.prebuilt import (
    create_bollinger_rsi_squeeze,
    create_gap_momentum,
    create_intraday_momentum,
    create_rsi_macd_confluence,
    create_trend_momentum_pullback,
    create_triple_confirmation,
    register_all_prebuilt_strategies,
)
from engine.strategies.price_action_volume_swing import PriceActionVolumeSwingStrategy
from engine.strategies.registry import StrategyRegistry

# Import strategies to register them (decorator auto-registers on import)
from engine.strategies.rsi import RSIStrategy
from engine.strategies.twap import TWAPStrategy
from engine.strategies.vwap import VWAPReversionStrategy
from engine.strategies.vwap_momentum import VWAPMomentumStrategy

__all__ = [
    "BaseStrategy",
    "StrategyRegistry",
    # Single-indicator strategies
    "RSIStrategy",
    "MACDCrossoverStrategy",
    "BollingerSqueezeStrategy",
    "MovingAverageCrossoverStrategy",
    # Intraday strategies
    "VWAPMomentumStrategy",
    "VWAPReversionStrategy",
    "ORBStrategy",
    "GapAndGoStrategy",
    "TWAPStrategy",
    # Swing trading strategies
    "PriceActionVolumeSwingStrategy",
    # Composite strategies
    "CompositeStrategy",
    "CompositeStrategyFactory",
    "CombineLogic",
    "StrategyComponent",
    # Pre-built combined strategies
    "create_rsi_macd_confluence",
    "create_trend_momentum_pullback",
    "create_bollinger_rsi_squeeze",
    "create_triple_confirmation",
    "create_intraday_momentum",
    "create_gap_momentum",
    "register_all_prebuilt_strategies",
]
