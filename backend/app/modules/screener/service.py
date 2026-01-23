"""Screener service for business logic."""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.screener.base import FilterType
from app.modules.screener.filters import (
    BreakoutFilter,
    ConsolidationFilter,
    MomentumFilter,
    MovingAverageFilter,
    VolumeFilter,
)
from app.modules.screener.models import CustomScreener, ScreenerResultRecord, ScreenerRun
from app.modules.screener.schemas import (
    CustomScreenerCreate,
    CustomScreenerUpdate,
    FilterConfig,
    FilterTypeEnum,
    ScreenerPresetInfo,
    ScreenerPresetType,
    ScreenerResultItem,
    ScreenerRunResponse,
)
from app.modules.screener.screener import StockScreener

if TYPE_CHECKING:
    from app.providers.data import DataProvider

logger = logging.getLogger(__name__)


# Cache utilities
def _generate_cache_key(
    universe: str,
    filters: list[FilterConfig],
    min_score: float,
    top_n: int,
) -> str:
    """Generate a cache key for screener results."""
    filter_str = json.dumps([f.model_dump() for f in filters], sort_keys=True)
    config_str = f"{universe}:{filter_str}:{min_score}:{top_n}"
    hash_val = hashlib.md5(config_str.encode()).hexdigest()[:12]
    return f"screener:results:{universe}:{hash_val}"


def _is_market_hours() -> bool:
    """Check if we're in Indian market hours (9:15 AM - 3:30 PM IST)."""
    now = datetime.now(timezone.utc)
    # IST is UTC+5:30
    ist_hour = (now.hour + 5) % 24
    ist_minute = now.minute + 30
    if ist_minute >= 60:
        ist_hour = (ist_hour + 1) % 24
        ist_minute -= 60

    # Market open: 9:15, Market close: 15:30
    market_open = 9 * 60 + 15  # 555 minutes
    market_close = 15 * 60 + 30  # 930 minutes
    current_time = ist_hour * 60 + ist_minute

    # Check weekday (0=Monday, 6=Sunday)
    weekday = now.weekday()
    if weekday >= 5:  # Weekend
        return False

    return market_open <= current_time <= market_close


def _get_cache_ttl() -> int:
    """Get cache TTL based on market hours."""
    if _is_market_hours():
        return 300  # 5 minutes during market hours
    return 3600  # 1 hour outside market hours


# Preset screener definitions
PRESET_DEFINITIONS: dict[ScreenerPresetType, ScreenerPresetInfo] = {
    ScreenerPresetType.MOMENTUM: ScreenerPresetInfo(
        preset=ScreenerPresetType.MOMENTUM,
        name="Momentum Screener",
        description="Stocks with strong upward momentum: high volume, bullish RSI, near 52-week high",
        filters=[
            FilterConfig(filter_type=FilterTypeEnum.VOLUME, params={"min_avg_volume": 100000}, weight=1.0),
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={"momentum_mode": "bullish", "min_roc": 5, "near_52w_high_pct": 15},
                weight=2.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_above_trend": True},
                weight=1.5,
            ),
        ],
    ),
    ScreenerPresetType.BREAKOUT: ScreenerPresetInfo(
        preset=ScreenerPresetType.BREAKOUT,
        name="Breakout Screener",
        description="Stocks breaking out of consolidation with volume confirmation",
        filters=[
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"min_avg_volume": 50000, "require_spike": True, "volume_spike_threshold": 1.5},
                weight=1.5,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.BREAKOUT,
                params={"lookback_period": 20, "breakout_pct": 2.0},
                weight=2.0,
            ),
        ],
    ),
    ScreenerPresetType.CONSOLIDATION: ScreenerPresetInfo(
        preset=ScreenerPresetType.CONSOLIDATION,
        name="Consolidation Screener",
        description="Pre-breakout candidates in tight trading ranges with declining volume",
        filters=[
            FilterConfig(filter_type=FilterTypeEnum.VOLUME, params={"min_avg_volume": 50000}, weight=1.0),
            FilterConfig(
                filter_type=FilterTypeEnum.CONSOLIDATION,
                params={"max_range_pct": 10, "declining_volume": True},
                weight=2.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_above_trend": True},
                weight=1.0,
            ),
        ],
    ),
    ScreenerPresetType.VALUE: ScreenerPresetInfo(
        preset=ScreenerPresetType.VALUE,
        name="Value/Pullback Screener",
        description="Pullback to support: near 50-day MA, oversold RSI, still in uptrend",
        filters=[
            FilterConfig(filter_type=FilterTypeEnum.VOLUME, params={"min_avg_volume": 50000}, weight=1.0),
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={"momentum_mode": "bearish", "rsi_oversold": 40},
                weight=1.5,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_above_trend": True, "trend_ma": 200},
                weight=2.0,
            ),
        ],
    ),
}


def get_filter_class(filter_type: FilterTypeEnum):
    """Get filter class from filter type enum."""
    mapping = {
        FilterTypeEnum.VOLUME: VolumeFilter,
        FilterTypeEnum.MOMENTUM: MomentumFilter,
        FilterTypeEnum.BREAKOUT: BreakoutFilter,
        FilterTypeEnum.CONSOLIDATION: ConsolidationFilter,
        FilterTypeEnum.MOVING_AVERAGE: MovingAverageFilter,
    }
    return mapping.get(filter_type)


class ScreenerService:
    """Service for screener operations."""

    def __init__(self, db: AsyncSession, redis: Redis | None = None):
        self.db = db
        self.redis = redis

    def _build_screener(
        self, filters: list[FilterConfig], data_provider: "DataProvider | None" = None
    ) -> StockScreener:
        """Build a StockScreener from filter configs."""
        screener = StockScreener(data_provider=data_provider)
        for fc in filters:
            filter_cls = get_filter_class(fc.filter_type)
            if filter_cls:
                screener.add_filter(filter_cls(weight=fc.weight, **fc.params))
        return screener

    async def _get_cached_results(
        self, cache_key: str
    ) -> ScreenerRunResponse | None:
        """Get cached screener results from Redis."""
        if not self.redis:
            return None
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                logger.info(f"Cache hit for screener: {cache_key}")
                return ScreenerRunResponse(**data)
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")
        return None

    async def _cache_results(
        self, cache_key: str, response: ScreenerRunResponse
    ) -> None:
        """Cache screener results to Redis."""
        if not self.redis:
            return
        try:
            ttl = _get_cache_ttl()
            # Convert to JSON-serializable dict
            data = response.model_dump(mode="json")
            await self.redis.setex(cache_key, ttl, json.dumps(data))
            logger.info(f"Cached screener results: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")

    async def get_custom_screeners(self, user_id: str) -> list[CustomScreener]:
        """Get all custom screeners for a user."""
        result = await self.db.execute(
            select(CustomScreener)
            .where(CustomScreener.user_id == user_id, CustomScreener.is_active == True)  # noqa: E712
            .order_by(CustomScreener.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_custom_screener(self, user_id: str, screener_id: str) -> CustomScreener | None:
        """Get a specific custom screener."""
        result = await self.db.execute(
            select(CustomScreener).where(
                CustomScreener.id == screener_id,
                CustomScreener.user_id == user_id,
                CustomScreener.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def create_custom_screener(
        self, user_id: str, data: CustomScreenerCreate
    ) -> CustomScreener:
        """Create a new custom screener."""
        screener = CustomScreener(
            user_id=user_id,
            name=data.name,
            description=data.description,
            universe=data.universe,
            filters=[f.model_dump() for f in data.filters],
            min_score=data.min_score,
            top_n=data.top_n,
        )
        self.db.add(screener)
        await self.db.flush()
        await self.db.refresh(screener)
        return screener

    async def update_custom_screener(
        self, user_id: str, screener_id: str, data: CustomScreenerUpdate
    ) -> CustomScreener | None:
        """Update a custom screener."""
        screener = await self.get_custom_screener(user_id, screener_id)
        if not screener:
            return None

        if data.name is not None:
            screener.name = data.name
        if data.description is not None:
            screener.description = data.description
        if data.universe is not None:
            screener.universe = data.universe
        if data.filters is not None:
            screener.filters = [f.model_dump() for f in data.filters]
        if data.min_score is not None:
            screener.min_score = data.min_score
        if data.top_n is not None:
            screener.top_n = data.top_n

        await self.db.flush()
        await self.db.refresh(screener)
        return screener

    async def delete_custom_screener(self, user_id: str, screener_id: str) -> bool:
        """Delete (soft) a custom screener."""
        screener = await self.get_custom_screener(user_id, screener_id)
        if not screener:
            return False
        screener.is_active = False
        await self.db.flush()
        return True

    async def run_screener(
        self,
        user_id: str,
        symbols: list[str],
        filters: list[FilterConfig],
        universe: str,
        min_score: float = 50.0,
        top_n: int = 50,
        data_provider: "DataProvider | None" = None,
        preset: str | None = None,
        custom_screener_id: str | None = None,
        use_cache: bool = True,
    ) -> ScreenerRunResponse:
        """Run a screener on a list of symbols.

        Args:
            user_id: User running the screener
            symbols: List of stock symbols to screen
            filters: List of filter configurations
            universe: Universe identifier
            min_score: Minimum score threshold (0-100)
            top_n: Maximum results to return
            data_provider: Data provider for OHLCV data
            preset: Preset name if using a preset screener
            custom_screener_id: ID of saved custom screener
            use_cache: Whether to use Redis caching
        """
        # Check cache first (only for preset screeners or when use_cache is True)
        cache_key = _generate_cache_key(universe, filters, min_score, top_n)
        if use_cache:
            cached = await self._get_cached_results(cache_key)
            if cached:
                return cached

        start_time = time.time()

        screener = self._build_screener(filters, data_provider)
        results = await screener.screen_universe(
            symbols=symbols, min_score=min_score, top_n=top_n
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Create run record
        run = ScreenerRun(
            user_id=user_id,
            custom_screener_id=custom_screener_id,
            preset=preset,
            universe=universe,
            filters=[f.model_dump() for f in filters],
            min_score=min_score,
            top_n=top_n,
            total_screened=len(symbols),
            passed_count=len(results),
            duration_ms=duration_ms,
        )
        self.db.add(run)
        await self.db.flush()

        # Create result records
        result_items = []
        for rank, r in enumerate(results, 1):
            result_record = ScreenerResultRecord(
                run_id=run.id,
                symbol=r.symbol,
                rank=rank,
                score=r.score,
                passed=r.passed,
                filter_scores=r.filter_scores,
                reasons=r.reasons,
                metadata=r.metadata,
            )
            self.db.add(result_record)
            result_items.append(
                ScreenerResultItem(
                    symbol=r.symbol,
                    rank=rank,
                    score=round(r.score, 2),
                    passed=r.passed,
                    filter_scores=r.filter_scores,
                    reasons=r.reasons,
                    metadata=r.metadata,
                )
            )

        await self.db.flush()

        response = ScreenerRunResponse(
            run_id=run.id,
            status="completed",
            universe=universe,
            total_screened=len(symbols),
            passed_count=len(results),
            min_score=min_score,
            results=result_items,
            executed_at=run.executed_at,
            duration_ms=duration_ms,
        )

        # Cache results
        if use_cache:
            await self._cache_results(cache_key, response)

        return response

    async def get_screener_run(self, user_id: str, run_id: str) -> ScreenerRun | None:
        """Get a specific screener run with results."""
        result = await self.db.execute(
            select(ScreenerRun).where(
                ScreenerRun.id == run_id,
                ScreenerRun.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def get_preset_definitions() -> list[ScreenerPresetInfo]:
        """Get all preset screener definitions."""
        return list(PRESET_DEFINITIONS.values())

    @staticmethod
    def get_preset(preset: ScreenerPresetType) -> ScreenerPresetInfo | None:
        """Get a specific preset definition."""
        return PRESET_DEFINITIONS.get(preset)

