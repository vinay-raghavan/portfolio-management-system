"""Stock Screener Module.

Provides infrastructure to filter stocks from large universes
before applying trading strategies.

Screeners can filter by:
- Volume (daily, average, spike detection)
- Momentum (52-week high/low, RSI, rate of change)
- Price action (breakouts, consolidation, gap detection)
- Fundamental (market cap, sector, industry)
- Technical (moving average position, trend direction)
"""

from app.modules.screener.base import BaseScreener, ScreenerResult
from app.modules.screener.filters import (
    BreakoutFilter,
    ConsolidationFilter,
    MomentumFilter,
    MovingAverageFilter,
    VolumeFilter,
)
from app.modules.screener.screener import StockScreener

__all__ = [
    "BaseScreener",
    "ScreenerResult",
    "StockScreener",
    "VolumeFilter",
    "MomentumFilter",
    "BreakoutFilter",
    "ConsolidationFilter",
    "MovingAverageFilter",
]

