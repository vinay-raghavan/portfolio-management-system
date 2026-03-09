"""Strategy Inference Engine.

Maps screener filter configurations to optimal strategy types and parameters.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel

from app.modules.screener.schemas import FilterConfig, FilterTypeEnum

logger = logging.getLogger(__name__)


class TradingIntent(str, Enum):
    """Primary trading intent detected from filters."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    TREND_FOLLOWING = "trend_following"
    SWING = "swing"
    SHORT_MOMENTUM = "short_momentum"  # Bearish momentum for short selling
    SHORT_BREAKDOWN = "short_breakdown"  # Support breakdown for short selling


class RiskProfile(str, Enum):
    """Risk profile derived from filter configuration."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class FilterAnalysis(BaseModel):
    """Analysis of screener filters."""

    primary_intent: TradingIntent
    secondary_intent: TradingIntent | None = None
    risk_profile: RiskProfile
    detected_patterns: list[str] = []


class StrategyRecommendation(BaseModel):
    """A recommended strategy with suggested parameters."""

    strategy_type: str
    strategy_name: str
    description: str
    suggested_params: dict
    confidence: float  # 0.0 - 1.0
    reasoning: list[str]


class InferenceResult(BaseModel):
    """Result of strategy inference."""

    recommended_strategy: StrategyRecommendation
    alternative_strategies: list[StrategyRecommendation] = []
    filter_analysis: FilterAnalysis


# Strategy metadata for recommendations
STRATEGY_INFO = {
    "rsi": {
        "name": "RSI Oversold/Overbought",
        "description": "Buy when RSI < 30 (oversold), Sell when RSI > 70 (overbought)",
    },
    "vwap_momentum": {
        "name": "VWAP Momentum",
        "description": "Multi-indicator momentum scoring for intraday trading",
    },
    "ma_crossover": {
        "name": "Moving Average Crossover",
        "description": "Buy on golden cross, Sell on death cross",
    },
    "bollinger": {
        "name": "Bollinger Bands",
        "description": "Mean reversion at Bollinger Band extremes",
    },
    "macd": {
        "name": "MACD Crossover",
        "description": "Momentum signals from MACD line crossovers",
    },
    "orb": {
        "name": "Opening Range Breakout",
        "description": "Intraday breakout from opening range",
    },
    "gap_go": {
        "name": "Gap and Go",
        "description": "Trade stocks gapping up with momentum",
    },
    "price_action_volume_swing": {
        "name": "Price Action Volume Swing",
        "description": "Swing trading with price action and volume confirmation",
    },
    "momentum_short": {
        "name": "Momentum Short",
        "description": "Bearish momentum signals for short selling (requires INTRADAY/SLB)",
    },
}


@dataclass
class FilterContext:
    """Extracted context from filter configurations."""

    has_momentum: bool = False
    has_volume: bool = False
    has_breakout: bool = False
    has_consolidation: bool = False
    has_moving_average: bool = False

    momentum_mode: str | None = None
    require_volume_spike: bool = False
    require_stacked_ma: bool = False
    require_trend_up: bool = False

    # Bearish/short selling detection
    is_bearish: bool = False  # Explicit bearish setup for shorting
    below_trend_ma: bool = False  # Price below 200MA
    near_52w_low: bool = False  # Price near 52-week low

    # Parameter values for derivation
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    rsi_period: int = 14
    volume_spike_threshold: float = 1.5
    near_52w_high_pct: float = 25
    min_pct_above_52w_low: float = 30
    breakout_lookback: int = 20
    max_consolidation_range: float = 10.0

    detected_patterns: list[str] = field(default_factory=list)


class StrategyInferenceEngine:
    """Engine for inferring optimal strategy from screener filters."""

    def __init__(self):
        """Initialize the inference engine."""
        pass

    def infer(self, filters: list[FilterConfig]) -> InferenceResult:
        """Infer optimal strategy from filter configurations.

        Args:
            filters: List of filter configurations from screener

        Returns:
            InferenceResult with recommended strategy and analysis
        """
        # Extract context from filters
        context = self._extract_context(filters)

        # Analyze trading intent
        analysis = self._analyze_intent(context)

        # Get strategy recommendations
        primary = self._get_primary_recommendation(context, analysis)
        alternatives = self._get_alternative_recommendations(context, analysis)

        return InferenceResult(
            recommended_strategy=primary,
            alternative_strategies=alternatives,
            filter_analysis=analysis,
        )

    def _extract_context(self, filters: list[FilterConfig]) -> FilterContext:
        """Extract relevant context from filter configurations."""
        context = FilterContext()

        for f in filters:
            params = f.params or {}

            if f.filter_type == FilterTypeEnum.MOMENTUM:
                context.has_momentum = True
                context.momentum_mode = params.get("momentum_mode", "bullish")
                context.rsi_oversold = params.get("rsi_oversold", 30)
                context.rsi_overbought = params.get("rsi_overbought", 70)
                context.rsi_period = params.get("rsi_period", 14)
                context.near_52w_high_pct = params.get("near_52w_high_pct", 25)
                context.min_pct_above_52w_low = params.get("min_pct_above_52w_low", 30)

                # Detect bearish momentum for short selling
                if context.momentum_mode == "bearish_short":
                    context.is_bearish = True
                    context.detected_patterns.append("Bearish momentum setup (SHORT)")
                elif context.momentum_mode == "bullish":
                    context.detected_patterns.append("Bullish momentum setup")
                elif context.momentum_mode == "bearish":
                    context.detected_patterns.append("Mean reversion / oversold setup")

            elif f.filter_type == FilterTypeEnum.VOLUME:
                context.has_volume = True
                context.require_volume_spike = params.get("require_spike", False)
                context.volume_spike_threshold = params.get("volume_spike_threshold", 1.5)

                if context.require_volume_spike:
                    context.detected_patterns.append("Volume spike confirmation required")

            elif f.filter_type == FilterTypeEnum.BREAKOUT:
                context.has_breakout = True
                context.breakout_lookback = params.get("lookback_period", 20)
                context.detected_patterns.append("Breakout pattern detection")

            elif f.filter_type == FilterTypeEnum.CONSOLIDATION:
                context.has_consolidation = True
                context.max_consolidation_range = params.get("max_range_pct", 10.0)
                context.detected_patterns.append("Consolidation / base building")

            elif f.filter_type == FilterTypeEnum.MOVING_AVERAGE:
                context.has_moving_average = True
                context.require_stacked_ma = params.get("require_stacked_ma", False)
                context.require_trend_up = params.get("require_trend_up", False)
                require_below_trend = params.get("require_below_trend", False)

                if context.require_stacked_ma:
                    context.detected_patterns.append("Stacked MAs (Minervini template)")
                if context.require_trend_up:
                    context.detected_patterns.append("Upward trending 200MA")
                if require_below_trend:
                    context.below_trend_ma = True
                    context.is_bearish = True
                    context.detected_patterns.append("Below 200MA (bearish trend)")

        return context

    def _analyze_intent(self, context: FilterContext) -> FilterAnalysis:
        """Analyze trading intent from filter context."""
        primary_intent = TradingIntent.MOMENTUM
        secondary_intent = None
        risk_profile = RiskProfile.MODERATE

        # Determine primary intent
        # Check for SHORT SELLING intent first (requires explicit bearish setup)
        if context.is_bearish and (context.below_trend_ma or context.has_momentum):
            primary_intent = TradingIntent.SHORT_MOMENTUM
            risk_profile = RiskProfile.AGGRESSIVE
        elif context.has_breakout and context.require_volume_spike:
            primary_intent = TradingIntent.BREAKOUT
            risk_profile = RiskProfile.AGGRESSIVE
        elif context.has_momentum and context.momentum_mode == "bearish":
            # Standard mean reversion (buy oversold), not shorting
            primary_intent = TradingIntent.MEAN_REVERSION
            risk_profile = RiskProfile.MODERATE
        elif context.require_stacked_ma or context.require_trend_up:
            primary_intent = TradingIntent.TREND_FOLLOWING
            risk_profile = RiskProfile.MODERATE
        elif context.has_consolidation:
            primary_intent = TradingIntent.SWING
            secondary_intent = TradingIntent.BREAKOUT
            risk_profile = RiskProfile.CONSERVATIVE
        elif context.has_momentum and context.momentum_mode == "bullish":
            if context.require_volume_spike:
                primary_intent = TradingIntent.MOMENTUM
                risk_profile = RiskProfile.AGGRESSIVE
            else:
                primary_intent = TradingIntent.MOMENTUM
                risk_profile = RiskProfile.MODERATE

        # Determine secondary intent
        if secondary_intent is None:
            if context.has_breakout and primary_intent != TradingIntent.BREAKOUT:
                secondary_intent = TradingIntent.BREAKOUT
            elif context.has_consolidation and primary_intent != TradingIntent.SWING:
                secondary_intent = TradingIntent.SWING

        return FilterAnalysis(
            primary_intent=primary_intent,
            secondary_intent=secondary_intent,
            risk_profile=risk_profile,
            detected_patterns=context.detected_patterns,
        )

    def _get_primary_recommendation(
        self, context: FilterContext, analysis: FilterAnalysis
    ) -> StrategyRecommendation:
        """Get the primary strategy recommendation."""
        strategy_type = "vwap_momentum"  # Default
        confidence = 0.7
        reasoning = []
        params = {}

        intent = analysis.primary_intent

        if intent == TradingIntent.SHORT_MOMENTUM:
            strategy_type = "momentum_short"
            confidence = 0.82
            reasoning = [
                "⚠️ SHORT SELLING strategy - requires INTRADAY or SLB product type",
                "Bearish momentum signals detected (below trend, weak momentum)",
                "Uses EMA, RSI, MACD, ADX for bearish confirmation",
                "Stop loss above entry, take profit below entry",
            ]
            params = {
                "ema_fast": 21,
                "ema_slow": 50,
                "ema_trend": 200,
                "rsi_period": context.rsi_period,
                "rsi_overbought": int(context.rsi_overbought),
                "adx_threshold": 25,
                "atr_stop_multiplier": 1.5,
                "risk_reward_ratio": 2.0,
                "min_score": 3,
            }

        elif intent == TradingIntent.BREAKOUT:
            strategy_type = "vwap_momentum"
            confidence = 0.85
            reasoning = [
                "Breakout filter detected - momentum strategy ideal for breakout plays",
                "Volume spike confirmation ensures valid breakout",
                "Wider stops recommended for breakout volatility",
            ]
            params = {
                "buy_threshold": 3,
                "strong_buy_threshold": 4,
                "atr_multiplier": 2.5,  # Wider stops for breakouts
                "risk_reward_ratio": 3.0,
                "volume_lookback": context.breakout_lookback,
            }

        elif intent == TradingIntent.MEAN_REVERSION:
            strategy_type = "rsi"
            confidence = 0.80
            reasoning = [
                "Bearish/oversold momentum mode detected",
                "RSI strategy optimal for mean reversion plays",
                "Parameters derived from screener RSI thresholds",
            ]
            params = {
                "rsi_period": context.rsi_period,
                "oversold_threshold": int(context.rsi_oversold),
                "overbought_threshold": int(context.rsi_overbought),
                "atr_multiplier": 1.5,  # Tighter stops for mean reversion
                "risk_reward_ratio": 2.0,
            }

        elif intent == TradingIntent.TREND_FOLLOWING:
            if context.require_stacked_ma:
                strategy_type = "ma_crossover"
                confidence = 0.82
                reasoning = [
                    "Stacked MA requirement indicates trend template (Minervini)",
                    "MA crossover strategy follows established trends",
                    "Trend confirmation via 200MA uptrend",
                ]
                params = {
                    "fast_period": 10,
                    "slow_period": 50,
                    "ma_type": "ema",
                    "atr_multiplier": 2.0,
                    "risk_reward_ratio": 2.5,
                }
            else:
                strategy_type = "vwap_momentum"
                confidence = 0.75
                reasoning = [
                    "Trend following intent with upward MA requirement",
                    "VWAP momentum provides trend confirmation",
                ]
                params = {
                    "buy_threshold": 3,
                    "ema_fast": 5,
                    "ema_medium": 9,
                    "ema_slow": 21,
                    "atr_multiplier": 2.0,
                    "risk_reward_ratio": 2.0,
                }

        elif intent == TradingIntent.SWING:
            if context.has_consolidation:
                strategy_type = "bollinger"
                confidence = 0.78
                reasoning = [
                    "Consolidation pattern detected - range-bound trading",
                    "Bollinger Bands ideal for consolidation breakouts",
                    "Tight range suggests potential squeeze",
                ]
                params = {
                    "bb_period": 20,
                    "bb_std": 2.0,
                    "atr_multiplier": 1.5,
                    "risk_reward_ratio": 2.0,
                }
            else:
                strategy_type = "price_action_volume_swing"
                confidence = 0.72
                reasoning = [
                    "Swing trading intent detected",
                    "Price action with volume confirmation",
                ]
                params = {
                    "atr_multiplier": 2.0,
                    "risk_reward_ratio": 2.5,
                }

        else:  # MOMENTUM (default)
            strategy_type = "vwap_momentum"
            confidence = 0.80 if context.require_volume_spike else 0.70
            reasoning = [
                "Bullish momentum mode detected",
                "VWAP momentum scoring for multi-indicator confirmation",
            ]
            if context.require_volume_spike:
                reasoning.append("Volume spike requirement adds confirmation")

            params = {
                "buy_threshold": 3,
                "strong_buy_threshold": 4,
                "rsi_period": context.rsi_period,
                "rsi_threshold": 50,
                "volume_lookback": 10,
                "atr_multiplier": 2.0,
                "risk_reward_ratio": 2.0,
            }

        info = STRATEGY_INFO.get(strategy_type, {"name": strategy_type, "description": ""})

        return StrategyRecommendation(
            strategy_type=strategy_type,
            strategy_name=info["name"],
            description=info["description"],
            suggested_params=params,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _get_alternative_recommendations(
        self, context: FilterContext, analysis: FilterAnalysis
    ) -> list[StrategyRecommendation]:
        """Get alternative strategy recommendations."""
        alternatives = []

        # Add alternatives based on context
        if analysis.primary_intent == TradingIntent.MOMENTUM:
            # RSI as alternative for momentum
            info = STRATEGY_INFO["rsi"]
            alternatives.append(
                StrategyRecommendation(
                    strategy_type="rsi",
                    strategy_name=info["name"],
                    description=info["description"],
                    suggested_params={
                        "rsi_period": context.rsi_period,
                        "oversold_threshold": 40,  # Adjusted for momentum
                        "overbought_threshold": 70,
                        "atr_multiplier": 2.0,
                        "risk_reward_ratio": 2.0,
                    },
                    confidence=0.60,
                    reasoning=["RSI can complement momentum with pullback entries"],
                )
            )

        if analysis.primary_intent == TradingIntent.BREAKOUT:
            # ORB as alternative for breakout
            info = STRATEGY_INFO.get("orb", {"name": "ORB", "description": ""})
            alternatives.append(
                StrategyRecommendation(
                    strategy_type="orb",
                    strategy_name=info["name"],
                    description=info["description"],
                    suggested_params={
                        "atr_multiplier": 2.0,
                        "risk_reward_ratio": 2.5,
                    },
                    confidence=0.55,
                    reasoning=["Opening Range Breakout for intraday breakout plays"],
                )
            )

        if context.has_moving_average and analysis.primary_intent != TradingIntent.TREND_FOLLOWING:
            # MA crossover as alternative
            info = STRATEGY_INFO["ma_crossover"]
            alternatives.append(
                StrategyRecommendation(
                    strategy_type="ma_crossover",
                    strategy_name=info["name"],
                    description=info["description"],
                    suggested_params={
                        "fast_period": 10,
                        "slow_period": 20,
                        "ma_type": "ema",
                        "atr_multiplier": 2.0,
                        "risk_reward_ratio": 2.0,
                    },
                    confidence=0.50,
                    reasoning=["MA crossover for trend confirmation signals"],
                )
            )

        return alternatives[:2]  # Limit to 2 alternatives


# Singleton instance
inference_engine = StrategyInferenceEngine()
