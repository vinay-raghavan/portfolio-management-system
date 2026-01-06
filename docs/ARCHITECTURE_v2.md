# Portfolio Management System - Architecture (v2)

## Overview

A containerized microservices architecture optimized for **personal algorithmic trading**. Uses Docker Compose for orchestration with a shared package pattern to eliminate code duplication across services.

---

## Architecture Comparison

| Aspect | Original (v1) | Current (v2) |
|--------|---------------|--------------|
| Deployment | Kubernetes | Docker Compose |
| Services | 11 microservices | 5 containers + shared package |
| Databases | PostgreSQL + MongoDB + TimescaleDB | PostgreSQL + TimescaleDB |
| Message Queue | Apache Kafka | Redis (Pub/Sub + Celery) |
| Code Sharing | Duplicated code | Shared Python package |
| Monthly Cost | ~$745 | ~$10-20 |
| Complexity | Very High | Medium |

---

## Container Architecture

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

### Container 1: Frontend (`web`)
- **Image**: Node.js 20 Alpine
- **Framework**: Next.js 14 with App Router
- **Port**: 3000
- **Features**: React UI, TradingView Charts, Algo trading dashboard

### Container 2: Backend API (`api`)
- **Image**: Python 3.13 Slim + uv
- **Framework**: FastAPI
- **Port**: 8010
- **Responsibilities**:
  - User authentication (JWT)
  - Portfolio management (positions, P&L)
  - Order placement
  - Algo strategy configuration
  - Market data API

### Container 3: Trading Engine (`trading-engine`)
- **Image**: Python 3.13 Slim + uv
- **Framework**: FastAPI
- **Port**: 8001
- **Responsibilities**:
  - Strategy execution
  - Signal generation
  - Order management via broker providers
  - Risk management (kill switch, circuit breakers)
  - Position tracking

### Container 4: Worker (`worker`)
- **Image**: Python 3.13 Slim + uv
- **Framework**: Celery
- **Responsibilities**:
  - Scheduled strategy execution (calls trading-engine)
  - Background data ingestion
  - Alert/notification processing

### Container 5: Database (`db`)
- **Image**: timescale/timescaledb:latest-pg15
- **Port**: 5432
- **Features**: PostgreSQL 15 + TimescaleDB for time-series

### Container 6: Cache (`redis`)
- **Image**: redis:7-alpine
- **Port**: 6379
- **Usage**: Caching, Celery broker, Kill switch state

---

## Shared Package Architecture

The `shared/` package is a Python library used by backend, trading-engine, and worker to eliminate code duplication.

### Package Structure

```
shared/
└── shared/
    ├── __init__.py
    ├── providers/              # External service integrations
    │   ├── broker/             # Broker implementations
    │   │   ├── base.py         # BaseBroker abstract class
    │   │   ├── paper.py        # PaperBroker (simulation)
    │   │   └── factory.py      # get_broker() factory
    │   ├── data/               # Data providers
    │   │   ├── base.py         # BaseDataProvider abstract class
    │   │   ├── yahoo.py        # YahooDataProvider
    │   │   ├── nse.py          # NSEDataProvider
    │   │   └── factory.py      # get_data_provider() factory
    │   ├── schemas.py          # Order, Quote, OHLCV schemas
    │   └── symbols.py          # Symbol utilities
    ├── strategies/             # Trading strategies
    │   ├── base.py             # BaseStrategy abstract class
    │   ├── registry.py         # StrategyRegistry
    │   ├── composite.py        # CompositeStrategy
    │   ├── prebuilt.py         # Pre-built strategy configs
    │   ├── indicators/         # Indicator-based strategies
    │   │   ├── rsi.py          # RSIStrategy
    │   │   ├── macd.py         # MACDStrategy
    │   │   ├── bollinger.py    # BollingerBandsStrategy
    │   │   └── moving_average.py
    │   ├── intraday/           # Intraday strategies
    │   │   ├── vwap.py         # VWAPReversionStrategy
    │   │   ├── vwap_momentum.py# VWAPMomentumStrategy
    │   │   ├── orb.py          # ORBStrategy
    │   │   ├── gap_go.py       # GapAndGoStrategy
    │   │   └── twap.py         # TWAPStrategy
    │   └── swing/              # Swing trading
    │       └── price_action_volume_swing.py
    └── models/
        └── signals.py          # SignalData, SignalType
```

### Usage in Services

Each service imports from the shared package:

```python
# In backend/app/providers/__init__.py
from shared.providers import Exchange, OrderSide, Quote
from shared.providers.broker import get_broker, PaperBroker
from shared.providers.data import get_data_provider, YahooDataProvider

# In trading-engine/engine/strategies/__init__.py
from shared.strategies import RSIStrategy, VWAPReversionStrategy
from shared.strategies import StrategyRegistry, CompositeStrategy
```

### Docker Integration

The shared package is mounted into containers:

```yaml
# docker-compose.yml
services:
  api:
    volumes:
      - ./shared:/shared:ro

  trading-engine:
    volumes:
      - ./shared:/shared:ro
```

---

## Project Structure

```
portfolio-management-system/
├── frontend/                     # Next.js application
│   ├── src/
│   │   ├── app/                  # App router pages
│   │   ├── components/           # React components
│   │   │   ├── algo/             # Algo trading UI
│   │   │   ├── charts/           # TradingView, Recharts
│   │   │   ├── portfolio/        # Portfolio widgets
│   │   │   └── ui/               # shadcn/ui components
│   │   └── lib/                  # API client, utilities
│   └── Dockerfile
├── backend/                      # User-facing API
│   ├── app/
│   │   ├── main.py               # FastAPI entry point
│   │   ├── modules/
│   │   │   ├── auth/             # Authentication
│   │   │   ├── portfolio/        # Portfolio management
│   │   │   ├── trading/          # Order placement
│   │   │   ├── algo/             # Algo config & P&L
│   │   │   └── data/             # Market data
│   │   ├── models/               # SQLAlchemy models
│   │   └── providers/            # Re-exports from shared
│   └── Dockerfile
├── trading-engine/               # Strategy execution
│   ├── engine/
│   │   ├── algo/                 # Executor, scheduler
│   │   ├── routes/               # Internal endpoints
│   │   ├── strategies/           # Re-exports from shared
│   │   └── providers/            # Re-exports from shared
│   └── Dockerfile
├── shared/                       # Shared Python package
│   └── shared/
│       ├── providers/            # Broker & data providers
│       ├── strategies/           # Trading strategies
│       └── models/               # Common models
├── worker/                       # Celery tasks
├── docker-compose.yml
├── docker-compose.dev.yml
└── docs/
```

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14, React 18, Tailwind CSS | Modern, fast, SSR support |
| **UI Components** | shadcn/ui | Accessible, customizable |
| **Charts** | TradingView Lightweight Charts | Professional financial charts |
| **Backend/Engine** | Python 3.13 + FastAPI | Async, fast, great for data processing |
| **Package Manager** | uv | Fast Python package management |
| **ORM** | SQLAlchemy 2.0 | Type-safe, async support |
| **Task Queue** | Celery + Redis | Scheduled strategy execution |
| **Database** | PostgreSQL 15 + TimescaleDB | Relational + time-series in one |
| **Cache** | Redis | Caching, pub/sub, kill switch state |
| **Data Providers** | Yahoo Finance, NSE | Free market data |

---

## API Design

### Backend API Endpoints (Port 8010)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/login` | User login |
| `POST` | `/api/v1/auth/register` | User registration |
| `GET` | `/api/v1/portfolio/summary` | Get portfolio summary |
| `GET` | `/api/v1/portfolio/positions` | List positions |
| `POST` | `/api/v1/trading/orders` | Place order |
| `GET` | `/api/v1/algo/strategies` | List algo strategies |
| `POST` | `/api/v1/algo/strategies` | Create strategy |
| `GET` | `/api/v1/algo/pnl/summary` | Algo P&L summary |
| `POST` | `/api/v1/algo/emergency-stop` | Emergency kill switch |

### Trading Engine Endpoints (Port 8001, Internal)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/internal/run-scheduled` | Execute due strategies |
| `POST` | `/internal/execute/{id}` | Execute specific strategy |
| `POST` | `/internal/kill-switch/{user_id}/activate` | Activate kill switch |
| `GET` | `/health` | Health check |
| `GET` | `/ready` | Readiness check |

---

## Database Schema

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Portfolio positions
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    avg_cost DECIMAL(18, 4) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trade history
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 4) NOT NULL,
    fees DECIMAL(18, 4) DEFAULT 0,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Price data (TimescaleDB hypertable)
CREATE TABLE price_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DECIMAL(18, 4),
    high DECIMAL(18, 4),
    low DECIMAL(18, 4),
    close DECIMAL(18, 4),
    volume BIGINT,
    PRIMARY KEY (time, symbol)
);
SELECT create_hypertable('price_data', 'time');

-- Watchlist
CREATE TABLE watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);

-- Trading signals
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    confidence DECIMAL(5, 2),
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Local Development

```bash
# Clone repository
git clone <repo-url>
cd portfolio-management-system

# Copy environment file
cp .env.example .env

# Start all containers
docker-compose up -d

# View logs
docker-compose logs -f api trading-engine

# Access the app
open http://localhost:3000

# Run tests
cd backend && uv run pytest
cd trading-engine && uv run pytest
cd shared && uv run pytest

# Stop containers
docker-compose down
```

---

## Deployment Options

| Option | Cost | Pros | Cons |
|--------|------|------|------|
| **Local machine** | $0 | Free, fast dev | Not always-on |
| **Hetzner VPS** | €5-10/mo | Great value | Manual setup |
| **DigitalOcean** | $12-24/mo | Easy, good docs | Slightly pricier |

**Recommended**: Hetzner CX21 (2 vCPU, 4GB RAM) - €5.39/month

---

## Future Enhancements

1. **Backtesting engine** - Validate strategies on historical data
2. **Live broker integration** - AngelOne, Zerodha
3. **Mobile app** - React Native or PWA
4. **Advanced ML** - Anomaly detection, trend prediction
