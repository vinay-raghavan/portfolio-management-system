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
    SectorPerformanceFilter,
    VolumeFilter,
)
from app.modules.screener.models import CustomScreener, ScreenerResultRecord, ScreenerRun
from app.modules.screener.router import router
from app.modules.screener.screener import StockScreener
from app.modules.screener.service import ScreenerService

__all__ = [
    # Base classes
    "BaseScreener",
    "ScreenerResult",
    "StockScreener",
    # Filters
    "VolumeFilter",
    "MomentumFilter",
    "BreakoutFilter",
    "ConsolidationFilter",
    "MovingAverageFilter",
    "SectorPerformanceFilter",
    # Models
    "CustomScreener",
    "ScreenerRun",
    "ScreenerResultRecord",
    # Service
    "ScreenerService",
    # Router
    "router",
]
