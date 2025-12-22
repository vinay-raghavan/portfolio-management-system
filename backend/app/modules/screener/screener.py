"""Stock Screener implementation."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from app.modules.screener.base import BaseScreener, ScreenerResult

if TYPE_CHECKING:
    from app.providers.data.base import BaseDataProvider

logger = logging.getLogger(__name__)


class StockScreener(BaseScreener):
    """Stock screener that applies multiple filters to a universe.

    Uses data providers to fetch historical data and applies
    configured filters to identify trading candidates.
    """

    def __init__(
        self,
        name: str = "stock_screener",
        data_provider: "BaseDataProvider | None" = None,
        cache_data: bool = True,
        lookback_days: int = 252,  # 1 year for 52-week calculations
    ):
        """Initialize stock screener.

        Args:
            name: Screener name
            data_provider: Data provider for fetching OHLCV data
            cache_data: Whether to cache fetched data
            lookback_days: Days of historical data to fetch
        """
        super().__init__(name)
        self.data_provider = data_provider
        self.cache_data = cache_data
        self.lookback_days = lookback_days
        self._data_cache: dict[str, pd.DataFrame] = {}

    def set_data_provider(self, provider: "BaseDataProvider") -> None:
        """Set the data provider."""
        self.data_provider = provider

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._data_cache.clear()

    async def _fetch_data(self, symbol: str) -> pd.DataFrame | None:
        """Fetch OHLCV data for a symbol."""
        if self.cache_data and symbol in self._data_cache:
            return self._data_cache[symbol]

        if not self.data_provider:
            logger.error("No data provider configured")
            return None

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)

            data = await self.data_provider.get_historical_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval="1d",
            )

            if data is not None and not data.empty and self.cache_data:
                self._data_cache[symbol] = data

            return data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    async def screen_symbol(
        self,
        symbol: str,
        data: pd.DataFrame | None = None,
    ) -> ScreenerResult:
        """Screen a single symbol against all filters.

        Args:
            symbol: Stock symbol
            data: Optional pre-fetched OHLCV data

        Returns:
            ScreenerResult with aggregated results
        """
        # Fetch data if not provided
        if data is None:
            data = await self._fetch_data(symbol)

        if data is None or data.empty:
            return ScreenerResult(
                symbol=symbol,
                passed=False,
                score=0,
                reasons=["No data available"],
            )

        if not self.filters:
            return ScreenerResult(
                symbol=symbol,
                passed=True,
                score=100,
                reasons=["No filters applied"],
            )

        # Apply each filter
        filter_scores: dict[str, float] = {}
        reasons: list[str] = []
        metadata: dict = {}
        all_passed = True
        total_weight = 0.0
        weighted_score = 0.0

        for filter_obj in self.filters:
            result = filter_obj.apply(symbol, data)
            filter_scores[filter_obj.name] = result.score

            if not result.passed:
                all_passed = False
                reasons.append(f"[FAIL] {filter_obj.name}: {result.reason}")
            else:
                reasons.append(f"[PASS] {filter_obj.name}: {result.reason}")

            weighted_score += result.score * filter_obj.weight
            total_weight += filter_obj.weight

            if result.metadata:
                metadata[filter_obj.name] = result.metadata

        # Calculate composite score
        composite_score = weighted_score / total_weight if total_weight > 0 else 0

        return ScreenerResult(
            symbol=symbol,
            passed=all_passed,
            score=composite_score,
            filter_scores=filter_scores,
            reasons=reasons,
            metadata=metadata,
        )

    async def screen_universe(
        self,
        symbols: list[str],
        min_score: float = 0.0,
        top_n: int | None = None,
        parallel: bool = True,
        max_concurrent: int = 10,
    ) -> list[ScreenerResult]:
        """Screen a universe of symbols.

        Args:
            symbols: List of symbols to screen
            min_score: Minimum score to include in results
            top_n: Return only top N results by score
            parallel: Whether to process symbols in parallel
            max_concurrent: Maximum concurrent requests

        Returns:
            List of ScreenerResults for passing stocks, sorted by score
        """
        logger.info(f"Screening {len(symbols)} symbols with {len(self.filters)} filters")

        results: list[ScreenerResult] = []

        if parallel:
            # Process in batches to avoid overwhelming the data provider
            semaphore = asyncio.Semaphore(max_concurrent)

            async def screen_with_limit(symbol: str) -> ScreenerResult:
                async with semaphore:
                    return await self.screen_symbol(symbol)

            tasks = [screen_with_limit(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error screening {symbols[i]}: {result}")
                else:
                    valid_results.append(result)
            results = valid_results
        else:
            for symbol in symbols:
                try:
                    result = await self.screen_symbol(symbol)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error screening {symbol}: {e}")

        # Filter by passed and min_score
        passing_results = [r for r in results if r.passed and r.score >= min_score]

        # Sort by score descending
        passing_results.sort(key=lambda x: x.score, reverse=True)

        # Return top N if specified
        if top_n is not None:
            passing_results = passing_results[:top_n]

        logger.info(
            f"Screener complete: {len(passing_results)}/{len(symbols)} passed "
            f"(min_score={min_score})"
        )

        return passing_results

    async def screen_with_ranking(
        self,
        symbols: list[str],
        top_n: int = 50,
    ) -> list[dict]:
        """Screen symbols and return ranked results with full details.

        Unlike screen_universe, this returns all symbols with their scores,
        allowing for analysis of why stocks failed.

        Args:
            symbols: List of symbols to screen
            top_n: Number of top results to return with full details

        Returns:
            List of dicts with symbol, rank, score, passed, and reasons
        """
        results = await self.screen_universe(
            symbols=symbols,
            min_score=0,  # Get all results
            parallel=True,
        )

        # All results, sorted by score
        all_results = sorted(results, key=lambda x: x.score, reverse=True)

        ranked = []
        for i, result in enumerate(all_results[:top_n], 1):
            ranked.append(
                {
                    "rank": i,
                    "symbol": result.symbol,
                    "score": round(result.score, 2),
                    "passed": result.passed,
                    "filter_scores": result.filter_scores,
                    "reasons": result.reasons,
                }
            )

        return ranked

    @classmethod
    def create_momentum_screener(
        cls,
        data_provider: "BaseDataProvider | None" = None,
    ) -> "StockScreener":
        """Factory method to create a momentum-based screener.

        Filters for stocks with strong upward momentum.
        """
        from app.modules.screener.filters import (
            MomentumFilter,
            MovingAverageFilter,
            VolumeFilter,
        )

        screener = cls(name="momentum_screener", data_provider=data_provider)
        screener.add_filter(VolumeFilter(min_avg_volume=100000, weight=1.0))
        screener.add_filter(
            MomentumFilter(
                momentum_mode="bullish",
                min_roc=5,
                near_52w_high_pct=15,
                weight=2.0,
            )
        )
        screener.add_filter(
            MovingAverageFilter(
                require_above_trend=True,
                weight=1.5,
            )
        )
        return screener

    @classmethod
    def create_breakout_screener(
        cls,
        data_provider: "BaseDataProvider | None" = None,
    ) -> "StockScreener":
        """Factory method to create a breakout screener.

        Filters for stocks breaking out of consolidation.
        """
        from app.modules.screener.filters import (
            BreakoutFilter,
            VolumeFilter,
        )

        screener = cls(name="breakout_screener", data_provider=data_provider)
        screener.add_filter(
            VolumeFilter(
                min_avg_volume=50000,
                require_spike=True,
                volume_spike_threshold=1.5,
                weight=1.5,
            )
        )
        screener.add_filter(
            BreakoutFilter(
                lookback_period=20,
                breakout_pct=2.0,
                weight=2.0,
            )
        )
        return screener

    @classmethod
    def create_consolidation_screener(
        cls,
        data_provider: "BaseDataProvider | None" = None,
    ) -> "StockScreener":
        """Factory method to create a consolidation/pre-breakout screener.

        Finds stocks in tight ranges ready for potential breakout.
        """
        from app.modules.screener.filters import (
            ConsolidationFilter,
            MovingAverageFilter,
            VolumeFilter,
        )

        screener = cls(name="consolidation_screener", data_provider=data_provider)
        screener.add_filter(VolumeFilter(min_avg_volume=50000, weight=1.0))
        screener.add_filter(
            ConsolidationFilter(
                max_range_pct=10,
                declining_volume=True,
                weight=2.0,
            )
        )
        screener.add_filter(
            MovingAverageFilter(
                require_above_trend=True,
                weight=1.0,
            )
        )
        return screener
