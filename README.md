# Portfolio Management System

A personal automated financial portfolio management system with algorithmic trading, paper trading, technical/fundamental analysis, and real-time market data for Indian markets (NSE/BSE).

## 🎯 Overview

This system performs comprehensive market analysis, executes automated trading strategies (simulated or live), and helps maximize returns through intelligent decision-making.

### Key Features

- **Algorithmic Trading**: Automated strategy execution with RSI, MACD, VWAP, ORB, and more
- **Paper Trading**: Simulated trading to test strategies risk-free
- **Portfolio Tracking**: Real-time P&L, positions, and performance analytics
- **Stock Screener**: Preset screeners (momentum, breakout, consolidation, pullback, sector) with daily recommendations and performance tracking
- **Modern UI**: Interactive charts, watchlists, trading signals, and research page
- **Risk Management**: Kill switch, circuit breakers, daily loss limits
- **Indian Market Focus**: NSE/BSE support with Yahoo Finance and NSE data providers

## 🏗️ Architecture

Containerized microservices architecture using Docker Compose:

```
┌──────────────────────────────────────────────────────────────────┐
│                        Docker Compose                             │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐  ┌──────────┐   │
│  │ Frontend │  │ Backend  │  │ Trading Engine │  │  Worker  │   │
│  │ (Next.js)│  │(FastAPI) │  │   (FastAPI)    │  │ (Celery) │   │
│  │  :3000   │  │  :8010   │  │     :8001      │  │          │   │
│  └──────────┘  └──────────┘  └────────────────┘  └──────────┘   │
│        │              │               │                │          │
│        └──────────────┴───────────────┴────────────────┘          │
│                               │                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │     PostgreSQL + TimescaleDB    │         Redis            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                               │                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     Shared Package                          │  │
│  │   (Providers, Strategies, Models - used by all services)   │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 14, React 18, TradingView Charts | User interface |
| **Backend API** | Python FastAPI | User-facing API, portfolio management |
| **Trading Engine** | Python FastAPI | Strategy execution, order management |
| **Worker** | Celery | Scheduled tasks, background jobs |
| **Shared** | Python package | Providers, strategies, common code |
| **Database** | PostgreSQL 15 + TimescaleDB | Data persistence |
| **Cache** | Redis 7 | Caching, pub/sub, Celery broker |

## 📁 Project Structure

```
portfolio-management-system/
├── frontend/                    # Next.js application
│   ├── src/
│   │   ├── app/                 # App router pages
│   │   ├── components/          # React components
│   │   └── lib/                 # Utilities
│   └── Dockerfile
├── backend/                     # User-facing API
│   ├── app/
│   │   ├── api/                 # API routes
│   │   ├── modules/             # Business logic modules
│   │   │   ├── auth/            # Authentication
│   │   │   ├── portfolio/       # Portfolio management
│   │   │   ├── trading/         # Order placement
│   │   │   ├── algo/            # Algo trading config
│   │   │   ├── screener/        # Stock screener & recommendations
│   │   │   └── data/            # Market data
│   │   ├── models/              # Database models
│   │   └── providers/           # Re-exports from shared
│   └── Dockerfile
├── trading-engine/              # Strategy execution service
│   ├── engine/
│   │   ├── algo/                # Executor, scheduler, safety
│   │   ├── routes/              # Internal API endpoints
│   │   ├── strategies/          # Re-exports from shared
│   │   └── providers/           # Re-exports from shared
│   └── Dockerfile
├── shared/                      # Shared Python package
│   └── shared/
│       ├── providers/           # Broker & data providers
│       │   ├── broker/          # PaperBroker, AngelOne, etc.
│       │   └── data/            # Yahoo, NSE providers
│       ├── strategies/          # Trading strategies
│       │   ├── indicators/      # RSI, MACD, Bollinger
│       │   ├── intraday/        # VWAP, ORB, Gap-Go
│       │   └── swing/           # Price action strategies
│       └── models/              # SignalData, etc.
├── worker/                      # Celery background tasks
├── docker-compose.yml
└── docs/
```

## 📚 Documentation

- [Architecture v2](docs/ARCHITECTURE_v2.md) - Current architecture details
- [System Design](docs/SYSTEM_DESIGN.md) - Detailed design document
- [Trading Engine Design](docs/trading-engine-design.md) - Trading engine separation
- [Design Review](docs/DESIGN_REVIEW.md) - Architecture decisions

## 🚀 Quick Start

```bash
# Prerequisites: Docker, Docker Compose (or Podman), Python 3.13+

# Clone and setup
git clone <repo-url>
cd portfolio-management-system

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Start all containers
docker-compose up -d

# Access the UI
open http://localhost:3000
```

## 🛠️ Development

```bash
# Start in development mode (with hot reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run backend tests
cd backend && uv run pytest

# Run trading engine tests
cd trading-engine && uv run pytest

# Run shared package tests
cd shared && uv run pytest

# View logs
docker-compose logs -f api trading-engine

# Stop all containers
docker-compose down
```

## 🔧 Shared Package

The `shared/` package contains code used by multiple services:

```python
# Providers
from shared.providers.broker import get_broker, PaperBroker
from shared.providers.data import get_data_provider, YahooDataProvider

# Strategies
from shared.strategies import RSIStrategy, VWAPReversionStrategy
from shared.strategies import StrategyRegistry, CompositeStrategy

# Models
from shared.models import SignalData, SignalType
```

## 💰 Estimated Costs

| Component | Cost |
|-----------|------|
| **Hosting** (Hetzner VPS) | ~€5-10/month |
| **Data** (Yahoo Finance) | Free |
| **Total** | **~€5-10/month** |

## License

MIT