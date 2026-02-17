"""DSL (Domain Specific Language) module for custom strategy definitions.

This module provides a safe, sandboxed way for users to define custom
rule-based trading strategies using a YAML/JSON-based DSL without
requiring full Python access.
"""

from shared.strategies.dsl.operators import (
    ALL_ARITHMETIC_OPS,
    ALL_COMPARISON_OPS,
    ALL_LOGICAL_OPS,
    DSL_FUNCTIONS,
    DSL_VARIABLES,
    ArithmeticOperator,
    ComparisonOperator,
    DSLFunctionDef,
    DSLFunctionParam,
    LogicalOperator,
)
from shared.strategies.dsl.parser import (
    ASTNode,
    DSLParseError,
    DSLParser,
    NodeType,
    parse_condition,
)
from shared.strategies.dsl.schemas import (
    DSLAction,
    DSLCondition,
    DSLEntryRule,
    DSLExitConfig,
    DSLIndicatorConfig,
    DSLRules,
    DSLStrategyDefinition,
)

__all__ = [
    # Operators
    "ArithmeticOperator",
    "ComparisonOperator",
    "LogicalOperator",
    "DSLFunctionDef",
    "DSLFunctionParam",
    "DSL_FUNCTIONS",
    "DSL_VARIABLES",
    "ALL_COMPARISON_OPS",
    "ALL_LOGICAL_OPS",
    "ALL_ARITHMETIC_OPS",
    # Parser
    "ASTNode",
    "DSLParseError",
    "DSLParser",
    "NodeType",
    "parse_condition",
    # Schemas
    "DSLAction",
    "DSLCondition",
    "DSLEntryRule",
    "DSLExitConfig",
    "DSLIndicatorConfig",
    "DSLRules",
    "DSLStrategyDefinition",
]
