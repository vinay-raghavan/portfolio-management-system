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

