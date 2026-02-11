# Portfolio Management System - Interview Preparation Guide

## 🎯 Problem Statement

### What Problem Does This Solve?

**The Challenge**: As a personal investor interested in algorithmic trading in Indian markets (NSE/BSE), I faced several pain points:

1. **No Affordable Algo Trading Platforms**: Most algorithmic trading platforms are enterprise-focused with high subscription costs ($50-500+/month) not suitable for personal use
2. **Manual Trading Limitations**: Manually monitoring multiple stocks, analyzing technical indicators, and executing trades is time-consuming and error-prone
3. **Strategy Validation Gap**: No way to safely test trading strategies before risking real money
4. **Data Fragmentation**: Market data, portfolio tracking, and analysis tools are scattered across multiple platforms
5. **Indian Market Focus**: Limited tools specifically designed for NSE/BSE with proper understanding of trading hours, settlement cycles (T+1), and regulatory requirements

### The Solution

A **personal algorithmic trading platform** that:
- **Automates strategy execution** with configurable trading algorithms (RSI, MACD, VWAP, ORB, etc.)
- **Paper trading first** - validate strategies risk-free before going live
- **Unified platform** - portfolio tracking, analysis, screener, signals, and execution in one place
- **Indian market optimized** - NSE/BSE focus with proper market hours awareness
- **Cost-effective** - runs on a $5-10/month VPS or local machine

---

## 🏗️ System Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Docker Compose                             │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐  ┌──────────┐   │
│  │ Frontend │  │ Backend  │  │ Trading Engine │  │  Worker  │   │
│  │ (Next.js)│  │(FastAPI) │  │   (FastAPI)    │  │ (Celery) │   │
│  │  :3000   │  │  :8010   │  │     :8001      │  │          │   │
│  └──────────┘  └──────────┘  └────────────────┘  └──────────┘   │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     Shared Package                          │  │
│  │        (Mounted into backend, trading-engine, worker)       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐  │
│  │  PostgreSQL + TimescaleDB│  │           Redis              │  │
│  │         :5432            │  │           :6379              │  │
│  └──────────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14, React 18, Tailwind CSS | Modern SSR, App Router, excellent DX |
| **UI Components** | shadcn/ui | Accessible, customizable, professional look |
| **Charts** | TradingView Lightweight Charts | Industry-standard financial charts |
| **Backend API** | Python 3.13 + FastAPI | Async, fast, type-safe, excellent for data |
| **Trading Engine** | Python 3.13 + FastAPI | Isolated execution, independent scaling |
| **Task Queue** | Celery + Redis | Scheduled strategy execution |
| **Database** | PostgreSQL + TimescaleDB | Relational + time-series in one DB |
| **Cache** | Redis | Caching, pub/sub, kill switch state |
| **Package Manager** | uv | 10-100x faster than pip |

### Service Responsibilities

| Service | Responsibility |
|---------|----------------|
| **Frontend** | User interface, dashboard, charts, trading console |
| **Backend API** | User auth, portfolio CRUD, order placement, algo config |
| **Trading Engine** | Strategy execution, signal generation, risk management |
| **Worker** | Scheduled tasks (strategy runs, data sync, instrument updates) |
| **Shared Package** | Strategies, broker/data providers, common models |

### Why This Architecture?

1. **Separation of Concerns**: Trading engine isolation prevents CPU-intensive strategy execution from affecting user-facing API
2. **Shared Package Pattern**: Eliminates code duplication (~40% code reuse), ensures consistency across services
3. **Provider Abstraction**: Switch from paper trading to live trading via config change (Strategy Pattern)
4. **Fault Isolation**: Trading engine crashes don't affect portfolio viewing/management

---

## 📊 Key Design Decisions

### 1. Provider Abstraction Pattern

All external integrations use abstract base classes:

```python
# Broker abstraction - switch paper/live via config
class BaseBroker(ABC):
    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult: ...
    
# Data provider abstraction
class BaseDataProvider(ABC):
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote: ...
```

**Benefits**:
- Paper trading → Live trading = config change
- Easy to add new brokers (Zerodha, Dhan)
- Testable - mock providers for unit tests

### 2. Strategy Registry Pattern

All trading strategies register with a central registry:

```python
registry = StrategyRegistry()
registry.register("rsi", RSIStrategy)
registry.register("macd", MACDStrategy)
registry.register("vwap_momentum", VWAPMomentumStrategy)

# Runtime strategy loading
strategy = registry.get_strategy("vwap_momentum", params={...})
```

**Benefits**:
- Dynamic strategy loading from database config
- Strategy versioning and A/B testing
- Easy to add new strategies without code changes

### 3. Composite Strategy Pattern

Combine multiple strategies with weighted voting:

```python
composite = CompositeStrategy(
    strategies=[RSIStrategy(), MACDStrategy(), VWAPMomentumStrategy()],
    weights=[0.4, 0.3, 0.3],
    min_agreement=0.5  # At least 50% agreement required
)
```

**Benefits**:
- More robust signals (multiple indicator confirmation)
- Configurable weights based on market conditions
- Reduces false signals from single-indicator strategies

---

## 🔧 Key Features Implemented

### Core Trading Features
- **10+ Trading Strategies**: RSI, MACD, Bollinger Bands, MA Crossover, VWAP, ORB, Gap & Go, TWAP
- **Paper Trading Engine**: Simulated execution with realistic slippage and fees
- **Position Management**: FIFO cost tracking, delivery vs intraday positions
- **Funds Management**: Virtual cash, margin tracking, realized/unrealized P&L

### Risk Management
- **Kill Switch**: Emergency stop all trading with one click
- **Circuit Breakers**: Auto-disable strategy on max daily loss
- **Position Limits**: Max position size, sector concentration limits
- **Rate Limiting**: Max orders per minute/day

### Stock Screener
- **Preset Screeners**: Momentum, Breakout, Consolidation, Pullback, Sector
- **Smart Strategy Inference**: Automatically suggest optimal strategy based on screener filters
- **Daily Recommendations**: Scheduled screener runs with top picks
- **Performance Tracking**: Track recommendation accuracy over time

### User Interface
- **Dashboard**: Portfolio summary, P&L, top movers, market overview
- **Analysis Page**: TradingView charts with technical indicators
- **Algo Trading Console**: Strategy management, execution history, safety controls
- **Multi-Chart View**: Monitor multiple instruments simultaneously

---

## 🐛 Challenges & Issues Faced

### Challenge 1: Database Transaction Locking

**Problem**: Dashboard loading was extremely slow (9-22 seconds) due to database transactions being held open during external API calls.

**Symptom**: PostgreSQL showed "idle in transaction" sessions for extended periods.

**Root Cause**: When fetching P&L data, we were:
1. Opening a DB transaction
2. Fetching positions from DB
3. Calling Yahoo Finance API for current prices (slow!)
4. Computing P&L
5. Closing transaction

The external API call was inside the transaction, holding locks for seconds.

**Solution** (Commit `8dcbe23`):
```python
# Before: External API call inside transaction
async def get_pnl_summary(db: AsyncSession):
    positions = await db.execute(query)
    prices = await yahoo.get_prices(symbols)  # Slow! Holds transaction
    return compute_pnl(positions, prices)

# After: Release transaction before external calls
async def get_pnl_summary(db: AsyncSession):
    positions = await db.execute(query)
    await db.commit()  # Release transaction FIRST
    prices = await asyncio.gather(*[get_price(s) for s in symbols])  # Parallel
    return compute_pnl(positions, prices)
```

**Learning**: Always release DB transactions before making external API calls.

---

### Challenge 2: Margin Double-Counting Bug

**Problem**: Short selling in paper trading was incorrectly handling funds.

**Symptom**:
- Opening a short position was crediting sale proceeds immediately (wrong!)
- Closing short wasn't releasing margin correctly

**Root Cause**: INTRADAY short selling has different fund flow than delivery trading:
- Short selling: Block margin only, don't credit proceeds until close
- Long buying: Debit full amount

**Solution** (Commit `fb478f1`):
```python
# Fixed fund handling for short positions
if order.side == OrderSide.SELL and not existing_position:
    # Opening short - block margin, don't credit proceeds
    margin_required = order.quantity * price * margin_factor
    funds.blocked_margin += margin_required
else:
    # Normal sell - credit proceeds
    funds.cash_balance += order.quantity * price
```

**Learning**: Financial calculations require careful attention to edge cases. Paper trading must accurately model real broker behavior.

---

### Challenge 3: Strategy Parameters Pollution

**Problem**: Creating strategies from screener was failing with unexpected parameter errors.

**Symptom**:
```
TypeError: VWAPMomentumStrategy.__init__() got an unexpected keyword argument 'source'
```

**Root Cause**: When creating strategies from the screener, metadata (`source`, `filters_used`, `product_type`) was being stored alongside actual strategy parameters. When instantiating the strategy, all parameters were passed to `__init__`.

**Solution** (Commit `246e005`):
```python
def get_strategy(self, strategy_type: str, params: dict):
    strategy_class = self._strategies[strategy_type]

    # Filter out metadata keys
    metadata_keys = {'source', 'filters_used', 'product_type', 'initial_symbols'}
    clean_params = {k: v for k, v in params.items() if k not in metadata_keys}

    # Use inspect to only pass valid parameters
    sig = inspect.signature(strategy_class.__init__)
    valid_params = {k: v for k, v in clean_params.items() if k in sig.parameters}

    return strategy_class(**valid_params)
```

**Learning**: Separate metadata from domain parameters. Use reflection for defensive programming.

---

### Challenge 4: Type Serialization Issues

**Problem**: Multiple JSON serialization failures with Decimal and NumPy types.

**Symptoms**:
- `TypeError: Object of type Decimal is not JSON serializable`
- `TypeError: Object of type float64 is not JSON serializable`

**Root Cause**:
1. SQLAlchemy returns `Decimal` types for numeric columns
2. pandas/numpy return `float64`, `int64` types
3. FastAPI's JSON encoder doesn't handle these by default

**Solutions**:
```python
# For Pydantic schemas - use mode='json'
data = model.model_dump(mode='json')  # Converts Decimal → float

# For NumPy types in signal generation
def sanitize_for_json(data: dict) -> dict:
    for key, value in data.items():
        if isinstance(value, (np.integer, np.floating)):
            data[key] = float(value)
    return data
```

**Learning**: Be explicit about serialization boundaries. Create utility functions for type conversion.

---

### Challenge 5: Architecture Over-Engineering (Initial Design)

**Problem**: Initial architecture was designed for enterprise scale (11 microservices, Kubernetes, Kafka) but the project is personal use.

**Impact**:
- Estimated $745/month infrastructure cost
- Months of additional development time
- Operational complexity requiring DevOps expertise

**Solution**: Simplified to practical architecture:
| Aspect | Original v1 | Revised v2 |
|--------|-------------|------------|
| Deployment | Kubernetes | Docker Compose |
| Services | 11 microservices | 5 containers |
| Databases | 3 engines | PostgreSQL only |
| Message Queue | Kafka | Redis |
| Monthly Cost | ~$745 | ~$10-20 |

**Learning**: "The best architecture is the simplest one that solves the problem." Start simple, extract services only when proven necessary.

---

## 📈 Project Statistics

| Metric | Value |
|--------|-------|
| **Total Commits** | 315 |
| **Lines of Code** | ~25,000+ |
| **Trading Strategies** | 10+ |
| **API Endpoints** | 50+ |
| **Services** | 5 containers |
| **Test Coverage** | Unit + Integration tests |

---

## 🚀 Future Enhancements

1. **Live Broker Integration** - AngelOne, Zerodha APIs
2. **Backtesting Engine** - Validate strategies on historical data
3. **Notification System** - Email, WhatsApp alerts for signals
4. **Mobile App** - React Native or PWA
5. **ML Integration** - Anomaly detection, trend prediction

---

## 💬 Common Interview Questions

### Q: Why did you choose FastAPI over Django/Flask?

FastAPI provides:
- **Async support** out of the box (crucial for I/O-bound trading operations)
- **Automatic OpenAPI docs** (reduces documentation effort)
- **Pydantic validation** (type-safe request/response handling)
- **Performance** (one of the fastest Python frameworks)

### Q: Why separate Trading Engine from Backend API?

1. **Fault isolation** - Strategy execution crashes don't affect user-facing API
2. **Independent scaling** - Can scale execution capacity separately
3. **Different performance profiles** - API is I/O-bound, engine is CPU-bound
4. **Independent deployment** - Update strategies without affecting portfolio management

### Q: How do you handle market data reliability?

- **Primary/Fallback pattern** - Yahoo Finance primary, NSE as fallback
- **Caching** - Redis cache with TTL for frequently accessed quotes
- **Rate limiting** - Respect API limits to avoid blocks
- **Graceful degradation** - Stale data warnings instead of failures

### Q: How would you scale this for 1000+ users?

1. **Database** - Read replicas for queries, write to primary
2. **Trading Engine** - Horizontal scaling with load balancer
3. **Caching** - Redis cluster for distributed caching
4. **Queue** - Redis Cluster or migrate to Kafka
5. **Infrastructure** - Move to Kubernetes for orchestration

### Q: What's your testing strategy?

- **Unit tests** - Individual strategy, provider, service testing
- **Integration tests** - API endpoint testing with test database
- **Paper trading validation** - Run strategies in simulation mode
- **Gradual rollout** - Enable strategies for subset of symbols first

---

## 📚 Quick Reference Links

- **TODO/Roadmap**: [docs/TODO.md](./TODO.md) - Full project plan with phases
- **System Design**: [docs/SYSTEM_DESIGN.md](./SYSTEM_DESIGN.md) - Technical architecture
- **Architecture v2**: [docs/ARCHITECTURE_v2.md](./ARCHITECTURE_v2.md) - Current simplified architecture
- **Design Review**: [docs/DESIGN_REVIEW.md](./DESIGN_REVIEW.md) - Architecture critique and lessons learned
- **Trading Engine**: [docs/trading-engine-design.md](./trading-engine-design.md) - Engine separation rationale
