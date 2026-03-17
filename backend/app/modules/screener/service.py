"""Screener service for business logic."""

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.screener.filters import (
    BreakoutFilter,
    ConsolidationFilter,
    MomentumFilter,
    MovingAverageFilter,
    SectorPerformanceFilter,
    VolumeFilter,
)
from app.modules.screener.market_regime import MarketRegimeData
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
    SignalDirectionEnum,
    StrictnessLevel,
    get_score_description,
    get_score_grade,
)
from app.modules.screener.screener import StockScreener

# Strictness level multipliers for filter parameters
# Format: {param_name: {strictness: multiplier}}
# For boolean params, strictness determines if they're required
STRICTNESS_MODIFIERS = {
    # Momentum filter params
    "near_52w_high_pct": {
        StrictnessLevel.STRICT: 1.0,  # 25% stays 25%
        StrictnessLevel.MODERATE: 1.5,  # 25% becomes 37.5%
        StrictnessLevel.RELAXED: 2.0,  # 25% becomes 50%
        StrictnessLevel.EXPLORATORY: 3.0,  # 25% becomes 75%
    },
    "min_pct_above_52w_low": {
        StrictnessLevel.STRICT: 1.0,  # 30% stays 30%
        StrictnessLevel.MODERATE: 0.7,  # 30% becomes 21%
        StrictnessLevel.RELAXED: 0.5,  # 30% becomes 15%
        StrictnessLevel.EXPLORATORY: 0.0,  # disabled
    },
    "min_roc": {
        StrictnessLevel.STRICT: 1.0,
        StrictnessLevel.MODERATE: 0.5,
        StrictnessLevel.RELAXED: 0.25,
        StrictnessLevel.EXPLORATORY: 0.0,
    },
    # Volume filter params
    "min_avg_volume": {
        StrictnessLevel.STRICT: 1.0,  # 50000 stays 50000
        StrictnessLevel.MODERATE: 0.5,  # becomes 25000
        StrictnessLevel.RELAXED: 0.2,  # becomes 10000
        StrictnessLevel.EXPLORATORY: 0.02,  # becomes 1000
    },
    "volume_spike_threshold": {
        StrictnessLevel.STRICT: 1.0,  # 2.0x stays 2.0x
        StrictnessLevel.MODERATE: 0.75,  # becomes 1.5x
        StrictnessLevel.RELAXED: 0.625,  # becomes 1.25x
        StrictnessLevel.EXPLORATORY: 0.5,  # becomes 1.0x
    },
    # Consolidation filter params
    "max_range_pct": {
        StrictnessLevel.STRICT: 1.0,  # 15% stays 15%
        StrictnessLevel.MODERATE: 1.5,  # becomes 22.5%
        StrictnessLevel.RELAXED: 2.0,  # becomes 30%
        StrictnessLevel.EXPLORATORY: 3.0,  # becomes 45%
    },
    # Breakout filter params
    "breakout_pct": {
        StrictnessLevel.STRICT: 1.0,  # 2% stays 2%
        StrictnessLevel.MODERATE: 0.5,  # becomes 1%
        StrictnessLevel.RELAXED: 0.25,  # becomes 0.5%
        StrictnessLevel.EXPLORATORY: 0.0,  # disabled
    },
}


def _detect_signal_direction(filters: list[FilterConfig]) -> SignalDirectionEnum:
    """Detect signal direction based on filter configuration.

    Returns SHORT if bearish filters are detected, otherwise LONG.
    """
    for f in filters:
        params = f.params or {}

        # Check for bearish momentum mode
        if (
            f.filter_type == FilterTypeEnum.MOMENTUM
            and params.get("momentum_mode") == "bearish_short"
        ):
            return SignalDirectionEnum.SHORT

        # Check for below trend MA (bearish)
        if f.filter_type == FilterTypeEnum.MOVING_AVERAGE and params.get(
            "require_below_trend", False
        ):
            return SignalDirectionEnum.SHORT

    return SignalDirectionEnum.LONG


# Boolean params that should be disabled at certain strictness levels
STRICTNESS_BOOL_OVERRIDES = {
    "require_stacked_ma": {
        StrictnessLevel.STRICT: True,
        StrictnessLevel.MODERATE: True,
        StrictnessLevel.RELAXED: False,
        StrictnessLevel.EXPLORATORY: False,
    },
    "require_trend_up": {
        StrictnessLevel.STRICT: True,
        StrictnessLevel.MODERATE: True,
        StrictnessLevel.RELAXED: False,
        StrictnessLevel.EXPLORATORY: False,
    },
    "require_spike": {
        StrictnessLevel.STRICT: True,
        StrictnessLevel.MODERATE: True,
        StrictnessLevel.RELAXED: False,
        StrictnessLevel.EXPLORATORY: False,
    },
    "require_volume_decline": {
        StrictnessLevel.STRICT: True,
        StrictnessLevel.MODERATE: False,
        StrictnessLevel.RELAXED: False,
        StrictnessLevel.EXPLORATORY: False,
    },
}


def apply_strictness_to_filters(
    filters: list[FilterConfig], strictness: StrictnessLevel
) -> list[FilterConfig]:
    """Apply strictness level modifiers to filter parameters."""
    if strictness == StrictnessLevel.STRICT:
        return filters  # No modifications needed

    modified_filters = []
    for fc in filters:
        new_params = dict(fc.params)

        for param_name, value in fc.params.items():
            # Apply numeric multipliers
            if param_name in STRICTNESS_MODIFIERS and isinstance(value, (int, float)):
                multiplier = STRICTNESS_MODIFIERS[param_name].get(strictness, 1.0)
                new_params[param_name] = type(value)(value * multiplier)

            # Apply boolean overrides
            if param_name in STRICTNESS_BOOL_OVERRIDES and isinstance(value, bool):
                new_params[param_name] = STRICTNESS_BOOL_OVERRIDES[param_name].get(
                    strictness, value
                )

        modified_filters.append(
            FilterConfig(
                filter_type=fc.filter_type,
                params=new_params,
                weight=fc.weight,
            )
        )

    return modified_filters


def _generate_detailed_reasons(metadata: dict, filter_scores: dict[str, float]) -> list[str]:
    """Generate detailed reason strings with actual values from filter metadata."""
    detailed = []

    # Extract momentum filter data
    momentum_data = metadata.get("momentum_filter", {})
    if momentum_data:
        if "rsi" in momentum_data:
            rsi = momentum_data["rsi"]
            if rsi is not None:
                if rsi >= 70:
                    detailed.append(f"RSI at {rsi:.0f} (overbought zone)")
                elif rsi >= 50:
                    detailed.append(f"RSI at {rsi:.0f} (bullish momentum)")
                elif rsi >= 30:
                    detailed.append(f"RSI at {rsi:.0f} (neutral zone)")
                else:
                    detailed.append(f"RSI at {rsi:.0f} (oversold zone)")

        if "pct_from_52w_high" in momentum_data:
            pct = momentum_data["pct_from_52w_high"]
            if pct is not None:
                if pct <= 10:
                    detailed.append(f"Within {pct:.1f}% of 52-week high (very strong)")
                elif pct <= 25:
                    detailed.append(f"{pct:.1f}% below 52-week high (strong)")
                else:
                    detailed.append(f"{pct:.1f}% below 52-week high")

        if "pct_above_52w_low" in momentum_data:
            pct = momentum_data["pct_above_52w_low"]
            if pct is not None and pct > 0:
                if pct >= 50:
                    detailed.append(f"{pct:.0f}% above 52-week low (well recovered)")
                elif pct >= 30:
                    detailed.append(f"{pct:.0f}% above 52-week low (good base)")
                else:
                    detailed.append(f"{pct:.0f}% above 52-week low")

        if "roc" in momentum_data:
            roc = momentum_data["roc"]
            if roc is not None:
                detailed.append(f"Rate of change: {roc:+.1f}%")

    # Extract moving average filter data
    ma_data = metadata.get("moving_average_filter", {})
    if ma_data:
        if ma_data.get("stacked_ma"):
            detailed.append("MAs properly stacked (50 > 150 > 200)")
        if ma_data.get("trend_up"):
            detailed.append("200-day MA trending upward")
        if "pct_above_ma" in ma_data:
            pct = ma_data["pct_above_ma"]
            if pct is not None:
                detailed.append(f"Price {pct:.1f}% above trend MA")

    # Extract volume filter data
    volume_data = metadata.get("volume_filter", {})
    if volume_data:
        if "avg_volume" in volume_data:
            vol = volume_data["avg_volume"]
            if vol is not None:
                if vol >= 1_000_000:
                    detailed.append(f"Avg volume: {vol / 1e6:.1f}M (very liquid)")
                elif vol >= 100_000:
                    detailed.append(f"Avg volume: {vol / 1e3:.0f}K (liquid)")
                else:
                    detailed.append(f"Avg volume: {vol / 1e3:.0f}K")

        if "volume_ratio" in volume_data:
            ratio = volume_data["volume_ratio"]
            if ratio is not None and ratio > 1.5:
                detailed.append(f"Volume spike: {ratio:.1f}x average")

    # Extract breakout filter data
    breakout_data = metadata.get("breakout_filter", {})
    if breakout_data and "breakout_pct" in breakout_data:
        pct = breakout_data["breakout_pct"]
        if pct is not None and pct > 0:
            detailed.append(f"Breaking out {pct:.1f}% above resistance")

    # Extract consolidation filter data
    consol_data = metadata.get("consolidation_filter", {})
    if consol_data and "range_pct" in consol_data:
        pct = consol_data["range_pct"]
        if pct is not None:
            detailed.append(f"Consolidating in {pct:.1f}% range")

    return detailed


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
    # MD5 used only for cache key generation, not security purposes
    hash_val = hashlib.md5(config_str.encode(), usedforsecurity=False).hexdigest()[:12]
    return f"screener:results:{universe}:{hash_val}"


def _is_market_hours() -> bool:
    """Check if we're in Indian market hours (9:15 AM - 3:30 PM IST)."""
    now = datetime.now(UTC)
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


# Preset screener definitions - aligned with professional trading standards
PRESET_DEFINITIONS: dict[ScreenerPresetType, ScreenerPresetInfo] = {
    # Minervini Trend Template - Professional Stage 2 Uptrend Screener
    ScreenerPresetType.MINERVINI: ScreenerPresetInfo(
        preset=ScreenerPresetType.MINERVINI,
        name="Minervini Trend Template",
        description=(
            "Mark Minervini's Stage 2 uptrend criteria: Price above stacked MAs "
            "(50>150>200), within 25% of 52w high, 30%+ above 52w low, 200MA trending up"
        ),
        filters=[
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"min_avg_volume": 50000},
                weight=1.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={
                    "short_ma": 50,
                    "mid_ma": 150,
                    "trend_ma": 200,
                    "require_above_trend": True,
                    "require_stacked_ma": True,
                    "require_trend_up": True,
                    "trend_up_days": 22,
                },
                weight=2.5,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={
                    "momentum_mode": "bullish",
                    "near_52w_high_pct": 25,
                    "min_pct_above_52w_low": 30,
                },
                weight=2.0,
            ),
        ],
    ),
    # Momentum Screener - Relaxed thresholds for more results
    ScreenerPresetType.MOMENTUM: ScreenerPresetInfo(
        preset=ScreenerPresetType.MOMENTUM,
        name="Momentum Screener",
        description="Stocks with strong upward momentum: high volume, bullish RSI, near 52-week high",
        filters=[
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"min_avg_volume": 50000},
                weight=1.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={
                    "momentum_mode": "bullish",
                    "min_roc": 2,  # Relaxed from 5%
                    "near_52w_high_pct": 25,  # Relaxed from 15% (Minervini standard)
                },
                weight=2.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_above_trend": True, "trend_ma": 200},
                weight=1.5,
            ),
        ],
    ),
    # Breakout Screener - Stronger volume confirmation
    ScreenerPresetType.BREAKOUT: ScreenerPresetInfo(
        preset=ScreenerPresetType.BREAKOUT,
        name="Breakout Screener",
        description="Stocks breaking out of consolidation with strong volume confirmation",
        filters=[
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={
                    "min_avg_volume": 50000,
                    "require_spike": True,
                    "volume_spike_threshold": 2.0,  # Increased from 1.5x for stronger signal
                },
                weight=1.5,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.BREAKOUT,
                params={"lookback_period": 20, "breakout_pct": 2.0},
                weight=2.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_above_trend": True, "trend_ma": 200},
                weight=1.0,
            ),
        ],
    ),
    # Consolidation Screener - VCP-style pre-breakout candidates
    ScreenerPresetType.CONSOLIDATION: ScreenerPresetInfo(
        preset=ScreenerPresetType.CONSOLIDATION,
        name="Consolidation / VCP Screener",
        description="Pre-breakout candidates in tight trading ranges with declining volume (VCP pattern)",
        filters=[
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"min_avg_volume": 50000},
                weight=1.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.CONSOLIDATION,
                params={
                    "max_range_pct": 15,  # Relaxed from 10%
                    "declining_volume": True,
                },
                weight=2.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_above_trend": True, "trend_ma": 200},
                weight=1.5,
            ),
        ],
    ),
    # Value/Pullback Screener - Fixed RSI threshold
    ScreenerPresetType.VALUE: ScreenerPresetInfo(
        preset=ScreenerPresetType.VALUE,
        name="Pullback to Support Screener",
        description="Pullback to support: oversold RSI (<30), still in long-term uptrend above 200MA",
        filters=[
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"min_avg_volume": 50000},
                weight=1.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={
                    "momentum_mode": "bearish",
                    "rsi_oversold": 30,  # Fixed from 40 (standard oversold level)
                },
                weight=1.5,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_above_trend": True, "trend_ma": 200},
                weight=2.0,
            ),
        ],
    ),
    # Sector Rotation Screener - Enhanced with momentum
    ScreenerPresetType.SECTOR_ROTATION: ScreenerPresetInfo(
        preset=ScreenerPresetType.SECTOR_ROTATION,
        name="Sector Rotation Screener",
        description="Find top-performing stocks with strong relative momentum",
        filters=[
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"min_avg_volume": 50000},
                weight=1.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.PRICE_ACTION,
                params={"lookback_period": 50, "min_sector_roc": 0},  # 50-day performance
                weight=2.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"require_above_trend": True, "trend_ma": 200},
                weight=1.5,
            ),
        ],
    ),
    # Bearish Short Screener - Find stocks to SHORT SELL
    # ⚠️ Requires INTRADAY or SLB product type!
    ScreenerPresetType.BEARISH_SHORT: ScreenerPresetInfo(
        preset=ScreenerPresetType.BEARISH_SHORT,
        name="⚠️ Bearish Short Screener",
        description=(
            "Find weak stocks for SHORT SELLING. ⚠️ Requires INTRADAY (MIS) or SLB product type!"
        ),
        filters=[
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"min_avg_volume": 50000},  # Relaxed volume requirement
                weight=1.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={
                    "momentum_mode": "bearish_short",
                    "rsi_overbought": 60,  # Relaxed from 70
                    "min_roc": -2,  # Relaxed from -5 (negative momentum)
                },
                weight=2.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={
                    "require_below_trend": True,  # Below 50MA (relaxed from 200MA)
                    "trend_ma": 50,
                },
                weight=1.5,
            ),
        ],
    ),
    # Adaptive Screener - Auto-switches between bullish/bearish based on market regime
    # This is a placeholder - actual filters are determined at runtime
    ScreenerPresetType.ADAPTIVE: ScreenerPresetInfo(
        preset=ScreenerPresetType.ADAPTIVE,
        name="Market Adaptive",
        description=(
            "Automatically detects market regime (bullish/bearish) and selects "
            "appropriate stocks. Uses NIFTY trend, market breadth, momentum, and VIX "
            "to determine direction. In bullish markets: finds breakout stocks. "
            "In bearish markets: finds breakdown stocks for shorting."
        ),
        filters=[
            # Default filters - will be overridden by regime detection
            FilterConfig(
                filter_type=FilterTypeEnum.VOLUME,
                params={"min_avg_volume": 50000},
                weight=1.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOMENTUM,
                params={"momentum_mode": "bullish"},  # Default, changed at runtime
                weight=2.0,
            ),
            FilterConfig(
                filter_type=FilterTypeEnum.MOVING_AVERAGE,
                params={"trend_ma": 50, "require_above_trend": True},
                weight=1.5,
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
        FilterTypeEnum.PRICE_ACTION: SectorPerformanceFilter,
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

    async def _get_cached_results(self, cache_key: str) -> ScreenerRunResponse | None:
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

    async def _cache_results(self, cache_key: str, response: ScreenerRunResponse) -> None:
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
        """Create a new custom screener.

        Supports both:
        - Preset screeners (preset field set, filters optional)
        - Custom screeners (filters provided, preset optional)
        """
        from datetime import time

        # Parse run_time if provided
        run_time_obj = None
        if data.run_time:
            h, m = map(int, data.run_time.split(":"))
            run_time_obj = time(hour=h, minute=m)

        # Build filters dict - can be empty for preset screeners
        filters_dict = [f.model_dump() for f in data.filters] if data.filters else []

        screener = CustomScreener(
            user_id=user_id,
            name=data.name,
            description=data.description,
            universe=data.universe,
            preset=data.preset,
            strictness=data.strictness.value if data.strictness else "moderate",
            filters=filters_dict,
            min_score=data.min_score,
            top_n=data.top_n,
            # Auto-trade fields
            is_auto_trade_enabled=data.is_auto_trade_enabled,
            run_frequency=data.run_frequency.value if data.run_frequency else "manual",
            run_time=run_time_obj,
            strategy_template_id=data.strategy_template_id,
        )
        self.db.add(screener)
        await self.db.flush()
        await self.db.refresh(screener)
        return screener

    async def update_custom_screener(
        self, user_id: str, screener_id: str, data: CustomScreenerUpdate
    ) -> CustomScreener | None:
        """Update a custom screener."""
        from datetime import time

        screener = await self.get_custom_screener(user_id, screener_id)
        if not screener:
            return None

        if data.name is not None:
            screener.name = data.name
        if data.description is not None:
            screener.description = data.description
        if data.universe is not None:
            screener.universe = data.universe
        if data.preset is not None:
            screener.preset = data.preset
        if data.strictness is not None:
            screener.strictness = data.strictness.value
        if data.filters is not None:
            screener.filters = [f.model_dump() for f in data.filters]
        if data.min_score is not None:
            screener.min_score = data.min_score
        if data.top_n is not None:
            screener.top_n = data.top_n

        # Auto-trade fields
        if data.is_auto_trade_enabled is not None:
            screener.is_auto_trade_enabled = data.is_auto_trade_enabled
        if data.run_frequency is not None:
            screener.run_frequency = data.run_frequency.value
        if data.run_time is not None:
            h, m = map(int, data.run_time.split(":"))
            screener.run_time = time(hour=h, minute=m)
        if data.strategy_template_id is not None:
            screener.strategy_template_id = data.strategy_template_id

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
        results = await screener.screen_universe(symbols=symbols, min_score=min_score, top_n=top_n)

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
                extra_data=r.metadata,
            )
            self.db.add(result_record)

            # Generate grade and detailed reasons
            score = round(r.score, 2)
            grade = get_score_grade(score).value
            grade_description = get_score_description(score)
            reasons_detailed = _generate_detailed_reasons(r.metadata, r.filter_scores)

            # Detect signal direction from filters
            signal_direction = _detect_signal_direction(filters)

            result_items.append(
                ScreenerResultItem(
                    symbol=r.symbol,
                    rank=rank,
                    score=score,
                    grade=grade,
                    grade_description=grade_description,
                    passed=r.passed,
                    signal_direction=signal_direction,
                    filter_scores=r.filter_scores,
                    reasons=r.reasons,
                    reasons_detailed=reasons_detailed,
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

    async def get_adaptive_filters(
        self, strictness: StrictnessLevel = StrictnessLevel.MODERATE
    ) -> tuple[list[FilterConfig], MarketRegimeData]:
        """Get filters based on current market regime.

        Detects whether market is bullish/bearish and returns appropriate filters.
        Uses Yahoo Finance for market data - NO DB ACCESS required.

        Args:
            strictness: How strict the filter criteria should be

        Returns:
            Tuple of (filters, regime_data)
        """
        from app.modules.screener.market_regime import MarketRegime, MarketRegimeDetector

        # Detect market regime using Yahoo (no DB needed)
        # Pass None for db since MarketRegimeDetector uses Yahoo provider
        detector = MarketRegimeDetector(db=None)  # type: ignore
        regime_data = await detector.detect_regime()

        logger.info(
            f"Market regime detected: {regime_data.regime.value} "
            f"(confidence: {regime_data.confidence:.0f}%, score: {regime_data.composite_score:.1f})"
        )
        for reason in regime_data.reasons:
            logger.debug(f"  - {reason}")

        # Select filters based on regime
        # Combines Minervini Trend Template + Momentum criteria based on direction
        if regime_data.regime in [MarketRegime.STRONGLY_BULLISH, MarketRegime.BULLISH]:
            # BULLISH: Minervini Trend Template for long positions
            # - Price above 150 & 200 DMA
            # - 150 DMA above 200 DMA
            # - Price at least 25% above 52-week low
            # - Price within 25% of 52-week high
            # - Strong relative strength
            base_filters = [
                FilterConfig(
                    filter_type=FilterTypeEnum.VOLUME,
                    params={"min_avg_volume": 50000},
                    weight=1.0,
                ),
                FilterConfig(
                    filter_type=FilterTypeEnum.MOMENTUM,
                    params={
                        "momentum_mode": "bullish",
                        "min_roc": 5,  # Strong momentum
                        "near_52w_high_pct": 25,  # Within 25% of 52w high
                        "min_rs_rating": 70,  # Relative strength > 70
                    },
                    weight=2.5,
                ),
                FilterConfig(
                    filter_type=FilterTypeEnum.MOVING_AVERAGE,
                    params={
                        "trend_ma": 50,
                        "require_above_trend": True,
                        "require_ma_alignment": True,  # 50 > 150 > 200
                    },
                    weight=2.0,
                ),
                FilterConfig(
                    filter_type=FilterTypeEnum.BREAKOUT,
                    params={
                        "consolidation_days": 20,
                        "volume_surge": 1.5,  # 50% above average
                    },
                    weight=1.5,
                ),
            ]
            logger.info(
                f"Using BULLISH (Minervini) filters for adaptive screener "
                f"(regime: {regime_data.regime.value}, score: {regime_data.composite_score:.1f})"
            )

        elif regime_data.regime in [MarketRegime.STRONGLY_BEARISH, MarketRegime.BEARISH]:
            # BEARISH: Relaxed bearish filters for short positions
            # - Price below key moving average (50 DMA)
            # - Negative momentum
            # - Weak relative strength
            base_filters = [
                FilterConfig(
                    filter_type=FilterTypeEnum.VOLUME,
                    params={"min_avg_volume": 50000},
                    weight=1.0,
                ),
                FilterConfig(
                    filter_type=FilterTypeEnum.MOMENTUM,
                    params={
                        "momentum_mode": "bearish_short",
                        "max_roc": 0,  # Relaxed: any negative or flat momentum
                        "max_rs_rating": 50,  # Relaxed: below average RS
                    },
                    weight=2.0,
                ),
                FilterConfig(
                    filter_type=FilterTypeEnum.MOVING_AVERAGE,
                    params={
                        "trend_ma": 50,  # Relaxed from 200 to 50
                        "require_below_trend": True,
                    },
                    weight=1.5,
                ),
            ]
            logger.info(
                f"Using BEARISH (Inverse Minervini) filters for adaptive screener "
                f"(regime: {regime_data.regime.value}, score: {regime_data.composite_score:.1f})"
            )

        else:  # NEUTRAL
            # NEUTRAL: Very selective - only the strongest setups
            # Look for stocks showing relative strength despite choppy market
            base_filters = [
                FilterConfig(
                    filter_type=FilterTypeEnum.VOLUME,
                    params={"min_avg_volume": 100000},  # Higher volume requirement
                    weight=1.0,
                ),
                FilterConfig(
                    filter_type=FilterTypeEnum.MOMENTUM,
                    params={
                        "momentum_mode": "bullish",
                        "min_roc": 8,  # Very strong momentum required
                        "near_52w_high_pct": 10,  # Very close to highs
                        "min_rs_rating": 85,  # Top 15% relative strength
                    },
                    weight=3.0,
                ),
                FilterConfig(
                    filter_type=FilterTypeEnum.CONSOLIDATION,
                    params={
                        "max_range_pct": 8,  # Tight consolidation
                        "min_consolidation_days": 10,
                    },
                    weight=2.0,
                ),
                FilterConfig(
                    filter_type=FilterTypeEnum.MOVING_AVERAGE,
                    params={
                        "trend_ma": 20,
                        "require_above_trend": True,
                    },
                    weight=1.5,
                ),
            ]
            logger.info(
                f"Using NEUTRAL (relative strength) filters for adaptive screener "
                f"(regime: {regime_data.regime.value}, score: {regime_data.composite_score:.1f})"
            )

        # Apply strictness adjustments
        filters = apply_strictness_to_filters(base_filters, strictness)

        return filters, regime_data

    async def get_screeners_by_frequency(self, frequency: str) -> list[CustomScreener]:
        """Get all custom screeners with the specified run frequency.

        Args:
            frequency: Either 'daily' or 'hourly'

        Returns:
            List of screeners with matching frequency that are auto-trade enabled
        """
        result = await self.db.execute(
            select(CustomScreener).where(
                CustomScreener.run_frequency == frequency,
                CustomScreener.is_auto_trade_enabled == True,  # noqa: E712
                CustomScreener.is_active == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def run_custom_screener_for_auto_trade(self, user_id: str, screener_id: str) -> dict:
        """Run a custom screener and process results for auto-trade.

        Architecture (optimized for long-running NIFTY 500 screeners):
        1. PHASE 1: Quick DB read - load screener config into memory
        2. PHASE 2: Long operation - run screener with Yahoo (NO DB access)
        3. PHASE 3: Cache results in Redis temporarily
        4. PHASE 4: Single fresh DB session for all writes

        This prevents DB session corruption during 3+ minute screener runs.

        Args:
            user_id: The user who owns the screener
            screener_id: UUID of the custom screener

        Returns:
            Dict with status, passed_count, results, pending_trades_created, etc.
        """
        import json
        from datetime import datetime, timedelta

        from app.core.database import async_session_maker
        from app.core.redis import get_redis

        # ===== PHASE 1: Quick DB read =====
        screener = await self.get_custom_screener(user_id, screener_id)
        if not screener:
            return {"status": "error", "message": "Screener not found"}

        if not screener.is_auto_trade_enabled:
            return {"status": "error", "message": "Auto-trade not enabled"}

        # Cache all screener attributes into plain dict (detached from session)
        screener_data = {
            "id": screener_id,
            "name": screener.name,
            "preset": screener.preset,
            "strictness": screener.strictness,
            "universe": screener.universe,
            "filters": screener.filters,
            "min_score": screener.min_score,
            "top_n": screener.top_n,
            "is_auto_trade_enabled": screener.is_auto_trade_enabled,
            "run_frequency": screener.run_frequency,
            "inferred_strategy_type": screener.inferred_strategy_type,
        }

        # Release the original session completely - we won't use self.db again
        await self.db.rollback()

        try:
            # ===== PHASE 2: Run screener (NO DB ACCESS) =====
            # Get universe symbols - this is a quick operation
            from app.modules.screener.router import _resolve_universe

            # Use a quick fresh session just for resolving universe
            async with async_session_maker() as quick_db:
                symbols = await _resolve_universe(screener_data["universe"], quick_db)

            if not symbols:
                return {
                    "status": "error",
                    "message": f"No symbols in universe {screener_data['universe']}",
                }

            logger.info(f"Running screener '{screener_data['name']}' on {len(symbols)} symbols")

            # Convert stored filters to FilterConfig objects
            from app.modules.screener.schemas import FilterConfig, StrictnessLevel

            # Track detected signal direction for adaptive screeners
            detected_signal_direction = None
            filters = []

            # Check if using a preset (filters empty but preset defined)
            stored_filters = screener_data.get("filters") or []
            if screener_data["preset"] and len(stored_filters) == 0:
                # Load from preset definition
                try:
                    preset_type = ScreenerPresetType(screener_data["preset"])
                    strictness = StrictnessLevel(screener_data["strictness"] or "moderate")

                    # Special handling for ADAPTIVE preset
                    if preset_type == ScreenerPresetType.ADAPTIVE:
                        from app.modules.screener.market_regime import MarketRegime

                        # get_adaptive_filters uses Yahoo (no DB needed)
                        filters, regime_data = await self.get_adaptive_filters(strictness)
                        logger.info(
                            f"Adaptive screener using {regime_data.regime.value} regime "
                            f"(score: {regime_data.composite_score:.1f})"
                        )
                        # Set signal direction based on regime
                        if regime_data.regime in [
                            MarketRegime.STRONGLY_BEARISH,
                            MarketRegime.BEARISH,
                        ]:
                            detected_signal_direction = SignalDirectionEnum.SHORT
                        elif regime_data.regime in [
                            MarketRegime.STRONGLY_BULLISH,
                            MarketRegime.BULLISH,
                        ]:
                            detected_signal_direction = SignalDirectionEnum.LONG
                        else:
                            detected_signal_direction = SignalDirectionEnum.LONG
                    else:
                        preset_def = PRESET_DEFINITIONS.get(preset_type)
                        if preset_def:
                            filters = apply_strictness_to_filters(preset_def.filters, strictness)
                            logger.info(
                                f"Loaded {len(filters)} filters from preset '{screener_data['preset']}' "
                                f"with {strictness.value} strictness"
                            )
                        else:
                            logger.warning(
                                f"Preset '{screener_data['preset']}' not found in PRESET_DEFINITIONS"
                            )
                except ValueError as e:
                    logger.warning(f"Invalid preset value '{screener_data['preset']}': {e}")
            else:
                # Use stored custom filters
                filters = [FilterConfig(**f) for f in stored_filters]

            # Always use Yahoo for screeners to avoid Fyers rate limits
            from shared.providers.data import get_data_provider

            provider = get_data_provider("yahoo")

            # Build the screener and run it (LONG OPERATION - 3+ mins for NIFTY 500)
            # NO DB access during this phase
            stock_screener = self._build_screener(filters, data_provider=provider)

            results = await stock_screener.screen_universe(
                symbols=symbols,
                min_score=screener_data["min_score"],
                top_n=screener_data["top_n"],
            )

            # ===== PHASE 3: Cache results in Redis =====
            redis = await get_redis()
            cache_key = f"screener_results:{screener_id}:{user_id}"
            results_data = [
                {"symbol": r.symbol, "score": r.score, "reasons": r.reasons} for r in results
            ]
            await redis.setex(cache_key, 300, json.dumps(results_data))  # 5 min TTL
            logger.info(f"Cached {len(results)} results in Redis: {cache_key}")

            # ===== PHASE 4: Single DB write with fresh session =====
            now = datetime.utcnow()
            run_frequency = screener_data["run_frequency"]

            async with async_session_maker() as db:
                from sqlalchemy import update

                # Update screener timestamps
                stmt = (
                    update(CustomScreener)
                    .where(CustomScreener.id == screener_id)
                    .values(
                        last_run_at=now,
                        next_run_at=(
                            now + timedelta(days=1)
                            if run_frequency == "daily"
                            else (now + timedelta(hours=1) if run_frequency == "hourly" else None)
                        ),
                    )
                )
                await db.execute(stmt)
                await db.commit()

            # Process results through auto-trade pipeline
            trades_created = 0
            pending_trades_created = 0

            if results and screener_data["is_auto_trade_enabled"]:
                try:
                    from app.modules.algo.auto_trade_service import (
                        AutoTradeConfigService,
                        PendingAutoTradeService,
                        StrategyTemplateService,
                    )
                    from app.modules.algo.models import ConfirmationMode
                    from app.modules.algo.multi_factor_scorer import MultiFactorScorer

                    # Use fresh session for auto-trade operations
                    # (original session may be stale after 3+ min screener run)
                    async with async_session_maker() as auto_trade_db:
                        # Get user's auto-trade config for custom screeners
                        config_service = AutoTradeConfigService(auto_trade_db)
                        config = await config_service.get_config_by_category(
                            user_id=user_id, category="custom"
                        )

                        if config and config.enabled:
                            logger.info(
                                f"Auto-trade config found: enabled={config.enabled}, "
                                f"mode={config.confirmation_mode}, min_conf={config.min_confidence}"
                            )
                            # Fetch fundamental data for scoring
                            # Note: Don't pass provider here - fundamentals come from Yahoo,
                            # not from user's trading provider (e.g., Fyers)
                            from app.modules.research.recommendation_service import (
                                RecommendationService,
                            )

                            rec_service = RecommendationService(auto_trade_db)
                            result_symbols = [r.symbol for r in results]
                            fundamentals_list = await rec_service.get_universe_fundamentals(
                                result_symbols
                            )
                            # Convert to dict keyed by symbol for easy lookup
                            fundamentals_by_symbol: dict[str, dict] = {
                                f["symbol"]: f for f in fundamentals_list
                            }
                            logger.info(
                                f"Fetched fundamentals for {len(fundamentals_by_symbol)}/{len(result_symbols)} symbols"
                            )

                            # Apply multi-factor scoring
                            scorer = MultiFactorScorer(auto_trade_db)
                            scored_results = []

                            # Use detected signal direction from adaptive screener, or detect from filters
                            if detected_signal_direction:
                                screener_direction = detected_signal_direction
                                logger.info(
                                    f"Using adaptive regime-detected direction: {screener_direction.value}"
                                )
                            else:
                                screener_direction = _detect_signal_direction(filters)

                            for r in results:
                                fund_data = fundamentals_by_symbol.get(r.symbol)
                                scores = await scorer.score_symbol(
                                    symbol=r.symbol,
                                    category="custom",
                                    technical_data={
                                        "score": r.score
                                    },  # Pass technical score as data
                                    fundamental_data=fund_data,  # Pass fundamental data
                                    screener_signal_direction=screener_direction.value,  # Pass screener direction
                                )
                                if scores.confidence.value != "skip":
                                    scored_results.append(
                                        {
                                            "symbol": r.symbol,
                                            "technical_score": r.score,
                                            "fundamental_score": scores.fundamental_score,
                                            "sentiment_score": scores.sentiment_score,
                                            "combined_score": scores.combined_score,
                                            "confidence_level": scores.confidence.value,
                                            "signal_direction": scores.direction.value,
                                            "recommended_strategy": scores.recommended_strategy,
                                            "position_size_multiplier": scores.position_size_multiplier,
                                            "reasons": r.reasons,
                                        }
                                    )
                            # Log first few scores for debugging
                            if scored_results:
                                sample = scored_results[:3]
                                logger.info(
                                    f"Sample scores: {[(s['symbol'], s['combined_score'], s['confidence_level']) for s in sample]}"
                                )

                            # Filter by confidence threshold
                            confidence_values = {"high": 80, "medium": 60, "low": 40}
                            # Handle both string and enum for min_confidence
                            min_confidence_str = (
                                config.min_confidence.value
                                if hasattr(config.min_confidence, "value")
                                else config.min_confidence
                            )
                            min_conf = confidence_values.get(min_confidence_str, 60)
                            logger.info(
                                f"Scored {len(scored_results)} symbols (non-skip). "
                                f"Min confidence threshold: {min_conf} ({min_confidence_str})"
                            )
                            filtered_results = [
                                r
                                for r in scored_results
                                if confidence_values.get(r["confidence_level"], 0) >= min_conf
                            ]
                            logger.info(
                                f"After confidence filter: {len(filtered_results)} symbols passed"
                            )

                            if filtered_results:
                                # Get strategy type from template or infer
                                strategy_type = (
                                    screener_data["inferred_strategy_type"] or "momentum"
                                )

                                if config.confirmation_mode == ConfirmationMode.AUTO:
                                    # Auto-execute: create strategies immediately
                                    template_service = StrategyTemplateService(auto_trade_db)
                                    for r in filtered_results[: config.max_positions_per_day]:
                                        strategy = (
                                            await template_service.create_strategy_from_template(
                                                user_id=user_id,
                                                template_id=str(config.strategy_template_id)
                                                if config.strategy_template_id
                                                else None,
                                                symbol=r["symbol"],
                                                strategy_type=strategy_type,
                                            )
                                        )
                                        if strategy:
                                            trades_created += 1
                                else:
                                    # Notify mode: create pending trades
                                    pending_service = PendingAutoTradeService(auto_trade_db)
                                    selected_symbols = [
                                        r["symbol"]
                                        for r in filtered_results[: config.max_positions_per_day]
                                    ]
                                    scores_dict = {r["symbol"]: r for r in filtered_results}

                                    pending = await pending_service.create_pending_trade(
                                        user_id=user_id,
                                        config=config,
                                        symbols=selected_symbols,
                                        scores=scores_dict,
                                        recommended_strategy_type=strategy_type,
                                        suggested_params={
                                            "source": "custom_screener",
                                            "screener_id": screener_id,
                                        },
                                    )
                                    if pending:
                                        pending_trades_created += 1

                except Exception as e:
                    logger.warning(f"Auto-trade processing failed for screener {screener_id}: {e}")
                    # Don't fail the whole operation, just log the warning

            return {
                "status": "success",
                "passed_count": len(results),
                "total_screened": len(symbols),
                "trades_created": trades_created,
                "pending_trades_created": pending_trades_created,
                "results": [
                    {
                        "symbol": r.symbol,
                        "score": r.score,
                        "reasons": r.reasons,
                    }
                    for r in results
                ],
            }

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error running screener {screener_id} for auto-trade: {e}")
            return {"status": "error", "message": str(e)}
