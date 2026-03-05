"""Keyword-based sentiment analysis for news articles."""

import logging
import re

from ..schemas import NewsArticle, SentimentScore

logger = logging.getLogger(__name__)

# Positive keywords with weights (higher = more positive)
POSITIVE_KEYWORDS: dict[str, float] = {
    # Strong positive
    "surge": 1.5,
    "soar": 1.5,
    "skyrocket": 1.5,
    "breakthrough": 1.5,
    "record high": 1.5,
    "all-time high": 1.5,
    "outperform": 1.2,
    "exceed": 1.2,
    "beat": 1.0,
    "rally": 1.0,
    "gain": 0.8,
    "gains": 0.8,
    "rise": 0.8,
    "rises": 0.8,
    "climb": 0.8,
    "climbs": 0.8,
    "jump": 0.9,
    "jumps": 0.9,
    "boost": 0.8,
    "upgrade": 1.0,
    "buy rating": 1.2,
    "strong buy": 1.5,
    # Moderate positive
    "growth": 0.7,
    "profit": 0.7,
    "profits": 0.7,
    "bullish": 0.9,
    "optimistic": 0.8,
    "positive": 0.6,
    "success": 0.7,
    "opportunity": 0.6,
    "recovery": 0.8,
    "expansion": 0.7,
    "innovation": 0.6,
    "dividend": 0.5,
    "revenue growth": 0.8,
    "earnings beat": 1.2,
    # Additional positive terms
    "strong": 0.7,
    "robust": 0.8,
    "bolstered": 0.7,
    "bolster": 0.7,
    "upbeat": 0.8,
    "optimism": 0.7,
    "confidence": 0.6,
    "rebound": 0.8,
    "momentum": 0.6,
    "higher": 0.5,
    "up": 0.4,
    "tops": 0.7,
    "exceeds": 1.0,
    "beats": 1.0,
    "advances": 0.7,
    "advance": 0.7,
    "advancing": 0.7,
    "strengthen": 0.7,
    "strengthens": 0.7,
    "improves": 0.7,
    "improve": 0.6,
    "improvement": 0.7,
    "record": 0.8,
    "peak": 0.7,
    "highest": 0.8,
    "best": 0.6,
    "win": 0.7,
    "wins": 0.7,
    "winner": 0.7,
    "winners": 0.6,
    "outperforms": 1.1,
    "exceeded": 1.0,
}

# Negative keywords with weights (higher = more negative)
NEGATIVE_KEYWORDS: dict[str, float] = {
    # Strong negative
    "crash": 1.5,
    "crashes": 1.5,
    "plunge": 1.5,
    "plunges": 1.5,
    "collapse": 1.5,
    "collapses": 1.5,
    "bankruptcy": 1.5,
    "bankrupt": 1.5,
    "fraud": 1.5,
    "fraudulent": 1.5,
    "scandal": 1.4,
    "lawsuit": 1.2,
    "lawsuits": 1.2,
    "investigation": 1.0,
    "investigations": 1.0,
    "downgrade": 1.0,
    "downgrades": 1.0,
    "sell rating": 1.2,
    "strong sell": 1.5,
    # Regulatory/Legal negative
    "probe": 1.2,
    "probes": 1.2,
    "antitrust": 1.2,
    "cartel": 1.4,
    "breach": 1.0,
    "breached": 1.0,
    "violation": 1.0,
    "violations": 1.0,
    "penalty": 1.0,
    "penalties": 1.0,
    "fine": 0.9,
    "fined": 1.0,
    "fines": 0.9,
    "regulatory": 0.6,
    "regulators": 0.5,
    "sued": 1.2,
    "sues": 1.1,
    # Moderate negative
    "drop": 0.8,
    "drops": 0.8,
    "fall": 0.8,
    "falls": 0.8,
    "falling": 0.8,
    "decline": 0.8,
    "declines": 0.8,
    "declining": 0.8,
    "loss": 0.9,
    "losses": 0.9,
    "miss": 0.9,
    "misses": 0.9,
    "missed": 0.9,
    "bearish": 0.9,
    "concern": 0.7,
    "concerns": 0.7,
    "worried": 0.7,
    "worry": 0.7,
    "worries": 0.7,
    "fear": 0.8,
    "fears": 0.8,
    "risk": 0.5,
    "risks": 0.5,
    "risky": 0.6,
    "warning": 0.8,
    "warns": 0.8,
    "warned": 0.8,
    "slowdown": 0.7,
    "recession": 1.0,
    "layoff": 0.9,
    "layoffs": 0.9,
    "cut": 0.6,
    "cuts": 0.6,
    "cutting": 0.6,
    "weak": 0.7,
    "weaker": 0.7,
    "weakness": 0.7,
    "disappointing": 0.9,
    "disappointed": 0.8,
    "disappointment": 0.8,
    "earnings miss": 1.2,
    "revenue miss": 1.0,
    # Market action negative
    "tumble": 1.2,
    "tumbles": 1.2,
    "slump": 1.1,
    "slumps": 1.1,
    "selloff": 1.2,
    "sell-off": 1.2,
    "tank": 1.2,
    "tanks": 1.2,
    "tanking": 1.2,
    "hammer": 1.0,
    "hammered": 1.1,
    "hit": 0.6,
    "hits": 0.5,
    "lower": 0.5,
    "down": 0.4,
    "negative": 0.6,
    "slide": 0.8,
    "slides": 0.8,
    "sliding": 0.8,
    "sink": 0.9,
    "sinks": 0.9,
    "sinking": 0.9,
    "retreats": 0.7,
    "retreat": 0.7,
    "dip": 0.5,
    "dips": 0.5,
    # Threat/danger terms
    "threat": 1.0,
    "threatens": 0.9,
    "threatened": 0.9,
    "danger": 0.9,
    "crisis": 1.2,
    "turmoil": 1.1,
    "volatility": 0.6,
    "volatile": 0.6,
    "uncertainty": 0.7,
    "uncertain": 0.6,
    # Specific negative events
    "tariff": 0.7,
    "tariffs": 0.7,
    "inflation": 0.6,
    "inflationary": 0.6,
    "defaults": 1.2,
    "default": 1.0,
    "debt": 0.5,
    "deficit": 0.7,
    "shortfall": 0.8,
    "underperform": 1.0,
    "underperforms": 1.0,
    "disappoints": 0.9,
    "struggle": 0.7,
    "struggles": 0.7,
    "struggling": 0.8,
    "challenges": 0.6,
    "challenge": 0.5,
    "pressure": 0.6,
    "pressures": 0.6,
    "pressured": 0.7,
}


class KeywordSentimentAnalyzer:
    """Keyword-based sentiment analyzer for financial news.

    Uses weighted keyword matching to determine article sentiment.
    Scores range from -1.0 (very negative) to 1.0 (very positive).
    """

    def __init__(
        self,
        positive_keywords: dict[str, float] | None = None,
        negative_keywords: dict[str, float] | None = None,
        neutral_threshold: float = 0.10,
    ):
        """Initialize the sentiment analyzer.

        Args:
            positive_keywords: Custom positive keywords with weights
            negative_keywords: Custom negative keywords with weights
            neutral_threshold: Threshold for neutral sentiment (abs(score) < threshold)
        """
        self.positive_keywords = positive_keywords or POSITIVE_KEYWORDS
        self.negative_keywords = negative_keywords or NEGATIVE_KEYWORDS
        self.neutral_threshold = neutral_threshold

    def analyze(self, article: NewsArticle) -> NewsArticle:
        """Analyze sentiment of a news article.

        Args:
            article: NewsArticle to analyze

        Returns:
            Same NewsArticle with updated sentiment fields
        """
        # Combine title and summary for analysis (title weighted higher)
        text = article.title.lower()
        if article.summary:
            text += " " + article.summary.lower()

        positive_score = 0.0
        negative_score = 0.0

        # Count positive keywords
        for keyword, weight in self.positive_keywords.items():
            count = len(re.findall(r"\b" + re.escape(keyword) + r"\b", text))
            positive_score += count * weight

        # Count negative keywords
        for keyword, weight in self.negative_keywords.items():
            count = len(re.findall(r"\b" + re.escape(keyword) + r"\b", text))
            negative_score += count * weight

        # Calculate net sentiment score (-1 to 1)
        total = positive_score + negative_score
        if total > 0:
            # Normalize to -1 to 1 range using tanh-like scaling
            raw_score = (positive_score - negative_score) / max(total, 1)
            # Clamp to -1, 1 range
            sentiment_score = max(-1.0, min(1.0, raw_score))
        else:
            sentiment_score = 0.0

        # Determine sentiment category
        if sentiment_score > self.neutral_threshold:
            sentiment = SentimentScore.POSITIVE
        elif sentiment_score < -self.neutral_threshold:
            sentiment = SentimentScore.NEGATIVE
        else:
            sentiment = SentimentScore.NEUTRAL

        article.sentiment = sentiment
        article.sentiment_score = round(sentiment_score, 3)
        return article


# Default analyzer instance
_default_analyzer = KeywordSentimentAnalyzer()


def analyze_sentiment(article: NewsArticle) -> NewsArticle:
    """Analyze sentiment of a news article using default analyzer."""
    return _default_analyzer.analyze(article)
