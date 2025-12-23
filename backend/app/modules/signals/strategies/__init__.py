"""Trading strategies for signal generation."""

from app.modules.signals.strategies.base import BaseStrategy, SignalData
from app.modules.signals.strategies.bollinger import BollingerSqueezeStrategy
from app.modules.signals.strategies.composite import (
    CombineLogic,
    CompositeStrategy,
    CompositeStrategyFactory,
    StrategyComponent,
)
from app.modules.signals.strategies.gap_go import GapAndGoStrategy
from app.modules.signals.strategies.macd import MACDCrossoverStrategy
from app.modules.signals.strategies.moving_average import MovingAverageCrossoverStrategy
from app.modules.signals.strategies.orb import ORBStrategy
from app.modules.signals.strategies.prebuilt import (
    PREBUILT_STRATEGIES,
    get_prebuilt_strategy,
    list_prebuilt_strategies,
    register_all_prebuilt_strategies,
)
from app.modules.signals.strategies.registry import StrategyRegistry
from app.modules.signals.strategies.rsi import RSIStrategy
from app.modules.signals.strategies.twap import TWAPStrategy
from app.modules.signals.strategies.vwap import VWAPReversionStrategy
from app.modules.signals.strategies.vwap_momentum import VWAPMomentumStrategy

__all__ = [
    "BaseStrategy",
    "SignalData",
    "StrategyRegistry",
    "RSIStrategy",
    "MACDCrossoverStrategy",
    "MovingAverageCrossoverStrategy",
    "BollingerSqueezeStrategy",
    "ORBStrategy",
    "VWAPReversionStrategy",
    "VWAPMomentumStrategy",
    "GapAndGoStrategy",
    "TWAPStrategy",
    # Composite strategies
    "CompositeStrategy",
    "CompositeStrategyFactory",
    "StrategyComponent",
    "CombineLogic",
    # Pre-built combined strategies
    "PREBUILT_STRATEGIES",
    "register_all_prebuilt_strategies",
    "get_prebuilt_strategy",
    "list_prebuilt_strategies",
]
