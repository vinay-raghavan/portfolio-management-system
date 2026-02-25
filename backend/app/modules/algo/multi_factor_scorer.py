"""Multi-Factor Scoring Service.

Combines technical, fundamental, and sentiment analysis to produce
comprehensive stock scores for the auto-trade pipeline.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SignalDirection(str, Enum):
    """Direction of trading signal."""

    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class ConfidenceLevel(str, Enum):
    """Confidence level based on score alignment."""

    HIGH = "high"  # 80+ combined score with aligned signals
    MEDIUM = "medium"  # 60-80 combined score
    LOW = "low"  # 40-60 combined score
    SKIP = "skip"  # Below 40 or conflicting signals


@dataclass
class MultiFactorScore:
    """Multi-factor score for a single symbol."""

    symbol: str
    technical_score: float  # 0-100 from screener
    fundamental_score: float  # 0-100 from RecommendationService
    sentiment_score: float  # -100 to +100 (scaled from -1 to 1)
    combined_score: float  # Weighted average (0-100)
    direction: SignalDirection  # Inferred from signals
    confidence: ConfidenceLevel  # Based on score alignment
    recommended_strategy: str  # Inferred strategy type
    position_size_multiplier: float  # 0.25 to 1.0 based on confidence
    reasons: list[str]  # Explanation of scoring
    skip_reason: str | None = None  # If confidence == SKIP

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "symbol": self.symbol,
            "technical_score": round(self.technical_score, 2),
            "fundamental_score": round(self.fundamental_score, 2),
            "sentiment_score": round(self.sentiment_score, 2),
            "combined_score": round(self.combined_score, 2),
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "recommended_strategy": self.recommended_strategy,
            "position_size_multiplier": round(self.position_size_multiplier, 2),
            "reasons": self.reasons,
            "skip_reason": self.skip_reason,
        }


# Strategy recommendations by category and confidence
STRATEGY_MAP = {
    "momentum": {
        "high": "vwap_momentum",
        "medium": "ma_crossover",
        "low": "rsi",
    },
    "breakout": {
        "high": "breakout_swing",
        "medium": "bollinger",
        "low": "range_breakout",
    },
    "value": {
        "high": "value_momentum",
        "medium": "rsi",
        "low": "bollinger",
    },
    "sector": {
        "high": "sector_rotation",
        "medium": "ma_crossover",
        "low": "trend_following",
    },
}


class MultiFactorScorer:
    """Combines technical, fundamental, and sentiment analysis.

    Produces comprehensive scores for the auto-trade pipeline.
    """

    def __init__(
        self,
        db: AsyncSession,
        weights: dict | None = None,
    ):
        """Initialize MultiFactorScorer.

        Args:
            db: Database session for queries
            weights: Custom weights for scoring factors
        """
        self.db = db
        # Default weights (must sum to 1.0)
        self.weights = weights or {
            "technical": 0.40,
            "fundamental": 0.40,
            "sentiment": 0.20,
        }

    async def score_symbol(
        self,
        symbol: str,
        category: str,
        technical_data: dict | None = None,
        fundamental_data: dict | None = None,
    ) -> MultiFactorScore:
        """Calculate multi-factor score for a single symbol.

        Args:
            symbol: Stock symbol
            category: Recommendation category (momentum, breakout, value, sector)
            technical_data: Pre-computed technical data from screener
            fundamental_data: Pre-computed fundamental data

        Returns:
            MultiFactorScore with combined analysis
        """
        reasons: list[str] = []

        # 1. Get technical score
        tech_score, tech_reasons = await self._get_technical_score(symbol, category, technical_data)
        reasons.extend(tech_reasons)

        # 2. Get fundamental score
        fund_score, fund_reasons = await self._get_fundamental_score(symbol, fundamental_data)
        reasons.extend(fund_reasons)

        # 3. Get sentiment score
        sent_score, sent_reasons = await self._get_sentiment_score(symbol)
        reasons.extend(sent_reasons)

        # 4. Calculate combined score (normalize sentiment to 0-100)
        normalized_sentiment = (sent_score + 100) / 2  # -100 to +100 -> 0 to 100
        combined = (
            tech_score * self.weights["technical"]
            + fund_score * self.weights["fundamental"]
            + normalized_sentiment * self.weights["sentiment"]
        )

        # 5. Infer direction
        direction = self._infer_direction(tech_score, fund_score, sent_score, category)

        # 6. Calculate confidence
        confidence, skip_reason = self._calculate_confidence(
            tech_score, fund_score, sent_score, combined, direction
        )

        # 7. Get recommended strategy
        recommended_strategy = self._recommend_strategy(category, confidence)

        # 8. Calculate position size multiplier
        size_multiplier = self._calculate_position_size(confidence, combined)

        return MultiFactorScore(
            symbol=symbol,
            technical_score=tech_score,
            fundamental_score=fund_score,
            sentiment_score=sent_score,
            combined_score=combined,
            direction=direction,
            confidence=confidence,
            recommended_strategy=recommended_strategy,
            position_size_multiplier=size_multiplier,
            reasons=reasons,
            skip_reason=skip_reason,
        )

    async def score_symbols(
        self,
        symbols: list[str],
        category: str,
        technical_data: dict[str, dict] | None = None,
        fundamental_data: dict[str, dict] | None = None,
    ) -> list[MultiFactorScore]:
        """Score multiple symbols concurrently.

        Args:
            symbols: List of stock symbols
            category: Recommendation category
            technical_data: Dict of symbol -> technical data
            fundamental_data: Dict of symbol -> fundamental data

        Returns:
            List of MultiFactorScore objects
        """
        tasks = [
            self.score_symbol(
                symbol,
                category,
                technical_data.get(symbol) if technical_data else None,
                fundamental_data.get(symbol) if fundamental_data else None,
            )
            for symbol in symbols
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def _get_technical_score(
        self,
        symbol: str,
        category: str,
        technical_data: dict | None = None,
    ) -> tuple[float, list[str]]:
        """Get technical score from screener data.

        Args:
            symbol: Stock symbol
            category: Category for context
            technical_data: Pre-computed screener data

        Returns:
            Tuple of (score 0-100, list of reasons)
        """
        reasons = []

        if technical_data:
            score = technical_data.get("score", 50.0)
            # Extract specific reasons from screener metadata
            if "momentum_score" in technical_data:
                reasons.append(f"Momentum: {technical_data['momentum_score']:.0f}")
            if "volume_ratio" in technical_data:
                vol_ratio = technical_data["volume_ratio"]
                if vol_ratio > 1.5:
                    reasons.append(f"High volume ({vol_ratio:.1f}x avg)")
            if "breakout_score" in technical_data:
                reasons.append(f"Breakout: {technical_data['breakout_score']:.0f}")
            if "ma_position" in technical_data:
                ma_pos = technical_data["ma_position"]
                if ma_pos == "above":
                    reasons.append("Price above MAs")
                elif ma_pos == "below":
                    reasons.append("Price below MAs")
            return float(score), reasons

        # Default score if no technical data
        return 50.0, ["Technical data not available"]

    async def _get_fundamental_score(
        self,
        symbol: str,
        fundamental_data: dict | None = None,
    ) -> tuple[float, list[str]]:
        """Get fundamental score from RecommendationService data.

        If fundamental_data is not provided, attempts to fetch it from the
        RecommendationService automatically.

        Args:
            symbol: Stock symbol
            fundamental_data: Pre-computed fundamental data

        Returns:
            Tuple of (score 0-100, list of reasons)
        """
        reasons = []

        # If fundamental data provided, use it
        if fundamental_data:
            score = fundamental_data.get("fundamental_score", 50.0)
            # Extract reasons from fundamental data
            if "reasons" in fundamental_data:
                reasons.extend(fundamental_data["reasons"][:3])  # Top 3 reasons
            elif "category" in fundamental_data:
                reasons.append(f"Category: {fundamental_data['category']}")
            return float(score), reasons

        # Try to fetch fundamental data if not provided
        try:
            from app.modules.research.recommendation_service import RecommendationService

            rec_service = RecommendationService(self.db)
            fund_list = await rec_service.get_universe_fundamentals([symbol])
            if fund_list:
                fund_data = fund_list[0]
                score = fund_data.get("fundamental_score", 50.0)
                if "category" in fund_data:
                    reasons.append(f"Category: {fund_data['category']}")
                if fund_data.get("pe_ratio"):
                    reasons.append(f"P/E: {fund_data['pe_ratio']:.1f}")
                return float(score), reasons
        except Exception as e:
            logger.warning(f"Error fetching fundamentals for {symbol}: {e}")

        # Default score if no fundamental data available
        return 50.0, ["Fundamental data not available"]

    async def _get_sentiment_score(
        self,
        symbol: str,
    ) -> tuple[float, list[str]]:
        """Get sentiment score from news data.

        Args:
            symbol: Stock symbol

        Returns:
            Tuple of (score -100 to +100, list of reasons)
        """
        reasons = []

        try:
            # Import here to avoid circular imports
            from app.modules.research.service import ResearchService

            research_service = ResearchService()
            news_response = await research_service.get_news(symbol, limit=10)

            if news_response and news_response.articles:
                avg_sentiment = news_response.average_sentiment
                # Scale from -1 to +1 -> -100 to +100
                score = avg_sentiment * 100

                # Build sentiment reasons
                if news_response.positive_count > news_response.negative_count:
                    reasons.append(f"Positive news ({news_response.positive_count} articles)")
                elif news_response.negative_count > news_response.positive_count:
                    reasons.append(f"Negative news ({news_response.negative_count} articles)")
                else:
                    reasons.append("Mixed news sentiment")

                return score, reasons
            else:
                return 0.0, ["No recent news"]

        except Exception as e:
            logger.warning(f"Error fetching sentiment for {symbol}: {e}")
            return 0.0, ["Sentiment unavailable"]

    def _infer_direction(
        self,
        tech_score: float,
        fund_score: float,
        sent_score: float,
        category: str,
    ) -> SignalDirection:
        """Infer trading direction from signals.

        Args:
            tech_score: Technical score (0-100)
            fund_score: Fundamental score (0-100)
            sent_score: Sentiment score (-100 to +100)
            category: Recommendation category

        Returns:
            SignalDirection (LONG, SHORT, NEUTRAL)
        """
        # Calculate directional bias
        tech_bias = (tech_score - 50) / 50  # -1 to +1
        fund_bias = (fund_score - 50) / 50  # -1 to +1
        sent_bias = sent_score / 100  # -1 to +1

        # Weight by category
        if category in ["momentum", "breakout"]:
            # More weight on technical for momentum/breakout
            combined_bias = tech_bias * 0.5 + fund_bias * 0.3 + sent_bias * 0.2
        elif category == "value":
            # More weight on fundamentals for value
            combined_bias = tech_bias * 0.25 + fund_bias * 0.55 + sent_bias * 0.2
        else:
            # Balanced
            combined_bias = tech_bias * 0.4 + fund_bias * 0.4 + sent_bias * 0.2

        # Threshold for direction
        if combined_bias > 0.2:
            return SignalDirection.LONG
        elif combined_bias < -0.2:
            return SignalDirection.SHORT
        else:
            return SignalDirection.NEUTRAL

    def _calculate_confidence(
        self,
        tech_score: float,
        fund_score: float,
        sent_score: float,
        combined_score: float,
        direction: SignalDirection,
    ) -> tuple[ConfidenceLevel, str | None]:
        """Calculate confidence level based on score alignment.

        Args:
            tech_score: Technical score (0-100)
            fund_score: Fundamental score (0-100)
            sent_score: Sentiment score (-100 to +100)
            combined_score: Weighted combined score
            direction: Inferred direction

        Returns:
            Tuple of (ConfidenceLevel, skip_reason or None)
        """
        skip_reason = None

        # Check for conflicting signals
        tech_bullish = tech_score > 55
        fund_bullish = fund_score > 55
        sent_bullish = sent_score > 10

        tech_bearish = tech_score < 45
        fund_bearish = fund_score < 45
        sent_bearish = sent_score < -10

        # Count aligned signals for LONG
        long_signals = sum([tech_bullish, fund_bullish, sent_bullish])
        short_signals = sum([tech_bearish, fund_bearish, sent_bearish])

        # Check for conflicts
        if direction == SignalDirection.LONG and short_signals >= 2:
            skip_reason = "Conflicting signals: 2+ factors bearish while direction is LONG"
            return ConfidenceLevel.SKIP, skip_reason
        elif direction == SignalDirection.SHORT and long_signals >= 2:
            skip_reason = "Conflicting signals: 2+ factors bullish while direction is SHORT"
            return ConfidenceLevel.SKIP, skip_reason

        # Neutral direction with low combined score
        if direction == SignalDirection.NEUTRAL and combined_score < 50:
            skip_reason = "Neutral direction with below-average combined score"
            return ConfidenceLevel.SKIP, skip_reason

        # Combined score thresholds
        if combined_score < 40:
            skip_reason = f"Combined score too low: {combined_score:.1f}"
            return ConfidenceLevel.SKIP, skip_reason
        elif combined_score >= 80:
            return ConfidenceLevel.HIGH, None
        elif combined_score >= 60:
            return ConfidenceLevel.MEDIUM, None
        else:
            return ConfidenceLevel.LOW, None

    def _recommend_strategy(
        self,
        category: str,
        confidence: ConfidenceLevel,
    ) -> str:
        """Recommend strategy based on category and confidence.

        Args:
            category: Recommendation category
            confidence: Confidence level

        Returns:
            Strategy type string
        """
        if confidence == ConfidenceLevel.SKIP:
            return "none"

        category_strategies = STRATEGY_MAP.get(category, STRATEGY_MAP["momentum"])
        return category_strategies.get(confidence.value, "rsi")

    def _calculate_position_size(
        self,
        confidence: ConfidenceLevel,
        combined_score: float,
    ) -> float:
        """Calculate position size multiplier based on confidence.

        Args:
            confidence: Confidence level
            combined_score: Weighted combined score

        Returns:
            Position size multiplier (0.25 to 1.0)
        """
        base_multipliers = {
            ConfidenceLevel.HIGH: 1.0,
            ConfidenceLevel.MEDIUM: 0.75,
            ConfidenceLevel.LOW: 0.5,
            ConfidenceLevel.SKIP: 0.0,
        }

        base = base_multipliers.get(confidence, 0.5)

        # Adjust based on combined score within the confidence band
        if confidence == ConfidenceLevel.HIGH:
            # 80-100 -> adjust between 0.9 and 1.0
            adjustment = (combined_score - 80) / 20 * 0.1
            return min(1.0, base + adjustment)
        elif confidence == ConfidenceLevel.MEDIUM:
            # 60-80 -> adjust between 0.6 and 0.75
            adjustment = (combined_score - 60) / 20 * 0.15
            return max(0.6, min(0.75, base + adjustment - 0.15))
        elif confidence == ConfidenceLevel.LOW:
            # 40-60 -> adjust between 0.25 and 0.5
            adjustment = (combined_score - 40) / 20 * 0.25
            return max(0.25, min(0.5, base + adjustment - 0.25))
        else:
            return 0.0
