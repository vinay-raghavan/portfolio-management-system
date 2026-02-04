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
    MINERVINI = "minervini"  # Mark Minervini Trend Template


class StrictnessLevel(str, Enum):
    """Strictness levels for preset screeners."""

    STRICT = "strict"  # Professional-grade criteria (Minervini exact)
    MODERATE = "moderate"  # Slightly relaxed (good for trending markets)
    RELAXED = "relaxed"  # More permissive (finds more candidates)
    EXPLORATORY = "exploratory"  # Very loose (for idea generation)


class ScoreGrade(str, Enum):
    """Grade interpretation of numeric score."""

    A_PLUS = "A+"  # 90-100: Exceptional
    A = "A"  # 80-89: Excellent
    B = "B"  # 70-79: Good
    C = "C"  # 60-69: Fair
    D = "D"  # 50-59: Weak
    F = "F"  # Below 50: Failed


def get_score_grade(score: float) -> ScoreGrade:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return ScoreGrade.A_PLUS
    elif score >= 80:
        return ScoreGrade.A
    elif score >= 70:
        return ScoreGrade.B
    elif score >= 60:
        return ScoreGrade.C
    elif score >= 50:
        return ScoreGrade.D
    return ScoreGrade.F


def get_score_description(score: float) -> str:
    """Get verbal description of score."""
    if score >= 90:
        return "Exceptional - meets all criteria strongly"
    elif score >= 80:
        return "Excellent - meets most criteria well"
    elif score >= 70:
        return "Good - solid candidate worth watching"
    elif score >= 60:
        return "Fair - some criteria met, needs confirmation"
    elif score >= 50:
        return "Weak - borderline, high risk"
    return "Failed - does not meet minimum criteria"


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
    strictness: StrictnessLevel = Field(
        default=StrictnessLevel.MODERATE,
        description="How strict the filter criteria should be",
    )
    min_score: float = Field(default=50.0, ge=0, le=100)
    top_n: int = Field(default=50, ge=1, le=500)


class ScreenerResultItem(BaseModel):
    """Single stock result from screener."""

    symbol: str
    rank: int
    score: float
    grade: str = Field(default="", description="Letter grade (A+, A, B, C, D, F)")
    grade_description: str = Field(default="", description="Verbal interpretation of score")
    passed: bool
    filter_scores: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    reasons_detailed: list[str] = Field(
        default_factory=list,
        description="Detailed reasons with actual values",
    )
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


class ScreenerAlertCreate(BaseModel):
    """Request to create a screener alert."""

    name: str = Field(..., min_length=1, max_length=100)
    custom_screener_id: str | None = Field(default=None, description="ID of custom screener")
    preset: str | None = Field(default=None, description="Preset screener name (if not custom)")
    universe: str | None = Field(default=None, description="Universe for preset screener")
    alert_on_new_symbols: bool = Field(default=True, description="Alert when new symbols match")
    alert_on_removed_symbols: bool = Field(
        default=False, description="Alert when symbols no longer match"
    )
    min_score_threshold: float | None = Field(
        default=None, ge=0, le=100, description="Minimum score threshold for alerts"
    )
    target_symbol: str | None = Field(
        default=None, max_length=20, description="Alert for specific symbol only"
    )
    enabled: bool = Field(default=True)


class ScreenerAlertUpdate(BaseModel):
    """Request to update a screener alert."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    alert_on_new_symbols: bool | None = None
    alert_on_removed_symbols: bool | None = None
    min_score_threshold: float | None = Field(default=None, ge=0, le=100)
    target_symbol: str | None = Field(default=None, max_length=20)
    enabled: bool | None = None


class ScreenerAlertResponse(BaseModel):
    """Response for screener alert."""

    id: str
    name: str
    custom_screener_id: str | None
    custom_screener_name: str | None = None
    preset: str | None
    universe: str | None
    alert_on_new_symbols: bool
    alert_on_removed_symbols: bool
    min_score_threshold: float | None
    target_symbol: str | None
    enabled: bool
    last_run_at: datetime | None
    last_symbols: list[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScreenerAlertListResponse(BaseModel):
    """Response for list of screener alerts."""

    alerts: list[ScreenerAlertResponse]


class CreateStrategyFromScreenerRequest(BaseModel):
    """Request to create an algo strategy from screener results."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    strategy_type: str = Field(default="momentum", description="Strategy type")
    symbols: list[str] = Field(..., min_length=1, description="Symbols from screener results")
    screener_config: dict | None = Field(
        default=None, description="Screener configuration for dynamic refresh"
    )
    is_dynamic_universe: bool = Field(
        default=False, description="If true, universe will be refreshed from screener"
    )


class CreateStrategyFromScreenerResponse(BaseModel):
    """Response after creating strategy from screener."""

    strategy_id: str
    strategy_name: str
    universe_id: str
    universe_name: str
    symbol_count: int
    is_dynamic: bool
    created_at: datetime


# ============== Strategy Inference Schemas ==============


class InferStrategyRequest(BaseModel):
    """Request to infer optimal strategy from screener filters."""

    screener_run_id: str | None = Field(
        default=None, description="ID of a completed screener run to infer from"
    )
    filters: list[FilterConfig] | None = Field(
        default=None, description="Filter configs to infer from directly"
    )

    def model_post_init(self, __context) -> None:
        """Validate that at least one source is provided."""
        if not self.screener_run_id and not self.filters:
            raise ValueError("Either screener_run_id or filters must be provided")


class StrategyRecommendationResponse(BaseModel):
    """A recommended strategy with suggested parameters."""

    strategy_type: str
    strategy_name: str
    description: str
    suggested_params: dict
    confidence: float
    reasoning: list[str]


class FilterAnalysisResponse(BaseModel):
    """Analysis of screener filters."""

    primary_intent: str
    secondary_intent: str | None = None
    risk_profile: str
    detected_patterns: list[str] = []


class InferStrategyResponse(BaseModel):
    """Response for strategy inference."""

    recommended_strategy: StrategyRecommendationResponse
    alternative_strategies: list[StrategyRecommendationResponse] = []
    filter_analysis: FilterAnalysisResponse


class CreateSmartStrategyRequest(BaseModel):
    """Request to create a strategy with inferred parameters."""

    screener_run_id: str | None = Field(default=None, description="ID of a completed screener run")
    filters: list[FilterConfig] | None = Field(
        default=None, description="Filter configs if not using run_id"
    )
    symbols: list[str] = Field(..., min_length=1, description="Symbols for the strategy")
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    strategy_type_override: str | None = Field(
        default=None, description="Override the inferred strategy type"
    )
    strategy_params_override: dict | None = Field(
        default=None, description="Override specific inferred parameters"
    )
    product_type: str = Field(default="INTRADAY")
    position_sizing_method: str = Field(default="PERCENT_OF_PORTFOLIO")
    position_size_value: float = Field(default=5.0, ge=0.1, le=100)
    is_dynamic_universe: bool = Field(default=False)
    screener_config: dict | None = Field(
        default=None, description="Screener config for dynamic universes"
    )


class CreateSmartStrategyResponse(BaseModel):
    """Response after creating a smart strategy."""

    strategy_id: str
    strategy_name: str
    universe_id: str
    universe_name: str
    symbol_count: int
    is_dynamic: bool
    created_at: datetime
    inferred_strategy_type: str
    inferred_params: dict
    params_overridden: list[str] = []
    inference_reasoning: list[str]


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


class StoreRecommendationsRequest(BaseModel):
    """Request to store daily recommendations (from worker task)."""

    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    category: str = Field(..., description="Category: momentum, breakout, pullback, sector")
    results: list[dict] = Field(..., description="Screener results to store")
