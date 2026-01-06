# Portfolio Shared Package

Shared code for the Portfolio Management System, used by both the backend and trading-engine services.

## Structure

```
shared/
├── providers/          # Provider abstractions
│   ├── broker/        # Broker providers (paper, angelone, etc.)
│   ├── data/          # Data providers (yahoo, nse, etc.)
│   ├── schemas.py     # Common schemas (Order, Quote, OHLCV, etc.)
│   └── symbols.py     # Symbol utilities
├── strategies/         # Trading strategies
│   ├── indicators/    # RSI, MACD, MA, Bollinger
│   ├── intraday/      # VWAP, ORB, Gap-Go, TWAP
│   ├── swing/         # Price Action Volume
│   ├── base.py        # BaseStrategy abstract class
│   ├── registry.py    # StrategyRegistry
│   ├── composite.py   # CompositeStrategy
│   └── prebuilt.py    # Pre-built strategy configs
├── models/            # Shared data models
│   └── signals.py     # SignalData, SignalType
├── core/              # Core utilities
├── utils/             # Common helper functions
└── tests/             # Test suite
```

## Installation

Add to your service's `pyproject.toml`:

```toml
dependencies = [
    "portfolio-shared @ file:///${PROJECT_ROOT}/../shared",
]
```

## Usage

### Providers

```python
from shared.providers import Exchange, OrderSide, Quote
from shared.providers.broker import get_broker, PaperBroker
from shared.providers.data import get_data_provider

# Get a broker instance
broker = get_broker("paper")

# Get a data provider instance
data_provider = get_data_provider("yahoo")
```

### Strategies

```python
from shared.strategies import StrategyRegistry, BaseStrategy
from shared.strategies.indicators import RSIStrategy, MACDStrategy
from shared.strategies.intraday import VWAPReversionStrategy

# Register strategies
registry = StrategyRegistry()
registry.register("rsi", RSIStrategy)

# Get a strategy instance
strategy = registry.get("rsi", period=14, overbought=70, oversold=30)
```

### Models

```python
from shared.models import SignalData, SignalType

signal = SignalData(
    signal_type=SignalType.BUY,
    strength=0.8,
    confidence=0.75,
    price=100.0,
    stop_loss=95.0,
    take_profit=110.0,
)
```

## Development

### Install dependencies

```bash
cd shared
uv sync --all-extras
```

### Run tests

```bash
uv run pytest
```

### Run linting

```bash
uv run ruff check .
uv run ruff format .
```

## Contributing

1. All shared code should be service-agnostic
2. Use dependency injection for configuration
3. Write comprehensive tests
4. Update documentation

