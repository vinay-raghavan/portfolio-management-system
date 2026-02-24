"""Tests for MultiFactorScorer service."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.multi_factor_scorer import (
    ConfidenceLevel,
    MultiFactorScorer,
    SignalDirection,
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def scorer(mock_db):
    """Create a MultiFactorScorer with default weights."""
    return MultiFactorScorer(mock_db)


@pytest.fixture
def custom_scorer(mock_db):
    """Create a MultiFactorScorer with custom weights."""
    return MultiFactorScorer(
        mock_db,
        weights={
            "technical": 0.50,
            "fundamental": 0.30,
            "sentiment": 0.20,
        },
    )


class TestSignalDirection:
    """Tests for signal direction inference."""

    def test_infer_direction_bullish_momentum(self, scorer):
        """Test bullish signal inference for momentum category."""
        direction = scorer._infer_direction(
            tech_score=85,
            fund_score=70,
            sent_score=50,  # All above neutral
            category="momentum",
        )
        assert direction == SignalDirection.LONG

    def test_infer_direction_bearish(self, scorer):
        """Test bearish signal inference."""
        direction = scorer._infer_direction(
            tech_score=25,
            fund_score=30,
            sent_score=-60,  # All below neutral
            category="value",
        )
        assert direction == SignalDirection.SHORT

    def test_infer_direction_neutral_mixed_signals(self, scorer):
        """Test neutral direction when signals conflict."""
        direction = scorer._infer_direction(
            tech_score=50,  # Neutral
            fund_score=50,  # Neutral
            sent_score=0,  # Neutral
            category="momentum",
        )
        assert direction == SignalDirection.NEUTRAL


class TestConfidenceLevel:
    """Tests for confidence level calculation."""

    def test_confidence_high(self, scorer):
        """Test high confidence (score >= 80)."""
        confidence, skip_reason = scorer._calculate_confidence(
            tech_score=85,
            fund_score=85,
            sent_score=50,
            combined_score=85,
            direction=SignalDirection.LONG,
        )
        assert confidence == ConfidenceLevel.HIGH
        assert skip_reason is None

    def test_confidence_medium(self, scorer):
        """Test medium confidence (60 <= score < 80)."""
        confidence, skip_reason = scorer._calculate_confidence(
            tech_score=70,
            fund_score=70,
            sent_score=30,
            combined_score=70,
            direction=SignalDirection.LONG,
        )
        assert confidence == ConfidenceLevel.MEDIUM
        assert skip_reason is None

    def test_confidence_low(self, scorer):
        """Test low confidence (40 <= score < 60)."""
        confidence, skip_reason = scorer._calculate_confidence(
            tech_score=55,
            fund_score=55,
            sent_score=10,
            combined_score=50,
            direction=SignalDirection.LONG,
        )
        assert confidence == ConfidenceLevel.LOW
        assert skip_reason is None

    def test_confidence_skip_low_score(self, scorer):
        """Test skip confidence (score < 40)."""
        confidence, skip_reason = scorer._calculate_confidence(
            tech_score=30,
            fund_score=30,
            sent_score=-20,
            combined_score=30,
            direction=SignalDirection.NEUTRAL,
        )
        assert confidence == ConfidenceLevel.SKIP
        assert skip_reason is not None


class TestPositionSizeMultiplier:
    """Tests for position size multiplier calculation."""

    def test_multiplier_high_confidence(self, scorer):
        """Test full position for high confidence."""
        multiplier = scorer._calculate_position_size(ConfidenceLevel.HIGH, 90)
        assert 0.9 <= multiplier <= 1.0

    def test_multiplier_medium_confidence(self, scorer):
        """Test reduced position for medium confidence."""
        multiplier = scorer._calculate_position_size(ConfidenceLevel.MEDIUM, 70)
        assert 0.6 <= multiplier <= 0.75

    def test_multiplier_low_confidence(self, scorer):
        """Test half position for low confidence."""
        multiplier = scorer._calculate_position_size(ConfidenceLevel.LOW, 50)
        assert 0.25 <= multiplier <= 0.5

    def test_multiplier_skip_confidence(self, scorer):
        """Test zero position for skip confidence."""
        multiplier = scorer._calculate_position_size(ConfidenceLevel.SKIP, 30)
        assert multiplier == 0.0


class TestStrategyRecommendation:
    """Tests for strategy recommendation."""

    def test_recommend_momentum_high_confidence(self, scorer):
        """Test momentum category with high confidence."""
        strategy = scorer._recommend_strategy("momentum", ConfidenceLevel.HIGH)
        assert strategy == "vwap_momentum"

    def test_recommend_breakout_medium_confidence(self, scorer):
        """Test breakout category with medium confidence."""
        strategy = scorer._recommend_strategy("breakout", ConfidenceLevel.MEDIUM)
        assert strategy == "bollinger"

    def test_recommend_value_low_confidence(self, scorer):
        """Test value category with low confidence."""
        strategy = scorer._recommend_strategy("value", ConfidenceLevel.LOW)
        assert strategy == "bollinger"

    def test_recommend_skip_returns_none(self, scorer):
        """Test skip confidence returns none strategy."""
        strategy = scorer._recommend_strategy("momentum", ConfidenceLevel.SKIP)
        assert strategy == "none"
