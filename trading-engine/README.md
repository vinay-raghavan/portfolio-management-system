# Trading Engine

Strategy Execution Service for Portfolio Management System.

## Overview

The Trading Engine is a dedicated microservice responsible for:
- Executing trading strategies on schedule
- Processing manual strategy triggers
- Managing safety controls (kill switch, circuit breaker)
- Interfacing with brokers and data providers

## Running Locally

```bash
cd trading-engine
uv sync
uv run uvicorn engine.main:app --host 0.0.0.0 --port 8001 --reload
```

## API Endpoints

### Health
- `GET /health` - Basic health check
- `GET /ready` - Readiness check (DB + Redis)
- `GET /metrics` - Prometheus metrics

### Execution
- `POST /internal/run-scheduled` - Execute due strategies
- `POST /internal/execute/{strategy_id}` - Execute specific strategy

### Safety
- `GET /internal/kill-switch/{user_id}` - Get kill switch status
- `POST /internal/kill-switch/{user_id}/activate` - Activate kill switch
- `POST /internal/kill-switch/{user_id}/deactivate` - Deactivate kill switch

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `INTERNAL_API_KEY` | `internal-worker-key` | API key for internal requests |
| `DATA_PROVIDER` | `yahoo` | Data provider (yahoo, nse) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Docker

```bash
docker build -t trading-engine .
docker run -p 8001:8001 trading-engine
```

