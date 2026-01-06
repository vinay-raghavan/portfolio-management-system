# Detailed File-by-File Duplication Comparison

## Provider Layer Duplications

### Broker Providers

| File | Backend Path | Trading-Engine Path | Similarity | Lines | Notes |
|------|-------------|---------------------|------------|-------|-------|
| **base.py** | `app/providers/broker/base.py` | `engine/providers/broker/base.py` | 100% | ~185 | Identical abstract base class |
| **factory.py** | `app/providers/broker/factory.py` | `engine/providers/broker/factory.py` | 100% | ~80 | Identical factory pattern |
| **paper.py** | `app/providers/broker/paper.py` | `engine/providers/broker/paper.py` | 98% | ~550 | Minor import path differences |

**Key Duplicated Classes:**
- `Broker` (abstract base class)
- `BrokerFactory` (factory with registry)
- `PaperBroker` (in-memory paper trading implementation)

**Key Duplicated Methods:**
- `connect()`, `disconnect()`, `is_connected()`
- `place_order()`, `cancel_order()`, `modify_order()`
- `get_order_status()`, `get_positions()`, `get_funds()`
- `square_off_all()`

---

### Data Providers

| File | Backend Path | Trading-Engine Path | Similarity | Lines | Notes |
|------|-------------|---------------------|------------|-------|-------|
| **base.py** | `app/providers/data/base.py` | `engine/providers/data/base.py` | 100% | ~170 | Identical abstract base class |
| **factory.py** | `app/providers/data/factory.py` | `engine/providers/data/factory.py` | 95% | ~90 | Backend has NSE, engine doesn't |
| **yahoo.py** | `app/providers/data/yahoo.py` | `engine/providers/data/yahoo.py` | 100% | ~350 | Identical Yahoo Finance implementation |
| **nse.py** | `app/providers/data/nse.py` | ❌ Not in engine | N/A | ~600 | Backend only |
| **rate_limiter.py** | `app/providers/data/rate_limiter.py` | ❌ Not in engine | N/A | ~80 | Backend only |

**Key Duplicated Classes:**
- `DataProvider` (abstract base class)
- `DataProviderFactory` (factory with registry)
- `YahooDataProvider` (Yahoo Finance implementation)

**Key Duplicated Methods:**
- `get_quote()`, `get_historical()`, `search_symbols()`
- `get_instrument_info()`, `get_current_price()`
- `is_market_open()`, `get_market_session()`
- `get_effective_price()`, `normalize_symbol()`

---

### Provider Schemas

| File | Backend Path | Trading-Engine Path | Similarity | Lines | Notes |
|------|-------------|---------------------|------------|-------|-------|
| **schemas.py** | `app/providers/schemas.py` | `engine/providers/schemas.py` | 95% | ~183 | Minor enum differences |
| **symbols.py** | `app/providers/symbols.py` | `engine/providers/symbols.py` | 100% | ~139 | Identical symbol utilities |

**Duplicated Enums:**
- `OrderSide` (BUY, SELL) - 100% identical
- `OrderType` (MARKET, LIMIT, SL, SL-M, GTT) - 100% identical
- `OrderStatus` - Backend has `TRIGGERED`, engine doesn't
- `ProductType` - Minor differences in values
- `MarketSession` (PRE_MARKET, REGULAR, POST_MARKET, CLOSED) - 100% identical

**Duplicated Models:**
- `Quote` - 100% identical (with extended hours support)
- `OHLCV` - 100% identical
- `InstrumentInfo` - 100% identical
- `SearchResult` - 100% identical
- `OrderRequest` - 98% identical
- `OrderResponse` - 98% identical
- `Position` - 90% similar (different fields)
- `Funds` - 95% identical

**Duplicated Classes:**
- `Exchange` enum (NSE, BSE, NYSE, NASDAQ, NFO, BFO, MCX) - 100% identical
- `Segment` enum (EQUITY, FUTURES, OPTIONS, INDEX, COMMODITY, CURRENCY) - 100% identical
- `Symbol` class with conversion methods - 100% identical
- `SymbolMapper` utility class - 100% identical

---

## Strategy Layer Duplications

### Base Infrastructure

| File | Backend Path | Trading-Engine Path | Similarity | Lines | Notes |
|------|-------------|---------------------|------------|-------|-------|
| **base.py** | `app/modules/signals/strategies/base.py` | `engine/strategies/base.py` | 100% | ~150 | Identical abstract base |
| **registry.py** | `app/modules/signals/strategies/registry.py` | `engine/strategies/registry.py` | 100% | ~120 | Identical registry pattern |
| **composite.py** | `app/modules/signals/strategies/composite.py` | `engine/strategies/composite.py` | 100% | ~250 | Identical composite pattern |
| **prebuilt.py** | `app/modules/signals/strategies/prebuilt.py` | `engine/strategies/prebuilt.py` | 100% | ~250 | Identical pre-built configs |

**Key Duplicated Classes:**
- `BaseStrategy` (abstract base class)
- `StrategyRegistry` (singleton registry)
- `CompositeStrategy` (strategy combiner)
- `CombineLogic` enum (AND, OR, MAJORITY, WEIGHTED)
- `StrategyComponent` dataclass

**Key Duplicated Methods:**
- `generate_signals()` (abstract)
- `get_parameters()` (abstract)
- `calculate_stop_loss()`, `calculate_take_profit()`
- `calculate_position_size()`
- `_to_decimal()` helper

---

### Indicator Strategies

| Strategy | Backend Path | Trading-Engine Path | Similarity | Lines |
|----------|-------------|---------------------|------------|-------|
| **RSI** | `strategies/rsi.py` | `strategies/rsi.py` | 100% | ~180 |
| **MACD** | `strategies/macd.py` | `strategies/macd.py` | 100% | ~200 |
| **Moving Average** | `strategies/moving_average.py` | `strategies/moving_average.py` | 100% | ~180 |
| **Bollinger Bands** | `strategies/bollinger.py` | `strategies/bollinger.py` | 100% | ~250 |

All indicator strategies are **100% identical** including:
- Constructor parameters
- Signal generation logic
- Stop loss/take profit calculation
- Strength and confidence calculation
- Parameter validation

---

### Intraday Strategies

| Strategy | Backend Path | Trading-Engine Path | Similarity | Lines |
|----------|-------------|---------------------|------------|-------|
| **VWAP Reversion** | `strategies/vwap.py` | `strategies/vwap.py` | 100% | ~200 |
| **VWAP Momentum** | `strategies/vwap_momentum.py` | `strategies/vwap_momentum.py` | 100% | ~220 |
| **ORB** | `strategies/orb.py` | `strategies/orb.py` | 100% | ~180 |
| **Gap and Go** | `strategies/gap_go.py` | `strategies/gap_go.py` | 100% | ~200 |
| **TWAP** | `strategies/twap.py` | `strategies/twap.py` | 100% | ~150 |

All intraday strategies are **100% identical**.

---

### Swing Strategies

| Strategy | Backend Path | Trading-Engine Path | Similarity | Lines |
|----------|-------------|---------------------|------------|-------|
| **Price Action Volume Swing** | `strategies/price_action_volume_swing.py` | `strategies/price_action_volume_swing.py` | 100% | ~300 |

---

## Models Duplications

| Model | Backend Path | Trading-Engine Path | Similarity | Lines |
|-------|-------------|---------------------|------------|-------|
| **SignalData** | `app/modules/signals/models.py` | `engine/models/signals.py` | 100% | ~30 |
| **SignalType** | `app/modules/signals/models.py` | `engine/models/signals.py` | 100% | ~10 |

---

## Core Infrastructure Duplications

### Database

| Aspect | Backend | Trading-Engine | Similarity |
|--------|---------|----------------|------------|
| **Engine creation** | `create_async_engine()` | `create_async_engine()` | 100% |
| **Session factory** | `async_sessionmaker()` | `async_sessionmaker()` | 100% |
| **Base class** | `DeclarativeBase` | `DeclarativeBase` | 100% |
| **Pool settings** | `pool_size=10, max_overflow=20` | `pool_size=10, max_overflow=20` | 100% |
| **get_db()** | Dependency injection | Dependency injection | 90% |
| **Differences** | Has `autocommit=False` | Has `get_db_context()` and `check_db_health()` | - |

### Redis

| Aspect | Backend | Trading-Engine | Similarity |
|--------|---------|----------------|------------|
| **Connection** | Simple client | Connection pool | 50% |
| **get_redis()** | Returns client | Yields from pool | 60% |
| **Health check** | ❌ No | ✅ `check_redis_health()` | - |
| **Cleanup** | `close_redis()` | `close_redis_pool()` | 80% |

**Recommendation:** Use trading-engine's more robust connection pool pattern in shared package.

---

## Summary Statistics

### Total Duplication by Category

| Category | Files | Total Lines | Duplicated Lines | Duplication % |
|----------|-------|-------------|------------------|---------------|
| **Broker Providers** | 3 | 815 | 800 | 98% |
| **Data Providers** | 3 | 610 | 580 | 95% |
| **Provider Schemas** | 2 | 322 | 305 | 95% |
| **Strategy Base** | 4 | 770 | 770 | 100% |
| **Indicator Strategies** | 4 | 810 | 810 | 100% |
| **Intraday Strategies** | 5 | 950 | 950 | 100% |
| **Swing Strategies** | 1 | 300 | 300 | 100% |
| **Models** | 1 | 40 | 40 | 100% |
| **Core Utils** | 2 | 115 | 70 | 61% |
| **TOTAL** | **25** | **4732** | **4625** | **98%** |

### Files to Move to Shared

**High Priority (100% duplicate):**
1. All strategy files (14 files)
2. Provider base classes (2 files)
3. Provider schemas (2 files)
4. Broker implementations (3 files)
5. Yahoo data provider (1 file)

**Medium Priority (95%+ duplicate):**
6. Data provider factory (1 file)
7. Signal models (1 file)

**Low Priority (needs reconciliation):**
8. NSE data provider (backend only)
9. Rate limiter (backend only)
10. Database utilities (minor differences)
11. Redis utilities (different patterns)


