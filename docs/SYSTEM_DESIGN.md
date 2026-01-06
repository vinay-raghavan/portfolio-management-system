# Portfolio Management System - System Design Document

## 1. Overview

An automated personal financial portfolio management system for Indian markets (NSE/BSE) that performs comprehensive market analysis, executes algorithmic trading strategies (simulated or live), and maximizes returns through intelligent decision-making.

### 1.1 Key Objectives
- Indian market focus (NSE/BSE) with Yahoo Finance and NSE data providers
- Algorithmic trading with multiple strategy types (RSI, MACD, VWAP, ORB, etc.)
- Paper trading for strategy validation
- Risk management with kill switch and circuit breakers
- Modern, intuitive user interface

---

## 2. System Architecture

### 2.1 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14 + React 18 | SSR, App Router, excellent DX |
| **UI Components** | shadcn/ui + Tailwind CSS | Modern, accessible, customizable |
| **Charts** | TradingView Lightweight Charts | Professional financial charts |
| **Backend API** | Python 3.13 + FastAPI | User-facing API, portfolio management |
| **Trading Engine** | Python 3.13 + FastAPI | Strategy execution, order management |
| **Task Queue** | Celery + Redis | Scheduled strategy execution |
| **Database** | PostgreSQL + TimescaleDB | Time-series optimized for market data |
| **Cache** | Redis | Caching, pub/sub, kill switch state |
| **Package Manager** | uv | Fast Python package management |
| **Analysis** | pandas, numpy, ta-lib | Quantitative analysis |

### 2.2 Core Modules

```
portfolio-management-system/
├── frontend/                    # Next.js application
│   ├── src/app/                 # App router pages
│   ├── src/components/          # React components
│   └── src/lib/                 # Utilities & API clients
├── backend/                     # User-facing API (port 8010)
│   ├── app/api/                 # FastAPI routes
│   ├── app/modules/             # Business logic modules
│   │   ├── auth/                # Authentication
│   │   ├── portfolio/           # Portfolio management
│   │   ├── trading/             # Order placement
│   │   ├── algo/                # Algo strategy config
│   │   └── data/                # Market data
│   ├── app/models/              # Database models
│   └── app/providers/           # Re-exports from shared
├── trading-engine/              # Strategy execution (port 8001)
│   ├── engine/algo/             # Executor, scheduler, safety
│   ├── engine/routes/           # Internal API endpoints
│   ├── engine/strategies/       # Re-exports from shared
│   └── engine/providers/        # Re-exports from shared
├── shared/                      # Shared Python package
│   └── shared/
│       ├── providers/           # Broker & data providers
│       ├── strategies/          # Trading strategies
│       └── models/              # Common models
├── worker/                      # Celery background tasks
└── docker-compose.yml           # Container orchestration
```

---

## 3. Data Sources & Ingestion

### 3.1 Market Data Providers

| Provider | Data Type | Markets | Cost |
|----------|-----------|---------|------|
| **Yahoo Finance (yfinance)** | Prices, fundamentals | Global | Free |
| **NSE India API** | Indian market data | India | Free |

### 3.2 Data Categories

1. **Price Data**: OHLCV (Open, High, Low, Close, Volume)
2. **Technical Indicators**: RSI, MACD, Bollinger Bands, VWAP, etc.
3. **Fundamental Data**: Financial statements, ratios (future)

---

## 4. Trading Strategies

### 4.1 Strategy Architecture

All strategies inherit from `BaseStrategy` in the shared package:

```python
class BaseStrategy(ABC):
    @abstractmethod
    def generate_signal(self, symbol: str, data: pd.DataFrame) -> SignalData | None:
        """Generate trading signal from market data."""
        pass
```

### 4.2 Available Strategies

**Indicator-Based:**
- `RSIStrategy` - RSI oversold/overbought signals
- `MACDStrategy` - MACD crossover signals
- `BollingerBandsStrategy` - Bollinger band breakouts
- `MovingAverageCrossoverStrategy` - MA crossovers

**Intraday:**
- `VWAPReversionStrategy` - Mean reversion to VWAP
- `VWAPMomentumStrategy` - VWAP momentum breakouts
- `ORBStrategy` - Opening Range Breakout
- `GapAndGoStrategy` - Gap continuation
- `TWAPStrategy` - Time-weighted execution

**Swing:**
- `PriceActionVolumeSwingStrategy` - Multi-day price action

### 4.3 Composite Strategies

Combine multiple strategies with weighted voting:

```python
composite = CompositeStrategy(
    strategies=[RSIStrategy(), MACDStrategy()],
    weights=[0.6, 0.4],
    min_agreement=0.5
)
```

---

## 5. Trading Engine

### 5.1 Signal Generation

Strategies generate `SignalData` with:
- Signal type (BUY, SELL, HOLD)
- Confidence score (0.0 - 1.0)
- Entry price, stop loss, take profit
- Reason/explanation

### 5.2 Order Management

```python
@dataclass
class Order:
    symbol: str
    side: OrderSide  # BUY, SELL
    order_type: OrderType  # MARKET, LIMIT, STOP_LOSS
    quantity: float
    price: float | None
```

### 5.3 Risk Management

- **Kill Switch**: Emergency stop all trading
- **Circuit Breakers**: Daily loss limits
- **Position Limits**: Max position size per symbol
- **Cooldown Periods**: Prevent overtrading

### 5.4 Paper Trading (PaperBroker)

Paper trading engine that:
- Simulates order execution with configurable slippage
- Tracks virtual portfolio performance
- Calculates realistic fees
- Provides performance analytics

---

## 6. Broker Providers

### 6.1 Provider Architecture

All brokers implement `BaseBroker`:

```python
class BaseBroker(ABC):
    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult: ...

    @abstractmethod
    async def get_positions(self) -> list[Position]: ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote: ...
```

### 6.2 Available Brokers

| Broker | Type | Status |
|--------|------|--------|
| `PaperBroker` | Simulation | ✅ Implemented |
| `AngelOneBroker` | Live | 🔄 Planned |
| `ZerodhaBroker` | Live | 🔄 Planned |

---

## 7. User Interface

### 7.1 Dashboard Views

1. **Portfolio Overview**
   - Total portfolio value, Daily/Weekly/Monthly P&L
   - Asset allocation, Top performers

2. **Algo Trading**
   - Strategy configuration
   - Active strategies, P&L tracking
   - Kill switch controls

3. **Trading Console**
   - Active signals, Order entry, Trade history

---

## 8. Database Schema (Core Tables)

```sql
-- Algo strategies
CREATE TABLE algo_strategies (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL,
    symbols TEXT[] NOT NULL,
    parameters JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT false
);

-- Algo trades
CREATE TABLE algo_trades (
    id UUID PRIMARY KEY,
    strategy_id UUID REFERENCES algo_strategies(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 4) NOT NULL,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Price data (TimescaleDB hypertable)
CREATE TABLE price_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DECIMAL, high DECIMAL, low DECIMAL, close DECIMAL,
    volume BIGINT
);
```

---

## 9. Key Dependencies

**Shared Package**: pydantic, pandas, numpy, ta-lib, yfinance
**Backend/Engine**: FastAPI, SQLAlchemy, httpx
**Worker**: Celery, Redis
**Frontend**: Next.js 14, React 18, TanStack Query, Tailwind, TradingView Charts

---

## 10. Deployment

- Docker Compose for container orchestration
- PostgreSQL + TimescaleDB for data persistence
- Redis for caching and Celery broker
- Hetzner VPS recommended (~€5-10/month)
