"""
Pytest configuration and fixtures for shared package tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """Generate sample OHLCV data for testing strategies."""
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    
    # Generate realistic price data
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * np.cumprod(1 + returns)
    
    data = pd.DataFrame({
        "open": prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
        "high": prices * (1 + np.random.uniform(0, 0.02, 100)),
        "low": prices * (1 - np.random.uniform(0, 0.02, 100)),
        "close": prices,
        "volume": np.random.randint(100000, 1000000, 100),
    }, index=dates)
    
    # Ensure high >= open, close, low and low <= open, close, high
    data["high"] = data[["open", "high", "close"]].max(axis=1)
    data["low"] = data[["open", "low", "close"]].min(axis=1)
    
    return data


@pytest.fixture
def sample_intraday_data() -> pd.DataFrame:
    """Generate sample intraday OHLCV data for testing intraday strategies."""
    np.random.seed(42)
    # Generate 5-minute bars for a trading day (9:15 AM to 3:30 PM = 75 bars)
    start_time = datetime(2024, 1, 15, 9, 15)
    dates = [start_time + timedelta(minutes=5*i) for i in range(75)]
    
    base_price = 100.0
    returns = np.random.normal(0.0001, 0.005, 75)
    prices = base_price * np.cumprod(1 + returns)
    
    data = pd.DataFrame({
        "open": prices * (1 + np.random.uniform(-0.002, 0.002, 75)),
        "high": prices * (1 + np.random.uniform(0, 0.005, 75)),
        "low": prices * (1 - np.random.uniform(0, 0.005, 75)),
        "close": prices,
        "volume": np.random.randint(10000, 100000, 75),
    }, index=pd.DatetimeIndex(dates))
    
    data["high"] = data[["open", "high", "close"]].max(axis=1)
    data["low"] = data[["open", "low", "close"]].min(axis=1)
    
    return data


@pytest.fixture
def bullish_data() -> pd.DataFrame:
    """Generate bullish trending data for testing."""
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
    
    # Strong uptrend
    base_price = 100.0
    trend = np.linspace(0, 0.5, 50)  # 50% gain
    noise = np.random.normal(0, 0.01, 50)
    prices = base_price * (1 + trend + noise)
    
    data = pd.DataFrame({
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(100000, 1000000, 50),
    }, index=dates)
    
    return data


@pytest.fixture
def bearish_data() -> pd.DataFrame:
    """Generate bearish trending data for testing."""
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
    
    # Strong downtrend
    base_price = 100.0
    trend = np.linspace(0, -0.3, 50)  # 30% loss
    noise = np.random.normal(0, 0.01, 50)
    prices = base_price * (1 + trend + noise)
    
    data = pd.DataFrame({
        "open": prices * 1.01,
        "high": prices * 1.02,
        "low": prices * 0.99,
        "close": prices,
        "volume": np.random.randint(100000, 1000000, 50),
    }, index=dates)
    
    return data

