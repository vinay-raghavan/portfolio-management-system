"""Trading strategies module.

This module provides base classes and utilities for trading strategies.
"""

from shared.strategies.base import BaseStrategy
from shared.strategies.composite import (
    CombineLogic,
    CompositeStrategy,
    CompositeStrategyFactory,
    StrategyComponent,
)
from shared.strategies.indicators import (
    BollingerBandsStrategy,
    MACDStrategy,
    MovingAverageCrossoverStrategy,
    RSIStrategy,
)
from shared.strategies.intraday import (
    GapAndGoStrategy,
    GapInfo,
    GapType,
    OpeningRange,
    ORBStrategy,
    TWAPPlan,
    TWAPSlice,
    TWAPStrategy,
    VWAPMomentumStrategy,
    VWAPReversionStrategy,
)
from shared.strategies.prebuilt import (
    PREBUILT_STRATEGIES,
    get_prebuilt_strategy,
    list_prebuilt_strategies,
    register_all_prebuilt_strategies,
)
from shared.strategies.registry import StrategyRegistry
from shared.strategies.swing import PriceActionVolumeSwingStrategy

__all__ = [
    # Base
    "BaseStrategy",
    "StrategyRegistry",
    # Composite
    "CompositeStrategy",
    "CompositeStrategyFactory",
    "StrategyComponent",
    "CombineLogic",
    # Indicator-based
    "MovingAverageCrossoverStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "BollingerBandsStrategy",
    # Intraday
    "VWAPReversionStrategy",
    "VWAPMomentumStrategy",
    "ORBStrategy",
    "OpeningRange",
    "GapAndGoStrategy",
    "GapType",
    "GapInfo",
    "TWAPStrategy",
    "TWAPSlice",
    "TWAPPlan",
    # Swing
    "PriceActionVolumeSwingStrategy",
    # Prebuilt
    "PREBUILT_STRATEGIES",
    "get_prebuilt_strategy",
    "list_prebuilt_strategies",
    "register_all_prebuilt_strategies",
]
