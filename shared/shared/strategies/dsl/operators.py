"""Supported operators, functions, and variables for DSL expressions.

This module defines the allowed operators and functions that can be used
in DSL condition expressions. Only these predefined elements are allowed
for security (sandboxed execution).
"""

from enum import Enum
from typing import NamedTuple


class ComparisonOperator(str, Enum):
    """Comparison operators for conditions."""

    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    EQ = "=="
    NEQ = "!="


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ArithmeticOperator(str, Enum):
    """Arithmetic operators for calculations."""

    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"


class DSLFunctionParam(NamedTuple):
    """Parameter definition for a DSL function."""

    name: str
    param_type: type
    default: int | float | None = None
    required: bool = True


class DSLFunctionDef(NamedTuple):
    """Definition of a DSL function."""

    name: str
    description: str
    params: list[DSLFunctionParam]
    returns: str  # Description of return value


# Supported indicator functions
DSL_FUNCTIONS: dict[str, DSLFunctionDef] = {
    "rsi": DSLFunctionDef(
        name="rsi",
        description="Relative Strength Index",
        params=[DSLFunctionParam("period", int, default=14, required=False)],
        returns="RSI value (0-100)",
    ),
    "macd": DSLFunctionDef(
        name="macd",
        description="MACD line value",
        params=[
            DSLFunctionParam("fast", int, default=12, required=False),
            DSLFunctionParam("slow", int, default=26, required=False),
            DSLFunctionParam("signal", int, default=9, required=False),
        ],
        returns="MACD line value",
    ),
    "macd_signal": DSLFunctionDef(
        name="macd_signal",
        description="MACD signal line value",
        params=[
            DSLFunctionParam("fast", int, default=12, required=False),
            DSLFunctionParam("slow", int, default=26, required=False),
            DSLFunctionParam("signal", int, default=9, required=False),
        ],
        returns="MACD signal line value",
    ),
    "macd_histogram": DSLFunctionDef(
        name="macd_histogram",
        description="MACD histogram (MACD - Signal)",
        params=[
            DSLFunctionParam("fast", int, default=12, required=False),
            DSLFunctionParam("slow", int, default=26, required=False),
            DSLFunctionParam("signal", int, default=9, required=False),
        ],
        returns="MACD histogram value",
    ),
    "sma": DSLFunctionDef(
        name="sma",
        description="Simple Moving Average",
        params=[
            DSLFunctionParam("source", str, default="close", required=False),
            DSLFunctionParam("period", int, default=20, required=True),
        ],
        returns="SMA value",
    ),
    "ema": DSLFunctionDef(
        name="ema",
        description="Exponential Moving Average",
        params=[
            DSLFunctionParam("source", str, default="close", required=False),
            DSLFunctionParam("period", int, default=20, required=True),
        ],
        returns="EMA value",
    ),
    "bbands_upper": DSLFunctionDef(
        name="bbands_upper",
        description="Bollinger Bands upper band",
        params=[
            DSLFunctionParam("period", int, default=20, required=False),
            DSLFunctionParam("std_dev", float, default=2.0, required=False),
        ],
        returns="Upper band value",
    ),
    "bbands_lower": DSLFunctionDef(
        name="bbands_lower",
        description="Bollinger Bands lower band",
        params=[
            DSLFunctionParam("period", int, default=20, required=False),
            DSLFunctionParam("std_dev", float, default=2.0, required=False),
        ],
        returns="Lower band value",
    ),
    "bbands_middle": DSLFunctionDef(
        name="bbands_middle",
        description="Bollinger Bands middle band (SMA)",
        params=[
            DSLFunctionParam("period", int, default=20, required=False),
            DSLFunctionParam("std_dev", float, default=2.0, required=False),
        ],
        returns="Middle band value",
    ),
    "atr": DSLFunctionDef(
        name="atr",
        description="Average True Range",
        params=[DSLFunctionParam("period", int, default=14, required=False)],
        returns="ATR value",
    ),
    "volume_sma": DSLFunctionDef(
        name="volume_sma",
        description="Volume Simple Moving Average",
        params=[DSLFunctionParam("period", int, default=20, required=False)],
        returns="Volume SMA value",
    ),
}

# Supported price/market variables (no function call needed)
DSL_VARIABLES: dict[str, str] = {
    "close": "Current closing price",
    "open": "Current opening price",
    "high": "Current high price",
    "low": "Current low price",
    "volume": "Current volume",
    "previous_close": "Previous bar's closing price",
    "previous_open": "Previous bar's opening price",
    "previous_high": "Previous bar's high price",
    "previous_low": "Previous bar's low price",
    "previous_volume": "Previous bar's volume",
}

# All supported operators for quick lookup
ALL_COMPARISON_OPS = {op.value for op in ComparisonOperator}
ALL_LOGICAL_OPS = {op.value for op in LogicalOperator}
ALL_ARITHMETIC_OPS = {op.value for op in ArithmeticOperator}
