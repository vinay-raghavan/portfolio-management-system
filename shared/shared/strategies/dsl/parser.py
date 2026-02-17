"""DSL parser for condition expressions.

This module parses DSL condition expressions into an AST (Abstract Syntax Tree)
that can be validated and executed against market data.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """Types of AST nodes."""

    LITERAL = "literal"  # Numeric value
    VARIABLE = "variable"  # Price/volume variable
    FUNCTION_CALL = "function_call"  # Indicator function
    BINARY_OP = "binary_op"  # Comparison or arithmetic
    LOGICAL_OP = "logical_op"  # AND/OR
    UNARY_OP = "unary_op"  # NOT


@dataclass
class ASTNode:
    """Base AST node."""

    node_type: NodeType
    value: Any = None
    left: "ASTNode | None" = None
    right: "ASTNode | None" = None
    operator: str | None = None
    function_name: str | None = None
    args: list[Any] | None = None


class DSLParseError(Exception):
    """Exception raised when parsing DSL expressions fails."""

    def __init__(self, message: str, position: int | None = None):
        self.position = position
        self.message = message
        super().__init__(f"{message}" + (f" at position {position}" if position else ""))


class DSLTokenizer:
    """Tokenize DSL condition expressions."""

    # Token patterns
    PATTERNS = [
        ("WHITESPACE", r"\s+"),
        ("NUMBER", r"\d+\.?\d*"),
        ("AND", r"\bAND\b"),
        ("OR", r"\bOR\b"),
        ("NOT", r"\bNOT\b"),
        ("GTE", r">="),
        ("LTE", r"<="),
        ("NEQ", r"!="),
        ("EQ", r"=="),
        ("GT", r">"),
        ("LT", r"<"),
        ("PLUS", r"\+"),
        ("MINUS", r"-"),
        ("MUL", r"\*"),
        ("DIV", r"/"),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("COMMA", r","),
        ("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ]

    def __init__(self, expression: str):
        self.expression = expression
        self.pos = 0
        self.tokens: list[tuple[str, str, int]] = []
        self._tokenize()

    def _tokenize(self) -> None:
        """Tokenize the expression."""
        while self.pos < len(self.expression):
            match = None
            for token_type, pattern in self.PATTERNS:
                regex = re.compile(pattern)
                match = regex.match(self.expression, self.pos)
                if match:
                    value = match.group(0)
                    if token_type != "WHITESPACE":
                        self.tokens.append((token_type, value, self.pos))
                    self.pos = match.end()
                    break

            if not match:
                raise DSLParseError(f"Unexpected character '{self.expression[self.pos]}'", self.pos)


class DSLParser:
    """Parse DSL condition expressions into AST."""

    def __init__(self, expression: str):
        self.tokenizer = DSLTokenizer(expression)
        self.tokens = self.tokenizer.tokens
        self.pos = 0

    def parse(self) -> ASTNode:
        """Parse the expression and return the AST."""
        if not self.tokens:
            raise DSLParseError("Empty expression")
        result = self._parse_or()
        if self.pos < len(self.tokens):
            token = self.tokens[self.pos]
            raise DSLParseError(f"Unexpected token '{token[1]}'", token[2])
        return result

    def _current_token(self) -> tuple[str, str, int] | None:
        """Get the current token."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _consume(self, expected_type: str | None = None) -> tuple[str, str, int]:
        """Consume the current token."""
        token = self._current_token()
        if token is None:
            raise DSLParseError("Unexpected end of expression")
        if expected_type and token[0] != expected_type:
            raise DSLParseError(f"Expected {expected_type}, got {token[0]}", token[2])
        self.pos += 1
        return token

    def _parse_or(self) -> ASTNode:
        """Parse OR expressions."""
        left = self._parse_and()
        while self._current_token() and self._current_token()[0] == "OR":
            self._consume("OR")
            right = self._parse_and()
            left = ASTNode(
                node_type=NodeType.LOGICAL_OP,
                operator="OR",
                left=left,
                right=right,
            )
        return left

    def _parse_and(self) -> ASTNode:
        """Parse AND expressions."""
        left = self._parse_not()
        while self._current_token() and self._current_token()[0] == "AND":
            self._consume("AND")
            right = self._parse_not()
            left = ASTNode(
                node_type=NodeType.LOGICAL_OP,
                operator="AND",
                left=left,
                right=right,
            )
        return left

    def _parse_not(self) -> ASTNode:
        """Parse NOT expressions."""
        if self._current_token() and self._current_token()[0] == "NOT":
            self._consume("NOT")
            operand = self._parse_not()
            return ASTNode(node_type=NodeType.UNARY_OP, operator="NOT", left=operand)
        return self._parse_comparison()

    def _parse_comparison(self) -> ASTNode:
        """Parse comparison expressions."""
        left = self._parse_additive()
        comp_ops = {"GT", "LT", "GTE", "LTE", "EQ", "NEQ"}
        op_map = {
            "GT": ">",
            "LT": "<",
            "GTE": ">=",
            "LTE": "<=",
            "EQ": "==",
            "NEQ": "!=",
        }

        if self._current_token() and self._current_token()[0] in comp_ops:
            op_token = self._consume()
            right = self._parse_additive()
            return ASTNode(
                node_type=NodeType.BINARY_OP,
                operator=op_map[op_token[0]],
                left=left,
                right=right,
            )
        return left

    def _parse_additive(self) -> ASTNode:
        """Parse addition/subtraction."""
        left = self._parse_multiplicative()
        while self._current_token() and self._current_token()[0] in ("PLUS", "MINUS"):
            op_token = self._consume()
            right = self._parse_multiplicative()
            left = ASTNode(
                node_type=NodeType.BINARY_OP,
                operator="+" if op_token[0] == "PLUS" else "-",
                left=left,
                right=right,
            )
        return left

    def _parse_multiplicative(self) -> ASTNode:
        """Parse multiplication/division."""
        left = self._parse_unary()
        while self._current_token() and self._current_token()[0] in ("MUL", "DIV"):
            op_token = self._consume()
            right = self._parse_unary()
            left = ASTNode(
                node_type=NodeType.BINARY_OP,
                operator="*" if op_token[0] == "MUL" else "/",
                left=left,
                right=right,
            )
        return left

    def _parse_unary(self) -> ASTNode:
        """Parse unary minus."""
        if self._current_token() and self._current_token()[0] == "MINUS":
            self._consume("MINUS")
            operand = self._parse_unary()
            return ASTNode(
                node_type=NodeType.BINARY_OP,
                operator="*",
                left=ASTNode(node_type=NodeType.LITERAL, value=-1),
                right=operand,
            )
        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        """Parse primary expressions (literals, variables, function calls, parens)."""
        token = self._current_token()
        if not token:
            raise DSLParseError("Unexpected end of expression")

        # Parenthesized expression
        if token[0] == "LPAREN":
            self._consume("LPAREN")
            node = self._parse_or()
            self._consume("RPAREN")
            return node

        # Number literal
        if token[0] == "NUMBER":
            self._consume("NUMBER")
            value = float(token[1]) if "." in token[1] else int(token[1])
            return ASTNode(node_type=NodeType.LITERAL, value=value)

        # Identifier (variable or function call)
        if token[0] == "IDENTIFIER":
            self._consume("IDENTIFIER")
            name = token[1]

            # Check if it's a function call
            if self._current_token() and self._current_token()[0] == "LPAREN":
                return self._parse_function_call(name)

            # It's a variable
            return ASTNode(node_type=NodeType.VARIABLE, value=name)

        raise DSLParseError(f"Unexpected token '{token[1]}'", token[2])

    def _parse_function_call(self, function_name: str) -> ASTNode:
        """Parse a function call with arguments."""
        self._consume("LPAREN")
        args: list[Any] = []

        # Parse arguments
        if self._current_token() and self._current_token()[0] != "RPAREN":
            args.append(self._parse_function_arg())
            while self._current_token() and self._current_token()[0] == "COMMA":
                self._consume("COMMA")
                args.append(self._parse_function_arg())

        self._consume("RPAREN")
        return ASTNode(
            node_type=NodeType.FUNCTION_CALL,
            function_name=function_name,
            args=args,
        )

    def _parse_function_arg(self) -> int | float | str:
        """Parse a function argument (number or identifier)."""
        token = self._current_token()
        if not token:
            raise DSLParseError("Expected function argument")

        if token[0] == "NUMBER":
            self._consume("NUMBER")
            return float(token[1]) if "." in token[1] else int(token[1])

        if token[0] == "IDENTIFIER":
            self._consume("IDENTIFIER")
            return token[1]

        raise DSLParseError(f"Invalid function argument: {token[1]}", token[2])


def parse_condition(expression: str) -> ASTNode:
    """Parse a DSL condition expression and return the AST.

    Args:
        expression: DSL condition string (e.g., "rsi(14) < 30 AND close > sma(20)")

    Returns:
        Root ASTNode of the parsed expression

    Raises:
        DSLParseError: If the expression is invalid
    """
    parser = DSLParser(expression)
    return parser.parse()
