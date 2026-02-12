"""Recommendation service combining fundamental and technical analysis."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shared.providers.data.base import DataProvider
from shared.providers.data.yahoo import YahooDataProvider
from shared.providers.schemas import FundamentalData
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.screener.filters import FundamentalCriteria, FundamentalFilter
from app.modules.screener.models import DailyRecommendation

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for generating and retrieving stock recommendations.

    Combines fundamental analysis (PE, ROE, Debt, etc.) with technical
    analysis (momentum, breakouts) to generate quality recommendations.
    """

    def __init__(
        self,
        db: AsyncSession,
        provider: DataProvider | None = None,
    ):
        """Initialize recommendation service."""
        self.db = db
        self.provider = provider or YahooDataProvider()
        self.fundamental_filter = FundamentalFilter()

    async def get_recommendations(
        self,
        date: datetime | None = None,
        category: str | None = None,
        limit: int = 20,
    ) -> list[DailyRecommendation]:
        """Get daily recommendations from database.

        Args:
            date: Date to get recommendations for (default: today)
            category: Optional category filter
            limit: Maximum number to return

        Returns:
            List of DailyRecommendation records
        """
        if date is None:
            date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        query = select(DailyRecommendation).where(
            DailyRecommendation.date >= date,
            DailyRecommendation.date < date.replace(hour=23, minute=59, second=59),
        )

        if category:
            query = query.where(DailyRecommendation.category == category)

        query = query.order_by(DailyRecommendation.score.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    def calculate_fundamental_score(self, fundamentals: FundamentalData) -> tuple[float, list[str]]:
        """Calculate fundamental quality score.

        Args:
            fundamentals: FundamentalData with valuation and quality metrics

        Returns:
            Tuple of (score, reasons)
        """
        score = 50.0
        reasons = []

        # PE Ratio (lower is better, but not negative)
        if fundamentals.pe_ratio is not None:
            if 0 < fundamentals.pe_ratio < 15:
                score += 15
                reasons.append(f"Low P/E: {fundamentals.pe_ratio:.1f}")
            elif 15 <= fundamentals.pe_ratio < 25:
                score += 8
                reasons.append(f"Moderate P/E: {fundamentals.pe_ratio:.1f}")
            elif fundamentals.pe_ratio >= 40:
                score -= 10
                reasons.append(f"High P/E: {fundamentals.pe_ratio:.1f}")

        # ROE (higher is better)
        if fundamentals.roe is not None:
            if fundamentals.roe >= 20:
                score += 15
                reasons.append(f"Strong ROE: {fundamentals.roe:.1f}%")
            elif fundamentals.roe >= 15:
                score += 10
                reasons.append(f"Good ROE: {fundamentals.roe:.1f}%")
            elif fundamentals.roe >= 10:
                score += 5

        # Debt to Equity (lower is better)
        if fundamentals.debt_to_equity is not None:
            if fundamentals.debt_to_equity < 0.5:
                score += 10
                reasons.append(f"Low debt: D/E {fundamentals.debt_to_equity:.2f}")
            elif fundamentals.debt_to_equity < 1.0:
                score += 5
            elif fundamentals.debt_to_equity > 2.0:
                score -= 10
                reasons.append(f"High debt: D/E {fundamentals.debt_to_equity:.2f}")

        # EPS Growth (higher is better)
        if fundamentals.eps_growth_yoy is not None:
            if fundamentals.eps_growth_yoy >= 20:
                score += 12
                reasons.append(f"Strong earnings growth: {fundamentals.eps_growth_yoy:.0f}%")
            elif fundamentals.eps_growth_yoy >= 10:
                score += 8
            elif fundamentals.eps_growth_yoy < 0:
                score -= 5

        # Dividend Yield (bonus for income)
        if fundamentals.dividend_yield is not None and fundamentals.dividend_yield > 2:
            score += 5
            reasons.append(f"Dividend: {fundamentals.dividend_yield:.1f}%")

        # Profit Margin
        if fundamentals.profit_margin is not None:
            if fundamentals.profit_margin >= 20:
                score += 8
                reasons.append(f"High margins: {fundamentals.profit_margin:.0f}%")
            elif fundamentals.profit_margin >= 10:
                score += 4

        return min(100, max(0, score)), reasons

    def categorize_stock(self, fundamentals: FundamentalData, fund_score: float) -> str:
        """Categorize a stock based on its characteristics."""
        # Dividend stock
        if fundamentals.dividend_yield and fundamentals.dividend_yield >= 3:
            return "dividend"

        # Value stock
        if fundamentals.pe_ratio and fundamentals.pe_ratio < 12 and fund_score >= 60:
            return "value"

        # Growth stock
        if fundamentals.eps_growth_yoy and fundamentals.eps_growth_yoy >= 20:
            return "growth"

        # Quality stock (default)
        return "quality"

    async def get_universe_fundamentals(
        self,
        symbols: list[str],
        criteria: FundamentalCriteria | None = None,
    ) -> list[dict]:
        """Get fundamental data for a universe of stocks.

        Args:
            symbols: List of stock symbols
            criteria: Optional filter criteria

        Returns:
            List of dicts with symbol, fundamentals, and score
        """
        import asyncio

        results = []

        # Process in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            tasks = [self._get_stock_data(symbol, criteria) for symbol in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.warning(f"Error fetching stock data: {result}")
                    continue
                if result:
                    results.append(result)

        # Sort by fundamental score
        results.sort(key=lambda x: x.get("fundamental_score", 0), reverse=True)
        return results

    async def _get_stock_data(
        self,
        symbol: str,
        criteria: FundamentalCriteria | None = None,
    ) -> dict | None:
        """Get stock data with fundamentals and score.

        Args:
            symbol: Stock symbol
            criteria: Optional filter criteria

        Returns:
            Dict with stock data or None if criteria not met
        """
        try:
            fundamentals = await self.provider.get_fundamentals(symbol)
            if not fundamentals:
                return None

            # Calculate fundamental score
            fund_score, reasons = self.calculate_fundamental_score(fundamentals)

            # Apply criteria filter if provided
            if criteria:
                self.fundamental_filter.configure(criteria=criteria)
                filter_result = self.fundamental_filter.apply_with_fundamentals(symbol, fundamentals)
                if not filter_result.passed:
                    return None

            # Get quote for current price
            quote = await self.provider.get_quote(symbol)

            return {
                "symbol": symbol,
                "name": fundamentals.symbol,  # TODO: Get proper company name
                "sector": fundamentals.sector,
                "industry": fundamentals.industry,
                "current_price": float(quote.price) if quote else None,
                "price_change_pct": float(quote.change_percent) if quote and quote.change_percent else None,
                "market_cap": fundamentals.market_cap,
                "pe_ratio": fundamentals.pe_ratio,
                "pb_ratio": fundamentals.pb_ratio,
                "ps_ratio": fundamentals.ps_ratio,
                "roe": fundamentals.roe,
                "roa": fundamentals.roa,
                "profit_margin": fundamentals.profit_margin,
                "debt_to_equity": fundamentals.debt_to_equity,
                "current_ratio": fundamentals.current_ratio,
                "dividend_yield": fundamentals.dividend_yield,
                "eps_growth": fundamentals.eps_growth_yoy,
                "revenue_growth": fundamentals.revenue_growth_yoy,
                "fundamental_score": fund_score,
                "reasons": reasons,
                "category": self.categorize_stock(fundamentals, fund_score),
            }
        except Exception as e:
            logger.warning(f"Error getting data for {symbol}: {e}")
            return None

    async def generate_recommendations(
        self,
        symbols: list[str],
        technical_scores: dict[str, dict] | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Generate recommendations combining fundamental and technical analysis.

        Args:
            symbols: List of symbols to analyze
            technical_scores: Optional dict of symbol -> {score, metadata} from screener
            limit: Maximum recommendations to return

        Returns:
            List of recommendation dicts
        """
        # Get fundamental data for all symbols
        fund_data = await self.get_universe_fundamentals(symbols)

        recommendations = []
        for stock in fund_data:
            symbol = stock["symbol"]
            fund_score = stock.get("fundamental_score", 50)

            # Get technical score if available
            tech_data = technical_scores.get(symbol, {}) if technical_scores else {}
            tech_score = tech_data.get("score", 50)

            # Combined score (weighted average: 60% fundamental, 40% technical)
            combined_score = (fund_score * 0.6) + (tech_score * 0.4)

            # Generate thesis
            thesis = self._generate_thesis(stock, tech_data)

            recommendations.append(
                {
                    "symbol": symbol,
                    "name": stock.get("name"),
                    "sector": stock.get("sector"),
                    "industry": stock.get("industry"),
                    "current_price": stock.get("current_price"),
                    "price_change_pct": stock.get("price_change_pct"),
                    "fundamental_score": fund_score,
                    "technical_score": tech_score,
                    "combined_score": combined_score,
                    "category": stock.get("category", "quality"),
                    "pe_ratio": stock.get("pe_ratio"),
                    "pb_ratio": stock.get("pb_ratio"),
                    "roe": stock.get("roe"),
                    "debt_to_equity": stock.get("debt_to_equity"),
                    "dividend_yield": stock.get("dividend_yield"),
                    "eps_growth": stock.get("eps_growth"),
                    "rsi": tech_data.get("rsi"),
                    "above_200ma": tech_data.get("above_200ma"),
                    "volume_ratio": tech_data.get("volume_ratio"),
                    "pct_from_52w_high": tech_data.get("pct_from_52w_high"),
                    "thesis": thesis,
                    "reasons": stock.get("reasons", []),
                }
            )

        # Sort by combined score and limit
        recommendations.sort(key=lambda x: x["combined_score"], reverse=True)
        return recommendations[:limit]

    def _generate_thesis(self, fund_data: dict, tech_data: dict) -> str:
        """Generate a brief investment thesis."""
        parts = []

        # Fundamental quality
        fund_score = fund_data.get("fundamental_score", 50)
        if fund_score >= 75:
            parts.append("Strong fundamentals")
        elif fund_score >= 60:
            parts.append("Good fundamentals")

        # Category-specific notes
        category = fund_data.get("category", "quality")
        if category == "value":
            pe = fund_data.get("pe_ratio")
            if pe:
                parts.append(f"trading at attractive P/E of {pe:.1f}")
        elif category == "dividend":
            div = fund_data.get("dividend_yield")
            if div:
                parts.append(f"with {div:.1f}% dividend yield")
        elif category == "growth":
            growth = fund_data.get("eps_growth")
            if growth:
                parts.append(f"with {growth:.0f}% EPS growth")

        # Technical conditions
        if tech_data.get("above_200ma"):
            parts.append("above 200-day MA")
        if tech_data.get("rsi") and 40 <= tech_data["rsi"] <= 60:
            parts.append("neutral RSI")

        if parts:
            return ". ".join(parts) + "."
        return "Meets quality criteria."

