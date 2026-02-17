"""Tests for the DSL (Domain Specific Language) module."""

import pandas as pd
import pytest

from shared.strategies.dsl import (
    DSLExecutor,
    DSLParseError,
    DSLStrategy,
    DSLStrategyDefinition,
    NodeType,
    create_dsl_strategy,
    parse_condition,
    validate_dsl_strategy,
)


class TestDSLParser:
    """Tests for the DSL parser."""

    def test_parse_simple_comparison(self):
        """Test parsing a simple comparison."""
        ast = parse_condition("rsi(14) < 30")
        assert ast.node_type == NodeType.BINARY_OP
        assert ast.operator == "<"
        assert ast.left.node_type == NodeType.FUNCTION_CALL
        assert ast.left.function_name == "rsi"
        assert ast.right.node_type == NodeType.LITERAL
        assert ast.right.value == 30

    def test_parse_logical_and(self):
        """Test parsing AND expression."""
        ast = parse_condition("rsi(14) < 30 AND macd_histogram > 0")
        assert ast.node_type == NodeType.LOGICAL_OP
        assert ast.operator == "AND"

    def test_parse_logical_or(self):
        """Test parsing OR expression."""
        ast = parse_condition("close > sma(20) OR close > ema(20)")
        assert ast.node_type == NodeType.LOGICAL_OP
        assert ast.operator == "OR"

    def test_parse_variable(self):
        """Test parsing price variables."""
        ast = parse_condition("close > previous_close")
        assert ast.left.node_type == NodeType.VARIABLE
        assert ast.left.value == "close"
        assert ast.right.node_type == NodeType.VARIABLE
        assert ast.right.value == "previous_close"

    def test_parse_function_with_multiple_args(self):
        """Test parsing function with multiple arguments."""
        ast = parse_condition("bbands_upper(20, 2) > close")
        assert ast.left.node_type == NodeType.FUNCTION_CALL
        assert ast.left.function_name == "bbands_upper"
        assert ast.left.args == [20, 2]

    def test_parse_parentheses(self):
        """Test parsing with parentheses for precedence."""
        ast = parse_condition("(rsi(14) < 30) AND (close > sma(50))")
        assert ast.node_type == NodeType.LOGICAL_OP

    def test_parse_not_operator(self):
        """Test parsing NOT operator."""
        ast = parse_condition("NOT close > sma(200)")
        assert ast.node_type == NodeType.UNARY_OP
        assert ast.operator == "NOT"

    def test_parse_arithmetic(self):
        """Test parsing arithmetic expressions."""
        ast = parse_condition("close * 1.02 > previous_close")
        assert ast.left.node_type == NodeType.BINARY_OP
        assert ast.left.operator == "*"

    def test_parse_invalid_syntax(self):
        """Test parsing invalid syntax raises error."""
        with pytest.raises(DSLParseError):
            parse_condition("rsi(14) <")

    def test_parse_empty_expression(self):
        """Test parsing empty expression raises error."""
        with pytest.raises(DSLParseError):
            parse_condition("")


class TestDSLValidator:
    """Tests for the DSL validator."""

    def test_validate_valid_definition(self):
        """Test validating a valid DSL definition."""
        definition = DSLStrategyDefinition(
            name="Test Strategy",
            rules={
                "entry": [{"condition": "rsi(14) < 30", "action": "BUY", "confidence": 0.8}],
                "exit": {"stop_loss_pct": 2.0, "take_profit_pct": 4.0},
            },
        )
        result = validate_dsl_strategy(definition)
        assert result.valid
        assert len(result.errors) == 0

    def test_validate_invalid_function(self):
        """Test validating with unknown function."""
        definition = DSLStrategyDefinition(
            name="Test Strategy",
            rules={
                "entry": [{"condition": "unknown_func(14) < 30", "action": "BUY"}],
                "exit": {"stop_loss_pct": 2.0, "take_profit_pct": 4.0},
            },
        )
        result = validate_dsl_strategy(definition)
        assert not result.valid
        assert any("unknown_func" in e.message for e in result.errors)

    def test_validate_invalid_variable(self):
        """Test validating with unknown variable."""
        definition = DSLStrategyDefinition(
            name="Test Strategy",
            rules={
                "entry": [{"condition": "unknown_var > 100", "action": "BUY"}],
                "exit": {"stop_loss_pct": 2.0, "take_profit_pct": 4.0},
            },
        )
        result = validate_dsl_strategy(definition)
        assert not result.valid

    def test_validate_too_many_entry_rules(self):
        """Test validating with too many entry rules."""
        definition = DSLStrategyDefinition(
            name="Test Strategy",
            rules={
                "entry": [
                    {"condition": f"rsi(14) < {30 + i}", "action": "BUY"}
                    for i in range(25)  # Exceeds max of 20
                ],
                "exit": {"stop_loss_pct": 2.0, "take_profit_pct": 4.0},
            },
        )
        result = validate_dsl_strategy(definition)
        assert not result.valid
        assert any("entry rules" in e.message for e in result.errors)


class TestDSLExecutor:
    """Tests for the DSL executor."""

    @pytest.fixture
    def sample_df(self):
        """Create sample OHLCV data for testing."""
        return pd.DataFrame(
            {
                "Open": [100.0] * 50 + [105.0] * 10,
                "High": [102.0] * 50 + [107.0] * 10,
                "Low": [98.0] * 50 + [103.0] * 10,
                "Close": [101.0] * 50 + [106.0] * 10,
                "Volume": [1000000] * 60,
            }
        )

    def test_evaluate_simple_condition(self, sample_df):
        """Test evaluating a simple condition."""
        executor = DSLExecutor(sample_df)
        ast = parse_condition("close > 100")
        result = executor.evaluate(ast)
        assert result is True

    def test_evaluate_rsi_function(self, sample_df):
        """Test evaluating RSI function."""
        executor = DSLExecutor(sample_df)
        ast = parse_condition("rsi(14) > 0")
        # RSI should be calculable with 60 data points
        result = executor.evaluate(ast)
        assert isinstance(result, bool)

    def test_evaluate_sma_function(self, sample_df):
        """Test evaluating SMA function."""
        executor = DSLExecutor(sample_df)
        ast = parse_condition("sma(20) > 0")
        result = executor.evaluate(ast)
        assert result is True

    def test_evaluate_logical_and(self, sample_df):
        """Test evaluating AND condition."""
        executor = DSLExecutor(sample_df)
        ast = parse_condition("close > 100 AND volume > 500000")
        result = executor.evaluate(ast)
        assert result is True

    def test_evaluate_logical_or(self, sample_df):
        """Test evaluating OR condition."""
        executor = DSLExecutor(sample_df)
        ast = parse_condition("close < 50 OR close > 100")
        result = executor.evaluate(ast)
        assert result is True

    def test_evaluate_arithmetic(self, sample_df):
        """Test evaluating arithmetic expressions."""
        executor = DSLExecutor(sample_df)
        ast = parse_condition("close * 0.98 < high")
        result = executor.evaluate(ast)
        assert result is True


class TestDSLStrategy:
    """Tests for the DSL strategy."""

    @pytest.fixture
    def sample_definition(self):
        """Create a sample DSL strategy definition."""
        return {
            "name": "Test RSI Strategy",
            "description": "Buy when RSI is oversold",
            "version": 1,
            "rules": {
                "entry": [{"condition": "rsi(14) < 30", "action": "BUY", "confidence": 0.8}],
                "exit": {"stop_loss_pct": 2.0, "take_profit_pct": 4.0},
            },
        }

    @pytest.fixture
    def sample_df(self):
        """Create sample OHLCV data with RSI < 30 condition."""
        # Create data where price drops to trigger oversold RSI
        prices = [100.0] * 20
        for i in range(30):
            prices.append(prices[-1] * 0.99)  # 1% drop each period
        return pd.DataFrame(
            {
                "Open": prices,
                "High": [p * 1.01 for p in prices],
                "Low": [p * 0.99 for p in prices],
                "Close": prices,
                "Volume": [1000000] * len(prices),
            }
        )

    def test_create_dsl_strategy(self, sample_definition):
        """Test creating a DSL strategy."""
        strategy = create_dsl_strategy(sample_definition)
        assert strategy is not None
        assert isinstance(strategy, DSLStrategy)

    def test_get_parameters(self, sample_definition):
        """Test getting strategy parameters."""
        strategy = create_dsl_strategy(sample_definition)
        params = strategy.get_parameters()
        assert "name" in params
        assert params["name"] == "Test RSI Strategy"
        assert "entry_rules_count" in params
        assert params["entry_rules_count"] == 1

    def test_generate_signals_returns_list(self, sample_definition, sample_df):
        """Test that generate_signals returns a list."""
        strategy = create_dsl_strategy(sample_definition)
        signals = strategy.generate_signals(sample_df, "TESTSTOCK")
        assert isinstance(signals, list)
