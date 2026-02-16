"""Unit tests for trading strategies."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from app.modules.signals.strategies import (
    BollingerSqueezeStrategy,
    MACDCrossoverStrategy,
    MovingAverageCrossoverStrategy,
    RSIStrategy,
)


def create_price_data(
    prices: list[float],
    volumes: list[float] | None = None,
    start_date: datetime | None = None,
) -> pd.DataFrame:
    """Create a DataFrame with OHLCV data for testing.

    Uses capitalized column names to match ta library expectations.
    """
    if start_date is None:
        start_date = datetime.now(UTC) - timedelta(days=len(prices))

    if volumes is None:
        volumes = [1000000.0] * len(prices)

    dates = [start_date + timedelta(days=i) for i in range(len(prices))]

    # Create simple OHLCV data where close = price
    # Use capitalized column names for ta library
    data = {
        "Open": [p * 0.99 for p in prices],
        "High": [p * 1.01 for p in prices],
        "Low": [p * 0.98 for p in prices],
        "Close": prices,
        "Volume": volumes,
    }

    df = pd.DataFrame(data, index=pd.DatetimeIndex(dates))
    return df


class TestRSIStrategy:
    """Tests for RSI Strategy."""

    def test_strategy_name(self):
        """Test strategy name."""
        strategy = RSIStrategy()
        assert strategy.name == "rsi"

    def test_strategy_description(self):
        """Test strategy description."""
        strategy = RSIStrategy()
        assert "RSI" in strategy.description

    def test_get_parameters(self):
        """Test get_parameters returns expected keys."""
        strategy = RSIStrategy()
        params = strategy.get_parameters()
        assert "rsi_period" in params
        assert "oversold_threshold" in params
        assert "overbought_threshold" in params

    def test_signal_generation_with_sufficient_data(self):
        """Test signal generation with sufficient data."""
        strategy = RSIStrategy(rsi_period=14)

        # Create price data with enough points for RSI calculation
        prices = [100.0] * 20
        for i in range(10):
            prices.append(100.0 - i * 2)  # Decline
        for i in range(5):
            prices.append(82.0 + i * 2)  # Recovery

        df = create_price_data(prices)
        signals = strategy.generate_signals(df, "TEST")

        # Should return a list (may be empty or have signals)
        assert isinstance(signals, list)

    def test_insufficient_data_returns_empty(self):
        """Test that empty list is returned when there's insufficient data."""
        strategy = RSIStrategy(rsi_period=14)

        # Only 5 data points, need at least 14 for RSI
        prices = [100.0, 101.0, 102.0, 101.5, 102.5]
        df = create_price_data(prices)

        signals = strategy.generate_signals(df, "TEST")
        assert signals == []


class TestMACDStrategy:
    """Tests for MACD Crossover Strategy."""

    def test_strategy_name(self):
        """Test strategy name."""
        strategy = MACDCrossoverStrategy()
        assert strategy.name == "macd"

    def test_get_parameters(self):
        """Test get_parameters returns expected keys."""
        strategy = MACDCrossoverStrategy()
        params = strategy.get_parameters()
        assert "fast_period" in params
        assert "slow_period" in params
        assert "signal_period" in params

    def test_signal_generation_with_sufficient_data(self):
        """Test MACD signal generation with sufficient data."""
        strategy = MACDCrossoverStrategy()

        # Create trending price data with enough points
        prices = []
        for i in range(50):
            prices.append(100.0 + i * 0.5 + np.sin(i / 5) * 2)

        df = create_price_data(prices)
        signals = strategy.generate_signals(df, "TEST")

        # Should return a list
        assert isinstance(signals, list)

    def test_insufficient_data_returns_empty(self):
        """Test that empty list is returned when there's insufficient data."""
        strategy = MACDCrossoverStrategy()

        # Only 10 data points, need at least 26 for MACD
        prices = [100.0 + i for i in range(10)]
        df = create_price_data(prices)

        signals = strategy.generate_signals(df, "TEST")
        assert signals == []


class TestMovingAverageCrossoverStrategy:
    """Tests for Moving Average Crossover Strategy."""

    def test_strategy_name(self):
        """Test strategy name."""
        strategy = MovingAverageCrossoverStrategy()
        assert strategy.name == "ma_crossover"

    def test_get_parameters(self):
        """Test get_parameters returns expected keys."""
        strategy = MovingAverageCrossoverStrategy()
        params = strategy.get_parameters()
        assert "fast_period" in params
        assert "slow_period" in params
        assert "ma_type" in params

    def test_ema_mode(self):
        """Test EMA mode configuration."""
        strategy = MovingAverageCrossoverStrategy(ma_type="ema")
        params = strategy.get_parameters()
        assert params["ma_type"] == "ema"

    def test_signal_generation_uptrend(self):
        """Test signal generation on uptrend."""
        strategy = MovingAverageCrossoverStrategy(fast_period=5, slow_period=20)

        # Create data where fast MA will cross above slow MA
        prices = [100.0] * 30
        for i in range(20):
            prices.append(100.0 + i * 2)  # Strong uptrend

        df = create_price_data(prices)
        signals = strategy.generate_signals(df, "TEST")

        assert isinstance(signals, list)

    def test_signal_generation_downtrend(self):
        """Test signal generation on downtrend."""
        strategy = MovingAverageCrossoverStrategy(fast_period=5, slow_period=20)

        # Create data where fast MA will cross below slow MA
        prices = [100.0] * 30
        for i in range(20):
            prices.append(100.0 - i * 2)  # Strong downtrend

        df = create_price_data(prices)
        signals = strategy.generate_signals(df, "TEST")

        assert isinstance(signals, list)

    def test_insufficient_data_returns_empty(self):
        """Test that empty list is returned when there's insufficient data."""
        strategy = MovingAverageCrossoverStrategy(fast_period=10, slow_period=50)

        # Only 20 data points, need at least 50 for slow MA
        prices = [100.0 + i for i in range(20)]
        df = create_price_data(prices)

        signals = strategy.generate_signals(df, "TEST")
        assert signals == []


class TestBollingerSqueezeStrategy:
    """Tests for Bollinger Squeeze Strategy."""

    def test_strategy_name(self):
        """Test strategy name."""
        strategy = BollingerSqueezeStrategy()
        assert strategy.name == "bollinger"

    def test_get_parameters(self):
        """Test get_parameters returns expected keys."""
        strategy = BollingerSqueezeStrategy()
        params = strategy.get_parameters()
        assert "bb_period" in params
        assert "bb_std" in params
        assert "atr_period" in params

    def test_signal_generation_with_sufficient_data(self):
        """Test signal generation with sufficient data."""
        strategy = BollingerSqueezeStrategy(bb_period=20)

        # Create data with enough points
        prices = [100.0] * 30
        for i in range(30):
            prices.append(100.0 + np.sin(i / 3) * 5)  # Oscillating prices

        df = create_price_data(prices)
        signals = strategy.generate_signals(df, "TEST")

        assert isinstance(signals, list)

    def test_insufficient_data_returns_empty(self):
        """Test that empty list is returned when there's insufficient data."""
        strategy = BollingerSqueezeStrategy(bb_period=20)

        # Only 10 data points, need at least 20 for BB
        prices = [100.0 + i for i in range(10)]
        df = create_price_data(prices)

        signals = strategy.generate_signals(df, "TEST")
        assert signals == []


class TestStrategyRegistry:
    """Tests for Strategy Registry."""

    def test_registry_has_strategies(self):
        """Test that registry contains all strategies."""
        from app.modules.signals.strategies import StrategyRegistry

        strategies = StrategyRegistry.list_strategies()
        assert len(strategies) >= 4

        names = [s["name"] for s in strategies]
        assert "rsi" in names
        assert "macd" in names
        assert "ma_crossover" in names
        assert "bollinger" in names

    def test_get_strategy_by_name(self):
        """Test getting strategy by name."""
        from app.modules.signals.strategies import StrategyRegistry

        strategy = StrategyRegistry.get("rsi")
        assert strategy is not None
        assert strategy.name == "rsi"

    def test_get_nonexistent_strategy(self):
        """Test getting non-existent strategy returns None."""
        from app.modules.signals.strategies import StrategyRegistry

        strategy = StrategyRegistry.get("NonExistent Strategy")
        assert strategy is None

    def test_get_all_strategies(self):
        """Test getting all strategy instances."""
        from app.modules.signals.strategies import StrategyRegistry

        strategies = StrategyRegistry.get_all()
        assert len(strategies) >= 4

        for strategy in strategies:
            assert hasattr(strategy, "generate_signals")
            assert hasattr(strategy, "name")
            assert hasattr(strategy, "description")

    def test_get_parameter_schema(self):
        """Test getting parameter schema for a strategy."""
        from app.modules.signals.strategies import StrategyRegistry

        schema = StrategyRegistry.get_parameter_schema("rsi")
        assert schema is not None
        assert isinstance(schema, list)
        assert len(schema) >= 1

        # Check that each parameter has required fields
        for param in schema:
            assert "name" in param
            assert "type" in param
            assert "default" in param
            assert "description" in param

        # Check that RSI-specific parameters are present
        param_names = [p["name"] for p in schema]
        assert "rsi_period" in param_names
        assert "oversold_threshold" in param_names
        assert "overbought_threshold" in param_names

    def test_get_parameter_schema_nonexistent(self):
        """Test getting parameter schema for non-existent strategy returns None."""
        from app.modules.signals.strategies import StrategyRegistry

        schema = StrategyRegistry.get_parameter_schema("nonexistent_strategy")
        assert schema is None

    def test_get_parameter_schema_type_inference(self):
        """Test that parameter types are correctly inferred."""
        from app.modules.signals.strategies import StrategyRegistry

        schema = StrategyRegistry.get_parameter_schema("rsi")
        assert schema is not None

        param_dict = {p["name"]: p for p in schema}

        # rsi_period should be an int
        assert param_dict["rsi_period"]["type"] == "int"
        assert isinstance(param_dict["rsi_period"]["default"], int)

        # atr_multiplier should be a float
        assert param_dict["atr_multiplier"]["type"] == "float"

    def test_get_parameter_schema_has_bounds(self):
        """Test that parameter schemas include min/max bounds."""
        from app.modules.signals.strategies import StrategyRegistry

        schema = StrategyRegistry.get_parameter_schema("macd")
        assert schema is not None

        for param in schema:
            # Period parameters should have bounds
            if "period" in param["name"]:
                assert param["min_value"] is not None
                assert param["max_value"] is not None
                assert param["min_value"] <= param["max_value"]
