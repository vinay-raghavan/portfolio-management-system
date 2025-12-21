# Portfolio Management System

A personal automated financial portfolio management system with paper trading, technical/fundamental analysis, and real-time market data.

## 🎯 Overview

This system performs comprehensive market analysis, executes simulated trades, and helps maximize returns through intelligent decision-making.

### Key Features

- **Market Analysis**: Technical indicators (RSI, MACD, Bollinger Bands) + fundamental metrics
- **Paper Trading**: Simulated trading to test strategies risk-free
- **Portfolio Tracking**: Real-time P&L, positions, and performance analytics
- **Modern UI**: Interactive charts, watchlists, and trading signals
- **Automated Signals**: Buy/sell recommendations based on multi-factor analysis

## 🏗️ Architecture

Simple containerized architecture using Docker Compose:

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Frontend │  │ Backend  │  │  Worker  │              │
│  │ (Next.js)│  │(FastAPI) │  │ (Celery) │              │
│  │  :3000   │  │  :8000   │  │          │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                      │                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │     PostgreSQL + TimescaleDB  │     Redis        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14, React 18, TradingView Charts, Tailwind CSS |
| **Backend** | Python FastAPI (modular monolith) |
| **Worker** | Celery for background jobs |
| **Database** | PostgreSQL 15 + TimescaleDB |
| **Cache** | Redis 7 |

## 📁 Project Structure

```
portfolio-management-system/
├── frontend/                    # Next.js application
│   ├── src/
│   │   ├── app/                 # App router pages
│   │   ├── components/          # React components
│   │   └── lib/                 # Utilities
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── api/                 # API routes
│   │   ├── modules/             # Business logic modules
│   │   │   ├── auth/
│   │   │   ├── portfolio/
│   │   │   ├── trading/
│   │   │   ├── analysis/
│   │   │   └── data/
│   │   ├── models/              # Database models
│   │   └── schemas/             # Pydantic schemas
│   └── Dockerfile
├── worker/                      # Celery background tasks
├── docker-compose.yml
├── .env.example
└── docs/
```

## 📚 Documentation

- [Architecture v2](docs/ARCHITECTURE_v2.md) - Current simplified architecture
- [System Design](docs/SYSTEM_DESIGN.md) - Detailed design document
- [Design Review](docs/DESIGN_REVIEW.md) - Architecture decisions

## 🚀 Quick Start

```bash
# Prerequisites: Docker, Docker Compose, Node.js 20+, Python 3.12+

# Clone and setup
git clone <repo-url>
cd portfolio-management-system

# Copy environment file
cp .env.example .env
# Edit .env with your API keys (Polygon.io recommended)

# Start all containers
docker compose up -d

# Access the UI
open http://localhost:3000
```

## 🛠️ Development

```bash
# Start in development mode (with hot reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run backend tests
docker compose exec api pytest

# Run frontend tests
docker compose exec web npm test

# View logs
docker compose logs -f api

# Stop all containers
docker compose down
```

## 💰 Estimated Costs

| Component | Cost |
|-----------|------|
| **Hosting** (Hetzner VPS) | ~€5-10/month |
| **Data** (Polygon.io Basic) | $0-29/month |
| **Total** | **~$10-40/month** |

## License

MIT