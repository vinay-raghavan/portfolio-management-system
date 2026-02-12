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
    "rise": 0.8,
    "climb": 0.8,
    "jump": 0.9,
    "boost": 0.8,
    "upgrade": 1.0,
    "buy rating": 1.2,
    "strong buy": 1.5,
    # Moderate positive
    "growth": 0.7,
    "profit": 0.7,
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
}

# Negative keywords with weights (higher = more negative)
NEGATIVE_KEYWORDS: dict[str, float] = {
    # Strong negative
    "crash": 1.5,
    "plunge": 1.5,
    "collapse": 1.5,
    "bankruptcy": 1.5,
    "fraud": 1.5,
    "scandal": 1.4,
    "lawsuit": 1.2,
    "investigation": 1.0,
    "downgrade": 1.0,
    "sell rating": 1.2,
    "strong sell": 1.5,
    # Moderate negative
    "drop": 0.8,
    "fall": 0.8,
    "decline": 0.8,
    "loss": 0.9,
    "miss": 0.9,
    "bearish": 0.9,
    "concern": 0.7,
    "worry": 0.7,
    "fear": 0.8,
    "risk": 0.5,
    "warning": 0.8,
    "slowdown": 0.7,
    "recession": 1.0,
    "layoff": 0.9,
    "layoffs": 0.9,
    "cut": 0.6,
    "weak": 0.7,
    "disappointing": 0.9,
    "earnings miss": 1.2,
    "revenue miss": 1.0,
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
        neutral_threshold: float = 0.15,
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
