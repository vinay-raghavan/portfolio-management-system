"""Base classes for stock screener."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd


class FilterType(str, Enum):
    """Types of screener filters."""

    VOLUME = "volume"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    CONSOLIDATION = "consolidation"
    MOVING_AVERAGE = "moving_average"
    PRICE_ACTION = "price_action"
    FUNDAMENTAL = "fundamental"
    CUSTOM = "custom"


@dataclass
class ScreenerResult:
    """Result of screening a stock."""

    symbol: str
    passed: bool
    score: float = 0.0  # 0-100 overall score
    filter_scores: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    screened_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FilterResult:
    """Result of applying a single filter."""

    passed: bool
    score: float = 0.0  # 0-100 filter score
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseFilter(ABC):
    """Base class for screener filters."""

    filter_type: FilterType = FilterType.CUSTOM
    name: str = "base_filter"
    weight: float = 1.0  # Weight for composite scoring

    def __init__(self, **params):
        """Initialize filter with parameters."""
        self.params = params
        self.configure(**params)

    def configure(self, **params) -> None:  # noqa: B027
        """Configure filter parameters. Override in subclasses."""
        pass

    @abstractmethod
    def apply(self, symbol: str, data: pd.DataFrame) -> FilterResult:
        """Apply filter to a stock's data.

        Args:
            symbol: Stock symbol
            data: OHLCV DataFrame with at minimum 'close', 'volume' columns

        Returns:
            FilterResult with pass/fail and score
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, params={self.params})"


class BaseScreener(ABC):
    """Base class for stock screeners."""

    def __init__(self, name: str = "base_screener"):
        """Initialize screener."""
        self.name = name
        self.filters: list[BaseFilter] = []

    def add_filter(self, filter_obj: BaseFilter) -> "BaseScreener":
        """Add a filter to the screener."""
        self.filters.append(filter_obj)
        return self

    def remove_filter(self, filter_name: str) -> bool:
        """Remove a filter by name."""
        for i, f in enumerate(self.filters):
            if f.name == filter_name:
                self.filters.pop(i)
                return True
        return False

    def clear_filters(self) -> None:
        """Remove all filters."""
        self.filters.clear()

    @abstractmethod
    async def screen_symbol(
        self,
        symbol: str,
        data: pd.DataFrame,
    ) -> ScreenerResult:
        """Screen a single symbol.

        Args:
            symbol: Stock symbol
            data: OHLCV DataFrame

        Returns:
            ScreenerResult with aggregated results from all filters
        """
        pass

    @abstractmethod
    async def screen_universe(
        self,
        symbols: list[str],
        min_score: float = 0.0,
        top_n: int | None = None,
    ) -> list[ScreenerResult]:
        """Screen a universe of symbols.

        Args:
            symbols: List of symbols to screen
            min_score: Minimum score to include in results
            top_n: Return only top N results by score

        Returns:
            List of ScreenerResults for passing stocks
        """
        pass
