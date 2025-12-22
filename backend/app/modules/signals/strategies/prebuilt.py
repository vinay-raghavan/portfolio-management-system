"""Pre-built Combined Strategies.

Popular multi-indicator strategies ready to use.
These combine multiple indicators for higher-probability signals.
"""

from app.modules.signals.strategies.composite import (
    CompositeStrategy,
    CompositeStrategyFactory,
)


def create_rsi_macd_confluence() -> CompositeStrategy:
    """RSI + MACD Confluence Strategy.

    Combines RSI oversold/overbought with MACD crossover.
    Both indicators must agree for a signal.

    BUY: RSI < 30 (oversold) AND MACD bullish crossover
    SELL: RSI > 70 (overbought) AND MACD bearish crossover

    Best for: Swing trading, catching reversals with confirmation
    """
    return CompositeStrategyFactory.create(
        name="rsi_macd_confluence",
        description="RSI + MACD Confluence - Both must agree for signal",
        components=[
            {
                "strategy": "rsi",
                "params": {"oversold": 30, "overbought": 70},
                "weight": 1.0,
                "required": True,
            },
            {
                "strategy": "macd_crossover",
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
    """Trend + Momentum Pullback Strategy.

    Uses MA crossover for trend direction, RSI for pullback entry.

    BUY: MA bullish (uptrend) AND RSI < 40 (pullback)
    SELL: MA bearish (downtrend) AND RSI > 60 (bounce)

    Best for: Trend following with better entries
    """
    return CompositeStrategyFactory.create(
        name="trend_momentum_pullback",
        description="Trend + Momentum Pullback - Enter trends on pullbacks",
        components=[
            {
                "strategy": "ma_crossover",
                "params": {"fast_period": 20, "slow_period": 50},
                "weight": 1.5,  # Trend is more important
                "required": True,
            },
            {
                "strategy": "rsi",
                "params": {"oversold": 40, "overbought": 60},  # Wider bands for pullbacks
                "weight": 1.0,
                "required": True,
            },
        ],
        combine_logic="AND",
        min_combined_confidence=0.5,
        risk_reward_ratio=2.5,
    )


def create_bollinger_rsi_squeeze() -> CompositeStrategy:
    """Bollinger + RSI Squeeze Strategy.

    Combines Bollinger squeeze breakout with RSI confirmation.

    BUY: Bollinger squeeze breakout up AND RSI > 50 (momentum)
    SELL: Bollinger squeeze breakout down AND RSI < 50

    Best for: Volatility breakouts with momentum confirmation
    """
    return CompositeStrategyFactory.create(
        name="bollinger_rsi_squeeze",
        description="Bollinger + RSI Squeeze - Breakouts with momentum",
        components=[
            {
                "strategy": "bollinger_squeeze",
                "params": {"squeeze_threshold": 0.04, "breakout_confirmation": 2},
                "weight": 1.5,
                "required": True,
            },
            {
                "strategy": "rsi",
                "params": {"oversold": 45, "overbought": 55},  # Momentum filter
                "weight": 1.0,
                "required": False,  # Nice to have
            },
        ],
        combine_logic="AND",
        min_combined_confidence=0.5,
        risk_reward_ratio=2.0,
    )


def create_triple_confirmation() -> CompositeStrategy:
    """Triple Confirmation Strategy.

    Requires 2 out of 3 indicators to agree (MAJORITY logic).
    Uses RSI, MACD, and MA crossover.

    BUY: At least 2 of 3 show bullish signal
    SELL: At least 2 of 3 show bearish signal

    Best for: High-probability setups, fewer but better signals
    """
    return CompositeStrategyFactory.create(
        name="triple_confirmation",
        description="Triple Confirmation - 2 of 3 indicators must agree",
        components=[
            {
                "strategy": "rsi",
                "params": {"oversold": 35, "overbought": 65},
                "weight": 1.0,
            },
            {
                "strategy": "macd_crossover",
                "params": {},
                "weight": 1.0,
            },
            {
                "strategy": "ma_crossover",
                "params": {"fast_period": 10, "slow_period": 30},
                "weight": 1.0,
            },
        ],
        combine_logic="MAJORITY",
        min_agreement_pct=0.66,  # 2 out of 3
        min_combined_confidence=0.5,
        risk_reward_ratio=2.0,
    )


def create_intraday_momentum() -> CompositeStrategy:
    """Intraday Momentum Strategy.

    Combines ORB breakout with VWAP trend confirmation.

    BUY: ORB breakout up AND price above VWAP
    SELL: ORB breakout down AND price below VWAP

    Best for: Intraday trading on 5m charts
    """
    return CompositeStrategyFactory.create(
        name="intraday_momentum",
        description="Intraday Momentum - ORB + VWAP confirmation",
        components=[
            {
                "strategy": "orb",
                "params": {"range_minutes": 15},
                "weight": 1.5,
                "required": True,
            },
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
    """Gap + Momentum Strategy.

    Trades gaps with RSI momentum confirmation.

    BUY: Gap up AND RSI > 50 (bullish momentum)
    SELL: Gap down AND RSI < 50 (bearish momentum)

    Best for: Morning gap trades with confirmation
    """
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
                "params": {"oversold": 45, "overbought": 55},
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
    """Register all pre-built strategies with the StrategyRegistry.

    Returns:
        List of registered CompositeStrategy instances
    """
    registered = []
    for _name, factory_fn in PREBUILT_STRATEGIES.items():
        strategy = factory_fn()
        CompositeStrategyFactory.register(strategy)
        registered.append(strategy)
    return registered


def get_prebuilt_strategy(name: str) -> CompositeStrategy | None:
    """Get a pre-built strategy by name.

    Args:
        name: Strategy name

    Returns:
        CompositeStrategy instance or None if not found
    """
    factory_fn = PREBUILT_STRATEGIES.get(name)
    if factory_fn:
        return factory_fn()
    return None


def list_prebuilt_strategies() -> list[dict]:
    """List all available pre-built strategies.

    Returns:
        List of strategy info dicts
    """
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
