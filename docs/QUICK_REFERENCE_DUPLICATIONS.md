# Quick Reference: Duplicate Files Mapping

This document provides a quick lookup table for finding duplicate files between backend and trading-engine.

## Provider Layer

### Broker Providers

| Component | Backend Location | Trading-Engine Location | Destination |
|-----------|-----------------|------------------------|-------------|
| Broker Base | `app/providers/broker/base.py` | `engine/providers/broker/base.py` | `shared/providers/broker/base.py` |
| Broker Factory | `app/providers/broker/factory.py` | `engine/providers/broker/factory.py` | `shared/providers/broker/factory.py` |
| Paper Broker | `app/providers/broker/paper.py` | `engine/providers/broker/paper.py` | `shared/providers/broker/paper.py` |

### Data Providers

| Component | Backend Location | Trading-Engine Location | Destination |
|-----------|-----------------|------------------------|-------------|
| Data Provider Base | `app/providers/data/base.py` | `engine/providers/data/base.py` | `shared/providers/data/base.py` |
| Data Provider Factory | `app/providers/data/factory.py` | `engine/providers/data/factory.py` | `shared/providers/data/factory.py` |
| Yahoo Provider | `app/providers/data/yahoo.py` | `engine/providers/data/yahoo.py` | `shared/providers/data/yahoo.py` |
| NSE Provider | `app/providers/data/nse.py` | ❌ Not in engine | `shared/providers/data/nse.py` |
| Rate Limiter | `app/providers/data/rate_limiter.py` | ❌ Not in engine | `shared/providers/data/rate_limiter.py` |

### Provider Utilities

| Component | Backend Location | Trading-Engine Location | Destination |
|-----------|-----------------|------------------------|-------------|
| Schemas | `app/providers/schemas.py` | `engine/providers/schemas.py` | `shared/providers/schemas.py` |
| Symbols | `app/providers/symbols.py` | `engine/providers/symbols.py` | `shared/providers/symbols.py` |

## Strategy Layer

### Base Infrastructure

| Component | Backend Location | Trading-Engine Location | Destination |
|-----------|-----------------|------------------------|-------------|
| Base Strategy | `app/modules/signals/strategies/base.py` | `engine/strategies/base.py` | `shared/strategies/base.py` |
| Registry | `app/modules/signals/strategies/registry.py` | `engine/strategies/registry.py` | `shared/strategies/registry.py` |
| Composite | `app/modules/signals/strategies/composite.py` | `engine/strategies/composite.py` | `shared/strategies/composite.py` |
| Prebuilt | `app/modules/signals/strategies/prebuilt.py` | `engine/strategies/prebuilt.py` | `shared/strategies/prebuilt.py` |

### Indicator Strategies

| Strategy | Backend Location | Trading-Engine Location | Destination |
|----------|-----------------|------------------------|-------------|
| RSI | `strategies/rsi.py` | `strategies/rsi.py` | `shared/strategies/indicators/rsi.py` |
| MACD | `strategies/macd.py` | `strategies/macd.py` | `shared/strategies/indicators/macd.py` |
| Moving Average | `strategies/moving_average.py` | `strategies/moving_average.py` | `shared/strategies/indicators/moving_average.py` |
| Bollinger Bands | `strategies/bollinger.py` | `strategies/bollinger.py` | `shared/strategies/indicators/bollinger.py` |

### Intraday Strategies

| Strategy | Backend Location | Trading-Engine Location | Destination |
|----------|-----------------|------------------------|-------------|
| VWAP Reversion | `strategies/vwap.py` | `strategies/vwap.py` | `shared/strategies/intraday/vwap.py` |
| VWAP Momentum | `strategies/vwap_momentum.py` | `strategies/vwap_momentum.py` | `shared/strategies/intraday/vwap_momentum.py` |
| ORB | `strategies/orb.py` | `strategies/orb.py` | `shared/strategies/intraday/orb.py` |
| Gap and Go | `strategies/gap_go.py` | `strategies/gap_go.py` | `shared/strategies/intraday/gap_go.py` |
| TWAP | `strategies/twap.py` | `strategies/twap.py` | `shared/strategies/intraday/twap.py` |

### Swing Strategies

| Strategy | Backend Location | Trading-Engine Location | Destination |
|----------|-----------------|------------------------|-------------|
| Price Action Volume | `strategies/price_action_volume_swing.py` | `strategies/price_action_volume_swing.py` | `shared/strategies/swing/price_action_volume_swing.py` |

## Models

| Component | Backend Location | Trading-Engine Location | Destination |
|-----------|-----------------|------------------------|-------------|
| Signal Models | `app/modules/signals/models.py` | `engine/models/signals.py` | `shared/models/signals.py` |

## Import Changes

### Backend Import Changes

**Before:**
```python
from app.providers.broker.factory import get_broker
from app.providers.data.factory import get_data_provider
from app.providers.schemas import OrderRequest, OrderSide
from app.providers.symbols import Exchange, SymbolMapper
from app.modules.signals.strategies.registry import StrategyRegistry
from app.modules.signals.strategies.rsi import RSIStrategy
from app.modules.signals.models import SignalData, SignalType
```

**After:**
```python
from shared.providers.broker.factory import get_broker
from shared.providers.data.factory import get_data_provider
from shared.providers.schemas import OrderRequest, OrderSide
from shared.providers.symbols import Exchange, SymbolMapper
from shared.strategies.registry import StrategyRegistry
from shared.strategies.indicators.rsi import RSIStrategy
from shared.models.signals import SignalData, SignalType
```

### Trading-Engine Import Changes

**Before:**
```python
from engine.providers.broker.factory import get_broker
from engine.providers.data.factory import get_data_provider
from engine.providers.schemas import OrderRequest, OrderSide
from engine.providers.symbols import Exchange, SymbolMapper
from engine.strategies.registry import StrategyRegistry
from engine.strategies.rsi import RSIStrategy
from engine.models.signals import SignalData, SignalType
```

**After:**
```python
from shared.providers.broker.factory import get_broker
from shared.providers.data.factory import get_data_provider
from shared.providers.schemas import OrderRequest, OrderSide
from shared.providers.symbols import Exchange, SymbolMapper
from shared.strategies.registry import StrategyRegistry
from shared.strategies.indicators.rsi import RSIStrategy
from shared.models.signals import SignalData, SignalType
```

## Files to Delete After Migration

### Backend Files to Delete

```bash
# Provider layer
rm -rf backend/app/providers/broker/base.py
rm -rf backend/app/providers/broker/factory.py
rm -rf backend/app/providers/broker/paper.py
rm -rf backend/app/providers/data/base.py
rm -rf backend/app/providers/data/factory.py
rm -rf backend/app/providers/data/yahoo.py
rm -rf backend/app/providers/data/nse.py
rm -rf backend/app/providers/data/rate_limiter.py
rm -rf backend/app/providers/schemas.py
rm -rf backend/app/providers/symbols.py

# Strategy layer
rm -rf backend/app/modules/signals/strategies/base.py
rm -rf backend/app/modules/signals/strategies/registry.py
rm -rf backend/app/modules/signals/strategies/composite.py
rm -rf backend/app/modules/signals/strategies/prebuilt.py
rm -rf backend/app/modules/signals/strategies/rsi.py
rm -rf backend/app/modules/signals/strategies/macd.py
rm -rf backend/app/modules/signals/strategies/moving_average.py
rm -rf backend/app/modules/signals/strategies/bollinger.py
rm -rf backend/app/modules/signals/strategies/vwap.py
rm -rf backend/app/modules/signals/strategies/vwap_momentum.py
rm -rf backend/app/modules/signals/strategies/orb.py
rm -rf backend/app/modules/signals/strategies/gap_go.py
rm -rf backend/app/modules/signals/strategies/twap.py
rm -rf backend/app/modules/signals/strategies/price_action_volume_swing.py
```

### Trading-Engine Files to Delete

```bash
# Provider layer
rm -rf trading-engine/engine/providers/broker/base.py
rm -rf trading-engine/engine/providers/broker/factory.py
rm -rf trading-engine/engine/providers/broker/paper.py
rm -rf trading-engine/engine/providers/data/base.py
rm -rf trading-engine/engine/providers/data/factory.py
rm -rf trading-engine/engine/providers/data/yahoo.py
rm -rf trading-engine/engine/providers/schemas.py
rm -rf trading-engine/engine/providers/symbols.py

# Strategy layer
rm -rf trading-engine/engine/strategies/base.py
rm -rf trading-engine/engine/strategies/registry.py
rm -rf trading-engine/engine/strategies/composite.py
rm -rf trading-engine/engine/strategies/prebuilt.py
rm -rf trading-engine/engine/strategies/rsi.py
rm -rf trading-engine/engine/strategies/macd.py
rm -rf trading-engine/engine/strategies/moving_average.py
rm -rf trading-engine/engine/strategies/bollinger.py
rm -rf trading-engine/engine/strategies/vwap.py
rm -rf trading-engine/engine/strategies/vwap_momentum.py
rm -rf trading-engine/engine/strategies/orb.py
rm -rf trading-engine/engine/strategies/gap_go.py
rm -rf trading-engine/engine/strategies/twap.py
rm -rf trading-engine/engine/strategies/price_action_volume_swing.py

# Models
rm -rf trading-engine/engine/models/signals.py
```

## Search & Replace Patterns

Use these patterns for bulk import updates:

### Backend

```bash
# In backend/ directory
find . -type f -name "*.py" -exec sed -i '' 's/from app\.providers/from shared.providers/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from app\.modules\.signals\.strategies/from shared.strategies/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from app\.modules\.signals\.models/from shared.models.signals/g' {} +
```

### Trading-Engine

```bash
# In trading-engine/ directory
find . -type f -name "*.py" -exec sed -i '' 's/from engine\.providers/from shared.providers/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from engine\.strategies/from shared.strategies/g' {} +
find . -type f -name "*.py" -exec sed -i '' 's/from engine\.models\.signals/from shared.models.signals/g' {} +
```

**⚠️ Warning:** Always review changes after bulk find/replace operations!


