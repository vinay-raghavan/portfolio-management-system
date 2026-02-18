# Portfolio Management System

[![Version](https://img.shields.io/badge/version-1.2.1-blue.svg)](https://github.com/vinay-raghavan/portfolio-management-system/releases/tag/v1.2.1)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A personal automated financial portfolio management system with algorithmic trading, paper trading, technical/fundamental analysis, and real-time market data for Indian markets (NSE/BSE).

## 🎯 Overview

This system performs comprehensive market analysis, executes automated trading strategies (simulated or live), and helps maximize returns through intelligent decision-making.

### Key Features

#### 📊 Dashboard & Portfolio
- **Unified Dashboard**: Portfolio summary, funds, algo status, market overview
- **Recommendations Carousel**: Combined screener + research picks with expandable details
- **Sector Heatmap**: Visual sector performance with drill-down
- **Recent Trades**: Trade history with P&L tracking

#### 🤖 Algorithmic Trading
- **Strategy Framework**: RSI, MACD, VWAP, ORB, Supertrend, and custom strategies
- **Safety Controls**: Kill switch, circuit breakers, daily loss limits
- **Trailing Stops & Profit Booking**: Automated position management
- **Backtesting**: Full metrics (Sharpe, Sortino, Max DD, Win Rate)

#### 📈 Stock Screener
- **Preset Screeners**: Momentum, Breakout, Consolidation, Pullback, Sector
- **Daily Recommendations**: Auto-generated picks with performance tracking
- **Custom Filters**: Build your own screener configurations

#### 🔬 Research Module
- **Fundamental Analysis**: P/E, EPS, ROE, Revenue trends
- **News Integration**: Multi-source news with sentiment scoring
- **Sector Analysis**: Heatmap with rotation tracking
- **Daily Digest**: Market summary, top movers, breakout candidates

#### 💹 Trading
- **Paper Trading**: Risk-free strategy validation
- **Live Trading**: Fyers broker integration (Angel One planned)
- **Order Types**: Market, Limit, Stop Loss, Stop Loss Market
- **Trade from Charts**: Quick trade panel with keyboard shortcuts

#### 🎨 User Experience
- **Keyboard Shortcuts**: Fast navigation and trading
- **Accessibility**: Skip links, ARIA labels, focus states
- **Error Handling**: Error boundaries with graceful recovery
- **Toast Notifications**: Real-time feedback for actions

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

- [Release Notes](docs/RELEASE_NOTES.md) - Version history and changelogs
- [Project Plan (TODO)](docs/TODO.md) - Detailed task breakdown and roadmap
- [Architecture v2](docs/ARCHITECTURE_v2.md) - Current architecture details
- [System Design](docs/SYSTEM_DESIGN.md) - Detailed design document
- [Trading Engine Design](docs/trading-engine-design.md) - Trading engine separation
- [Design Review](docs/DESIGN_REVIEW.md) - Architecture decisions

## 🚀 Quick Start

### Option 1: Use Pre-built Images (Recommended)

Pre-built hardened images are available on GitHub Container Registry (GHCR). These use [Chainguard](https://chainguard.dev) distroless base images for enhanced security.

```bash
# Prerequisites: Docker/Podman, Docker Compose

# Clone the repository
git clone https://github.com/vinay-raghavan/portfolio-management-system.git
cd portfolio-management-system

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Start with production images from GHCR
docker-compose -f docker-compose.prod.yml up -d

# Access the UI
open http://localhost:3001  # Frontend
open http://localhost:8010  # Backend API docs
```

Available images:
| Image | Description |
|-------|-------------|
| `ghcr.io/vinay-raghavan/portfolio-api:latest` | Backend API (FastAPI) |
| `ghcr.io/vinay-raghavan/portfolio-trading-engine:latest` | Trading Engine |
| `ghcr.io/vinay-raghavan/portfolio-worker:latest` | Celery Worker |
| `ghcr.io/vinay-raghavan/portfolio-web:latest` | Frontend (Next.js) |
| `ghcr.io/vinay-raghavan/portfolio-migrations:latest` | Database migrations |

### Option 2: Build Locally (Development)

```bash
# Prerequisites: Docker/Podman, Docker Compose, Python 3.13+

# Clone and setup
git clone https://github.com/vinay-raghavan/portfolio-management-system.git
cd portfolio-management-system

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Build and start all containers
docker-compose up -d --build

# Access the UI
open http://localhost:3001  # Frontend
open http://localhost:8010  # Backend API docs
```

## 🛠️ Development

```bash
# Start in development mode (with hot reload)
docker-compose up -d

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

### Building Production Images Locally

Each service supports multi-stage builds with `dev` and `prod` targets:

```bash
# Build hardened production image (Chainguard base)
docker build --target prod -t my-api:prod -f backend/Dockerfile .

# Build development image (with shell for debugging)
docker build --target dev -t my-api:dev -f backend/Dockerfile .

# Frontend requires API URL at build time
docker build --target prod \
  --build-arg NEXT_PUBLIC_API_URL="http://localhost:8010/api/v1" \
  -t my-frontend:prod -f frontend/Dockerfile frontend/
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