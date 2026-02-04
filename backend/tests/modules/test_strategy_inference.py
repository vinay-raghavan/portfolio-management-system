"""Unit tests for Strategy Inference Engine."""

import pytest

from app.modules.algo.strategy_inference import (
    FilterAnalysis,
    FilterContext,
    InferenceResult,
    RiskProfile,
    StrategyInferenceEngine,
    StrategyRecommendation,
    TradingIntent,
)
from app.modules.screener.schemas import FilterConfig, FilterTypeEnum


@pytest.fixture
def engine():
    """Create inference engine instance."""
    return StrategyInferenceEngine()


class TestFilterContextExtraction:
    """Tests for filter context extraction."""

    def test_extract_momentum_filter(self, engine):
        """Test extraction of momentum filter parameters."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={
                    "momentum_mode": "bullish",
                    "rsi_oversold": 25,
                    "rsi_overbought": 75,
                    "rsi_period": 10,
                    "near_52w_high_pct": 20,
                },
            )
        ]

        context = engine._extract_context(filters)

        assert context.has_momentum is True
        assert context.momentum_mode == "bullish"
        assert context.rsi_oversold == 25
        assert context.rsi_overbought == 75
        assert context.rsi_period == 10
        assert context.near_52w_high_pct == 20

    def test_extract_volume_filter(self, engine):
        """Test extraction of volume filter parameters."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={
                    "require_spike": True,
                    "volume_spike_threshold": 2.0,
                },
            )
        ]

        context = engine._extract_context(filters)

        assert context.has_volume is True
        assert context.require_volume_spike is True
        assert context.volume_spike_threshold == 2.0

    def test_extract_breakout_filter(self, engine):
        """Test extraction of breakout filter parameters."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.BREAKOUT,
                params={"lookback_period": 30},
            )
        ]

        context = engine._extract_context(filters)

        assert context.has_breakout is True
        assert context.breakout_lookback == 30

    def test_extract_consolidation_filter(self, engine):
        """Test extraction of consolidation filter parameters."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.CONSOLIDATION,
                params={"max_range_pct": 8.0},
            )
        ]

        context = engine._extract_context(filters)

        assert context.has_consolidation is True
        assert context.max_consolidation_range == 8.0

    def test_extract_moving_average_filter(self, engine):
        """Test extraction of MA filter parameters."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={
                    "require_stacked_ma": True,
                    "require_trend_up": True,
                },
            )
        ]

        context = engine._extract_context(filters)

        assert context.has_moving_average is True
        assert context.require_stacked_ma is True
        assert context.require_trend_up is True

    def test_extract_multiple_filters(self, engine):
        """Test extraction with multiple filters."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={"momentum_mode": "bullish"},
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"require_spike": True},
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.BREAKOUT,
                params={},
            ),
        ]

        context = engine._extract_context(filters)

        assert context.has_momentum is True
        assert context.has_volume is True
        assert context.has_breakout is True
        assert context.require_volume_spike is True


class TestIntentAnalysis:
    """Tests for trading intent analysis."""

    def test_breakout_intent(self, engine):
        """Test breakout intent detection."""
        context = FilterContext(
            has_breakout=True,
            require_volume_spike=True,
        )

        analysis = engine._analyze_intent(context)

        assert analysis.primary_intent == TradingIntent.BREAKOUT
        assert analysis.risk_profile == RiskProfile.AGGRESSIVE

    def test_mean_reversion_intent(self, engine):
        """Test mean reversion intent detection."""
        context = FilterContext(
            has_momentum=True,
            momentum_mode="bearish",
        )

        analysis = engine._analyze_intent(context)

        assert analysis.primary_intent == TradingIntent.MEAN_REVERSION

    def test_trend_following_intent(self, engine):
        """Test trend following intent detection."""
        context = FilterContext(
            has_moving_average=True,
            require_stacked_ma=True,
            require_trend_up=True,
        )

        analysis = engine._analyze_intent(context)

        assert analysis.primary_intent == TradingIntent.TREND_FOLLOWING

    def test_swing_intent(self, engine):
        """Test swing trading intent detection."""
        context = FilterContext(
            has_consolidation=True,
        )

        analysis = engine._analyze_intent(context)

        assert analysis.primary_intent == TradingIntent.SWING
        assert analysis.risk_profile == RiskProfile.CONSERVATIVE

    def test_momentum_intent(self, engine):
        """Test momentum intent detection."""
        context = FilterContext(
            has_momentum=True,
            momentum_mode="bullish",
            require_volume_spike=True,
        )

        analysis = engine._analyze_intent(context)

        assert analysis.primary_intent == TradingIntent.MOMENTUM
        assert analysis.risk_profile == RiskProfile.AGGRESSIVE


class TestStrategyRecommendation:
    """Tests for strategy recommendation generation."""

    def test_breakout_recommends_vwap_momentum(self, engine):
        """Test breakout scenario recommends VWAP momentum."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.BREAKOUT,
                params={"lookback_period": 20},
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"require_spike": True},
            ),
        ]

        result = engine.infer(filters)

        assert result.recommended_strategy.strategy_type == "vwap_momentum"
        assert result.recommended_strategy.confidence >= 0.8
        assert "atr_multiplier" in result.recommended_strategy.suggested_params
        # Breakouts should have wider stops
        assert result.recommended_strategy.suggested_params["atr_multiplier"] >= 2.0

    def test_bearish_momentum_recommends_rsi(self, engine):
        """Test oversold/bearish momentum recommends RSI strategy."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={
                    "momentum_mode": "bearish",
                    "rsi_oversold": 25,
                    "rsi_overbought": 80,
                    "rsi_period": 12,
                },
            ),
        ]

        result = engine.infer(filters)

        assert result.recommended_strategy.strategy_type == "rsi"
        assert result.recommended_strategy.suggested_params["oversold_threshold"] == 25
        assert result.recommended_strategy.suggested_params["overbought_threshold"] == 80
        assert result.recommended_strategy.suggested_params["rsi_period"] == 12

    def test_stacked_ma_recommends_ma_crossover(self, engine):
        """Test stacked MA requirement recommends MA crossover."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={
                    "require_stacked_ma": True,
                    "require_trend_up": True,
                },
            ),
        ]

        result = engine.infer(filters)

        assert result.recommended_strategy.strategy_type == "ma_crossover"

    def test_consolidation_recommends_bollinger(self, engine):
        """Test consolidation recommends Bollinger strategy."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.CONSOLIDATION,
                params={"max_range_pct": 8.0},
            ),
        ]

        result = engine.infer(filters)

        assert result.recommended_strategy.strategy_type == "bollinger"

    def test_bullish_momentum_recommends_vwap_momentum(self, engine):
        """Test bullish momentum recommends VWAP momentum."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={"momentum_mode": "bullish"},
            ),
        ]

        result = engine.infer(filters)

        assert result.recommended_strategy.strategy_type == "vwap_momentum"


class TestAlternativeRecommendations:
    """Tests for alternative strategy recommendations."""

    def test_momentum_has_rsi_alternative(self, engine):
        """Test momentum strategy has RSI as alternative."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={"momentum_mode": "bullish"},
            ),
        ]

        result = engine.infer(filters)

        alt_types = [a.strategy_type for a in result.alternative_strategies]
        assert "rsi" in alt_types

    def test_breakout_has_orb_alternative(self, engine):
        """Test breakout strategy has ORB as alternative."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.BREAKOUT,
                params={},
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"require_spike": True},
            ),
        ]

        result = engine.infer(filters)

        alt_types = [a.strategy_type for a in result.alternative_strategies]
        assert "orb" in alt_types

    def test_max_two_alternatives(self, engine):
        """Test that at most 2 alternatives are returned."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={"momentum_mode": "bullish"},
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_stacked_ma": False},
            ),
        ]

        result = engine.infer(filters)

        assert len(result.alternative_strategies) <= 2


class TestFullInference:
    """Integration tests for full inference pipeline."""

    def test_infer_returns_valid_result(self, engine):
        """Test that inference returns a valid InferenceResult."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={"momentum_mode": "bullish"},
            ),
        ]

        result = engine.infer(filters)

        assert isinstance(result, InferenceResult)
        assert isinstance(result.recommended_strategy, StrategyRecommendation)
        assert isinstance(result.filter_analysis, FilterAnalysis)
        assert result.recommended_strategy.strategy_type != ""
        assert 0 <= result.recommended_strategy.confidence <= 1
        assert len(result.recommended_strategy.reasoning) > 0

    def test_complex_filter_combination(self, engine):
        """Test inference with complex filter combination."""
        filters = [
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={"momentum_mode": "bullish", "near_52w_high_pct": 15},
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"require_spike": True, "volume_spike_threshold": 2.0},
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_above_trend": True},
            ),
        ]

        result = engine.infer(filters)

        # Should detect momentum as primary intent with volume confirmation
        assert result.filter_analysis.primary_intent in [
            TradingIntent.MOMENTUM,
            TradingIntent.BREAKOUT,
        ]
        assert result.recommended_strategy.strategy_type in [
            "vwap_momentum",
            "ma_crossover",
        ]
        assert "Volume spike" in str(result.filter_analysis.detected_patterns)

