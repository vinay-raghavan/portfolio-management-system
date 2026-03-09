"""Pre-built Combined Strategies.

Popular multi-indicator strategies ready to use.
These combine multiple indicators for higher-probability signals.
"""

from shared.strategies.composite import CompositeStrategy, CompositeStrategyFactory

# Import short strategies to trigger their @StrategyRegistry.register decorators
# This ensures they are registered when the prebuilt module is loaded
from shared.strategies.short import MomentumShortStrategy as _MomentumShortStrategy  # noqa: F401


def create_rsi_macd_confluence() -> CompositeStrategy:
    """RSI + MACD Confluence Strategy."""
    return CompositeStrategyFactory.create(
        name="rsi_macd_confluence",
        description="RSI + MACD Confluence - Both must agree for signal",
        components=[
            {
                "strategy": "rsi",
                "params": {"oversold_threshold": 30, "overbought_threshold": 70},
                "weight": 1.0,
                "required": True,
            },
            {
                "strategy": "macd",
                "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
                "weight": 1.0,
                "required": True,
            },
        ],
        combine_logic="AND",
        min_combined_confidence=0.5,
        risk_reward_ratio=2.0,
    )


def create_trend_momentum_pullback() -> CompositeStrategy:
    """Trend + Momentum Pullback Strategy."""
    return CompositeStrategyFactory.create(
        name="trend_momentum_pullback",
        description="Trend + Momentum Pullback - Enter trends on pullbacks",
        components=[
            {
                "strategy": "moving_average",
                "params": {"fast_period": 20, "slow_period": 50},
                "weight": 1.5,
                "required": True,
            },
            {
                "strategy": "rsi",
                "params": {"oversold_threshold": 40, "overbought_threshold": 60},
                "weight": 1.0,
                "required": True,
            },
        ],
        combine_logic="AND",
        min_combined_confidence=0.5,
        risk_reward_ratio=2.5,
    )


def create_bollinger_rsi_squeeze() -> CompositeStrategy:
    """Bollinger + RSI Squeeze Strategy."""
    return CompositeStrategyFactory.create(
        name="bollinger_rsi_squeeze",
        description="Bollinger + RSI Squeeze - Breakouts with momentum",
        components=[
            {
                "strategy": "bollinger_bands",
                "params": {"squeeze_percentile": 20, "lookback_periods": 50},
                "weight": 1.5,
                "required": True,
            },
            {
                "strategy": "rsi",
                "params": {"oversold_threshold": 45, "overbought_threshold": 55},
                "weight": 1.0,
                "required": False,
            },
        ],
        combine_logic="AND",
        min_combined_confidence=0.5,
        risk_reward_ratio=2.0,
    )


def create_triple_confirmation() -> CompositeStrategy:
    """Triple Confirmation Strategy."""
    return CompositeStrategyFactory.create(
        name="triple_confirmation",
        description="Triple Confirmation - 2 of 3 indicators must agree",
        components=[
            {
                "strategy": "rsi",
                "params": {"oversold_threshold": 35, "overbought_threshold": 65},
                "weight": 1.0,
            },
            {"strategy": "macd", "params": {}, "weight": 1.0},
            {
                "strategy": "moving_average",
                "params": {"fast_period": 10, "slow_period": 30},
                "weight": 1.0,
            },
        ],
        combine_logic="MAJORITY",
        min_agreement_pct=0.66,
        min_combined_confidence=0.5,
        risk_reward_ratio=2.0,
    )


def create_intraday_momentum() -> CompositeStrategy:
    """Intraday Momentum Strategy."""
    return CompositeStrategyFactory.create(
        name="intraday_momentum",
        description="Intraday Momentum - ORB + VWAP confirmation",
        components=[
            {"strategy": "orb", "params": {"range_minutes": 15}, "weight": 1.5, "required": True},
            {
                "strategy": "vwap_reversion",
                "params": {"require_band_touch": False},
                "weight": 1.0,
                "required": False,
            },
        ],
        combine_logic="AND",
        min_combined_confidence=0.5,
        risk_reward_ratio=2.0,
    )


def create_gap_momentum() -> CompositeStrategy:
    """Gap + Momentum Strategy."""
    return CompositeStrategyFactory.create(
        name="gap_momentum",
        description="Gap + Momentum - Gaps with RSI confirmation",
        components=[
            {
                "strategy": "gap_go",
                "params": {"min_gap_pct": 1.0, "max_gap_pct": 5.0},
                "weight": 1.5,
                "required": True,
            },
            {
                "strategy": "rsi",
                "params": {"oversold_threshold": 45, "overbought_threshold": 55},
                "weight": 1.0,
                "required": False,
            },
        ],
        combine_logic="AND",
        min_combined_confidence=0.5,
        risk_reward_ratio=2.0,
    )


# Registry of all pre-built strategies
PREBUILT_STRATEGIES = {
    "rsi_macd_confluence": create_rsi_macd_confluence,
    "trend_momentum_pullback": create_trend_momentum_pullback,
    "bollinger_rsi_squeeze": create_bollinger_rsi_squeeze,
    "triple_confirmation": create_triple_confirmation,
    "intraday_momentum": create_intraday_momentum,
    "gap_momentum": create_gap_momentum,
}


def register_all_prebuilt_strategies() -> list[CompositeStrategy]:
    """Register all pre-built strategies with the StrategyRegistry."""
    registered = []
    for _name, factory_fn in PREBUILT_STRATEGIES.items():
        strategy = factory_fn()
        CompositeStrategyFactory.register(strategy)
        registered.append(strategy)
    return registered


def get_prebuilt_strategy(name: str) -> CompositeStrategy | None:
    """Get a pre-built strategy by name."""
    factory_fn = PREBUILT_STRATEGIES.get(name)
    if factory_fn:
        return factory_fn()
    return None


def list_prebuilt_strategies() -> list[dict]:
    """List all available pre-built strategies."""
    strategies = []
    for _name, factory_fn in PREBUILT_STRATEGIES.items():
        strategy = factory_fn()
        strategies.append(
            {
                "name": strategy.name,
                "description": strategy.description,
                "components": [c.strategy_name for c in strategy.components],
                "combine_logic": strategy.combine_logic.value,
            }
        )
    return strategies
