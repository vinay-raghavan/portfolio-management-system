"""Trading strategies for signal generation.

This module re-exports strategies from the shared package for backward compatibility.
All strategy implementations are now in the shared package.
"""

# Re-export everything from shared.strategies
from shared.models.signals import SignalData
from shared.strategies import (
    PREBUILT_STRATEGIES,
    BaseStrategy,
    BollingerBandsStrategy,
    CombineLogic,
    CompositeStrategy,
    CompositeStrategyFactory,
    GapAndGoStrategy,
    GapInfo,
    GapType,
    MACDStrategy,
    MovingAverageCrossoverStrategy,
    OpeningRange,
    ORBStrategy,
    PriceActionVolumeSwingStrategy,
    RSIStrategy,
    StrategyComponent,
    StrategyRegistry,
    TWAPPlan,
    TWAPSlice,
    TWAPStrategy,
    VWAPMomentumStrategy,
    VWAPReversionStrategy,
    get_prebuilt_strategy,
    list_prebuilt_strategies,
    register_all_prebuilt_strategies,
)
from shared.strategies.prebuilt import (
    create_bollinger_rsi_squeeze,
    create_gap_momentum,
    create_intraday_momentum,
    create_rsi_macd_confluence,
    create_trend_momentum_pullback,
    create_triple_confirmation,
)

# Aliases for backward compatibility with old naming
BollingerSqueezeStrategy = BollingerBandsStrategy
MACDCrossoverStrategy = MACDStrategy
MovingAverageStrategy = MovingAverageCrossoverStrategy

__all__ = [
    "BaseStrategy",
    "SignalData",
    "StrategyRegistry",
    # Single-indicator strategies
    "RSIStrategy",
    "MACDCrossoverStrategy",
    "MACDStrategy",
    "BollingerSqueezeStrategy",
    "BollingerBandsStrategy",
    "MovingAverageCrossoverStrategy",
    "MovingAverageStrategy",
    # Intraday strategies
    "VWAPMomentumStrategy",
    "VWAPReversionStrategy",
    "ORBStrategy",
    "OpeningRange",
    "GapAndGoStrategy",
    "GapType",
    "GapInfo",
    "TWAPStrategy",
    "TWAPSlice",
    "TWAPPlan",
    # Swing trading strategies
    "PriceActionVolumeSwingStrategy",
    # Composite strategies
    "CompositeStrategy",
    "CompositeStrategyFactory",
    "CombineLogic",
    "StrategyComponent",
    # Pre-built combined strategies
    "PREBUILT_STRATEGIES",
    "create_rsi_macd_confluence",
    "create_trend_momentum_pullback",
    "create_bollinger_rsi_squeeze",
    "create_triple_confirmation",
    "create_intraday_momentum",
    "create_gap_momentum",
    "register_all_prebuilt_strategies",
    "get_prebuilt_strategy",
    "list_prebuilt_strategies",
]
