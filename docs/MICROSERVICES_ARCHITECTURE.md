# Portfolio Management System - Microservices Architecture

## 1. Overview

A cloud-native, event-driven microservices architecture designed for Kubernetes deployment. Each service is independently deployable, scalable, and maintainable.

---

## 2. Service Catalog

### 2.1 Frontend Services

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| `web-ui` | Next.js 14 | 3000 | React-based web application |

### 2.2 Core Business Services

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| `auth-service` | FastAPI | 8001 | JWT authentication, OAuth2, session management |
| `user-service` | FastAPI | 8002 | User profiles, preferences, settings |
| `portfolio-service` | FastAPI | 8003 | Portfolio CRUD, positions, P&L tracking |
| `trading-service` | FastAPI | 8004 | Order execution, paper/live trading |
| `analysis-service` | FastAPI | 8005 | Technical & fundamental analysis |
| `signal-service` | FastAPI | 8006 | Trading signal generation |
| `notification-service` | FastAPI | 8007 | Email, SMS, push notifications |

### 2.3 Data Ingestion Services

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| `market-data-service` | FastAPI | 8010 | Real-time & historical price data |
| `news-service` | FastAPI | 8011 | News aggregation & sentiment analysis |
| `fundamental-service` | FastAPI | 8012 | Financial statements, ratios |

### 2.4 Background Workers

| Worker | Technology | Description |
|--------|------------|-------------|
| `data-worker` | Python/Celery | Data processing, ETL jobs |
| `analysis-worker` | Python/Celery | Batch analysis, ML inference |
| `scheduler-worker` | Python/Celery | Scheduled tasks, cron jobs |

---

## 3. Project Structure

```
portfolio-management-system/
├── services/
│   ├── web-ui/                      # Next.js frontend
│   │   ├── src/
│   │   ├── Dockerfile
│   │   └── package.json
│   ├── auth-service/                # Authentication microservice
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── models/
│   │   │   └── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── portfolio-service/           # Portfolio management
│   ├── trading-service/             # Trading execution
│   ├── analysis-service/            # Stock analysis
│   ├── signal-service/              # Signal generation
│   ├── market-data-service/         # Market data ingestion
│   ├── news-service/                # News & sentiment
│   ├── fundamental-service/         # Fundamental data
│   └── notification-service/        # Notifications
├── workers/
│   ├── data-worker/
│   ├── analysis-worker/
│   └── scheduler-worker/
├── shared/
│   ├── proto/                       # gRPC protocol buffers
│   ├── schemas/                     # Shared Pydantic schemas
│   └── utils/                       # Common utilities
├── infrastructure/
│   ├── kubernetes/
│   │   ├── base/                    # Base K8s manifests
│   │   ├── overlays/
│   │   │   ├── development/
│   │   │   ├── staging/
│   │   │   └── production/
│   │   └── kustomization.yaml
│   ├── helm/
│   │   └── portfolio-system/        # Helm chart
│   ├── terraform/                   # Infrastructure as Code
│   └── docker-compose.yaml          # Local development
├── docs/
├── scripts/
└── Makefile
```

---

## 4. Communication Patterns

### 4.1 Synchronous Communication

**REST API** - External client communication via Kong API Gateway
**gRPC** - Internal service-to-service for low-latency calls

```protobuf
// proto/analysis.proto
service AnalysisService {
  rpc GetTechnicalAnalysis(AnalysisRequest) returns (TechnicalAnalysis);
  rpc GetFundamentalAnalysis(AnalysisRequest) returns (FundamentalAnalysis);
  rpc GetStockScore(ScoreRequest) returns (StockScore);
}
```

### 4.2 Asynchronous Communication (Kafka)

| Topic | Producer | Consumers | Purpose |
|-------|----------|-----------|---------|
| `market.prices` | market-data-service | analysis, portfolio, signal | Real-time price updates |
| `market.fundamentals` | fundamental-service | analysis, data-worker | Financial data updates |
| `orders.created` | trading-service | notification | New order events |
| `orders.executed` | trading-service | portfolio, notification | Trade execution events |
| `signals.generated` | signal-service | notification, portfolio | Trading signals |
| `news.sentiment` | news-service | analysis | Sentiment scores |
| `portfolio.updated` | portfolio-service | notification, web-ui | Portfolio changes |

### 4.3 Real-time Communication

WebSocket connections through Kong for:
- Live price streaming
- Portfolio value updates
- Trade notifications
- Signal alerts

---

## 5. Data Architecture

### 5.1 Database per Service Pattern

| Service | Database | Purpose |
|---------|----------|---------|
| auth-service | PostgreSQL | Users, sessions, tokens |
| user-service | PostgreSQL | Profiles, preferences |
| portfolio-service | PostgreSQL | Positions, trades, P&L |
| trading-service | PostgreSQL | Orders, executions |
| market-data-service | TimescaleDB | Time-series price data |
| analysis-service | Redis + PostgreSQL | Cached analysis, historical |
| news-service | MongoDB | Articles, sentiment data |
| fundamental-service | PostgreSQL | Financial statements |

### 5.2 Shared Data Access

Services access other services' data ONLY through APIs, never directly.

```
┌─────────────────┐     API Call      ┌─────────────────┐
│ portfolio-svc   │ ───────────────▶  │ analysis-svc    │
└─────────────────┘                   └─────────────────┘
        │                                     │
        ▼                                     ▼
┌─────────────────┐                   ┌─────────────────┐
│ portfolio-db    │                   │ analysis-db     │
└─────────────────┘                   └─────────────────┘
```

---

## 6. Kubernetes Architecture

### 6.1 Namespaces

| Namespace | Purpose |
|-----------|---------|
| `portfolio-system` | Application services, ConfigMaps, Secrets, HPA |
| `portfolio-data` | StatefulSets (PostgreSQL, MongoDB), PVCs |
| `portfolio-messaging` | Kafka, Redis |
| `portfolio-monitoring` | Prometheus, Grafana, Jaeger, Loki |
| `portfolio-ingress` | NGINX Ingress, Cert-Manager, Kong |

### 6.2 Deployment Strategy

- **Deployments**: All stateless microservices
- **StatefulSets**: Databases, Kafka, Redis
- **DaemonSets**: Log collectors, node exporters
- **CronJobs**: Scheduled data ingestion, cleanup tasks
- **HPA**: Auto-scaling based on CPU/memory/custom metrics

### 6.3 Service Mesh (Istio - Optional)

- mTLS between services
- Traffic management (canary, blue-green)
- Circuit breaking and retries
- Distributed tracing integration

---

## 7. API Gateway (Kong)

### 7.1 Route Configuration

| Path | Service | Auth Required |
|------|---------|---------------|
| `/api/v1/auth/*` | auth-service | No |
| `/api/v1/portfolio/*` | portfolio-service | Yes |
| `/api/v1/orders/*` | trading-service | Yes |
| `/api/v1/analysis/*` | analysis-service | Yes |
| `/api/v1/stocks/*` | market-data-service | Yes |
| `/ws/*` | WebSocket upstream | Yes |

### 7.2 Plugins Enabled

- **JWT Authentication**: Token validation
- **Rate Limiting**: 100 req/min per user
- **CORS**: Cross-origin requests
- **Request Transformer**: Header manipulation
- **Prometheus**: Metrics export

---

## 8. Observability Stack

### 8.1 Components

| Tool | Purpose | Integration |
|------|---------|-------------|
| **Prometheus** | Metrics collection | `/metrics` endpoint on all services |
| **Grafana** | Dashboards & visualization | Prometheus datasource |
| **Jaeger** | Distributed tracing | OpenTelemetry SDK |
| **Loki** | Log aggregation | Promtail sidecar |
| **AlertManager** | Alerting | Slack, PagerDuty integration |

### 8.2 Key Metrics

```python
# Custom metrics per service
METRICS = {
    "business": [
        "orders_total",
        "orders_executed_total",
        "portfolio_value_dollars",
        "signals_generated_total",
        "analysis_requests_total"
    ],
    "technical": [
        "http_requests_total",
        "http_request_duration_seconds",
        "kafka_messages_consumed_total",
        "db_query_duration_seconds"
    ]
}
```

---

## 9. Security Architecture

### 9.1 Authentication Flow

```
User → Kong (JWT validation) → Service → Database
         ↓
    auth-service (token refresh, validation)
```

### 9.2 Secrets Management

- **Kubernetes Secrets**: Database credentials, API keys
- **External Secrets Operator**: Sync with AWS Secrets Manager/Vault
- **Sealed Secrets**: GitOps-friendly encrypted secrets

### 9.3 Network Policies

```yaml
# Allow only specific service-to-service communication
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: portfolio-service-policy
spec:
  podSelector:
    matchLabels:
      app: portfolio-service
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: kong
        - podSelector:
            matchLabels:
              app: trading-service
```

---

## 10. CI/CD Pipeline

### 10.1 GitOps Workflow (ArgoCD)

```
Developer → GitHub PR → CI (GitHub Actions) → Container Registry
                                                      ↓
                                              ArgoCD Sync
                                                      ↓
                                            Kubernetes Cluster
```

### 10.2 Pipeline Stages

1. **Build**: Lint, test, build Docker images
2. **Scan**: Security scanning (Trivy, Snyk)
3. **Push**: Push to container registry (ECR/GCR)
4. **Deploy**: ArgoCD syncs manifests to cluster

---

## 11. Local Development

### 11.1 Prerequisites

- Docker & Docker Compose
- kubectl & Helm
- Python 3.11+
- Node.js 20+
- Make

### 11.2 Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/portfolio-management-system
cd portfolio-management-system

# Start infrastructure (databases, Kafka, Redis)
make infra-up

# Start all services in development mode
make dev

# Or start individual services
make dev-portfolio-service
make dev-analysis-service
```

### 11.3 Docker Compose (Local)

```yaml
# docker-compose.yaml (simplified)
version: '3.8'
services:
  postgres:
    image: timescale/timescaledb:latest-pg15
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports: ["9092:9092"]

  mongodb:
    image: mongo:7
    ports: ["27017:27017"]

  kong:
    image: kong:3.5
    ports: ["8000:8000", "8001:8001"]
```

---

## 12. Scaling Strategy

| Service | Scaling Trigger | Min | Max |
|---------|-----------------|-----|-----|
| web-ui | CPU > 70% | 2 | 10 |
| portfolio-service | CPU > 70% | 3 | 20 |
| trading-service | CPU > 60% | 3 | 15 |
| analysis-service | CPU > 80% | 2 | 10 |
| market-data-service | Kafka lag | 2 | 8 |
| signal-service | Queue depth | 2 | 10 |

---

## 13. Disaster Recovery

- **Database Backups**: Automated daily backups to S3
- **Multi-AZ Deployment**: Services spread across availability zones
- **PDB (Pod Disruption Budget)**: Ensure minimum replicas during updates
- **Kafka Replication**: Factor of 3 for all topics
- **State Recovery**: Replay Kafka events to rebuild state

---

## 14. Technology Summary

| Category | Technology |
|----------|------------|
| **Container Runtime** | Docker, containerd |
| **Orchestration** | Kubernetes 1.28+ |
| **Service Mesh** | Istio (optional) |
| **API Gateway** | Kong |
| **Ingress** | NGINX Ingress Controller |
| **CI/CD** | GitHub Actions + ArgoCD |
| **Container Registry** | ECR / GCR / Harbor |
| **Secrets** | External Secrets Operator |
| **Monitoring** | Prometheus + Grafana |
| **Logging** | Loki + Promtail |
| **Tracing** | Jaeger + OpenTelemetry |
| **Message Broker** | Apache Kafka |
| **Cache** | Redis |
| **Databases** | PostgreSQL, TimescaleDB, MongoDB |
