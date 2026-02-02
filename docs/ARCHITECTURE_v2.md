# Portfolio Management System - Revised Architecture (v2)

## Overview

A simplified, containerized architecture optimized for **personal use**. Uses Docker Compose for orchestration with a modular monolith backend instead of microservices.

---

## Architecture Comparison

| Aspect | Original (v1) | Revised (v2) |
|--------|---------------|--------------|
| Deployment | Kubernetes | Docker Compose |
| Services | 11 microservices | 4 containers |
| Databases | PostgreSQL + MongoDB + TimescaleDB | PostgreSQL + TimescaleDB |
| Message Queue | Apache Kafka | Redis (Pub/Sub + Celery) |
| API Gateway | Kong | Traefik (simple reverse proxy) |
| Monthly Cost | ~$745 | ~$20-50 |
| Complexity | Very High | Low |
| Time to MVP | 34-44 weeks | 10-14 weeks |

---

## Container Architecture

### Container 1: Frontend (`web`)
- **Image**: Node.js 20 Alpine
- **Framework**: Next.js 14 with App Router
- **Port**: 3000
- **Features**: React UI, TradingView Charts, WebSocket client

### Container 2: Backend (`api`)
- **Image**: Python 3.12 Slim
- **Framework**: FastAPI (modular monolith)
- **Port**: 8000
- **Modules**:
  - `auth` - JWT authentication, session management
  - `portfolio` - Positions, P&L, holdings
  - `trading` - Orders, execution, simulation
  - `analysis` - Technical & fundamental analysis
  - `data` - Market data ingestion, caching

### Container 3: Worker (`worker`)
- **Image**: Python 3.12 Slim
- **Framework**: Celery
- **Tasks**:
  - Scheduled data ingestion (every 1 min during market hours)
  - Batch analysis jobs
  - Portfolio rebalancing checks
  - Alert/notification processing

### Container 4: Database (`db`)
- **Image**: timescale/timescaledb:latest-pg15
- **Port**: 5432
- **Features**: PostgreSQL 15 + TimescaleDB extension for time-series

### Container 5: Cache (`redis`)
- **Image**: redis:7-alpine
- **Port**: 6379
- **Usage**: Caching, Celery broker, Pub/Sub for real-time updates

---

## Project Structure

```
portfolio-management-system/
├── frontend/                     # Next.js application
│   ├── src/
│   │   ├── app/                  # App router pages
│   │   ├── components/           # React components
│   │   │   ├── charts/           # TradingView, Recharts
│   │   │   ├── portfolio/        # Portfolio widgets
│   │   │   └── ui/               # shadcn/ui components
│   │   ├── lib/                  # API client, utilities
│   │   └── hooks/                # Custom React hooks
│   ├── Dockerfile
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point
│   │   ├── config.py             # Settings & configuration
│   │   ├── database.py           # Database connection
│   │   ├── api/
│   │   │   ├── routes/           # API route handlers
│   │   │   └── deps.py           # Dependencies (auth, db)
│   │   ├── modules/
│   │   │   ├── auth/             # Authentication module
│   │   │   ├── portfolio/        # Portfolio management
│   │   │   ├── trading/          # Trading engine
│   │   │   ├── analysis/         # Analysis engine
│   │   │   └── data/             # Data ingestion
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic schemas
│   │   └── services/             # Business logic
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── worker/
│   ├── tasks/                    # Celery task definitions
│   ├── celery_app.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml            # Main compose file
├── docker-compose.dev.yml        # Development overrides
├── .env.example                  # Environment template
├── Makefile                      # Common commands
└── docs/
```

---

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  web:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api

  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/portfolio
      - REDIS_URL=redis://redis:6379/0
      - POLYGON_API_KEY=${POLYGON_API_KEY}
    depends_on:
      - db
      - redis

  worker:
    build: ./worker
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/portfolio
      - REDIS_URL=redis://redis:6379/0
      - POLYGON_API_KEY=${POLYGON_API_KEY}
    depends_on:
      - db
      - redis

  db:
    image: timescale/timescaledb:latest-pg15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=portfolio
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14, React 18, Tailwind CSS | Modern, fast, SSR support |
| **UI Components** | shadcn/ui | Accessible, customizable |
| **Charts** | TradingView Lightweight Charts | Professional financial charts |
| **Backend** | Python FastAPI | Async, fast, great for data processing |
| **ORM** | SQLAlchemy 2.0 | Type-safe, async support |
| **Task Queue** | Celery + Redis | Simple, reliable background jobs |
| **Database** | PostgreSQL 15 + TimescaleDB | Relational + time-series in one |
| **Cache** | Redis | Fast caching, pub/sub |
| **Data** | yfinance + Polygon.io | Free fallback + paid reliable |

---

## API Design

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | User login |
| `POST` | `/api/auth/register` | User registration |
| `GET` | `/api/portfolio` | Get portfolio summary |
| `GET` | `/api/portfolio/positions` | List all positions |
| `GET` | `/api/portfolio/history` | P&L history |
| `GET` | `/api/stocks/{symbol}` | Get stock details |
| `GET` | `/api/stocks/{symbol}/analysis` | Technical + fundamental analysis |
| `GET` | `/api/stocks/{symbol}/price` | Current price + history |
| `POST` | `/api/orders` | Place order (paper trade) |
| `GET` | `/api/orders` | List orders |
| `GET` | `/api/watchlist` | Get watchlist |
| `POST` | `/api/watchlist` | Add to watchlist |
| `WS` | `/ws/prices` | Real-time price stream |
| `WS` | `/ws/portfolio` | Portfolio updates |

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

## Development Phases (Revised)

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1** | Weeks 1-3 | Project setup, Docker config, DB schema, basic API |
| **Phase 2** | Weeks 4-6 | Data ingestion, price storage, basic UI scaffold |
| **Phase 3** | Weeks 7-9 | Technical analysis, charts, stock detail page |
| **Phase 4** | Weeks 10-11 | Paper trading, order placement, portfolio tracking |
| **Phase 5** | Weeks 12-14 | Signals, alerts, polish, testing |

**Total: ~14 weeks to MVP**

---

## Local Development

```bash
# Clone repository
git clone <repo-url>
cd portfolio-management-system

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start all containers
docker compose up -d

# View logs
docker compose logs -f

# Access the app
open http://localhost:3000

# Stop containers
docker compose down
```

---

## Deployment Options

| Option | Cost | Pros | Cons |
|--------|------|------|------|
| **Local machine** | $0 | Free, fast dev | Not always-on |
| **Hetzner VPS** | €5-10/mo | Great value, EU | Manual setup |
| **DigitalOcean** | $12-24/mo | Easy, good docs | Slightly pricier |
| **Railway** | $5-20/mo | Zero config | Limited control |
| **Fly.io** | $5-15/mo | Global edge | Learning curve |

**Recommended**: Hetzner CX21 (2 vCPU, 4GB RAM) - €5.39/month

---

## What's NOT Included (Intentionally)

| Excluded | Reason |
|----------|--------|
| Kubernetes | Overkill for personal use |
| Kafka | Redis pub/sub sufficient |
| MongoDB | PostgreSQL JSONB covers document needs |
| Microservices | Modular monolith simpler to maintain |
| ML predictions | Add later if proven valuable |
| Multi-market | Start with US, add others later |

---

## Future Enhancements (Post-MVP)

1. **Backtesting engine** - Validate strategies on historical data
2. **Live broker integration** - Alpaca, Interactive Brokers
3. **Mobile app** - React Native or PWA
4. **Multi-market support** - India (NSE), UK (LSE)
5. **Advanced ML** - Anomaly detection, trend prediction

