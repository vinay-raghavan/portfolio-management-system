"""DSL executor for evaluating conditions against market data.

This module evaluates parsed DSL expressions against actual OHLCV data
to generate trading signals.
"""

from decimal import Decimal
from typing import Any

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands

from shared.strategies.dsl.parser import ASTNode, NodeType


class DSLExecutionError(Exception):
    """Exception raised when DSL execution fails."""

    pass


class DSLExecutor:
    """Execute DSL expressions against market data."""

    def __init__(self, df: pd.DataFrame):
        """Initialize executor with market data.

        Args:
            df: DataFrame with OHLCV columns (Open, High, Low, Close, Volume)
        """
        self.df = df
        self._indicator_cache: dict[str, Any] = {}

    def evaluate(self, node: ASTNode) -> bool | float | int:
        """Evaluate an AST node against the market data.

        Args:
            node: The AST node to evaluate

        Returns:
            Boolean for logical/comparison expressions, numeric for arithmetic
        """
        if node.node_type == NodeType.LITERAL:
            return node.value

        elif node.node_type == NodeType.VARIABLE:
            return self._get_variable(node.value)

        elif node.node_type == NodeType.FUNCTION_CALL:
            return self._call_function(node.function_name, node.args or [])

        elif node.node_type == NodeType.BINARY_OP:
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            return self._apply_binary_op(node.operator, left, right)

        elif node.node_type == NodeType.LOGICAL_OP:
            left = self.evaluate(node.left)
            right = self.evaluate(node.right) if node.right else None
            return self._apply_logical_op(node.operator, left, right)

        elif node.node_type == NodeType.UNARY_OP:
            operand = self.evaluate(node.left)
            if node.operator == "NOT":
                return not operand
            raise DSLExecutionError(f"Unknown unary operator: {node.operator}")

        raise DSLExecutionError(f"Unknown node type: {node.node_type}")

    def _get_variable(self, name: str) -> float:
        """Get a price/volume variable value."""
        if len(self.df) < 1:
            raise DSLExecutionError("Not enough data")

        current_idx = -1
        prev_idx = -2 if len(self.df) >= 2 else -1

        var_map = {
            "close": ("Close", current_idx),
            "open": ("Open", current_idx),
            "high": ("High", current_idx),
            "low": ("Low", current_idx),
            "volume": ("Volume", current_idx),
            "previous_close": ("Close", prev_idx),
            "previous_open": ("Open", prev_idx),
            "previous_high": ("High", prev_idx),
            "previous_low": ("Low", prev_idx),
            "previous_volume": ("Volume", prev_idx),
        }

        if name not in var_map:
            raise DSLExecutionError(f"Unknown variable: {name}")

        col, idx = var_map[name]
        value = self.df[col].iloc[idx]
        return float(value) if not pd.isna(value) else 0.0

    def _call_function(self, func_name: str, args: list) -> float:
        """Call an indicator function."""
        cache_key = f"{func_name}:{args}"
        if cache_key in self._indicator_cache:
            return self._indicator_cache[cache_key]

        result = self._compute_indicator(func_name, args)
        self._indicator_cache[cache_key] = result
        return result

    def _compute_indicator(self, func_name: str, args: list) -> float:
        """Compute an indicator value."""
        close = self.df["Close"]
        high = self.df["High"]
        low = self.df["Low"]
        volume = self.df["Volume"]

        if func_name == "rsi":
            period = int(args[0]) if args else 14
            if len(close) < period + 1:
                return 50.0  # Default neutral RSI
            indicator = RSIIndicator(close, window=period)
            value = indicator.rsi().iloc[-1]
            return float(value) if not pd.isna(value) else 50.0

        elif func_name == "sma":
            source_name = args[0] if args and isinstance(args[0], str) else "close"
            period = int(args[-1]) if args else 20
            source = self._get_source(source_name)
            if len(source) < period:
                return float(source.iloc[-1])
            indicator = SMAIndicator(source, window=period)
            value = indicator.sma_indicator().iloc[-1]
            return float(value) if not pd.isna(value) else float(source.iloc[-1])

        elif func_name == "ema":
            source_name = args[0] if args and isinstance(args[0], str) else "close"
            period = int(args[-1]) if args else 20
            source = self._get_source(source_name)
            if len(source) < period:
                return float(source.iloc[-1])
            indicator = EMAIndicator(source, window=period)
            value = indicator.ema_indicator().iloc[-1]
            return float(value) if not pd.isna(value) else float(source.iloc[-1])

        elif func_name in ("macd", "macd_signal", "macd_histogram"):
            fast = int(args[0]) if len(args) > 0 else 12
            slow = int(args[1]) if len(args) > 1 else 26
            signal = int(args[2]) if len(args) > 2 else 9
            if len(close) < slow + signal:
                return 0.0
            indicator = MACD(close, window_fast=fast, window_slow=slow, window_sign=signal)
            if func_name == "macd":
                value = indicator.macd().iloc[-1]
            elif func_name == "macd_signal":
                value = indicator.macd_signal().iloc[-1]
            else:
                value = indicator.macd_diff().iloc[-1]
            return float(value) if not pd.isna(value) else 0.0

        elif func_name in ("bbands_upper", "bbands_lower", "bbands_middle"):
            period = int(args[0]) if len(args) > 0 else 20
            std_dev = float(args[1]) if len(args) > 1 else 2.0
            if len(close) < period:
                return float(close.iloc[-1])
            indicator = BollingerBands(close, window=period, window_dev=int(std_dev))
            if func_name == "bbands_upper":
                value = indicator.bollinger_hband().iloc[-1]
            elif func_name == "bbands_lower":
                value = indicator.bollinger_lband().iloc[-1]
            else:
                value = indicator.bollinger_mavg().iloc[-1]
            return float(value) if not pd.isna(value) else float(close.iloc[-1])

        elif func_name == "atr":
            period = int(args[0]) if args else 14
            if len(close) < period:
                return 0.0
            indicator = AverageTrueRange(high, low, close, window=period)
            value = indicator.average_true_range().iloc[-1]
            return float(value) if not pd.isna(value) else 0.0

        elif func_name == "volume_sma":
            period = int(args[0]) if args else 20
            if len(volume) < period:
                return float(volume.iloc[-1])
            indicator = SMAIndicator(volume, window=period)
            value = indicator.sma_indicator().iloc[-1]
            return float(value) if not pd.isna(value) else float(volume.iloc[-1])

        raise DSLExecutionError(f"Unknown function: {func_name}")

    def _get_source(self, source_name: str) -> pd.Series:
        """Get a price series by name."""
        source_map = {
            "close": "Close",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "volume": "Volume",
        }
        col = source_map.get(source_name.lower(), "Close")
        return self.df[col]

    def _apply_binary_op(self, op: str, left: Any, right: Any) -> bool | float:
        """Apply a binary operator."""
        if op == ">":
            return left > right
        elif op == "<":
            return left < right
        elif op == ">=":
            return left >= right
        elif op == "<=":
            return left <= right
        elif op == "==":
            return left == right
        elif op == "!=":
            return left != right
        elif op == "+":
            return left + right
        elif op == "-":
            return left - right
        elif op == "*":
            return left * right
        elif op == "/":
            if right == 0:
                raise DSLExecutionError("Division by zero")
            return left / right
        raise DSLExecutionError(f"Unknown operator: {op}")

    def _apply_logical_op(self, op: str, left: Any, right: Any) -> bool:
        """Apply a logical operator."""
        if op == "AND":
            return bool(left) and bool(right)
        elif op == "OR":
            return bool(left) or bool(right)
        raise DSLExecutionError(f"Unknown logical operator: {op}")

    def get_current_price(self) -> Decimal:
        """Get the current closing price as Decimal."""
        if len(self.df) < 1:
            raise DSLExecutionError("Not enough data")
        return Decimal(str(self.df["Close"].iloc[-1]))

    def get_atr(self, period: int = 14) -> Decimal | None:
        """Get the ATR value as Decimal."""
        if len(self.df) < period:
            return None
        indicator = AverageTrueRange(
            self.df["High"], self.df["Low"], self.df["Close"], window=period
        )
        value = indicator.average_true_range().iloc[-1]
        if pd.isna(value):
            return None
        return Decimal(str(value))
