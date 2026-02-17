"""DSL validator for checking strategy definitions.

This module validates DSL strategy definitions to ensure:
- All referenced functions exist and have valid parameters
- All variables are known price/market data
- No security vulnerabilities (code injection)
- Proper structure and types
"""

from dataclasses import dataclass, field

from shared.strategies.dsl.operators import DSL_FUNCTIONS, DSL_VARIABLES
from shared.strategies.dsl.parser import ASTNode, DSLParseError, NodeType, parse_condition
from shared.strategies.dsl.schemas import DSLStrategyDefinition


@dataclass
class ValidationError:
    """A validation error."""

    message: str
    field: str | None = None
    line: int | None = None


@dataclass
class ValidationResult:
    """Result of validating a DSL strategy."""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DSLValidator:
    """Validator for DSL strategy definitions."""

    # Maximum allowed complexity to prevent DoS
    MAX_ENTRY_RULES = 20
    MAX_FILTERS = 10
    MAX_INDICATORS = 20
    MAX_CONDITION_LENGTH = 500

    def __init__(self):
        self.errors: list[ValidationError] = []
        self.warnings: list[str] = []

    def validate(self, definition: DSLStrategyDefinition) -> ValidationResult:
        """Validate a DSL strategy definition.

        Args:
            definition: The DSL strategy definition to validate

        Returns:
            ValidationResult with errors and warnings
        """
        self.errors = []
        self.warnings = []

        # Validate structure limits
        self._validate_limits(definition)

        # Validate entry rules
        for i, rule in enumerate(definition.rules.entry):
            self._validate_condition(rule.condition, f"rules.entry[{i}].condition")

        # Validate filter conditions
        for i, filter_expr in enumerate(definition.rules.filters):
            self._validate_condition(filter_expr, f"rules.filters[{i}]")

        # Validate indicator configs
        for i, indicator in enumerate(definition.indicators):
            self._validate_indicator(indicator.name, indicator.params, f"indicators[{i}]")

        return ValidationResult(
            valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings,
        )

    def _validate_limits(self, definition: DSLStrategyDefinition) -> None:
        """Validate structural limits."""
        if len(definition.rules.entry) > self.MAX_ENTRY_RULES:
            self.errors.append(
                ValidationError(
                    f"Too many entry rules ({len(definition.rules.entry)}). "
                    f"Maximum is {self.MAX_ENTRY_RULES}.",
                    field="rules.entry",
                )
            )

        if len(definition.rules.filters) > self.MAX_FILTERS:
            self.errors.append(
                ValidationError(
                    f"Too many filters ({len(definition.rules.filters)}). "
                    f"Maximum is {self.MAX_FILTERS}.",
                    field="rules.filters",
                )
            )

        if len(definition.indicators) > self.MAX_INDICATORS:
            self.errors.append(
                ValidationError(
                    f"Too many indicators ({len(definition.indicators)}). "
                    f"Maximum is {self.MAX_INDICATORS}.",
                    field="indicators",
                )
            )

    def _validate_condition(self, condition: str, field: str) -> None:
        """Validate a condition expression."""
        if len(condition) > self.MAX_CONDITION_LENGTH:
            self.errors.append(
                ValidationError(
                    f"Condition too long ({len(condition)} chars). "
                    f"Maximum is {self.MAX_CONDITION_LENGTH}.",
                    field=field,
                )
            )
            return

        try:
            ast = parse_condition(condition)
            self._validate_ast_node(ast, field)
        except DSLParseError as e:
            self.errors.append(
                ValidationError(f"Parse error: {e.message}", field=field, line=e.position)
            )

    def _validate_ast_node(self, node: ASTNode, field: str) -> None:
        """Recursively validate an AST node."""
        if node.node_type == NodeType.VARIABLE:
            if node.value not in DSL_VARIABLES:
                self.errors.append(
                    ValidationError(
                        f"Unknown variable '{node.value}'. "
                        f"Valid variables: {', '.join(sorted(DSL_VARIABLES.keys()))}",
                        field=field,
                    )
                )

        elif node.node_type == NodeType.FUNCTION_CALL:
            if node.function_name not in DSL_FUNCTIONS:
                self.errors.append(
                    ValidationError(
                        f"Unknown function '{node.function_name}'. "
                        f"Valid functions: {', '.join(sorted(DSL_FUNCTIONS.keys()))}",
                        field=field,
                    )
                )
            else:
                # Validate function arguments
                self._validate_function_args(node.function_name, node.args or [], field)

        # Recursively validate children
        if node.left:
            self._validate_ast_node(node.left, field)
        if node.right:
            self._validate_ast_node(node.right, field)

    def _validate_function_args(self, func_name: str, args: list, field: str) -> None:
        """Validate function arguments against the function definition."""
        func_def = DSL_FUNCTIONS[func_name]

        # Count required params
        required_count = sum(1 for p in func_def.params if p.required)

        if len(args) < required_count:
            self.errors.append(
                ValidationError(
                    f"Function '{func_name}' requires at least {required_count} "
                    f"argument(s), got {len(args)}",
                    field=field,
                )
            )

        if len(args) > len(func_def.params):
            self.warnings.append(
                f"Function '{func_name}' called with extra arguments "
                f"({len(args)} > {len(func_def.params)})"
            )

        # Validate argument types
        for i, (arg, param) in enumerate(zip(args, func_def.params, strict=False)):
            if param.param_type is int and not isinstance(arg, int | float):
                self.errors.append(
                    ValidationError(
                        f"Function '{func_name}' argument {i + 1} ('{param.name}') "
                        f"must be a number, got '{type(arg).__name__}'",
                        field=field,
                    )
                )
            elif param.param_type is float and not isinstance(arg, int | float):
                self.errors.append(
                    ValidationError(
                        f"Function '{func_name}' argument {i + 1} ('{param.name}') "
                        f"must be a number, got '{type(arg).__name__}'",
                        field=field,
                    )
                )
            elif param.param_type is str and not isinstance(arg, str):
                self.errors.append(
                    ValidationError(
                        f"Function '{func_name}' argument {i + 1} ('{param.name}') "
                        f"must be a string, got '{type(arg).__name__}'",
                        field=field,
                    )
                )

    def _validate_indicator(self, name: str, params: dict, field: str) -> None:
        """Validate an indicator configuration."""
        if name not in DSL_FUNCTIONS:
            self.errors.append(
                ValidationError(
                    f"Unknown indicator '{name}'. "
                    f"Valid indicators: {', '.join(sorted(DSL_FUNCTIONS.keys()))}",
                    field=field,
                )
            )
            return

        func_def = DSL_FUNCTIONS[name]

        # Check for unknown parameters
        valid_param_names = {p.name for p in func_def.params}
        for param_name in params:
            if param_name not in valid_param_names:
                self.warnings.append(
                    f"Unknown parameter '{param_name}' for indicator '{name}' "
                    f"in {field}. Valid params: {', '.join(valid_param_names)}"
                )


def validate_dsl_strategy(definition: DSLStrategyDefinition) -> ValidationResult:
    """Validate a DSL strategy definition.

    Args:
        definition: The DSL strategy definition to validate

    Returns:
        ValidationResult with errors and warnings
    """
    validator = DSLValidator()
    return validator.validate(definition)
