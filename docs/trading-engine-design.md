# Trading Engine Separation - Technical Design Document

## 1. Executive Summary

The trading engine will be extracted from the backend API into a **dedicated microservice** to:
- **Eliminate API latency** caused by CPU-intensive strategy execution
- **Enable independent scaling** of execution capacity
- **Improve fault isolation** - trading engine crashes won't affect user API
- **Allow independent deployment** of trading logic updates

## 2. Architecture Overview

### Current State
```
Celery Worker → HTTP → Backend API (includes /internal/algo/*)
                              ↓
                    Strategy Execution (causes latency)
```

### Target State
```
Celery Worker → HTTP → Trading Engine :8001 (execution only)
User Request  → HTTP → Backend API :8000 → HTTP → Trading Engine
```

## 3. Container Configuration

### docker-compose.yml Addition

```yaml
# Trading Engine - Strategy Execution Service
trading-engine:
  build:
    context: ./trading-engine
    dockerfile: Dockerfile
  container_name: portfolio-trading-engine
  restart: unless-stopped
  environment:
    DATABASE_URL: postgresql+asyncpg://postgres:${POSTGRES_PASSWORD:-postgres}@db:5432/portfolio
    REDIS_URL: redis://redis:6379/0
    INTERNAL_API_KEY: ${INTERNAL_API_KEY:-internal-worker-key}
    DATA_PROVIDER: ${DATA_PROVIDER:-yahoo}
    DEFAULT_MARKET: ${DEFAULT_MARKET:-IN}
    LOG_LEVEL: ${LOG_LEVEL:-INFO}
  ports:
    - "${TRADING_ENGINE_PORT:-8001}:8001"
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 10s
    timeout: 5s
    retries: 3
  networks:
    - portfolio-net
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

### Worker Configuration Update

```yaml
worker:
  environment:
    # Change from api:8000 to trading-engine:8001
    INTERNAL_API_URL: http://trading-engine:8001
```

## 4. API Endpoints

### Execution Endpoints

| Method | Path | Description | Called By |
|--------|------|-------------|-----------|
| `POST` | `/internal/run-scheduled` | Execute all due strategies | Celery Worker |
| `POST` | `/internal/execute/{strategy_id}` | Execute specific strategy | Backend API, Celery |
| `POST` | `/internal/backtest/{strategy_id}` | Run backtest | Backend API |

### Safety Endpoints

| Method | Path | Description | Called By |
|--------|------|-------------|-----------|
| `GET` | `/internal/kill-switch/{user_id}` | Check kill switch status | Internal |
| `POST` | `/internal/kill-switch/{user_id}/activate` | Activate kill switch | Backend API |
| `POST` | `/internal/kill-switch/{user_id}/deactivate` | Deactivate kill switch | Backend API |
| `GET` | `/internal/circuit-breaker/{strategy_id}` | Check circuit breaker | Internal |

### Health Endpoints

| Method | Path | Description | Called By |
|--------|------|-------------|-----------|
| `GET` | `/health` | Basic health check | Docker |
| `GET` | `/ready` | Readiness check (DB + Redis) | Kubernetes |
| `GET` | `/metrics` | Prometheus metrics | Monitoring |

## 5. Directory Structure

```
trading-engine/
├── pyproject.toml
├── Dockerfile
├── README.md
├── engine/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Settings
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py         # Async SQLAlchemy setup
│   │   ├── redis.py            # Redis connection
│   │   └── health.py           # Health check utilities
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── execution.py        # /internal/run-scheduled, /execute
│   │   ├── safety.py           # /internal/kill-switch, circuit-breaker
│   │   └── health.py           # /health, /ready, /metrics
│   │
│   ├── algo/
│   │   ├── __init__.py
│   │   ├── executor.py         # Strategy execution orchestration
│   │   ├── scheduler.py        # Schedule management
│   │   ├── position_sizer.py   # Position sizing calculations
│   │   ├── safety.py           # Kill switch, circuit breaker, rate limiter
│   │   └── notifications.py    # Execution notifications
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── algo.py             # UserStrategy, StrategyExecution, etc.
│   │   ├── signals.py          # SignalType, SignalData
│   │   └── schemas.py          # Pydantic request/response schemas
│   │
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py             # BaseStrategy abstract class
│   │   ├── registry.py         # StrategyRegistry
│   │   └── ...                 # Strategy implementations
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── schemas.py          # OHLCV, Quote, OrderRequest, etc.
│   │   ├── broker/
│   │   │   └── ...
│   │   └── data/
│   │       └── ...
│   │
│   └── risk/
│       ├── __init__.py
│       └── service.py          # RiskService
│
└── tests/
    └── ...
```

## 6. Dependencies (pyproject.toml)

```toml
[project]
name = "trading-engine"
version = "0.1.0"
description = "Portfolio Management System - Trading Engine"
requires-python = ">=3.13"
dependencies = [
    # Web framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",

    # Database
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",

    # Redis
    "redis>=5.2.0",

    # Data & Analysis
    "pandas>=2.2.0",
    "numpy>=2.1.0",
    "yfinance>=0.2.50",
    "ta>=0.11.0",

    # HTTP client
    "httpx>=0.28.0",

    # Validation
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",

    # Monitoring (optional)
    "prometheus-client>=0.21.0",
]
```

## 7. Code Migration Mapping

| Source (backend/app/) | Destination (trading-engine/engine/) | Action |
|----------------------|--------------------------------------|--------|
| `modules/algo/internal_router.py` | `routes/execution.py` | Move + refactor |
| `modules/algo/executor.py` | `algo/executor.py` | Move |
| `modules/algo/scheduler.py` | `algo/scheduler.py` | Move |
| `modules/algo/position_sizer.py` | `algo/position_sizer.py` | Move |
| `modules/algo/safety.py` | `algo/safety.py` | Move |
| `modules/algo/notifications.py` | `algo/notifications.py` | Move |
| `modules/algo/models.py` | `models/algo.py` | Copy (shared) |
| `modules/algo/schemas.py` | `models/schemas.py` | Copy (partial) |
| `modules/signals/strategies/*` | `strategies/*` | Copy |
| `modules/signals/models.py` | `models/signals.py` | Copy (partial) |
| `modules/risk/service.py` | `risk/service.py` | Copy |
| `providers/broker/*` | `providers/broker/*` | Copy |
| `providers/data/*` | `providers/data/*` | Copy |
| `providers/schemas.py` | `providers/schemas.py` | Copy |

## 8. Backend Changes Required

### Remove from Backend
- `app/modules/algo/internal_router.py` - moved to trading-engine
- `app/modules/algo/executor.py` - moved to trading-engine
- Remove internal router mounting from `app/main.py`

### Update in Backend
1. **router.py** - Add HTTP client to call trading-engine for:
   - Manual strategy trigger → `POST http://trading-engine:8001/internal/execute/{id}`
   - Kill switch operations → `POST http://trading-engine:8001/internal/kill-switch/...`

2. **Add trading engine client:**
```python
# app/clients/trading_engine.py
import httpx
from app.core.config import settings

class TradingEngineClient:
    def __init__(self):
        self.base_url = settings.TRADING_ENGINE_URL  # http://trading-engine:8001
        self.api_key = settings.INTERNAL_API_KEY

    async def execute_strategy(self, strategy_id: str, symbols: list[str] | None = None):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/internal/execute/{strategy_id}",
                headers={"X-Internal-Key": self.api_key},
                params={"symbols_override": symbols} if symbols else None,
            )
            return response.json()

    async def activate_kill_switch(self, user_id: str, reason: str, square_off: bool):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/internal/kill-switch/{user_id}/activate",
                headers={"X-Internal-Key": self.api_key},
                json={"reason": reason, "square_off": square_off},
            )
            return response.json()
```

## 9. Worker Changes Required

Update `worker/worker/config.py`:
```python
class Settings(BaseSettings):
    # Change default from api:8000 to trading-engine:8001
    INTERNAL_API_URL: str = "http://trading-engine:8001"
```

## 10. Environment Variables

### New Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `TRADING_ENGINE_URL` | `http://trading-engine:8001` | Trading engine URL for backend |
| `TRADING_ENGINE_PORT` | `8001` | Port for trading engine |

### Updated Variables
| Variable | Old Value | New Value |
|----------|-----------|-----------|
| `INTERNAL_API_URL` (worker) | `http://api:8000` | `http://trading-engine:8001` |

## 11. Monitoring & Observability

### Health Checks
```python
@router.get("/health")
async def health():
    return {"status": "healthy", "service": "trading-engine"}

@router.get("/ready")
async def ready(db: AsyncSession, redis: Redis):
    db_ok = await check_db(db)
    redis_ok = await check_redis(redis)
    return {"db": "ok" if db_ok else "error", "redis": "ok" if redis_ok else "error"}
```

### Metrics to Expose
- `trading_engine_strategies_executed_total` - Counter
- `trading_engine_signals_generated_total` - Counter
- `trading_engine_orders_placed_total` - Counter
- `trading_engine_execution_duration_seconds` - Histogram
- `trading_engine_data_fetch_errors_total` - Counter

## 12. Testing Strategy

1. **Unit Tests**: Test each component in isolation
2. **Integration Tests**: Test full execution flow with test DB
3. **Contract Tests**: Verify API contracts between services
4. **Load Tests**: Verify performance under concurrent strategy execution

## 13. Rollback Plan

If issues arise:
1. Update `INTERNAL_API_URL` in worker back to `http://api:8000`
2. Re-enable `internal_router` in backend
3. Stop trading-engine container

## 14. Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Setup | 4 hours | Directory structure, Docker, core modules |
| Phase 2: Models & Providers | 4 hours | All models and providers copied |
| Phase 3: Strategies | 3 hours | All strategies copied and working |
| Phase 4: Execution Logic | 4 hours | Executor, scheduler, safety modules |
| Phase 5: Routes & Integration | 4 hours | Routes wired, services connected |
| Phase 6: Testing & Cleanup | 4 hours | Tests passing, old code removed |
| **Total** | **~3 days** | Fully separated trading engine |

