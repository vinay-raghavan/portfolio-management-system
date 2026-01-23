"""Pydantic schemas for screener module."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FilterTypeEnum(str, Enum):
    """Filter types available for screening."""

    VOLUME = "volume"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    CONSOLIDATION = "consolidation"
    MOVING_AVERAGE = "moving_average"
    PRICE_ACTION = "price_action"
    FUNDAMENTAL = "fundamental"
    CUSTOM = "custom"


class UniverseType(str, Enum):
    """Predefined universe types."""

    NIFTY50 = "nifty50"
    NIFTY100 = "nifty100"
    NIFTY200 = "nifty200"
    NIFTY500 = "nifty500"
    ALL_NSE = "all_nse"
    FO_STOCKS = "fo_stocks"
    CUSTOM = "custom"


class ScreenerPresetType(str, Enum):
    """Preset screener types."""

    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    CONSOLIDATION = "consolidation"
    VALUE = "value"
    SECTOR_ROTATION = "sector_rotation"


class FilterConfig(BaseModel):
    """Configuration for a single filter."""

    filter_type: FilterTypeEnum
    params: dict = Field(default_factory=dict)
    weight: float = Field(default=1.0, ge=0.1, le=10.0)


class ScreenerRunRequest(BaseModel):
    """Request to run a screener."""

    universe: str = Field(
        description="Universe ID or type: 'nifty50', 'nifty500', 'all_nse', or UUID"
    )
    filters: list[FilterConfig] = Field(min_length=1)
    min_score: float = Field(default=50.0, ge=0, le=100)
    top_n: int = Field(default=50, ge=1, le=500)


class ScreenerPresetRunRequest(BaseModel):
    """Request to run a preset screener."""

    preset: ScreenerPresetType
    universe: str = Field(default="nifty500")
    min_score: float = Field(default=50.0, ge=0, le=100)
    top_n: int = Field(default=50, ge=1, le=500)


class ScreenerResultItem(BaseModel):
    """Single stock result from screener."""

    symbol: str
    rank: int
    score: float
    passed: bool
    filter_scores: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ScreenerRunResponse(BaseModel):
    """Response from running a screener."""

    run_id: str
    status: str = "completed"
    universe: str
    total_screened: int
    passed_count: int
    min_score: float
    results: list[ScreenerResultItem]
    executed_at: datetime
    duration_ms: int


class CustomScreenerCreate(BaseModel):
    """Request to create/save a custom screener."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    universe: str = Field(default="nifty500")
    filters: list[FilterConfig] = Field(min_length=1)
    min_score: float = Field(default=50.0, ge=0, le=100)
    top_n: int = Field(default=50, ge=1, le=500)


class CustomScreenerUpdate(BaseModel):
    """Request to update a custom screener."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    universe: str | None = None
    filters: list[FilterConfig] | None = None
    min_score: float | None = Field(None, ge=0, le=100)
    top_n: int | None = Field(None, ge=1, le=500)


class CustomScreenerResponse(BaseModel):
    """Response for a custom screener."""

    id: str
    name: str
    description: str | None
    universe: str
    filters: list[FilterConfig]
    min_score: float
    top_n: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomScreenerListResponse(BaseModel):
    """Response for list of custom screeners."""

    screeners: list[CustomScreenerResponse]


class ScreenerPresetInfo(BaseModel):
    """Information about a preset screener."""

    preset: ScreenerPresetType
    name: str
    description: str
    filters: list[FilterConfig]


class ScreenerPresetsResponse(BaseModel):
    """Response for list of preset screeners."""

    presets: list[ScreenerPresetInfo]


class RecommendationCategory(str, Enum):
    """Categories for daily recommendations."""

    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    SECTOR = "sector"


class RecommendationItem(BaseModel):
    """Single recommendation item."""

    symbol: str
    rank: int
    score: float
    price_at_rec: float
    filter_scores: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    # Performance (if available)
    return_1d: float | None = None
    return_1w: float | None = None
    return_1m: float | None = None


class CategoryRecommendations(BaseModel):
    """Recommendations for a single category."""

    category: RecommendationCategory
    title: str
    description: str
    recommendations: list[RecommendationItem]


class DailyRecommendationsResponse(BaseModel):
    """Response for daily recommendations endpoint."""

    date: datetime
    generated_at: datetime
    categories: list[CategoryRecommendations]


# ============== Screener → Algo Integration Schemas ==============


class CreateUniverseFromScreenerRequest(BaseModel):
    """Request to create a universe from screener results."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    symbols: list[str] = Field(..., min_length=1, description="Symbols from screener results")
    screener_config: dict | None = Field(
        default=None, description="Original screener configuration for dynamic refresh"
    )
    is_dynamic: bool = Field(
        default=False,
        description="If true, universe can be refreshed by re-running the screener",
    )


class CreateUniverseFromScreenerResponse(BaseModel):
    """Response after creating universe from screener."""

    id: str
    name: str
    description: str | None
    symbol_count: int
    is_dynamic: bool
    created_at: datetime


class ScreenerAlertConfig(BaseModel):
    """Configuration for screener alerts."""

    screener_id: str = Field(..., description="ID of custom screener to monitor")
    alert_on_new_symbols: bool = Field(default=True, description="Alert when new symbols match")
    alert_on_removed_symbols: bool = Field(default=False, description="Alert when symbols no longer match")
    min_score_change: float | None = Field(default=None, ge=0.1, description="Alert on score change threshold")
    enabled: bool = Field(default=True)


class ScreenerAlertResponse(BaseModel):
    """Response for screener alert configuration."""

    id: str
    screener_id: str
    screener_name: str
    alert_on_new_symbols: bool
    alert_on_removed_symbols: bool
    min_score_change: float | None
    enabled: bool
    created_at: datetime
    last_run_at: datetime | None


# ============== Performance Tracking Schemas ==============


class RecommendationPerformanceItem(BaseModel):
    """Performance data for a single recommendation."""

    symbol: str
    category: str
    date: datetime
    score: float
    price_at_rec: float
    price_1d: float | None = None
    price_1w: float | None = None
    price_1m: float | None = None
    return_1d: float | None = None
    return_1w: float | None = None
    return_1m: float | None = None


class CategoryPerformanceStats(BaseModel):
    """Aggregated performance stats for a category."""

    category: str
    total_recommendations: int
    win_rate_1d: float | None = None  # % of picks with positive 1d return
    win_rate_1w: float | None = None
    win_rate_1m: float | None = None
    avg_return_1d: float | None = None
    avg_return_1w: float | None = None
    avg_return_1m: float | None = None
    best_pick_1d: str | None = None
    best_pick_1w: str | None = None
    best_pick_1m: str | None = None
    best_return_1d: float | None = None
    best_return_1w: float | None = None
    best_return_1m: float | None = None


class OverallPerformanceStats(BaseModel):
    """Overall screener performance stats."""

    total_recommendations: int
    unique_symbols: int
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    categories: list[CategoryPerformanceStats]
    overall_win_rate_1d: float | None = None
    overall_win_rate_1w: float | None = None
    overall_win_rate_1m: float | None = None
    overall_avg_return_1d: float | None = None
    overall_avg_return_1w: float | None = None
    overall_avg_return_1m: float | None = None


class UpdateReturnsResponse(BaseModel):
    """Response for update returns endpoint."""

    status: str
    updated_1d: int = 0
    updated_1w: int = 0
    updated_1m: int = 0
    errors: list[str] = []

