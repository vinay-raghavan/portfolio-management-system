"""Pydantic schemas for DSL strategy definitions.

These schemas define the structure of DSL-based strategy configurations
that users can write in YAML or JSON format.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DSLAction(str, Enum):
    """Supported trading actions in DSL rules."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class DSLCondition(BaseModel):
    """A condition expression in the DSL.

    Conditions are string expressions that get parsed and evaluated
    against market data. Example: "rsi(14) < 30 AND macd_histogram > 0"
    """

    expression: str = Field(
        ...,
        description="Condition expression using supported operators and functions",
        min_length=1,
        max_length=500,
    )

    @field_validator("expression")
    @classmethod
    def validate_expression_syntax(cls, v: str) -> str:
        """Basic validation - detailed parsing done by DSL parser."""
        # Remove extra whitespace
        v = " ".join(v.split())
        if not v:
            raise ValueError("Condition expression cannot be empty")
        return v


class DSLEntryRule(BaseModel):
    """An entry rule defining when to enter a trade."""

    condition: str = Field(
        ...,
        description="Condition expression for entry",
        min_length=1,
    )
    action: DSLAction = Field(
        ...,
        description="Action to take when condition is met (BUY/SELL)",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence level for this signal (0.0-1.0)",
    )
    strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Signal strength (0.0-1.0)",
    )


class DSLExitConfig(BaseModel):
    """Exit configuration for the strategy."""

    stop_loss_pct: float = Field(
        default=2.0,
        ge=0.1,
        le=20.0,
        description="Stop loss percentage (e.g., 2.0 = 2%)",
    )
    take_profit_pct: float = Field(
        default=4.0,
        ge=0.1,
        le=50.0,
        description="Take profit percentage (e.g., 4.0 = 4%)",
    )
    trailing_stop_pct: float | None = Field(
        default=None,
        ge=0.1,
        le=20.0,
        description="Optional trailing stop percentage",
    )


class DSLIndicatorConfig(BaseModel):
    """Configuration for an indicator used in the strategy."""

    name: str = Field(
        ...,
        description="Indicator name (rsi, macd, sma, ema, bbands, atr)",
        min_length=1,
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Indicator parameters (e.g., period, fast, slow)",
    )


class DSLRules(BaseModel):
    """Rules section containing entry, exit, and filter conditions."""

    entry: list[DSLEntryRule] = Field(
        default_factory=list,
        description="List of entry rules",
    )
    exit: DSLExitConfig = Field(
        default_factory=DSLExitConfig,
        description="Exit configuration",
    )
    filters: list[str] = Field(
        default_factory=list,
        description="Filter conditions that must all be true for signals",
    )


class DSLStrategyDefinition(BaseModel):
    """Complete DSL strategy definition.

    This is the root schema that represents a complete strategy
    definition in YAML or JSON format.
    """

    name: str = Field(
        ...,
        description="Strategy name",
        min_length=1,
        max_length=100,
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Strategy definition version",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Strategy description",
    )
    rules: DSLRules = Field(
        ...,
        description="Trading rules (entry, exit, filters)",
    )
    indicators: list[DSLIndicatorConfig] = Field(
        default_factory=list,
        description="Indicators used by this strategy",
    )
    timeframe: str = Field(
        default="1d",
        description="Default timeframe for this strategy",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate strategy name."""
        v = v.strip()
        if not v:
            raise ValueError("Strategy name cannot be empty")
        return v
