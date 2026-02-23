# Portfolio Management System - Project Plan

## � Executive Summary

A two-phase approach to build a complete algorithmic trading platform:
- **Phase 1**: Paper trading with free APIs (Yahoo Finance, NSE) - validate all operations
- **Phase 2**: Live trading with Angel One API - same platform, just flip the switch

**Key Principle**: The broker/data layer is abstracted. Switching from paper to live trading is a configuration change, not a code change.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                          │
│  Dashboard │ Charts │ Watchlist │ Orders │ Portfolio │ Signals     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                            │
├─────────────────────────────────────────────────────────────────────┤
│  Auth │ Portfolio │ Trading │ Analysis │ Data │ Watchlist │ Alerts │
└─────────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   DATA PROVIDER     │ │   BROKER PROVIDER   │ │   BACKGROUND JOBS   │
│   (Abstract Layer)  │ │   (Abstract Layer)  │ │   (Celery Workers)  │
├─────────────────────┤ ├─────────────────────┤ ├─────────────────────┤
│ • YahooFinance      │ │ • PaperTrading      │ │ • Price Updates     │
│ • NSE India         │ │ • AngelOne          │ │ • Signal Generation │
│ • AngelOne Data     │ │ • Dhan (future)     │ │ • Portfolio Metrics │
│ • Polygon (future)  │ │ • Zerodha (future)  │ │ • Alerts            │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE                                  │
│         PostgreSQL + TimescaleDB │ Redis │ Docker                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Architecture Diagram (Mermaid)

```mermaid
flowchart TB
    subgraph Frontend["🖥️ FRONTEND (Next.js)"]
        FE[Dashboard | Charts | Watchlist | Orders | Portfolio | Signals | Algo]
    end

    subgraph Backend["⚙️ BACKEND (FastAPI)"]
        direction LR
        Auth[Auth]
        Portfolio[Portfolio]
        Trading[Trading]
        Analysis[Analysis]
        Data[Data]
        Watchlist[Watchlist]
        Alerts[Alerts]
        Algo[Algo Engine]
    end

    subgraph Providers["🔌 PROVIDER ABSTRACTION LAYER"]
        direction TB
        subgraph DataProviders["Data Providers"]
            Yahoo[Yahoo Finance]
            NSE[NSE India]
            AngelData[Angel One Data]
        end
        subgraph BrokerProviders["Broker Providers"]
            Paper[Paper Trading]
            AngelBroker[Angel One]
            Dhan[Dhan]
        end
        subgraph NotificationProviders["Notification Providers"]
            Email[Email]
            WhatsApp[WhatsApp]
            WebSocket[WebSocket]
            Push[Push/SMS]
        end
    end

    subgraph Workers["👷 BACKGROUND JOBS (Celery)"]
        PriceUpdates[Price Updates]
        SignalGen[Signal Generation]
        PortfolioMetrics[Portfolio Metrics]
        AlertTasks[Alerts]
        AlgoExec[Algo Execution]
        NotifyTasks[Notifications]
    end

    subgraph Infra["🏗️ INFRASTRUCTURE"]
        DB[(PostgreSQL + TimescaleDB)]
        Redis[(Redis)]
        Docker[Docker]
    end

    Frontend --> Backend
    Backend --> Providers
    Backend --> Workers
    Workers --> Providers
    Providers --> Infra
    Backend --> Infra
    Workers --> Infra

    style Frontend fill:#e3f2fd,stroke:#1976d2
    style Backend fill:#e8f5e9,stroke:#4caf50
    style Providers fill:#f3e5f5,stroke:#9c27b0
    style Workers fill:#fff3e0,stroke:#ff9800
    style Infra fill:#fce4ec,stroke:#e91e63
```

---

## 🌿 Git Branching Strategy

### Branch Naming Convention

```
main                           # Production-ready code
├── develop                    # Integration branch for all features
│   ├── phase-1/               # Phase 1: Paper Trading Platform
│   │   ├── infrastructure     # Week 1: Core infrastructure
│   │   ├── indian-market      # Week 2: NSE/BSE data
│   │   ├── trading-risk       # Week 3: Trading + Risk management
│   │   ├── frontend           # Week 3-4: Frontend development
│   │   ├── notifications      # Week 4-5: Notification system
│   │   ├── signals-backtest   # Week 5: Signals & backtesting
│   │   ├── algo-trading       # Week 5-6: Algo trading engine
│   │   ├── testing            # Week 6-7: Testing & polish
│   │   └── ux-improvements    # Week 8-9: UX enhancements
│   │
│   ├── phase-2/               # Phase 2: Live Trading
│   │   ├── angelone           # Angel One integration
│   │   └── live-safety        # Live trading safety features
│   │
│   └── phase-3/               # Phase 3: Future Enhancements
│       ├── multi-broker       # Additional brokers
│       ├── options            # Options trading
│       ├── advanced-algo      # Advanced algo features
│       └── mobile             # Mobile app
│
└── hotfix/                    # Emergency fixes for production
```

### Workflow

1. **Create feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b phase-1/infrastructure
   ```

2. **Work on feature**, commit frequently:
   ```bash
   git add .
   git commit -m "feat(infra): add data provider abstraction"
   ```

3. **Push and create PR** to `develop`:
   ```bash
   git push origin phase-1/infrastructure
   # Create PR: phase-1/infrastructure → develop
   ```

4. **After review**, merge to `develop`

5. **At phase completion**, merge `develop` → `main` with tag:
   ```bash
   git checkout main
   git merge develop
   git tag -a v1.0.0 -m "Phase 1: Paper Trading Complete"
   ```

### Branch Summary Table

| Phase | Week | Branch Name | Description |
|-------|------|-------------|-------------|
| 1 | 1 | `phase-1/infrastructure` | Data/Broker/Notification abstraction, Symbol system |
| 1 | 2 | `phase-1/indian-market` | NSE data provider, Instrument master |
| 1 | 3 | `phase-1/trading-risk` | Order types, Position mgmt, Risk limits |
| 1 | 3-4 | `phase-1/frontend` | Dashboard, Portfolio, Order entry, Charts |
| 1 | 4-5 | `phase-1/notifications` | Email, WhatsApp, WebSocket notifications |
| 1 | 5 | `phase-1/signals-backtest` | Signal engine, Backtesting framework |
| 1 | 5-6 | `phase-1/algo-trading` | Strategy framework, Executor, Scheduler |
| 1 | 7 | `phase-1/screener` | Stock screener, Research page, Recommendations |
| 1 | 7 | `phase-1/testing` | Unit tests, E2E tests, Validation |
| 1 | 8-9 | `phase-1/ux-improvements` | UX enhancements, Accessibility, Trading workflow |
| 2 | 9-10 | `phase-2/angelone` | Angel One API integration |
| 2 | 8-9 | `phase-2/live-safety` | Live trading safety features |
| 2 | 10-11 | `phase-2/reporting-ledger` | Transaction ledger, gains tracking, API logging |
| 2 | 11-12 | `phase-2/reports-frontend` | Reports UI: statement, gains, API logs, activity |
| 2 | 12-13 | `phase-2/auto-trade-pipeline` | Recommendation → Algo automation, templates, pending trades |
| 2 | 13-14 | `phase-2/algo-time-window` | Trading time window for strategies (from/to time) |
| 3 | - | `phase-3/multi-broker` | Dhan, Zerodha integration |
| 3 | - | `phase-3/advanced-orders` | Bracket, Cover, GTT orders |
| 3 | - | `phase-3/options` | Options trading support |
| 3 | - | `phase-3/advanced-algo` | ML strategies, optimization |
| 3 | - | `phase-3/mobile` | React Native mobile app |
| 3 | - | `phase-3/social` | Strategy sharing, leaderboard |

### Git Flow Diagram

```mermaid
gitGraph
    commit id: "Initial"
    branch develop
    checkout develop
    commit id: "Setup"

    branch phase-1/infrastructure
    checkout phase-1/infrastructure
    commit id: "Data abstraction"
    commit id: "Broker abstraction"
    commit id: "Notification abstraction"
    checkout develop
    merge phase-1/infrastructure tag: "v0.1.0"

    branch phase-1/indian-market
    checkout phase-1/indian-market
    commit id: "NSE provider"
    commit id: "Instrument master"
    checkout develop
    merge phase-1/indian-market tag: "v0.2.0"

    branch phase-1/trading-risk
    checkout phase-1/trading-risk
    commit id: "Order types"
    commit id: "Risk limits"
    checkout develop
    merge phase-1/trading-risk tag: "v0.3.0"

    branch phase-1/frontend
    checkout phase-1/frontend
    commit id: "Dashboard"
    commit id: "Trading UI"
    checkout develop
    merge phase-1/frontend tag: "v0.4.0"

    branch phase-1/notifications
    checkout phase-1/notifications
    commit id: "Email provider"
    commit id: "WhatsApp provider"
    checkout develop
    merge phase-1/notifications tag: "v0.5.0"

    branch phase-1/algo-trading
    checkout phase-1/algo-trading
    commit id: "Strategy framework"
    commit id: "Built-in strategies"
    checkout develop
    merge phase-1/algo-trading tag: "v0.6.0"

    branch phase-1/testing
    checkout phase-1/testing
    commit id: "Unit tests"
    commit id: "E2E tests"
    checkout develop
    merge phase-1/testing

    checkout main
    merge develop tag: "v1.0.0 Phase 1"

    checkout develop
    branch phase-2/angelone
    checkout phase-2/angelone
    commit id: "Angel One API"
    checkout develop
    merge phase-2/angelone

    branch phase-2/live-safety
    checkout phase-2/live-safety
    commit id: "Safety features"
    checkout develop
    merge phase-2/live-safety

    checkout main
    merge develop tag: "v2.0.0 Phase 2"
```

---

## 🎯 PHASE 1: Paper Trading Platform (Weeks 1-6)

**Goal**: Complete trading platform with simulated execution using free data APIs

### Phase 1 Overview Diagram

```mermaid
flowchart TB
    subgraph Phase1["📊 PHASE 1: Paper Trading Platform (Weeks 1-7)"]
        direction TB

        subgraph Week1["Week 1: Infrastructure"]
            W1A[Data Provider Abstraction]
            W1B[Broker Abstraction]
            W1C[Notification Abstraction]
            W1D[Symbol System]
        end

        subgraph Week2["Week 2: Indian Market"]
            W2A[NSE Data Provider]
            W2B[Instrument Master]
        end

        subgraph Week3["Week 3: Trading + Risk"]
            W3A[All Order Types]
            W3B[Position Management]
            W3C[Risk Limits]
        end

        subgraph Week4["Week 4: Frontend + Notifications"]
            W4A[Dashboard]
            W4B[Portfolio View]
            W4C[Order Entry]
            W4D[Charts]
            W4E[Notification UI]
        end

        subgraph Week5["Week 5: Signals + Notifications"]
            W5A[Signal Engine]
            W5B[Backtesting]
            W5C[Email Provider]
            W5D[WhatsApp Provider]
        end

        subgraph Week6["Week 6: 🤖 Algo Trading"]
            W6A[Strategy Framework]
            W6B[Built-in Strategies]
            W6C[Executor + Scheduler]
            W6D[Safety Controls]
        end

        subgraph Week7["Week 7: 🔍 Research + Testing"]
            W7A[Stock Screener]
            W7B[Recommendations]
            W7C[Unit + E2E Tests]
        end

        subgraph Week8["Week 8-9: 🎨 UX Improvements"]
            W8A[Trade from Charts]
            W8B[Keyboard Shortcuts]
            W8C[Accessibility]
            W8D[Toast Notifications]
        end

        Week1 --> Week2 --> Week3 --> Week4 --> Week5 --> Week6 --> Week7 --> Week8
    end

    subgraph Providers["🔌 Provider Abstraction Layer"]
        DP[Data Providers]
        BP[Broker Providers]
        NP[Notification Providers]
    end

    DP --> |Yahoo/NSE| Phase1
    BP --> |Paper Trading| Phase1
    NP --> |Email/WhatsApp/UI| Phase1

    subgraph Phase2["🚀 PHASE 2: Live Trading (Weeks 8-9)"]
        P2A[Angel One Integration]
        P2B[Live Safety Features]
    end

    Phase1 -->|"Validation ✅"| Phase2
    DP --> |Angel One Data| Phase2
    BP --> |Angel One Broker| Phase2

    style Phase1 fill:#e8f5e9,stroke:#4caf50
    style Week6 fill:#bbdefb,stroke:#1976d2
    style Providers fill:#f3e5f5,stroke:#9c27b0
    style Phase2 fill:#e3f2fd,stroke:#2196f3
```

### Current Status Assessment

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI Backend | ✅ Done | Full module structure with 15+ modules |
| PostgreSQL + TimescaleDB | ✅ Done | Docker configured with Alembic migrations |
| Redis | ✅ Done | Docker configured for caching and Celery |
| Celery Workers | ✅ Done | Tasks for trading, signals, screener, research, algo |
| Authentication | ✅ Done | JWT-based auth with secure password hashing |
| Portfolio Models | ✅ Done | Positions, Trades, Funds, Holdings |
| Order Models | ✅ Done | Orders with full lifecycle, AMO support |
| Paper Trading Service | ✅ Done | Full broker implementation with SL/TP/trailing stop |
| Technical Analysis | ✅ Done | RSI, MACD, BB, ATR, Moving Averages, Supertrend |
| yfinance Integration | ✅ Done | US and Indian stocks working |
| Frontend | ✅ Done | Dashboard, Portfolio, Orders, Watchlist, Signals, Backtest, Algo, Research, Screener, Settings pages |
| Indian Stock Data | ✅ Done | NSE provider with 2220+ stocks, industry data for Nifty 500 |
| Abstracted Data Layer | ✅ Done | DataProvider + Yahoo + NSE + Fyers + Factory |
| Abstracted Broker Layer | ✅ Done | Broker + PaperBroker + FyersBroker + Factory |
| Symbol System | ✅ Done | Symbol + SymbolMapper for multi-exchange |
| Notification Abstraction | ✅ Done | NotificationProvider + Console provider + types defined |
| Instrument Master | ✅ Done | 2220+ NSE stocks with ISIN, industry, series |
| Instrument Sync | ✅ Done | Weekly scheduled sync + manual API endpoints |
| Market Status | ✅ Done | NSE trading hours awareness |
| Signal Engine | ✅ Done | 4 strategies (RSI, MACD, MA Crossover, Bollinger) with HOLD support |
| Backtesting | ✅ Done | BacktestRunner with full metrics (Sharpe, Sortino, Max DD, Win Rate) |
| Risk Management | ✅ Done | Position limits, sector concentration, SL/TP enforcement, auto square-off |
| Stock Screener | ✅ Done | Preset screeners, daily recommendations, performance tracking, algo integration with alerts |
| Research Module | ✅ Done | Fundamental data, news integration, sector heatmap, daily digest, recommendations |
| Algo Trading Engine | ✅ Done | Strategy framework, executor, scheduler, safety controls, kill switch |
| Trading Engine Service | ✅ Done | Standalone service for algo execution |
| Fyers Integration | ✅ Done | Full broker + data provider implementation |
| UX Improvements | ✅ Done | Keyboard shortcuts, error boundaries, accessibility, toast notifications |
| Dashboard Carousel | ✅ Done | Unified recommendations carousel with screener + research picks |
| Alerts/Notifications Impl | ⚠️ Partial | Console provider done, Email/WhatsApp pending |


### 1.1 Core Infrastructure (Week 1)
> 🌿 **Branch:** `phase-1/infrastructure`

#### Data Flow Diagram

```mermaid
flowchart LR
    subgraph External["🌐 External Data Sources"]
        Yahoo[Yahoo Finance API]
        NSE[NSE India API]
        Angel[Angel One API]
    end

    subgraph DataProviders["📊 Data Provider Layer"]
        DP[DataProvider Interface]
        YahooProvider[Yahoo Provider]
        NSEProvider[NSE Provider]
        AngelProvider[Angel Provider]
        Factory[ProviderFactory]
    end

    subgraph Cache["⚡ Caching Layer"]
        Redis[(Redis Cache)]
        TTL[TTL Management]
    end

    subgraph Storage["💾 Persistent Storage"]
        TimescaleDB[(TimescaleDB)]
        OHLCV[OHLCV Tables]
        Instruments[Instrument Master]
    end

    subgraph Consumers["🔄 Data Consumers"]
        Trading[Trading Module]
        Analysis[Analysis Module]
        Algo[Algo Engine]
        Signals[Signal Generator]
    end

    Yahoo --> YahooProvider
    NSE --> NSEProvider
    Angel --> AngelProvider

    YahooProvider --> DP
    NSEProvider --> DP
    AngelProvider --> DP

    Factory --> DP
    DP --> Redis
    Redis --> Storage

    Storage --> Consumers
    Redis --> Consumers

    style External fill:#e3f2fd,stroke:#1976d2
    style DataProviders fill:#f3e5f5,stroke:#9c27b0
    style Cache fill:#fff3e0,stroke:#ff9800
    style Storage fill:#e8f5e9,stroke:#4caf50
    style Consumers fill:#fce4ec,stroke:#e91e63
```

#### 1.1.1 Abstract Data Provider Layer
Create a pluggable data provider system so we can switch between Yahoo Finance, NSE, or Angel One.

```
backend/app/providers/
├── __init__.py
├── data/
│   ├── __init__.py
│   ├── base.py              # Abstract DataProvider interface
│   ├── yahoo.py             # Yahoo Finance implementation
│   ├── nse.py               # NSE India implementation
│   └── factory.py           # DataProviderFactory
```

**Tasks:**
- [x] Create `DataProvider` abstract base class
  - `get_quote(symbol) -> Quote`
  - `get_historical(symbol, period, interval) -> List[OHLCV]`
  - `search_symbols(query) -> List[Symbol]`
  - `get_instrument_info(symbol) -> InstrumentInfo`
- [x] Migrate existing yfinance code to `YahooDataProvider`
- [ ] Create `NSEDataProvider` using free NSE APIs *(deferred to phase-1/indian-market)*
- [x] Create `DataProviderFactory` for runtime selection
- [x] Add `DATA_PROVIDER` config setting

#### 1.1.2 Abstract Broker Layer
Create a pluggable broker system for order execution.

```
backend/app/providers/
├── broker/
│   ├── __init__.py
│   ├── base.py              # Abstract Broker interface
│   ├── paper.py             # Paper trading implementation
│   ├── factory.py           # BrokerFactory
```

**Tasks:**
- [x] Create `Broker` abstract base class
  - `place_order(order) -> OrderResponse`
  - `cancel_order(order_id) -> bool`
  - `modify_order(order_id, changes) -> OrderResponse`
  - `get_order_status(order_id) -> OrderStatus`
  - `get_positions() -> List[Position]`
  - `get_funds() -> Funds`
- [x] Migrate existing paper trading to `PaperBroker`
- [x] Create `BrokerFactory` for runtime selection
- [x] Add `BROKER_TYPE` config setting (paper/live)

#### 1.1.3 Unified Symbol System
Handle different symbol formats across exchanges.

**Tasks:**
- [x] Create `Symbol` model with exchange-specific tokens
  - `symbol` (display name: "RELIANCE")
  - `exchange` (NSE, BSE, NYSE, NASDAQ)
  - `token` (exchange-specific ID)
  - `isin` (for Indian stocks)
- [x] Create symbol mapper for Indian stocks
- [x] Handle Yahoo format (RELIANCE.NS) vs broker format (RELIANCE-EQ)

---

### 1.2 Indian Market Data (Week 2)
> 🌿 **Branch:** `phase-1/indian-market`

#### 1.2.1 NSE Data Provider ✅
Free NSE data for Indian stocks.

**Tasks:**
- [x] Implement NSE data fetching
  - [x] Get live quotes from NSE website/API
  - [x] Get historical data from NSE archives
  - [x] Get index data (Nifty 50, Bank Nifty)
- [x] Handle market hours (9:15 AM - 3:30 PM IST)
- [x] Cache frequently accessed data in Redis
- [x] Rate limiting to avoid blocks

#### 1.2.2 Instrument Master Database ✅
Store all tradeable instruments.

**Tasks:**
- [x] Create `Instrument` model
  ```python
  class Instrument:
      symbol: str
      name: str
      exchange: str  # NSE, BSE
      segment: str   # EQ, FO, CD
      token: str     # Exchange token
      lot_size: int  # For F&O
      tick_size: Decimal
      expiry: date   # For F&O
  ```
- [x] Daily job to download instrument master
- [x] Search endpoint for instruments
- [x] Filter by segment (Equity, F&O, etc.)

---

### 1.3 Enhanced Trading System (Week 2-3)
> 🌿 **Branch:** `phase-1/trading-risk`

#### Order Lifecycle Diagram

```mermaid
stateDiagram-v2
    [*] --> PENDING: Order Created

    PENDING --> VALIDATING: Submit Order

    VALIDATING --> REJECTED: Validation Failed
    VALIDATING --> OPEN: Validation Passed

    OPEN --> PARTIALLY_FILLED: Partial Execution
    OPEN --> FILLED: Full Execution
    OPEN --> CANCELLED: User Cancelled
    OPEN --> EXPIRED: Time Expired

    PARTIALLY_FILLED --> FILLED: Remaining Filled
    PARTIALLY_FILLED --> CANCELLED: User Cancelled

    REJECTED --> [*]
    FILLED --> [*]
    CANCELLED --> [*]
    EXPIRED --> [*]

    note right of VALIDATING
        Checks:
        - Risk limits
        - Buying power
        - Position limits
        - Market hours
    end note

    note right of OPEN
        Paper: Simulated execution
        Live: Sent to broker
    end note
```

#### 1.3.1 Order Management
Enhance the order system to support all order types.

**Tasks:**
- [x] Extend order types
  - [x] Market Order
  - [x] Limit Order
  - [x] Stop Loss (SL)
  - [x] Stop Loss Market (SL-M)
- [x] Order validation
  - [x] Check market hours
  - [x] Validate price vs LTP (circuit limits)
  - [x] Validate quantity (lot size for F&O)
  - [x] Check available funds/margin
- [x] Order lifecycle events
  - [x] PENDING → OPEN → FILLED/CANCELLED/REJECTED
  - [x] Partial fills tracking
- [x] GTT orders (simulated for paper trading)

#### 1.3.2 Position Management
Enhanced position tracking.

**Tasks:**
- [x] Separate delivery vs intraday positions
- [x] Track P&L (realized + unrealized)
- [x] Day-wise P&L tracking
- [x] Average price calculation (FIFO method)
- [x] Position limits and warnings

#### 1.3.3 Funds & Margins ✅
Track virtual funds for paper trading.

**Tasks:**
- [x] Create `Funds` model (`UserFunds` in `backend/app/modules/portfolio/models.py`)
  - `user_id`, `cash_balance`, `margin_used`, `available_margin`, `collateral`
- [x] Initialize new users with virtual cash (via `FundsService.initialize_funds()`)
- [x] Update funds on trade execution (via `FundsService.process_trade_settlement()`)
- [ ] Margin calculation for F&O (basic) - *deferred to F&O implementation*

---

### 1.4 Risk Management (Week 3)
> 🌿 **Branch:** `phase-1/trading-risk` *(continues from 1.3)*

#### Risk Management Flow Diagram

```mermaid
flowchart TB
    subgraph Input["📥 Order/Trade Input"]
        NewOrder[New Order Request]
        AlgoSignal[Algo Signal]
    end

    subgraph PreTrade["🔍 Pre-Trade Risk Checks"]
        direction TB
        PositionSize[Position Size Check<br/>Max % of portfolio]
        BuyingPower[Buying Power Check<br/>Available funds]
        DailyLimit[Daily Trade Limit<br/>Max trades/day]
        SectorLimit[Sector Concentration<br/>Max % per sector]
    end

    subgraph Decision{{"✅ All Checks Pass?"}}
    end

    subgraph Execute["💹 Order Execution"]
        PlaceOrder[Place Order]
        UpdatePosition[Update Position]
    end

    subgraph PostTrade["📊 Post-Trade Monitoring"]
        direction TB
        PnLTracking[P&L Tracking]
        DailyLoss[Daily Loss Check<br/>Max loss limit]
        Drawdown[Drawdown Monitor<br/>Max drawdown %]
        AutoSquareOff[Auto Square-Off<br/>Time-based]
    end

    subgraph Actions["⚠️ Risk Actions"]
        Reject[Reject Order]
        Alert[Send Alert]
        StopTrading[Stop All Trading]
        SquareOff[Square Off Positions]
    end

    Input --> PreTrade
    PreTrade --> Decision
    Decision -->|Yes| Execute
    Decision -->|No| Reject
    Reject --> Alert

    Execute --> PostTrade
    PostTrade -->|Loss Limit Hit| StopTrading
    PostTrade -->|Drawdown Exceeded| Alert
    PostTrade -->|Time Trigger| SquareOff
    StopTrading --> Alert
    SquareOff --> Alert

    style Input fill:#e3f2fd,stroke:#1976d2
    style PreTrade fill:#fff3e0,stroke:#ff9800
    style Execute fill:#e8f5e9,stroke:#4caf50
    style PostTrade fill:#f3e5f5,stroke:#9c27b0
    style Actions fill:#ffebee,stroke:#c62828
```

#### 1.4.1 Position Risk
**Tasks:**
- [x] Max position size per stock (% of portfolio)
- [x] Max sector concentration
- [x] Stop loss enforcement (auto square-off)
- [x] Take profit enforcement

#### 1.4.2 Daily Risk Limits
**Tasks:**
- [x] Max daily loss limit (stop trading for day)
- [x] Max number of trades per day
- [x] Max intraday exposure
- [x] Alert when approaching limits

#### 1.4.3 Market Hours & Auto Square-off ✅
**Tasks:**
- [x] Define market hours per exchange
- [x] Block orders outside market hours (or queue them)
- [x] Auto square-off intraday positions at 3:15 PM
- [x] Pre-market/After-market order handling (AMO - After Market Orders)
  - `is_amo` flag in order creation
  - `AMO_PENDING` status for queued orders
  - Celery task to process AMO orders at market open (9:15 AM IST)

---

### 1.5 Frontend Development (Week 3-4)
> 🌿 **Branch:** `phase-1/frontend`

#### Frontend Architecture Diagram

```mermaid
flowchart TB
    subgraph NextJS["🖥️ Next.js Frontend"]
        subgraph Pages["📄 Pages/Routes"]
            Dashboard["/dashboard"]
            Portfolio["/portfolio"]
            Trading["/trading"]
            Charts["/charts"]
            Watchlist["/watchlist"]
            Algo["/algo"]
            Backtest["/backtest"]
            Settings["/settings"]
        end

        subgraph Components["🧩 Components"]
            direction TB
            subgraph UI["UI Components"]
                Button[Buttons]
                Cards[Cards]
                Tables[Tables]
                Modals[Modals]
            end
            subgraph Feature["Feature Components"]
                PortfolioView[Portfolio View]
                OrderForm[Order Entry Form]
                ChartWidget[Chart Widget]
                NotificationBell[Notification Bell]
                StrategyCard[Strategy Card]
            end
        end

        subgraph State["📦 State Management"]
            ReactQuery[React Query<br/>Server State]
            Zustand[Zustand<br/>Client State]
        end

        subgraph Services["🔌 API Services"]
            APIClient[API Client]
            WebSocketClient[WebSocket Client]
        end
    end

    subgraph Backend["⚙️ Backend APIs"]
        REST[REST API<br/>FastAPI]
        WS[WebSocket<br/>Real-time]
    end

    Pages --> Components
    Components --> State
    State --> Services
    Services --> Backend

    style NextJS fill:#e3f2fd,stroke:#1976d2
    style Pages fill:#e8f5e9,stroke:#4caf50
    style Components fill:#f3e5f5,stroke:#9c27b0
    style State fill:#fff3e0,stroke:#ff9800
    style Services fill:#fce4ec,stroke:#e91e63
    style Backend fill:#e0f2f1,stroke:#00897b
```

#### 1.5.1 Dashboard ✅
**Tasks:**
- [x] Portfolio summary widget
  - Total value, day P&L, overall P&L
- [x] Top gainers/losers
- [x] Recent trades
- [x] Market overview (Nifty, Bank Nifty, Sensex)

#### 1.5.2 Portfolio View ✅
**Tasks:**
- [x] Holdings table (symbol, qty, avg cost, LTP, P&L, %)
- [x] Sector allocation pie chart
- [x] Performance chart (value over time)
- [x] Export to CSV

#### 1.5.3 Trading Interface ✅
**Tasks:**
- [x] Order entry form
  - Buy/Sell toggle
  - Market/Limit selector
  - Quantity, Price, Stop Loss, Target
- [x] Order confirmation modal
- [x] Order book (pending orders)
- [x] Trade history

#### 1.5.4 Charts ✅
**Tasks:**
- [x] Candlestick chart (TradingView Lightweight Charts or similar)
- [x] Technical indicators overlay (moving averages, Bollinger)
- [x] Volume bars
- [ ] Drawing tools (basic) - *Deferred to future enhancement*

#### 1.5.5 Watchlist ✅
**Tasks:**
- [x] Multiple watchlists support
- [x] Add/remove symbols
- [x] Live price updates
- [x] Quick buy/sell from watchlist

#### 1.5.6 Alerts Configuration ✅
**Tasks:**
- [x] Price alerts (above/below threshold)
- [x] Order execution alerts
- [x] Daily P&L summary alerts
- [x] Strategy signal alerts
- [x] Risk limit breach alerts

---

### 1.6 Notification System (Week 4-5)
> 🌿 **Branch:** `phase-1/notifications`
>
> 📖 **Implementation Guide:** [notification-system-implementation.md](./notification-system-implementation.md)

**Goal**: Modular notification system that can send alerts via multiple channels. New channels can be added without changing core code.

#### Notification Flow Diagram

```mermaid
flowchart TB
    subgraph Triggers["📢 Notification Triggers"]
        OrderEvents[Order Events<br/>placed/filled/cancelled]
        PriceAlerts[Price Alerts<br/>target hit]
        AlgoSignals[Algo Signals<br/>buy/sell generated]
        RiskBreaches[Risk Breaches<br/>limits exceeded]
        SystemAlerts[System Alerts<br/>errors/warnings]
    end

    subgraph NotificationService["🔔 Notification Service"]
        Orchestrator[NotificationOrchestrator]
        UserPrefs[(User Preferences)]
        Templates[Message Templates]
        RateLimiter[Rate Limiter]
        QuietHours[Quiet Hours Check]
    end

    subgraph Providers["📤 Notification Providers"]
        direction TB
        EmailProvider[📧 Email Provider<br/>SMTP/SendGrid/SES]
        WhatsAppProvider[💬 WhatsApp Provider<br/>Twilio API]
        WebSocketProvider[🔌 WebSocket Provider<br/>Real-time UI]
        SMSProvider[📱 SMS Provider<br/>Twilio/MSG91]
        PushProvider[📲 Push Provider<br/>FCM/APNs]
    end

    subgraph Destinations["👤 User Channels"]
        EmailInbox[Email Inbox]
        WhatsAppChat[WhatsApp Chat]
        UINotification[UI Notification Bell]
        SMSMessage[SMS Message]
        MobileApp[Mobile App]
    end

    Triggers --> Orchestrator
    Orchestrator --> UserPrefs
    Orchestrator --> Templates
    Orchestrator --> RateLimiter
    Orchestrator --> QuietHours

    Orchestrator --> EmailProvider
    Orchestrator --> WhatsAppProvider
    Orchestrator --> WebSocketProvider
    Orchestrator --> SMSProvider
    Orchestrator --> PushProvider

    EmailProvider --> EmailInbox
    WhatsAppProvider --> WhatsAppChat
    WebSocketProvider --> UINotification
    SMSProvider --> SMSMessage
    PushProvider --> MobileApp

    style Triggers fill:#ffebee,stroke:#c62828
    style NotificationService fill:#e3f2fd,stroke:#1976d2
    style Providers fill:#f3e5f5,stroke:#9c27b0
    style Destinations fill:#e8f5e9,stroke:#4caf50
```

#### 1.6.1 Notification Provider Abstraction

```
backend/app/providers/
├── notification/
│   ├── __init__.py
│   ├── base.py              # Abstract NotificationProvider interface
│   ├── email.py             # Email (SMTP/SendGrid/SES)
│   ├── whatsapp.py          # WhatsApp (Twilio/WhatsApp Business API)
│   ├── sms.py               # SMS (Twilio/MSG91)
│   ├── push.py              # Push notifications (FCM/APNs)
│   ├── websocket.py         # Real-time UI notifications
│   ├── telegram.py          # Telegram bot (future)
│   ├── discord.py           # Discord webhook (future)
│   └── factory.py           # NotificationProviderFactory
```

**Tasks:**
- [ ] Create `NotificationProvider` abstract base class
  ```python
  from abc import ABC, abstractmethod
  from enum import Enum

  class NotificationPriority(Enum):
      LOW = "low"           # Daily summaries
      MEDIUM = "medium"     # Order fills, signals
      HIGH = "high"         # Risk alerts
      CRITICAL = "critical" # Kill switch, margin call

  class NotificationProvider(ABC):
      name: str
      supports_rich_content: bool  # HTML, images, etc.

      @abstractmethod
      async def send(
          self,
          user_id: str,
          title: str,
          message: str,
          priority: NotificationPriority = NotificationPriority.MEDIUM,
          data: dict | None = None,  # Additional structured data
      ) -> bool:
          """Send notification. Returns True if successful."""
          pass

      @abstractmethod
      async def send_bulk(
          self,
          user_ids: list[str],
          title: str,
          message: str,
          priority: NotificationPriority = NotificationPriority.MEDIUM,
      ) -> dict[str, bool]:
          """Send to multiple users. Returns {user_id: success}."""
          pass

      @abstractmethod
      async def is_available(self, user_id: str) -> bool:
          """Check if this channel is configured for user."""
          pass
  ```
- [ ] Create `NotificationProviderFactory`
- [ ] Support for enabling/disabling providers via config

#### 1.6.2 Email Notifications
**Tasks:**
- [ ] Implement `EmailNotificationProvider`
  - SMTP support (Gmail, custom SMTP)
  - SendGrid integration (optional)
  - AWS SES integration (optional)
- [ ] HTML email templates
  - Order confirmation
  - Daily P&L summary
  - Alert triggered
  - Strategy signal
- [ ] Email queue with retry logic
- [ ] Unsubscribe handling

#### 1.6.3 WhatsApp Notifications
**Tasks:**
- [ ] Implement `WhatsAppNotificationProvider`
  - Twilio WhatsApp API
  - WhatsApp Business API (for scale)
- [ ] Message templates (WhatsApp requires pre-approved templates)
  - Order executed: "✅ {side} {qty} {symbol} @ ₹{price}"
  - Alert: "🚨 {symbol} crossed ₹{price}"
  - Daily summary: "📊 Today's P&L: ₹{pnl}"
- [ ] Rich message formatting
- [ ] Rate limiting (WhatsApp has strict limits)

#### 1.6.4 Real-time UI Notifications (WebSocket)
**Tasks:**
- [ ] Implement `WebSocketNotificationProvider`
  - WebSocket connection management
  - Reconnection handling
  - Message queuing for offline users
- [ ] Frontend notification system
  - Toast notifications (non-blocking)
  - Notification bell with badge count
  - Notification center/drawer
  - Sound alerts (optional)
- [ ] Notification persistence
  - Store in database
  - Mark as read/unread
  - Notification history

#### 1.6.5 Push Notifications (Optional - for future mobile)
**Tasks:**
- [ ] Implement `PushNotificationProvider`
  - Firebase Cloud Messaging (FCM) for Android
  - Apple Push Notification Service (APNs) for iOS
- [ ] Device token management
- [ ] Rich push (images, action buttons)

#### 1.6.6 Notification Service & Orchestrator
Central service that routes notifications to appropriate channels.

**Tasks:**
- [ ] Create `NotificationService`
  ```python
  class NotificationService:
      def __init__(self, providers: list[NotificationProvider]):
          self.providers = providers

      async def notify(
          self,
          user_id: str,
          notification_type: NotificationType,
          title: str,
          message: str,
          priority: NotificationPriority = NotificationPriority.MEDIUM,
          data: dict | None = None,
          channels: list[str] | None = None,  # None = use user preferences
      ) -> dict[str, bool]:
          """
          Send notification via configured channels.
          Returns {channel: success} dict.
          """
          pass

      async def notify_bulk(
          self,
          user_ids: list[str],
          notification_type: NotificationType,
          title: str,
          message: str,
      ) -> dict[str, dict[str, bool]]:
          """Bulk notify multiple users."""
          pass
  ```
- [ ] Channel routing based on:
  - User preferences
  - Notification priority
  - Notification type
  - Time of day (quiet hours)
- [ ] Fallback chain (if WhatsApp fails, try email)
- [ ] Rate limiting per user per channel
- [ ] Notification deduplication

#### 1.6.7 User Notification Preferences
**Tasks:**
- [ ] Create `NotificationPreferences` model
  ```python
  class NotificationPreferences:
      user_id: str

      # Channel settings
      email_enabled: bool = True
      email_address: str

      whatsapp_enabled: bool = False
      whatsapp_number: str  # With country code

      push_enabled: bool = True

      ui_enabled: bool = True
      ui_sound: bool = True

      # Per-type settings
      order_notifications: list[str]  # ["email", "whatsapp", "ui"]
      alert_notifications: list[str]
      signal_notifications: list[str]
      daily_summary: list[str]
      risk_alerts: list[str]  # Always include critical channels

      # Quiet hours
      quiet_hours_enabled: bool = False
      quiet_hours_start: time  # e.g., 22:00
      quiet_hours_end: time    # e.g., 08:00
      quiet_hours_timezone: str
  ```
- [ ] Preferences UI in settings
- [ ] Channel verification (verify email, WhatsApp number)
- [ ] Default preferences for new users

#### 1.6.8 Notification Types & Templates
**Tasks:**
- [ ] Define notification types
  ```python
  class NotificationType(Enum):
      # Trading
      ORDER_PLACED = "order_placed"
      ORDER_FILLED = "order_filled"
      ORDER_CANCELLED = "order_cancelled"
      ORDER_REJECTED = "order_rejected"

      # Alerts
      PRICE_ALERT = "price_alert"

      # Algo
      SIGNAL_GENERATED = "signal_generated"
      STRATEGY_STARTED = "strategy_started"
      STRATEGY_STOPPED = "strategy_stopped"
      STRATEGY_ERROR = "strategy_error"

      # Risk
      RISK_LIMIT_WARNING = "risk_limit_warning"
      RISK_LIMIT_BREACH = "risk_limit_breach"
      MARGIN_WARNING = "margin_warning"
      KILL_SWITCH_TRIGGERED = "kill_switch_triggered"

      # Reports
      DAILY_SUMMARY = "daily_summary"
      WEEKLY_REPORT = "weekly_report"

      # System
      SYSTEM_ALERT = "system_alert"
      MAINTENANCE = "maintenance"
  ```
- [ ] Template system for each notification type
- [ ] Localization support (English, Hindi)
- [ ] Variable substitution in templates

#### 1.6.9 Notification Queue & Delivery
**Tasks:**
- [ ] Celery task for async notification delivery
- [ ] Retry logic with exponential backoff
- [ ] Dead letter queue for failed notifications
- [ ] Delivery status tracking
- [ ] Analytics (open rates for email, delivery rates)

#### 1.6.10 Notification Frontend Components
**Tasks:**
- [ ] `NotificationBell` component
  - Badge with unread count
  - Dropdown with recent notifications
  - Click to open notification center
- [ ] `NotificationCenter` page/modal
  - List of all notifications
  - Filter by type, read status
  - Mark as read, mark all as read
  - Clear notifications
- [ ] `Toast` component for real-time alerts
  - Different styles for priority levels
  - Auto-dismiss with configurable duration
  - Action buttons (e.g., "View Order")
- [ ] `NotificationSettings` page
  - Channel configuration
  - Per-type preferences
  - Quiet hours
  - Test notification button

---

### 1.7 Signal Generation & Backtesting (Week 5)
> 🌿 **Branch:** `phase-1/signals-backtest`

#### Signal & Backtest Flow Diagram

```mermaid
flowchart TB
    subgraph DataInput["📊 Market Data"]
        HistoricalData[(Historical OHLCV)]
        LiveData[Live Price Feed]
    end

    subgraph Indicators["📈 Technical Indicators"]
        RSI[RSI]
        MACD[MACD]
        MA[Moving Averages]
        BB[Bollinger Bands]
        ATR[ATR]
    end

    subgraph SignalEngine["🚦 Signal Engine"]
        StrategyRunner[Strategy Runner]
        SignalGen[Signal Generator]
        SignalFilter[Signal Filter<br/>Strength threshold]
    end

    subgraph Signals["📢 Signals"]
        BuySignal[🟢 BUY Signal]
        SellSignal[🔴 SELL Signal]
        HoldSignal[🟡 HOLD Signal]
    end

    subgraph Backtesting["🔬 Backtesting Framework"]
        BacktestEngine[Backtest Engine]
        SimulatedTrades[Simulated Trades]
        PerformanceCalc[Performance Calculator]
    end

    subgraph Metrics["📊 Performance Metrics"]
        TotalReturn[Total Return / CAGR]
        Sharpe[Sharpe Ratio]
        MaxDrawdown[Max Drawdown]
        WinRate[Win Rate]
        ProfitFactor[Profit Factor]
    end

    subgraph Validation["✅ Validation"]
        PaperTrade[Paper Trading Test]
        Compare[Compare Results]
    end

    DataInput --> Indicators
    Indicators --> SignalEngine
    SignalEngine --> Signals

    HistoricalData --> Backtesting
    SignalEngine --> Backtesting
    Backtesting --> Metrics

    Metrics --> Validation
    Signals --> PaperTrade
    PaperTrade --> Compare

    style DataInput fill:#e3f2fd,stroke:#1976d2
    style Indicators fill:#fff3e0,stroke:#ff9800
    style SignalEngine fill:#e8f5e9,stroke:#4caf50
    style Signals fill:#f3e5f5,stroke:#9c27b0
    style Backtesting fill:#fce4ec,stroke:#e91e63
    style Metrics fill:#e0f2f1,stroke:#00897b
    style Validation fill:#f5f5f5,stroke:#616161
```

#### 1.7.1 Signal Engine ✅
**Tasks:**
- [x] Define Signal schema
  ```python
  class Signal:
      symbol: str
      signal_type: str  # BUY, SELL, HOLD
      strength: float   # 0.0 to 1.0
      strategy: str     # Which strategy generated it
      indicators: dict  # Supporting data
      generated_at: datetime
  ```
- [x] Strategy runner framework (BaseStrategy ABC + StrategyRegistry)
- [x] Built-in strategies:
  - [x] RSI Oversold/Overbought
  - [x] MACD Crossover
  - [x] Moving Average Crossover (SMA/EMA)
  - [x] Bollinger Band Squeeze
- [x] Signal persistence and history
- [x] HOLD signal support for all strategies
- [x] API endpoints for signal generation and listing
- [x] Celery tasks for scheduled signal generation

#### 1.7.2 Backtesting Framework ✅
**Tasks:**
- [x] Historical data loader (via yfinance)
- [x] Strategy backtester (BacktestRunner)
  - Apply strategy to historical data
  - Track simulated trades
  - Calculate returns
- [x] Performance metrics
  - Total return, CAGR
  - Sharpe ratio, Sortino ratio
  - Max drawdown
  - Win rate, Profit factor
- [x] Backtest results visualization (equity curve chart)
- [x] Backtest API endpoints
- [x] Backtest Celery tasks for async execution

#### 1.7.3 Frontend UI ✅
**Tasks:**
- [x] Signals page with signal listing and generation
- [x] Backtest page with configuration form
- [x] Equity curve visualization
- [x] Strategy selection dropdown
- [x] Confidence display fix (0-1 to percentage conversion)

---

### 1.8 Algo Trading Engine (Week 5-6)
> 🌿 **Branch:** `phase-1/algo-trading`

**Goal**: Fully automated trading system that can run strategies without manual intervention

#### Algo Trading Flow Diagram

```mermaid
flowchart TB
    subgraph Scheduler["⏰ Strategy Scheduler"]
        CronJob[Cron/Interval Trigger]
        MarketHours[Market Hours Check]
        ScheduleDB[(Strategy Schedules)]
    end

    subgraph DataLayer["📊 Data Layer"]
        DataProvider[Data Provider]
        OHLCV[OHLCV Data]
        Indicators[Technical Indicators]
    end

    subgraph StrategyEngine["🧠 Strategy Engine"]
        direction TB
        subgraph Strategies["Available Strategies"]
            RSI[RSI Strategy]
            MACD[MACD Crossover]
            MA[Moving Average]
            BB[Bollinger Bands]
            Custom[Custom Strategies]
        end
        SignalGen[Signal Generator]
        PositionSizer[Position Sizer]
    end

    subgraph RiskLayer["⚠️ Risk Management"]
        RiskCheck[Risk Validator]
        DailyLoss[Daily Loss Limit]
        PositionLimit[Position Limits]
        CircuitBreaker[Circuit Breakers]
    end

    subgraph Execution["💹 Execution"]
        OrderQueue[Order Queue]
        Executor[Strategy Executor]
        Broker[Broker Provider]
    end

    subgraph Safety["🛡️ Safety Controls"]
        KillSwitch[Kill Switch]
        RateLimiter[Rate Limiter]
        AuditLog[(Audit Log)]
    end

    subgraph Notifications["📢 Notifications"]
        NotifyService[Notification Service]
        Email[Email]
        WhatsApp[WhatsApp]
        UI[UI Alerts]
    end

    Scheduler --> DataLayer
    DataLayer --> StrategyEngine
    StrategyEngine --> |Signals| RiskLayer
    RiskLayer --> |Approved| Execution
    RiskLayer --> |Rejected| Notifications
    Execution --> Broker
    Execution --> Safety
    Broker --> Notifications
    Safety --> AuditLog

    style Scheduler fill:#fff3e0,stroke:#ff9800
    style DataLayer fill:#e3f2fd,stroke:#1976d2
    style StrategyEngine fill:#e8f5e9,stroke:#4caf50
    style RiskLayer fill:#ffebee,stroke:#c62828
    style Execution fill:#f3e5f5,stroke:#9c27b0
    style Safety fill:#fce4ec,stroke:#e91e63
    style Notifications fill:#e0f2f1,stroke:#00897b
```

#### 1.8.1 Strategy Framework ✅
Create a pluggable strategy system.

```
backend/app/modules/algo/
├── __init__.py
├── strategies/
│   ├── base.py              # Abstract Strategy interface
│   ├── momentum.py          # Momentum strategies
│   ├── mean_reversion.py    # Mean reversion strategies
│   ├── trend_following.py   # Trend following strategies
│   └── multi_factor.py      # Multi-factor strategies
├── executor.py              # Strategy executor
├── scheduler.py             # Job scheduler
├── models.py                # DB models
├── router.py                # API endpoints
└── schemas.py               # Pydantic schemas
```

**Tasks:**
- [x] Create `Strategy` abstract base class
  ```python
  class Strategy(ABC):
      name: str
      description: str
      timeframe: str          # 1m, 5m, 15m, 1h, 1d
      universe: List[str]     # Symbols to trade

      @abstractmethod
      def generate_signals(self, data: DataFrame) -> List[Signal]:
          """Generate trading signals from market data"""
          pass

      @abstractmethod
      def calculate_position_size(self, signal: Signal, portfolio: Portfolio) -> Decimal:
          """Determine position size based on risk rules"""
          pass

      def on_signal(self, signal: Signal) -> Optional[Order]:
          """Convert signal to order (can be overridden)"""
          pass
  ```
- [x] Create strategy registry for dynamic loading
- [x] Strategy configuration via YAML/JSON
- [x] Strategy versioning and history

#### 1.8.2 Built-in Strategies ✅

**Momentum Strategies:**
- [x] **RSI Strategy**
  - Buy when RSI < 30 (oversold)
  - Sell when RSI > 70 (overbought)
  - Configurable thresholds
- [x] **MACD Crossover**
  - Buy on bullish crossover (MACD crosses above signal)
  - Sell on bearish crossover
  - Histogram confirmation option
- [x] **Breakout Strategy**
  - Buy on breakout above N-day high
  - Sell on breakdown below N-day low
  - Volume confirmation

**Mean Reversion Strategies:**
- [x] **Bollinger Band Strategy**
  - Buy when price touches lower band
  - Sell when price touches upper band
  - Mean reversion to middle band
- [x] **Moving Average Reversion**
  - Buy when price is N% below MA
  - Sell when price is N% above MA

**Trend Following Strategies:**
- [x] **Moving Average Crossover**
  - Buy when fast MA crosses above slow MA
  - Sell when fast MA crosses below slow MA
  - Configurable periods (e.g., 9/21, 20/50, 50/200)
- [x] **Supertrend Strategy**
  - Buy on supertrend flip to bullish
  - Sell on supertrend flip to bearish

**Multi-Factor Strategies:**
- [x] **Combined Technical Strategy**
  - Requires multiple indicators to align
  - Weighted scoring system
  - Configurable factor weights

#### 1.8.3 Strategy Executor ✅
Runs strategies and executes orders automatically.

**Tasks:**
- [x] Create `StrategyExecutor` class
  ```python
  class StrategyExecutor:
      def __init__(self, strategy: Strategy, broker: Broker, data_provider: DataProvider):
          pass

      async def run_once(self) -> List[Order]:
          """Run strategy once and return orders"""
          pass

      async def start(self, interval_seconds: int):
          """Start continuous execution loop"""
          pass

      async def stop(self):
          """Stop execution"""
          pass
  ```
- [x] Order queue with rate limiting
- [x] Execution logging and audit trail
- [x] Error handling and recovery
- [x] Dry-run mode (generate signals but don't execute)

#### 1.8.4 Strategy Scheduler ✅
Schedule strategies to run at specific times/intervals.

**Tasks:**
- [x] Create `StrategySchedule` model
  ```python
  class StrategySchedule:
      id: str
      strategy_id: str
      user_id: str
      enabled: bool
      schedule_type: str      # interval | cron | market_hours
      interval_seconds: int   # For interval type
      cron_expression: str    # For cron type
      market_session: str     # pre_market | market | post_market
      last_run: datetime
      next_run: datetime
  ```
- [x] Celery Beat integration for scheduling
- [x] Market hours awareness (only run during trading hours)
- [x] Pre-market and post-market strategy support
- [x] Manual trigger option

#### 1.8.5 Universe Selection ✅
Define which stocks a strategy trades.

**Tasks:**
- [x] Create `Universe` model
  ```python
  class Universe:
      id: str
      name: str              # "Nifty 50", "Bank Nifty", "Custom"
      symbols: List[str]
      filter_criteria: dict  # Market cap, sector, liquidity
  ```
- [x] Pre-built universes:
  - [x] Nifty 50
  - [x] Nifty Next 50
  - [x] Bank Nifty
  - [x] F&O stocks
  - [x] Sectoral indices
- [x] Custom universe builder
- [x] Dynamic universe (e.g., top 10 by volume)

#### 1.8.6 Position Sizing & Money Management ✅
Automated position sizing based on risk.

**Tasks:**
- [x] Position sizing methods:
  - [x] Fixed quantity
  - [x] Fixed amount (₹ per trade)
  - [x] Percentage of portfolio
  - [x] Risk-based (% of portfolio at risk)
  - [x] Kelly criterion
  - [x] Volatility-adjusted (ATR-based)
- [x] Create `PositionSizer` class
  ```python
  class PositionSizer:
      def calculate(
          self,
          portfolio_value: Decimal,
          entry_price: Decimal,
          stop_loss: Decimal,
          risk_per_trade_pct: Decimal,
      ) -> int:
          """Calculate position size based on risk"""
          pass
  ```
- [x] Maximum position limits
- [x] Sector/correlation limits

#### 1.8.7 Algo Trading Dashboard (Frontend) ✅

**Tasks:**
- [x] Strategy management page
  - List of strategies (active/inactive)
  - Enable/disable toggle
  - Strategy configuration
- [x] Strategy performance view
  - P&L by strategy
  - Win rate, Sharpe ratio
  - Drawdown chart
- [x] Signals view
  - Real-time signal feed
  - Signal history
  - Signal to order mapping
- [x] Algo order book
  - Orders placed by algo
  - Execution status
  - Manual override option
- [ ] Strategy builder (future)
  - Drag-and-drop indicator selection
  - Condition builder
  - Backtest before deploy

#### 1.8.8 Algo Trading Safety Controls ✅

**Tasks:**
- [x] **Kill Switch**
  - One-click disable all algos
  - Cancel all pending algo orders
  - Optional: square off all algo positions
- [x] **Circuit Breakers**
  - Max daily loss per strategy
  - Max consecutive losses
  - Max drawdown limit
  - Auto-disable when triggered
- [x] **Rate Limits**
  - Max orders per minute
  - Max orders per day
  - Cooldown after order
- [x] **Monitoring & Alerts**
  - Strategy health monitoring
  - Execution quality alerts
  - Deviation from backtest alerts
  - API error alerts

---

### 1.9 Testing & Polish (Week 6-7)
> 🌿 **Branch:** `phase-1/testing`

#### 1.9.1 Automated Testing
**Tasks:**
- [ ] Unit tests for all services
- [ ] Integration tests for API endpoints
- [ ] Mock broker/data provider for tests
- [ ] Strategy backtesting validation
- [ ] CI/CD pipeline

#### 1.9.2 End-to-End Testing
**Tasks:**
- [ ] Complete manual trading flow (search → order → position → P&L)
- [ ] Complete algo trading flow (strategy → signal → order → position)
- [ ] Paper trading accuracy verification
- [ ] Error handling and edge cases
- [ ] Performance testing (high frequency signals)

#### 1.9.3 Documentation
**Tasks:**
- [ ] API documentation (auto-generated from FastAPI)
- [ ] User guide
- [ ] Developer setup guide
- [ ] Trading strategies documentation
- [ ] Algo trading guide (creating custom strategies)

---

### 1.10 Stock Screener & Research Module (Week 7)
> 🌿 **Branch:** `phase-1/screener`

**Goal**: Standalone stock screening facility that helps users discover trading candidates from large universes (2200+ stocks) with recommendations and seamless integration into trading workflow.

#### Screener Flow Diagram

```mermaid
flowchart TB
    subgraph Input["📊 Universe Selection"]
        Nifty50[Nifty 50]
        Nifty500[Nifty 500]
        AllNSE[All NSE Stocks<br/>2200+]
        Custom[Custom Universe]
    end

    subgraph Filters["🔍 Screening Filters"]
        direction TB
        VolumeFilter[Volume Filter<br/>Min volume, spikes]
        MomentumFilter[Momentum Filter<br/>RSI, ROC, 52w high]
        MAFilter[Moving Average<br/>Above/below trend]
        BreakoutFilter[Breakout Detection<br/>Range breakouts]
        ConsolidationFilter[Consolidation<br/>Tight ranges]
        SectorFilter[Sector Filter<br/>Industry groups]
    end

    subgraph Screener["⚡ Stock Screener"]
        ScreenerEngine[Screener Engine]
        Scoring[Weighted Scoring]
        Ranking[Ranking & Sorting]
    end

    subgraph Results["📋 Screener Results"]
        TopPicks[Top Picks<br/>Ranked by score]
        FilterBreakdown[Filter Breakdown<br/>Why each passed]
        Metadata[Stock Metadata<br/>Volume, momentum, etc.]
    end

    subgraph Actions["🎯 User Actions"]
        AddWatchlist[Add to Watchlist]
        ViewChart[View Chart]
        CreateStrategy[Create Algo Strategy]
        SetAlert[Set Alert]
        ManualTrade[Quick Trade]
    end

    subgraph Recommendations["💡 Daily Recommendations"]
        MomentumPicks[Top Momentum Stocks]
        BreakoutPicks[Potential Breakouts]
        ValuePicks[Value Opportunities]
        SectorLeaders[Sector Leaders]
    end

    Input --> Screener
    Filters --> Screener
    Screener --> Results
    Results --> Actions
    Screener --> Recommendations

    style Input fill:#e3f2fd,stroke:#1976d2
    style Filters fill:#fff3e0,stroke:#ff9800
    style Screener fill:#e8f5e9,stroke:#4caf50
    style Results fill:#f3e5f5,stroke:#9c27b0
    style Actions fill:#fce4ec,stroke:#e91e63
    style Recommendations fill:#e0f2f1,stroke:#00897b
```

#### 1.10.1 Screener API Endpoints ✅
Expose the existing screener module via REST API.

**Tasks:**
- [x] Create screener router (`/api/v1/screener`)
  - `GET /screener/presets` - List preset screeners (momentum, breakout, consolidation)
  - `POST /screener/run` - Run screener on universe with filters
  - `GET /screener/results/{id}` - Get cached screener results
  - `POST /screener/custom` - Save custom screener configuration
  - `GET /screener/custom` - List user's saved screeners
  - `DELETE /screener/custom/{id}` - Delete saved screener
- [x] Create screener schemas
  ```python
  class ScreenerRunRequest(BaseModel):
      universe: str  # "nifty50", "nifty500", "all_nse", or universe_id
      filters: list[FilterConfig]
      min_score: float = 50.0
      top_n: int = 50

  class FilterConfig(BaseModel):
      filter_type: str  # "volume", "momentum", "breakout", etc.
      params: dict      # Filter-specific parameters
      weight: float = 1.0

  class ScreenerResult(BaseModel):
      symbol: str
      rank: int
      score: float
      passed: bool
      filter_scores: dict[str, float]
      reasons: list[str]
      metadata: dict  # Current price, volume, momentum, etc.
  ```
- [x] Async screener execution with Celery for large universes
- [x] Result caching in Redis (TTL based on market hours)

#### 1.10.2 Preset Screeners ✅
Pre-configured screeners for common use cases.

**Tasks:**
- [x] **Momentum Screener**
  - High volume (>100K avg)
  - RSI between 50-70 (bullish but not overbought)
  - Near 52-week high (within 10%)
  - Above 20-day and 50-day MA
- [x] **Breakout Screener**
  - Breaking above 20-day range high
  - Volume spike (1.5x+ average)
  - Above all major moving averages
- [x] **Consolidation Screener** (pre-breakout candidates)
  - Tight price range (< 10% over 20 days)
  - Declining volume (squeeze)
  - Above trend lines
- [x] **Value Screener** (for swing trading)
  - Pullback to support (near 50-day MA)
  - RSI oversold (30-40 range)
  - Still in uptrend (above 200-day MA)
- [x] **Sector Rotation Screener**
  - Group by sector/industry
  - Find strongest sectors this week
  - Top stocks within strong sectors

#### 1.10.3 Daily Recommendations Widget ✅
Automated daily stock picks displayed on dashboard.

**Tasks:**
- [x] Celery task to run preset screeners daily at market open
- [x] Store recommendations in database with timestamp
- [x] API endpoint `GET /screener/recommendations`
- [x] Recommendation categories:
  - "🚀 Top Momentum Today" (momentum screener top 5)
  - "💥 Potential Breakouts" (breakout screener top 5)
  - "📈 Strong Sectors" (sector rotation analysis)
  - "🎯 Pullback Opportunities" (value screener top 5)
- [x] Recommendation history (what was recommended, did it work?)

#### 1.10.4 Frontend: Research/Screener Page ✅
New dedicated page for stock discovery.

**Tasks:**
- [x] Create `/research` or `/screener` page
- [x] **Universe Selector**
  - Dropdown: Nifty 50, Nifty 500, All NSE, Custom
  - Show stock count for each
- [x] **Filter Builder UI**
  - Add/remove filters
  - Configure filter parameters (sliders, inputs)
  - Set filter weights
  - Save as preset
- [x] **Results Table**
  - Sortable columns (rank, score, symbol, price, change%)
  - Filter score breakdown (expandable row)
  - Pagination for large results
  - Export to CSV
- [x] **Quick Actions per Stock**
  - "Add to Watchlist" button
  - "View Chart" button (opens chart modal/page)
  - "Create Alert" button
  - "Quick Trade" button (opens order form)
- [x] **Saved Screeners Sidebar**
  - List of user's saved screener configs (via preset selection)
  - One-click run
  - Edit/delete options

#### 1.10.5 Frontend: Screener Performance Widget ✅
Show daily picks and performance on screener page.

**Tasks:**
- [x] `PerformanceWidget` component
  - Tabbed view: Momentum | Pullbacks | Sectors
  - Show stocks per category with expandable lists
  - Compact card with Sheet slide-out for detailed view
  - Click to expand details
- [x] Link to full screener results
- [x] Win rate tracking (1D/1W/1M)
- [x] Timestamp showing when recommendations were generated

#### 1.10.6 Screener → Algo Integration ✅
Allow screener results to feed into algo trading.

**Tasks:**
- [x] "Create Strategy from Results" action
  - Takes top N screener results
  - Creates custom universe with those symbols
  - Links to strategy creation dialog
  - Endpoint: `POST /screener/create-strategy`
- [x] Dynamic screener-based universe
  - Universe type: "screener"
  - Re-runs screener to update symbols via `POST /screener/refresh-universe/{universe_id}`
  - Algo trades whatever passes the screen
  - Universe `filter_criteria` stores screener config for dynamic refresh
- [x] Screener alerts
  - ScreenerAlert model for alert configuration
  - CRUD endpoints: `POST/GET/PUT/DELETE /screener/alerts`
  - Celery task `process_screener_alerts` runs every 15 minutes
  - Tracks new/removed symbols compared to last run
  - Support for preset or custom screener alerts
  - Optional target symbol and minimum score threshold

#### 1.10.7 Performance Tracking ✅
Track screener effectiveness over time.

**Tasks:**
- [x] Store screener results with timestamp
- [x] Track what happened to recommended stocks
  - 1-day, 1-week, 1-month returns after recommendation
- [x] Screener performance dashboard
  - Win rate of recommendations
  - Average return of picks
  - Best performing preset screener (via category tabs)
- [ ] Use data to improve screener weights *(future enhancement)*

### 1.11 Research Module (Week 8) ✅
> 🌿 **Branch:** `phase-1/research`

**Status**: Complete - Full research module with fundamental data, news integration, sector heatmap, daily digest, and recommendations.

**Goal**: Comprehensive stock research capabilities combining fundamental data, news, and deep-dive analysis pages inspired by FYERS MarketSmith integration.

#### Research Module Flow Diagram

```mermaid
flowchart TB
    subgraph DataSources["📡 Data Sources"]
        TechnicalData[Technical Data<br/>Price, Volume, Indicators]
        FundamentalData[Fundamental Data<br/>P/E, EPS, Revenue]
        NewsData[News API<br/>Headlines, Sentiment]
        PeerData[Peer Comparison<br/>Industry averages]
    end

    subgraph ResearchEngine["🔬 Research Engine"]
        FundamentalFilters[Fundamental Filters<br/>P/E, EPS Growth, Dividend]
        NewsAggregator[News Aggregator<br/>Multi-source, Dedupe]
        SentimentAnalyzer[Sentiment Scoring<br/>Bullish/Bearish/Neutral]
        PeerAnalyzer[Peer Analyzer<br/>Relative performance]
    end

    subgraph ResearchOutputs["📊 Research Outputs"]
        StockResearchPage[Stock Research Page<br/>/research/{symbol}]
        DailyDigest[Daily Research Digest<br/>Market Summary]
        SectorHeatmap[Sector Heatmap<br/>Performance visualization]
        FundamentalScreener[Fundamental Screener<br/>Value/Growth filters]
    end

    subgraph UserActions["🎯 User Actions"]
        AddWatchlist[Add to Watchlist]
        SetAlert[Set Price Alert]
        ViewChart[View Chart]
        QuickTrade[Quick Trade]
        SaveResearch[Save Research Note]
    end

    DataSources --> ResearchEngine
    ResearchEngine --> ResearchOutputs
    ResearchOutputs --> UserActions

    style DataSources fill:#e3f2fd,stroke:#1976d2
    style ResearchEngine fill:#fff3e0,stroke:#ff9800
    style ResearchOutputs fill:#e8f5e9,stroke:#4caf50
    style UserActions fill:#fce4ec,stroke:#e91e63
```

#### 1.11.1 Fundamental Data Integration ✅
Extend data providers to include fundamental metrics.

**Tasks:**
- [x] Extend `YahooDataProvider` with fundamental data methods
  - `get_fundamentals(symbol)` - P/E, P/B, EPS, Revenue, etc.
  - `get_financials(symbol)` - Income statement, balance sheet
  - `get_dividends(symbol)` - Dividend history and yield
- [x] Create fundamental data schemas
  ```python
  class FundamentalData(BaseModel):
      symbol: str
      pe_ratio: float | None
      pb_ratio: float | None
      eps: float | None
      eps_growth_yoy: float | None
      revenue: float | None
      revenue_growth_yoy: float | None
      dividend_yield: float | None
      market_cap: float | None
      debt_to_equity: float | None
      roe: float | None
      sector: str | None
      industry: str | None
  ```
- [x] Cache fundamental data (refresh daily after market close)

#### 1.11.2 Fundamental Screener Filters ✅
Add fundamental analysis filters to the screener engine.

**Tasks:**
- [x] Create `FundamentalFilter` class
  ```python
  class FundamentalFilter(BaseFilter):
      filter_type = FilterType.FUNDAMENTAL

      def configure(
          self,
          max_pe: float | None = None,      # P/E ratio ceiling
          min_pe: float | None = None,      # P/E ratio floor
          min_eps_growth: float | None = None,  # YoY EPS growth %
          min_revenue_growth: float | None = None,
          min_dividend_yield: float | None = None,
          max_debt_to_equity: float | None = None,
          min_roe: float | None = None,
          sectors: list[str] | None = None,
          industries: list[str] | None = None,
      ):
          ...
  ```
- [x] Create preset fundamental screeners:
  - **Value Screener**: P/E < 15, P/B < 2, Dividend > 2%
  - **Growth Screener**: EPS growth > 20%, Revenue growth > 15%
  - **Dividend Screener**: Dividend yield > 3%, consistent payout
  - **Quality Screener**: ROE > 15%, Debt/Equity < 0.5
- [x] Update screener API to support fundamental filters

#### 1.11.3 News Integration ✅
Integrate news feeds for market and stock-level news.

**Tasks:**
- [x] Create news provider abstraction (`shared/shared/providers/news/base.py`)
  ```python
  class BaseNewsProvider(ABC):
      @abstractmethod
      async def get_stock_news(symbol: str, limit: int) -> list[NewsArticle]

      @abstractmethod
      async def get_market_news(limit: int) -> list[NewsArticle]

      @abstractmethod
      async def get_sector_news(sector: str, limit: int) -> list[NewsArticle]
  ```
- [x] Implement news providers:
  - `FinnhubNewsProvider` - Finnhub API integration
  - `YahooNewsProvider` - Yahoo Finance news
  - `GoogleRSSNewsProvider` - Google News RSS feeds
  - `NewsProviderFactory` - Factory pattern for provider selection
- [x] Create news schemas with sentiment support
  ```python
  class NewsArticle(BaseModel):
      title: str
      summary: str | None
      source: str
      url: str
      published_at: datetime
      symbols: list[str]  # Related stock symbols
      sentiment: str | None  # "bullish", "bearish", "neutral"
      sentiment_score: float | None  # -1.0 to 1.0
  ```
- [x] Sentiment scoring (`shared/shared/providers/news/sentiment.py`)
  - Keyword-based sentiment analysis
  - Bullish/Bearish/Neutral classification

#### 1.11.4 Stock Research Page ✅
Dedicated deep-dive page for comprehensive stock analysis.

**Tasks:**
- [x] Create `/research` page with tabbed interface
- [x] **Header Section**
  - Stock name, symbol, current price, change %
  - Quick action buttons (Add to Watchlist, Trade, Set Alert)
  - Last updated timestamp
- [x] **Technical Analysis Tab**
  - TradingView chart embed or custom chart
  - Key technical indicators (RSI, MACD, Moving Averages)
  - Support/resistance levels
  - Technical signal summary (Buy/Sell/Hold)
- [x] **Fundamental Analysis Tab**
  - Key ratios: P/E, P/B, EPS, ROE, D/E
  - Revenue and earnings trends (mini charts)
  - Dividend history
  - Comparison to sector averages
- [x] **News & Sentiment Tab**
  - Recent news articles (last 7 days)
  - Sentiment indicator (overall bullish/bearish)
  - News volume chart (articles per day)
- [x] **Peer Comparison Tab**
  - Industry peers table
  - Comparative metrics (P/E, Market Cap, Performance)
  - Relative strength ranking
- [x] **Notes Section**
  - User can save personal research notes
  - Notes stored per symbol per user

#### 1.11.5 Daily Research Digest ✅
Automated daily market intelligence summary.

**Tasks:**
- [x] Create daily digest Celery task (runs at market close)
- [x] Digest components:
  - **Market Summary**: Index performance (Nifty, BankNifty, Sensex)
  - **Top Gainers/Losers**: Top 5 each with % change and reason
  - **Sector Performance**: Heatmap data for all sectors
  - **Volume Leaders**: Unusual volume activity
  - **Breakout Candidates**: From breakout screener
  - **News Highlights**: Top 5 market-moving news
- [x] API endpoint `GET /research/digest` to fetch daily digest
- [x] Frontend Dashboard widget showing digest summary (`DigestWidget.tsx`)
- [ ] Optional: Email digest to subscribed users *(future enhancement)*

#### 1.11.6 Sector Heatmap ✅
Visual sector performance analysis.

**Tasks:**
- [x] Create sector performance API
  - `GET /research/sectors` - All sectors with daily/weekly/monthly performance
  - `GET /research/sectors/{sector}` - Stocks in sector with performance
- [x] Frontend sector heatmap component (`SectorHeatmap.tsx`)
  - Color-coded by performance (green = up, red = down)
  - Click to drill down into sector stocks
  - Toggle timeframe (1D, 1W, 1M, 3M, 1Y)
- [x] Sector rotation analysis
  - Track sector momentum over time
  - Identify rotating leadership

#### 1.11.7 Research API Endpoints ✅
Expose research functionality via REST API.

**Tasks:**
- [x] Create research router (`/api/v1/research`)
  ```python
  # Stock research
  GET /research/{symbol}          # Full research data for symbol
  GET /research/{symbol}/fundamentals  # Fundamental data only
  GET /research/{symbol}/news     # News for symbol
  GET /research/{symbol}/peers    # Peer comparison

  # Market research
  GET /research/digest            # Daily digest
  GET /research/sectors           # Sector performance
  GET /research/sectors/{sector}  # Stocks in sector
  GET /research/recommendations   # Research-based recommendations

  # User research notes
  GET /research/notes             # User's saved notes
  POST /research/notes            # Save research note
  DELETE /research/notes/{id}     # Delete note
  ```
- [x] Register research router in main API router


---

### 1.12 UX Improvements (Week 8-9) ✅
> 🌿 **Branch:** `phase-1/ux-improvements`

**Goal**: Address UX gaps identified in comprehensive UX review to improve trading workflow efficiency, accessibility, and user feedback.

**Status**: All priority 1 and 2 tasks completed (1.12.1-1.12.10).

#### UX Improvement Categories

```mermaid
flowchart TB
    subgraph Priority1["🔴 Priority 1: Critical (Week 8)"]
        P1A[Trade from Analysis Page]
        P1B[Keyboard Shortcuts]
        P1C[Error Boundary]
        P1D[Skip Links & Focus States]
        P1E[Toast Notifications]
    end

    subgraph Priority2["🟡 Priority 2: Important (Week 8-9)"]
        P2A[Multi-Chart Layout]
        P2B[Signal → Trade Flow]
        P2C[One-Click Square-Off]
        P2D[ARIA Labels]
        P2E[Order Templates]
    end

    subgraph Priority3["🟢 Priority 3: Enhancement (Week 9+)"]
        P3A[Branded Loading]
        P3B[Drag-and-Drop Reordering]
        P3C[Chart Comparison]
        P3D[Theme-aware Charts]
        P3E[Backtest Comparison]
    end

    Priority1 --> Priority2 --> Priority3

    style Priority1 fill:#ffebee,stroke:#c62828
    style Priority2 fill:#fff3e0,stroke:#ff9800
    style Priority3 fill:#e8f5e9,stroke:#4caf50
```

#### 1.12.1 Trade from Analysis Page ✅
Reduce trading friction by allowing order placement directly from the Analysis page.

**Tasks:**
- [x] Add collapsible order panel to Analysis page
  - Side panel or bottom drawer
  - Pre-fill symbol from current chart
  - Show real-time quote in order form
- [x] Quick trade buttons on chart
  - Buy/Sell buttons near price display
  - Right-click context menu on chart
- [x] Price level selection from chart
  - Click on chart to set limit price
  - Drag to set stop loss / take profit levels
- [x] Order confirmation inline (no page navigation)

#### 1.12.2 Keyboard Shortcuts ✅
Essential for active traders who need fast execution.

**Tasks:**
- [x] Create keyboard shortcut system
  ```typescript
  // Global navigation shortcuts
  G + D → Dashboard
  G + P → Portfolio
  G + A → Analysis
  G + S → Signals
  G + O → Orders
  G + W → Watchlist
  G + T → Algo Trading
  G + B → Backtest
  G + , → Settings

  // Trading shortcuts
  B → Focus Buy order
  S → Focus Sell order
  N → New order
  ESC → Cancel/Close modal

  // Chart shortcuts
  + / - → Zoom in/out
  ← / → → Pan chart
  1-9 → Switch timeframes
  I → Toggle indicators panel
  D → Toggle drawing tools
  ```
- [x] Create `useKeyboardShortcuts` hook
- [x] Add shortcut hints in UI (tooltips, menu items)
- [x] Settings page to customize shortcuts
- [x] Shortcut help modal (`?` key to open)
- [x] Prevent shortcuts when typing in inputs

#### 1.12.3 Error Boundary & Error Handling ✅
Prevent app crashes and provide graceful error recovery.

**Tasks:**
- [x] Create React Error Boundary component
  - Catch rendering errors
  - Display friendly error message
  - "Reload" and "Report Issue" buttons
  - Log errors to backend/monitoring
- [x] Add error boundaries at page level
- [x] Add error boundaries around critical widgets
- [x] Global error handler for API failures
  - Retry logic with exponential backoff
  - Offline detection and indicator
  - Queue failed mutations for retry
- [x] Error state components for each widget
  - Consistent error UI across app
  - "Try Again" button

#### 1.12.4 Accessibility: Skip Links & Focus States ✅
Basic WCAG 2.1 AA compliance for accessibility.

**Tasks:**
- [x] Add skip link ("Skip to main content")
  - Visible on focus at top of page
  - Links to main content area
- [x] Implement visible focus indicators
  - Focus ring on all interactive elements
  - High contrast focus styles
  - Respect `prefers-reduced-motion`
- [x] Keyboard navigation for sidebar
  - Tab through navigation items
  - Enter to navigate, Space to expand
  - Arrow keys for menu items
- [x] Screen reader improvements
  - ARIA labels on icon-only buttons
  - ARIA live regions for dynamic content
  - Proper heading hierarchy (h1 → h2 → h3)
- [x] Add `prefers-reduced-motion` support
  - Disable animations when preferred
  - Alternative transitions

#### 1.12.5 Toast Notification System ✅
Consistent feedback for user actions.

**Tasks:**
- [x] Create Toast component (or use shadcn/ui Sonner)
  - Success, Error, Warning, Info variants
  - Auto-dismiss with configurable duration
  - Dismiss button
  - Action button support ("Undo", "View")
- [x] Create `useToast` hook for triggering toasts
- [x] Add toasts for:
  - Order placed/filled/cancelled/rejected
  - Watchlist symbol added/removed
  - Portfolio created/deleted
  - Settings saved
  - Strategy enabled/disabled
  - Kill switch activated
  - Alert triggered
- [x] Toast queue management (prevent stacking too many)
- [x] Position configuration (top-right, bottom-right, etc.)

#### 1.12.6 Multi-Chart Layout ✅
Professional trading feature for monitoring multiple instruments.

**Tasks:**
- [x] Create multi-chart container component
  - 1x1, 2x1, 2x2, 3x2 grid layouts
  - Layout selector UI
- [x] Independent chart state per panel
  - Symbol, timeframe, indicators per chart
  - Synced crosshairs (optional)
- [x] Chart panel controls
  - Symbol search per panel
  - Close/maximize panel
  - Swap panel positions
- [x] Save/load chart layouts
  - User can save favorite layouts
  - Quick switch between saved layouts
- [x] Responsive behavior
  - Stack vertically on smaller screens

#### 1.12.7 Signal to Trade Flow ✅
Enable direct order placement from signals.

**Tasks:**
- [x] Add "Trade Now" button on signal rows
  - Opens order form pre-filled with signal data
  - Symbol, side (buy/sell), suggested price
- [x] Signal detail modal with trade option
  - View full signal analysis
  - "Place Order" button in modal
- [x] Bulk signal actions
  - Select multiple signals
  - "Trade All Selected" action
- [x] Signal → Order tracking
  - Link orders to originating signals
  - Show which signals resulted in trades

#### 1.12.8 One-Click Square-Off ✅
Critical for fast markets and risk management.

**Tasks:**
- [x] Add "Square Off" button on position rows
  - Single click to close position
  - Confirmation optional (can be disabled in settings)
- [x] "Square Off All" button in portfolio header
  - Close all open positions
  - Requires confirmation
- [x] Square off by category
  - Square off all intraday positions
  - Square off all loss-making positions
  - Square off by sector
- [x] Quick square-off keyboard shortcut
  - `X` key on selected position

#### 1.12.9 ARIA Labels & Screen Reader Support ✅
Improve accessibility for users with disabilities.

**Tasks:**
- [x] Add ARIA labels to all icon-only buttons
  ```tsx
  <Button aria-label="Close modal">
    <X className="h-4 w-4" />
  </Button>
  ```
- [x] Add ARIA roles to data tables
  - `role="table"`, `role="row"`, `role="cell"`
  - Column headers with `scope="col"`
- [x] Add ARIA live regions for dynamic content
  - Price updates: `aria-live="polite"`
  - Alerts: `aria-live="assertive"`
- [x] Announce route changes to screen readers
- [x] Add descriptive text for charts (alt text)

#### 1.12.10 Order Templates & Presets ✅
Faster repeat orders for active traders.

**Tasks:**
- [x] Create `OrderTemplate` model
  ```python
  class OrderTemplate:
      id: str
      user_id: str
      name: str  # "Quick RELIANCE Buy"
      symbol: str
      side: str  # buy/sell
      order_type: str
      quantity: int | None
      quantity_pct: float | None  # % of portfolio
      stop_loss_pct: float | None
      take_profit_pct: float | None
  ```
- [x] Order template management UI
  - Create/Edit/Delete templates
  - List saved templates
- [x] Quick template buttons in order form
  - "Use Template" dropdown
  - Recent templates section
- [x] One-click trade from template
  - Template button executes immediately
  - Optional confirmation

#### 1.12.11 Branded Loading States ✅
Visual polish for professional appearance.

**Tasks:**
- [x] Create branded loading spinner
  - App logo animation
  - Consistent with brand colors
- [x] Full-page loading state for initial load
- [x] Skeleton screens for all data-loading components
  - Dashboard cards
  - Tables
  - Charts
- [x] Progress indicators for long operations
  - Backtest progress
  - Bulk operations

#### 1.12.12 Drag-and-Drop Reordering ✅
Customization for watchlists and portfolios.

**Tasks:**
- [x] Watchlist symbol reordering
  - Drag symbols to reorder
  - Persist order to backend
- [x] Watchlist list reordering
  - Reorder watchlists in sidebar
- [ ] Dashboard widget reordering (future)
  - Drag widgets to rearrange
  - Resize widgets

#### 1.12.13 Chart Comparison & Overlay ✅
Enhanced technical analysis capabilities.

**Tasks:**
- [x] Symbol comparison overlay
  - Add multiple symbols to same chart
  - Normalized/percentage view
  - Toggle symbols on/off
- [x] Index comparison
  - Compare stock to Nifty 50
  - Relative strength display
- [x] Custom comparison groups
  - Save groups of symbols
  - Quick switch between comparisons

#### 1.12.14 Theme-Aware Charts ✅
Visual consistency between app theme and charts.

**Tasks:**
- [x] Dynamic chart colors based on theme
  - Read CSS variables for colors
  - Apply to chart background, grid, text
- [x] Profit/loss colors match app theme
  - Use `--profit` and `--loss` variables
- [x] Indicator colors theme-aware
  - Configurable indicator palette
- [x] Chart theme persistence
  - Save chart theme preference

#### 1.12.15 Backtest Results Comparison ✅
Better strategy evaluation through comparison.

**Tasks:**
- [x] Save backtest results to database
  - Store results with timestamp
  - Tag results with notes
- [x] Backtest history list
  - View past backtest results
  - Filter by strategy, symbol, date
- [x] Side-by-side comparison view
  - Compare 2-4 backtests
  - Metrics comparison table
  - Overlaid equity curves
- [x] Export backtest results
  - CSV export
  - PDF report generation

---

### 1.13 Strategy Parameter Customization ✅
> 🌿 **Branch:** `phase-1/strategy-params`

**Goal**: Allow users to customize parameters of prebuilt strategies instead of using only default values.

**Effort Estimate**: 2-3 days

**Architecture Note**: The infrastructure already exists via `StrategyRegistry.get_strategy(name, params)` which accepts custom parameters. This task exposes that functionality to end users.

#### 1.13.1 Strategy Parameter Schema Endpoints
**Tasks:**
- [x] Create `GET /api/v1/algo/strategy-types` endpoint
  - List all registered strategies with name, description, default timeframe
  - Include parameter schemas for each strategy
- [x] Create `GET /api/v1/algo/strategy-types/{name}/parameters` endpoint
  - Return detailed parameter schema with types, defaults, min/max bounds
  ```python
  class StrategyParameterSchema(BaseModel):
      name: str               # "rsi_period"
      type: str               # "int", "float", "bool", "select"
      default: Any            # 14
      min: float | None       # 5
      max: float | None       # 50
      options: list | None    # For select type
      description: str        # "RSI calculation period"
  ```
- [x] Add parameter validation in strategy creation/update endpoints
  - Validate parameter types and bounds
  - Return clear error messages for invalid parameters

#### 1.13.2 Frontend Strategy Parameter Form
**Tasks:**
- [x] Create `StrategyParameterForm` component
  - Dynamic form based on parameter schema
  - Appropriate input types (number, slider, checkbox, select)
  - Show defaults and valid ranges
  - Real-time validation feedback
- [x] Integrate into strategy creation dialog
  - Show parameters when strategy type is selected
  - Allow customization before saving
- [x] Integrate into strategy edit dialog
  - Load existing parameters
  - Allow modification
- [x] Add "Reset to Defaults" button

#### 1.13.3 Backend Parameter Storage
**Tasks:**
- [x] `UserStrategy.strategy_params` JSON field already exists
- [x] Store user-customized parameters when strategy is created/updated
- [x] Pass `strategy_params` to `StrategyRegistry.get_strategy()` at execution time
- [x] Validate parameters match expected schema before execution

---

### 1.14 Composite Strategy Builder ✅
> 🌿 **Branch:** `phase-1/composite-builder`

**Goal**: Allow users to combine 2-5 prebuilt strategies with configurable logic (AND/OR/MAJORITY/WEIGHTED) without writing code.

**Effort Estimate**: 3-5 days

**Architecture Note**: `CompositeStrategy` class already exists in `shared/shared/strategies/composite.py` with full support for AND/OR/MAJORITY/WEIGHTED logic. This task exposes that functionality via UI.

#### 1.14.1 Composite Strategy API
**Tasks:**
- [x] Create `POST /api/v1/algo/strategies/composite` endpoint
  - Accept list of component strategies with parameters
  - Accept combining logic (AND/OR/MAJORITY/WEIGHTED)
  - Accept per-strategy weights (for WEIGHTED logic)
  - Validate component count (2-5 strategies)
  ```python
  class CompositeStrategyCreate(BaseModel):
      name: str
      description: str | None
      components: list[StrategyComponent]
      combining_logic: CombiningLogic  # AND | OR | MAJORITY | WEIGHTED
      min_agreement: float | None      # For MAJORITY, e.g., 0.6 for 60%

  class StrategyComponent(BaseModel):
      strategy_name: str               # "rsi", "macd", etc.
      weight: float = 1.0              # For WEIGHTED logic
      required: bool = False           # Must agree for AND logic
      custom_params: dict | None       # Per-component parameters
  ```
- [x] Store composite config in `UserStrategy.strategy_params` with `type: "composite"`
- [x] Runtime composite strategy creation via `CompositeStrategyFactory`

#### 1.14.2 Frontend Composite Builder UI
**Tasks:**
- [x] Create `CompositeStrategyBuilder` component (merged into StrategyDialog)
  - Multi-select for choosing component strategies (2-5)
  - Per-component parameter customization (reuse `StrategyParameterForm`)
  - Per-component weight slider
  - Combining logic selector (AND/OR/MAJORITY/WEIGHTED)
  - Visual preview of logic flow
- [x] Add "Composite Strategy" tab/option in strategy creation dialog
- [x] Visual representation of combined strategy (Task 1.14.2a - CompositeFlowDiagram)
  ```
  ┌─────────────────────────────────────────────────────┐
  │ My RSI + MACD Strategy                              │
  ├─────────────────────────────────────────────────────┤
  │ ┌─────────┐    ┌─────────┐    ┌─────────┐          │
  │ │   RSI   │    │  MACD   │    │   BB    │          │
  │ │ wt: 1.5 │ OR │ wt: 1.0 │ OR │ wt: 0.5 │          │
  │ └─────────┘    └─────────┘    └─────────┘          │
  │                     │                               │
  │              WEIGHTED (60% min)                     │
  │                     ↓                               │
  │               Final Signal                          │
  └─────────────────────────────────────────────────────┘
  ```
- [x] Show combined parameter summary
- [x] Strategy testing (dry run) before saving (Task 1.14.2b - dry-run endpoint)

#### 1.14.3 Composite Strategy Execution
**Tasks:**
- [x] Detect `type: "composite"` in `strategy_params` at execution time
- [x] Build composite strategy via `CompositeStrategyFactory.create()`
- [x] Register temporarily in `StrategyRegistry` for execution
- [x] Track individual component signals in execution logs (Task 1.14.3a)
- [x] Show per-component performance metrics in strategy dashboard (Task 1.14.3b)

---

### 1.15 Custom Strategy DSL ✅ Complete
> 🌿 **Branch:** `phase-2/strategy-dsl`

**Goal**: Allow power users to define custom rule-based strategies using a domain-specific language without full Python access.

**Security Note**: This is sandboxed execution - no arbitrary code, only predefined operators and indicators.

**Completed**: February 2026

#### 1.15.1 DSL Design ✅
**Tasks:**
- [x] Define DSL syntax (JSON-based)
  ```yaml
  name: "My Custom RSI Divergence Strategy"
  version: 1
  rules:
    entry:
      - condition: "rsi(14) < 30 AND macd_histogram > 0"
        action: BUY
        confidence: 0.8
      - condition: "rsi(14) > 70 AND macd_histogram < 0"
        action: SELL
        confidence: 0.8
    exit:
      stop_loss_pct: 2.0
      take_profit_pct: 4.0
      trailing_stop_pct: 1.5
    filters:
      - "volume > sma(volume, 20) * 1.5"
      - "close > sma(close, 200)"
  indicators:
    - rsi: { period: 14 }
    - macd: { fast: 12, slow: 26, signal: 9 }
    - sma: { periods: [20, 50, 200] }
  ```
- [x] Define supported operators: `>`, `<`, `>=`, `<=`, `==`, `!=`, `AND`, `OR`, `NOT`, `+`, `-`, `*`, `/`
- [x] Define supported functions: `rsi()`, `macd()`, `sma()`, `ema()`, `bbands_upper/lower/middle()`, `atr()`, `volume_sma()`
- [x] Define supported variables: `close`, `open`, `high`, `low`, `volume`, `previous_close`, etc.

**Implementation Files:**
- `shared/shared/strategies/dsl/schemas.py` - Pydantic schemas for DSL definitions
- `shared/shared/strategies/dsl/operators.py` - Operator and function definitions

#### 1.15.2 DSL Parser & Validator ✅
**Tasks:**
- [x] Create DSL parser (convert JSON to AST)
- [x] Validate syntax and semantics
  - Check indicator availability
  - Validate parameter types
  - Check for undefined variables
- [x] Return clear error messages with position information
- [x] Security validation (max condition length, max rules limit)

**Implementation Files:**
- `shared/shared/strategies/dsl/parser.py` - Recursive descent parser with tokenizer
- `shared/shared/strategies/dsl/validator.py` - DSL validation with error reporting

#### 1.15.3 DSL Executor ✅
**Tasks:**
- [x] Create `DSLStrategy` class implementing `BaseStrategy`
- [x] Evaluate conditions against market data using `ta` library
- [x] Generate signals based on rule evaluation
- [x] Calculate confidence from rule matches
- [x] Support for complex nested conditions with logical operators

**Implementation Files:**
- `shared/shared/strategies/dsl/executor.py` - AST evaluation and indicator calculation
- `shared/shared/strategies/dsl/strategy.py` - DSLStrategy class

#### 1.15.4 DSL Backend API ✅
**Tasks:**
- [x] Add `POST /api/algo/strategies/dsl` endpoint
- [x] Create DSL strategy schema and service methods
- [x] Dynamic strategy registration in StrategyRegistry
- [x] Support all execution settings (schedule, position sizing, risk)

**Implementation Files:**
- `backend/app/modules/algo/schemas.py` - DSLStrategyCreate/Response schemas
- `backend/app/modules/algo/service.py` - create_dsl_strategy method
- `backend/app/modules/algo/router.py` - DSL endpoint

#### 1.15.5 DSL Editor UI ✅
**Tasks:**
- [x] JSON editor component for DSL definition
- [x] DSL syntax reference with supported functions/operators
- [x] Real-time JSON validation
- [x] Example template for RSI oversold strategy
- [x] Execution settings accordion (schedule, position sizing, risk)
- [x] "Custom DSL" button in algo page header

**Implementation Files:**
- `frontend/src/components/algo/DSLStrategyBuilder.tsx` - DSL editor component
- `frontend/src/types/api.ts` - DSL TypeScript types
- `frontend/src/lib/api.ts` - createDSLStrategy API function

#### 1.15.6 Tests ✅
**Tasks:**
- [x] Parser tests (comparison, logical ops, functions, variables, arithmetic)
- [x] Validator tests (valid/invalid definitions, security limits)
- [x] Executor tests (condition evaluation, indicator calculations)
- [x] Strategy tests (signal generation, parameter retrieval)

**Implementation Files:**
- `shared/tests/strategies/test_dsl.py` - 23 test cases

#### Deferred Items (nice-to-have)
- [x] Syntax highlighting in editor (Monaco Editor with JSON highlighting)
- [x] Auto-complete for indicators and functions (DSL_FUNCTIONS, DSL_VARIABLES, DSL_OPERATORS)
- [x] Required backtesting before activation (requireBacktest toggle + validation)
- [x] Paper trading trial period option (paperTradingDays config)
- [x] Visual rule builder (drag-and-drop) - Implemented with @dnd-kit


---

## 🚀 PHASE 2: Live Trading with Angel One (Weeks 8-9)

**Goal**: Connect to Angel One API for real trading. Platform stays the same!

### Phase 2 Architecture Diagram

```mermaid
flowchart TB
    subgraph Phase1Complete["✅ Phase 1 Complete"]
        PaperSystem[Paper Trading System<br/>Fully Validated]
    end

    subgraph ConfigChange["⚙️ Configuration Change"]
        EnvSwitch["BROKER_TYPE=angelone<br/>DATA_PROVIDER=angelone"]
    end

    subgraph AngelOne["🏦 Angel One Integration"]
        subgraph Auth["🔐 Authentication"]
            Login[API Login]
            TOTP[TOTP Generation]
            Session[Session Management]
        end

        subgraph AngelDataProvider["📊 Angel One Data Provider"]
            Quotes[Real-time Quotes]
            Historical[Historical Data]
            WebSocket[WebSocket Feed]
        end

        subgraph AngelBroker["💹 Angel One Broker"]
            PlaceOrder[Place Orders]
            OrderStatus[Order Status]
            Positions[Positions]
            Holdings[Holdings]
        end
    end

    subgraph SafetyLayer["🛡️ Live Trading Safety"]
        KillSwitch[Master Kill Switch]
        StartSmall[Start Small<br/>₹1000 trades]
        RealTimeMonitor[Real-time Monitoring]
        AlertsActive[All Alerts Active]
    end

    subgraph ReportingSystem["📊 Reporting & Ledger"]
        subgraph Ledger["💰 Transaction Ledger"]
            TxnHistory[Cash Flow History]
            RunningBalance[Running Balances]
            Statement[Account Statement]
        end

        subgraph CapGains["📈 Capital Gains"]
            STCG[Short-Term Gains]
            LTCG[Long-Term Gains]
            TaxReport[Tax Reports]
        end

        subgraph APILogs["🔍 API Logging"]
            BrokerLogs[Broker API Logs]
            Latency[Latency Tracking]
            ErrorLogs[Error Logs]
        end

        subgraph Activity["📋 Activity Log"]
            UserActions[User Actions]
            SystemEvents[System Events]
            AuditTrail[Audit Trail]
        end
    end

    subgraph LiveTrading["🚀 Live Trading"]
        RealMoney[Real Money Trades]
        RealPnL[Real P&L]
        RealPositions[Real Positions]
    end

    Phase1Complete --> ConfigChange
    ConfigChange --> AngelOne
    AngelOne --> SafetyLayer
    SafetyLayer --> ReportingSystem
    ReportingSystem --> LiveTrading

    style Phase1Complete fill:#e8f5e9,stroke:#4caf50
    style ConfigChange fill:#fff3e0,stroke:#ff9800
    style AngelOne fill:#e3f2fd,stroke:#1976d2
    style SafetyLayer fill:#ffebee,stroke:#c62828
    style ReportingSystem fill:#e8eaf6,stroke:#3f51b5
    style LiveTrading fill:#f3e5f5,stroke:#9c27b0
```

### 2.1 Angel One Integration
> 🌿 **Branch:** `phase-2/angelone`

#### 2.1.1 Authentication
**Tasks:**
- [ ] Implement Angel One login
  - API key + Client ID + Password + TOTP
- [ ] TOTP generation using pyotp
- [ ] Session management (token refresh every 12 hours)
- [ ] Secure credential storage

#### 2.1.2 Angel One Data Provider
**Tasks:**
- [ ] Implement `AngelOneDataProvider`
  - Get LTP, full quote
  - Get historical data (candlestick API)
  - Get market depth (Level 2)
- [ ] WebSocket for live streaming
- [ ] Symbol mapping (our format ↔ Angel format)

#### 2.1.3 Angel One Broker
**Tasks:**
- [ ] Implement `AngelOneBroker`
  - Place order (all types)
  - Cancel order
  - Modify order
  - Get order status/history
  - Get positions (day/net)
  - Get holdings
  - Get funds/margins
- [ ] Order status webhooks
- [ ] Error handling and retries

### 2.2 Fyers Integration ✅
> 🌿 **Branch:** `phase-2/fyers`

**Status**: Complete - Full Fyers broker integration implemented.

#### 2.2.1 Fyers OAuth2 Authentication ✅
**Tasks:**
- [x] Implement `FyersAuthHandler` class for OAuth2 flow
  - Generate authorization URL for user login
  - Exchange auth code for access token
  - Token refresh mechanism
  - Token validation check
- [x] Create `FyersCredentials` dataclass
  - client_id, secret_key, redirect_uri, access_token
- [x] `create_auth_handler_from_env()` helper function
  - Load credentials from environment variables
  - FYERS_CLIENT_ID, FYERS_SECRET_KEY, FYERS_REDIRECT_URI, FYERS_ACCESS_TOKEN

#### 2.2.2 Fyers Data Provider ✅
**Tasks:**
- [x] Implement `FyersDataProvider` class extending `DataProvider`
  - `get_quote()` - Real-time quotes
  - `get_historical()` - Historical OHLCV data
  - `search_symbols()` - Symbol search
  - `get_instrument_info()` - Instrument details
  - `get_option_chain()` - Option chain data
- [x] Symbol normalization (e.g., "RELIANCE" → "NSE:RELIANCE-EQ")
- [x] Market hours awareness (NSE: 9:15 AM - 3:30 PM IST)
- [x] Resolution mapping for historical data (1m, 5m, 15m, 1h, 1d)
- [x] Support for NSE and BSE exchanges

#### 2.2.3 Fyers Broker ✅
**Tasks:**
- [x] Implement `FyersBroker` class extending `Broker`
  - `place_order()` - Order placement
  - `cancel_order()` - Order cancellation
  - `modify_order()` - Order modification
  - `get_order_status()` - Order status query
  - `get_positions()` - Get open positions
  - `get_funds()` - Account funds/balance
  - `get_holdings()` - Delivery holdings
- [x] Order type mapping (MARKET, LIMIT, STOP_LOSS, STOP_LOSS_MARKET)
- [x] Product type mapping (INTRADAY, DELIVERY)
- [x] Side mapping (BUY=1, SELL=-1 for Fyers format)
- [x] Register `FyersBroker` in `BrokerFactory`

#### 2.2.4 Fyers Unit Tests ✅
**Tasks:**
- [x] Create `test_fyers.py` with comprehensive tests
- [x] Mock Fyers API responses for isolated testing
- [x] Test FyersDataProvider methods
- [x] Test FyersBroker methods
- [x] Test FyersAuthHandler OAuth flow

### 2.3 Live Trading Safety
> 🌿 **Branch:** `phase-2/live-safety`

#### 2.3.1 Kill Switch
**Tasks:**
- [ ] Emergency stop button (cancel all orders, square off)
- [ ] API failure detection and auto-stop
- [ ] Connectivity monitoring

#### 2.3.2 Order Confirmation
**Tasks:**
- [ ] Double confirmation for large orders
- [ ] SMS/Email confirmation (optional)
- [ ] Daily trade limit warnings

#### 2.3.3 Audit Trail
**Tasks:**
- [ ] Log all API calls to broker
- [ ] Record order placement source (manual/algo)
- [ ] Daily reconciliation with broker

### 2.4 Reporting & Ledger System ✅
> 🌿 **Branch:** `phase-2/reporting-ledger`

**Status**: Complete - Full reporting infrastructure with transaction ledger, capital gains tracking, broker API logging, and activity feed.

#### 2.4.1 Transaction Ledger ✅
Full ledger/statement view of all cash flow activity with running balances.

**Database Model: `TransactionLedger`**
```python
class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"           # Cash added to account
    WITHDRAWAL = "WITHDRAWAL"     # Cash withdrawn
    BUY = "BUY"                   # Cash used to buy securities
    SELL = "SELL"                 # Cash received from selling
    FEE = "FEE"                   # Trading fees, brokerage
    DIVIDEND = "DIVIDEND"         # Dividend received
    INTEREST = "INTEREST"         # Interest earned/paid
    ADJUSTMENT = "ADJUSTMENT"     # Manual adjustments
    TRANSFER_IN = "TRANSFER_IN"   # Transfer from another portfolio
    TRANSFER_OUT = "TRANSFER_OUT" # Transfer to another portfolio

class TransactionLedger(Base):
    __tablename__ = "transaction_ledger"

    id: UUID
    user_id: UUID (FK users.id)
    portfolio_id: UUID | None (FK portfolios.id)

    # Transaction details
    transaction_type: TransactionType
    amount: Decimal(18,4)         # Positive for credits, negative for debits

    # Running balances after this transaction
    running_cash_balance: Decimal(18,4)
    running_margin_used: Decimal(18,4)
    running_total_balance: Decimal(18,4)  # cash + margin available

    # Reference to source entity
    reference_type: str | None    # "trade", "order", "manual", "dividend"
    reference_id: UUID | None     # ID of the source entity

    # Descriptive info
    symbol: str | None            # For trade-related transactions
    description: str              # Human-readable description
    metadata: JSON | None         # Additional context (fees breakdown, etc.)

    # Timestamps
    transaction_date: DateTime    # When the transaction occurred
    created_at: DateTime
```

**Tasks:**
- [x] Create `TransactionLedger` model in `backend/app/modules/portfolio/models.py`
- [x] Create Alembic migration for new table
- [x] Create `LedgerService` with methods:
  - `record_transaction()` - Record any transaction with auto-calculated running balance
  - `get_ledger()` - Paginated ledger with filters (date range, type, symbol)
  - `get_statement()` - Generate statement for date range
  - `get_balance_history()` - Balance over time for charts
- [x] Integrate with existing services:
  - `FundsService.add_cash()` → record DEPOSIT
  - `FundsService.deduct_cash()` → record WITHDRAWAL
  - `TradingService.execute_market_order()` → record BUY/SELL
  - Trade fees → record FEE
- [x] API endpoints:
  - `GET /portfolio/ledger` - Paginated ledger
  - `GET /portfolio/ledger/statement` - Statement PDF/CSV export
  - `GET /portfolio/ledger/balance-history` - Balance over time

#### 2.4.2 Capital Gains Tracking ✅
Track realized gains with short-term vs long-term classification for tax reporting.

**Database Model: `RealizedGain`**
```python
class RealizedGain(Base):
    __tablename__ = "realized_gains"

    id: UUID
    user_id: UUID (FK users.id)
    portfolio_id: UUID | None (FK portfolios.id)

    # Security info
    symbol: str

    # Lot details
    quantity: Decimal(18,8)
    cost_basis: Decimal(18,4)      # Total cost of shares sold
    sale_proceeds: Decimal(18,4)   # Total sale proceeds
    fees: Decimal(18,4)            # Total fees (buy + sell)

    # Calculated gain/loss
    gain_loss: Decimal(18,4)       # sale_proceeds - cost_basis - fees
    gain_loss_pct: Decimal(10,4)   # Percentage gain/loss

    # Holding period
    purchase_date: DateTime
    sale_date: DateTime
    holding_days: Integer
    is_long_term: Boolean          # True if holding_days > 365

    # Tax classification (India-specific)
    tax_type: str                  # "STCG", "LTCG", "SPECULATIVE" (intraday)

    # References
    cost_lot_id: UUID | None (FK cost_lots.id)
    buy_trade_id: UUID | None (FK trades.id)
    sell_trade_id: UUID | None (FK trades.id)

    # Financial year
    financial_year: str            # "2024-25" format

    created_at: DateTime
```

**Tasks:**
- [x] Create `RealizedGain` model in `backend/app/modules/portfolio/models.py`
- [x] Create Alembic migration for new table
- [x] Modify `PortfolioService.consume_cost_lots_fifo()` to:
  - Create `RealizedGain` record for each lot consumed
  - Calculate holding period and classify as short/long term
  - Determine financial year
- [x] Create `CapitalGainsService` with methods:
  - `get_realized_gains()` - List all gains with filters
  - `get_gains_summary()` - Summary by type (STCG/LTCG)
  - `get_tax_report()` - Tax-ready report by financial year
  - `export_gains_csv()` - Export for tax filing
- [x] API endpoints:
  - `GET /portfolio/gains` - Paginated realized gains
  - `GET /portfolio/gains/summary` - Aggregated summary
  - `GET /portfolio/gains/tax-report/{financial_year}` - Tax report
  - `GET /portfolio/gains/export` - CSV export

#### 2.4.3 Broker API Logging ✅
Log all broker API interactions for debugging and audit purposes.

**Database Model: `BrokerAPILog`**
```python
class BrokerAPILog(Base):
    __tablename__ = "broker_api_logs"

    id: UUID
    user_id: UUID (FK users.id)

    # Broker info
    broker_type: str              # "fyers", "angelone", "paper", etc.

    # Request details
    endpoint: str                 # API endpoint called
    method: str                   # "GET", "POST", "PUT", "DELETE"
    request_data: JSON | None     # Request payload (sensitive data masked)

    # Response details
    status_code: Integer | None   # HTTP status code
    response_data: JSON | None    # Response payload (sensitive data masked)
    is_success: Boolean
    error_message: str | None     # Error message if failed

    # Performance
    latency_ms: Integer           # Response time in milliseconds

    # Context
    action: str                   # "place_order", "cancel_order", "get_positions", etc.
    reference_type: str | None    # "order", "position", etc.
    reference_id: UUID | None     # ID of related entity

    # Timestamps
    request_at: DateTime
    response_at: DateTime | None

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_broker_api_logs_user_date", "user_id", "request_at"),
        Index("ix_broker_api_logs_broker_action", "broker_type", "action"),
    )
```

**Tasks:**
- [x] Create `BrokerAPILog` model in `backend/app/modules/broker/models.py`
- [x] Create Alembic migration for new table
- [x] Create `BrokerLoggingService` with methods:
  - `log_request()` - Log outgoing request
  - `log_response()` - Update with response
  - `get_api_logs()` - Paginated logs with filters
  - `get_api_stats()` - Success rates, avg latency by broker
- [x] Create broker logging decorator/middleware:
  ```python
  @log_broker_api
  async def place_order(self, user_id: str, order: OrderRequest) -> OrderResponse:
      ...
  ```
- [x] Update broker implementations to use logging:
  - `FyersBroker` - Wrap all API calls
  - `PaperBroker` - Log simulated calls
  - Future brokers - Apply decorator
- [x] Mask sensitive data before logging (access tokens, secrets)
- [x] API endpoints:
  - `GET /brokers/logs` - Paginated API logs
  - `GET /brokers/logs/stats` - API statistics
  - `GET /brokers/logs/{log_id}` - Single log detail

#### 2.4.4 Activity Log ✅
User-facing activity feed showing all significant actions.

**Database Model: `ActivityLog`**
```python
class ActivityType(str, Enum):
    # Auth
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"

    # Trading
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_MODIFIED = "ORDER_MODIFIED"

    # Portfolio
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"

    # Algo
    STRATEGY_CREATED = "STRATEGY_CREATED"
    STRATEGY_STARTED = "STRATEGY_STARTED"
    STRATEGY_STOPPED = "STRATEGY_STOPPED"
    STRATEGY_DELETED = "STRATEGY_DELETED"
    KILL_SWITCH_ACTIVATED = "KILL_SWITCH_ACTIVATED"
    CIRCUIT_BREAKER_TRIGGERED = "CIRCUIT_BREAKER_TRIGGERED"

    # Risk
    RISK_LIMIT_BREACHED = "RISK_LIMIT_BREACHED"
    DAILY_LOSS_LIMIT_HIT = "DAILY_LOSS_LIMIT_HIT"

    # Broker
    BROKER_CONNECTED = "BROKER_CONNECTED"
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"
    BROKER_ERROR = "BROKER_ERROR"

    # Settings
    SETTINGS_UPDATED = "SETTINGS_UPDATED"
    WATCHLIST_UPDATED = "WATCHLIST_UPDATED"
    ALERT_CREATED = "ALERT_CREATED"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: UUID
    user_id: UUID (FK users.id)

    # Activity details
    activity_type: ActivityType
    category: str                 # "auth", "trading", "portfolio", "algo", "risk", "broker", "settings"
    title: str                    # Short title (e.g., "Order Placed")
    description: str              # Detailed description

    # Entity reference
    entity_type: str | None       # "order", "position", "strategy", etc.
    entity_id: UUID | None        # ID of related entity

    # Additional context
    metadata: JSON | None         # Extra data (symbol, quantity, price, etc.)

    # Severity/importance
    severity: str                 # "info", "warning", "error", "critical"
    is_read: Boolean              # For notification badge

    # Client info
    ip_address: str | None
    user_agent: str | None

    # Timestamps
    created_at: DateTime

    # Indexes
    __table_args__ = (
        Index("ix_activity_logs_user_date", "user_id", "created_at"),
        Index("ix_activity_logs_user_unread", "user_id", "is_read"),
        Index("ix_activity_logs_category", "user_id", "category"),
    )
```

**Tasks:**
- [x] Create `ActivityLog` model in `backend/app/modules/activity/models.py`
- [x] Create new `activity` module structure:
  - `backend/app/modules/activity/__init__.py`
  - `backend/app/modules/activity/models.py`
  - `backend/app/modules/activity/schemas.py`
  - `backend/app/modules/activity/service.py`
  - `backend/app/modules/activity/router.py`
- [x] Create Alembic migration for new table
- [x] Create `ActivityService` with methods:
  - `log_activity()` - Record an activity
  - `get_activities()` - Paginated activity feed
  - `get_unread_count()` - Count of unread activities
  - `mark_as_read()` - Mark activities as read
  - `get_activities_by_entity()` - Activities for specific entity
- [x] Create helper for easy logging:
  ```python
  await activity_service.log_activity(
      user_id=user_id,
      activity_type=ActivityType.ORDER_PLACED,
      title="Order Placed",
      description=f"Buy 10 RELIANCE @ ₹2,500",
      entity_type="order",
      entity_id=order.id,
      metadata={"symbol": "RELIANCE", "quantity": 10, "price": 2500},
  )
  ```
- [x] Integrate with existing services:
  - `AuthService` - Login/logout events
  - `TradingService` - Order events
  - `AlgoService` - Strategy events
  - `RiskService` - Risk breach events
  - `BrokerService` - Connection events
- [x] API endpoints:
  - `GET /activity` - Paginated activity feed
  - `GET /activity/unread-count` - Unread count
  - `POST /activity/mark-read` - Mark as read
  - `GET /activity/entity/{type}/{id}` - Activities for entity

### 2.5 Reports Frontend ✅
> 🌿 **Branch:** `phase-2/reports-frontend`
> **Status:** ✅ Complete (2026-02-19)

New "Reports" section in the frontend sidebar with comprehensive reporting pages.

#### 2.5.1 Frontend Navigation Update ✅
Add Reports section to the main sidebar.

**Tasks:**
- [x] Update `frontend/src/config/navigation.ts`:
  - Add "Reports" section with FileBarChart icon
  - Sub-items: Statement, Gains Report, API Logs, Activity
- [x] Add routes:
  - `/reports` - Overview/landing page
  - `/reports/statement` - Account statement
  - `/reports/gains` - Capital gains report
  - `/reports/api-logs` - Broker API logs
  - `/reports/activity` - Activity feed

#### 2.5.2 Account Statement Page ✅
Ledger view with filtering and export.

**Page: `/reports/statement`**

**Features:**
- Date range picker (default: last 30 days)
- Filter by transaction type (multi-select)
- Filter by symbol
- Running balance column
- Export to CSV/PDF
- Summary cards: Total In, Total Out, Net Change

**Tasks:**
- [x] Create `frontend/src/app/(dashboard)/reports/statement/page.tsx`
- [x] Add API functions in `frontend/src/lib/api.ts`:
  - `reportsApi.getLedger()`
  - `reportsApi.exportStatement()`
- [x] Add types in `frontend/src/types/api.ts`

#### 2.5.3 Capital Gains Report Page ✅
Tax-focused gains report with short/long term breakdown.

**Page: `/reports/gains`**

**Features:**
- Financial year selector
- Summary: Total Gains, STCG, LTCG
- Gains by symbol
- Holding period breakdown chart
- Export for tax filing (CSV with required columns)

**Tasks:**
- [x] Create `frontend/src/app/(dashboard)/reports/gains/page.tsx`
- [x] Add API functions:
  - `reportsApi.getRealizedGains()`
  - `reportsApi.getGainsSummary()`
  - `reportsApi.exportGainsCSV()`

#### 2.5.4 Broker API Logs Page ✅
Debug view for broker API interactions.

**Page: `/reports/api-logs`**

**Features:**
- Filter by broker, action, status, date range
- Expandable rows showing request/response
- Latency indicator (color-coded)
- Success/failure stats
- Auto-refresh toggle

**Tasks:**
- [x] Create `frontend/src/app/(dashboard)/reports/api-logs/page.tsx`
- [x] Add API functions:
  - `reportsApi.getAPILogs()`
  - `reportsApi.getAPIStats()`

#### 2.5.5 Activity Feed Page ✅
Timeline of all user activities.

**Page: `/reports/activity`**

**Features:**
- Timeline view with icons by activity type
- Filter by category (trading, algo, risk, etc.)
- Filter by date range
- Click to navigate to related entity
- Mark all as read
- Real-time updates via WebSocket (optional)

**Tasks:**
- [x] Create `frontend/src/app/(dashboard)/reports/activity/page.tsx`
- [x] Add API functions:
  - `reportsApi.getActivities()`
  - `reportsApi.markAsRead()`
  - `reportsApi.getUnreadCount()`

#### 2.5.6 Reports Overview Page ✅
Landing page with summary of all reports.

**Page: `/reports`**

**Features:**
- Quick stats cards (Today's P&L, Month's Gains, API Health)
- Recent activity preview
- Quick links to detailed reports
- Account balance chart (last 30 days)

**Tasks:**
- [x] Create `frontend/src/app/(dashboard)/reports/page.tsx`

### 2.6 Recommendation Auto-Trade Pipeline
> 🌿 **Branch:** `phase-2/auto-trade-pipeline`
> **Status:** 🔲 Not Started

**Goal**: Automate the flow from screener recommendations to algo execution with minimal user intervention. User configures preferences once, then just confirms/skips daily picks.

#### Auto-Trade Pipeline Architecture

```mermaid
flowchart TB
    subgraph Config["⚙️ USER CONFIGURATION (One-time Setup)"]
        direction LR
        UC1[Auto-Trade Settings<br/>per category]
        UC2[Strategy Templates<br/>preset params per style]
        UC3[Risk Limits<br/>per auto-trade profile]
        UC4[Confirmation Mode<br/>auto/notify/disabled]
    end

    subgraph Pipeline["🔄 DAILY PIPELINE"]
        direction TB
        PP1[Celery: generate_daily_recommendations]
        PP2[New task: process_auto_trades]
        PP3[For each user with<br/>auto-trade enabled]
        PP4[Match recommendations<br/>to user categories]
        PP5[Create pending strategy<br/>from template]

        PP1 --> PP2 --> PP3 --> PP4 --> PP5
    end

    subgraph Confirmation["✅ CONFIRMATION LAYER"]
        direction TB
        CM1{Confirmation<br/>Mode?}
        CM2[Auto-Execute:<br/>Activate immediately]
        CM3[Notify-First:<br/>Push notification +<br/>await user action]
        CM4[Queue pending<br/>strategies]
        CM5[User reviews in<br/>Pending Trades UI]
        CM6[One-click approve<br/>or reject]

        CM1 -->|auto| CM2
        CM1 -->|notify| CM3 --> CM4 --> CM5 --> CM6
    end

    subgraph Execution["💹 ALGO EXECUTION"]
        EX1[Strategy activated]
        EX2[Position sizing<br/>per user template]
        EX3[Risk checks<br/>per profile]
        EX4[Execute via<br/>existing algo engine]
    end

    Config --> Pipeline
    Pipeline --> Confirmation
    CM2 --> Execution
    CM6 -->|Approved| Execution

    style Config fill:#e3f2fd,stroke:#1976d2
    style Pipeline fill:#fff3e0,stroke:#ff9800
    style Confirmation fill:#f3e5f5,stroke:#9c27b0
    style Execution fill:#e8f5e9,stroke:#4caf50
```

#### 2.6.1 Database Models

**Model: `AutoTradeConfig`** - Per-user, per-category auto-trade settings
```python
class ConfirmationMode(str, Enum):
    AUTO = "auto"           # Execute immediately without confirmation
    NOTIFY = "notify"       # Create pending, notify user, await confirmation
    DISABLED = "disabled"   # Don't auto-trade this category

class AutoTradeConfig(Base):
    __tablename__ = "auto_trade_configs"

    id: UUID
    user_id: UUID (FK users.id)
    category: str                    # momentum, breakout, value, sector
    enabled: bool = False
    confirmation_mode: ConfirmationMode = NOTIFY

    # Link to strategy template for execution params
    strategy_template_id: UUID | None (FK strategy_templates.id)

    # Daily limits for this category
    max_positions_per_day: int = 3
    max_capital_per_day: Decimal = 50000.00

    # Auto-expiry for pending trades
    expiry_hours: int = 4            # Auto-reject if not confirmed within N hours

    created_at: DateTime
    updated_at: DateTime
```

**Model: `StrategyTemplate`** - Reusable strategy configurations
```python
class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"

    id: UUID
    user_id: UUID (FK users.id)
    name: str                        # "My Momentum Setup", "Conservative Swing"
    description: str | None

    # Strategy execution params (same as UserStrategy)
    strategy_type: str               # vwap_momentum, breakout, etc.
    strategy_params: JSON            # Strategy-specific params

    # Position sizing
    position_sizing_method: PositionSizingMethod
    position_size_value: Decimal = 5.00     # % or fixed amount
    max_position_value: Decimal | None

    # Risk limits
    stop_loss_percent: Decimal = 2.00
    take_profit_percent: Decimal = 4.00
    max_daily_loss: Decimal = 5000.00
    max_consecutive_losses: int = 3

    # Product type
    product_type: str = "CNC"        # CNC/MIS/MTF

    # Trading window (new feature!)
    trading_start_time: Time | None  # e.g., 09:45:00
    trading_end_time: Time | None    # e.g., 15:15:00

    is_default: bool = False         # Default template for category
    created_at: DateTime
    updated_at: DateTime
```

**Model: `PendingAutoTrade`** - Queue for user confirmation
```python
class PendingTradeStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"

class PendingAutoTrade(Base):
    __tablename__ = "pending_auto_trades"

    id: UUID
    user_id: UUID (FK users.id)
    auto_trade_config_id: UUID (FK auto_trade_configs.id)

    # Source recommendation
    category: str                    # momentum, breakout, etc.
    recommendation_date: Date
    symbols: JSON                    # List of recommended symbols

    # Inferred strategy details
    recommended_strategy_type: str
    suggested_params: JSON

    # Status
    status: PendingTradeStatus = PENDING

    # If executed, link to created strategy
    created_strategy_id: UUID | None (FK user_strategies.id)

    # Timing
    created_at: DateTime
    expires_at: DateTime
    actioned_at: DateTime | None     # When user approved/rejected
    executed_at: DateTime | None     # When strategy was created & activated

    # User action details
    action_source: str | None        # "ui", "api", "auto_expire"
```

**Tasks:**
- [x] Create `AutoTradeConfig` model in `backend/app/modules/algo/models.py`
- [x] Create `StrategyTemplate` model in `backend/app/modules/algo/models.py`
- [x] Create `PendingAutoTrade` model in `backend/app/modules/algo/models.py`
- [x] Create Alembic migration for new tables
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(algo): add auto-trade pipeline database models`

#### 2.6.2 Auto-Trade Service

**Service: `AutoTradeService`**
```python
class AutoTradeService:
    """Service for managing auto-trade configurations and execution."""

    async def get_user_configs(self, user_id: str) -> list[AutoTradeConfig]:
        """Get all auto-trade configs for a user."""

    async def update_config(
        self, user_id: str, category: str, data: AutoTradeConfigUpdate
    ) -> AutoTradeConfig:
        """Create or update auto-trade config for a category."""

    async def process_recommendations(
        self, category: str, symbols: list[str], recommendation_date: date
    ) -> dict:
        """
        Process new recommendations for all users with auto-trade enabled.
        Called by Celery task after daily recommendations are generated.

        Returns: {user_id: {status, pending_trade_id or strategy_id}}
        """

    async def create_pending_trade(
        self,
        user_id: str,
        config: AutoTradeConfig,
        symbols: list[str],
        recommendation_date: date,
    ) -> PendingAutoTrade:
        """Create a pending auto-trade for user confirmation."""

    async def approve_pending_trade(
        self, user_id: str, pending_id: str
    ) -> UserStrategy:
        """Approve pending trade and create/activate strategy."""

    async def reject_pending_trade(
        self, user_id: str, pending_id: str, reason: str | None = None
    ) -> PendingAutoTrade:
        """Reject pending trade."""

    async def expire_pending_trades(self) -> int:
        """Expire pending trades past their expiry time. Returns count."""

    async def get_pending_trades(
        self, user_id: str, status: PendingTradeStatus | None = None
    ) -> list[PendingAutoTrade]:
        """Get pending trades for a user."""
```

**Tasks:**
- [x] Create `AutoTradeService` in `backend/app/modules/algo/auto_trade_service.py`
- [x] Implement `get_user_configs()` and `update_config()`
- [ ] Implement `process_recommendations()` - core pipeline logic (TODO: integrate with Celery task)
- [x] Implement `create_pending_trade()` with strategy inference
- [x] Implement `approve_pending_trade()` - creates UserStrategy from template
- [x] Implement `reject_pending_trade()` and `expire_pending_trades()`
- [ ] Add unit tests for AutoTradeService
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(algo): implement AutoTradeService for pipeline orchestration`

#### 2.6.3 Strategy Template Service

**Service: `StrategyTemplateService`**
```python
class StrategyTemplateService:
    """Service for managing reusable strategy templates."""

    async def create_template(
        self, user_id: str, data: StrategyTemplateCreate
    ) -> StrategyTemplate:
        """Create a new strategy template."""

    async def get_templates(self, user_id: str) -> list[StrategyTemplate]:
        """Get all templates for a user."""

    async def get_template(
        self, user_id: str, template_id: str
    ) -> StrategyTemplate | None:
        """Get a specific template."""

    async def update_template(
        self, user_id: str, template_id: str, data: StrategyTemplateUpdate
    ) -> StrategyTemplate:
        """Update a template."""

    async def delete_template(self, user_id: str, template_id: str) -> bool:
        """Delete a template."""

    async def create_strategy_from_template(
        self,
        user_id: str,
        template_id: str,
        symbols: list[str],
        name: str,
        auto_activate: bool = False,
    ) -> UserStrategy:
        """Create a UserStrategy from a template with given symbols."""

    async def get_default_for_category(
        self, user_id: str, category: str
    ) -> StrategyTemplate | None:
        """Get the default template for a recommendation category."""
```

**Tasks:**
- [x] Create `StrategyTemplateService` in `backend/app/modules/algo/auto_trade_service.py` (combined with AutoTradeService)
- [x] Implement CRUD operations for templates
- [ ] Implement `create_strategy_from_template()` - converts template to active strategy (TODO: integrate with AlgoService)
- [ ] Implement `get_default_for_category()` for auto-trade pipeline
- [ ] Add unit tests for StrategyTemplateService
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(algo): implement StrategyTemplateService for reusable configs`

#### 2.6.4 API Endpoints

**Router: Auto-Trade Configuration**
```python
# backend/app/modules/algo/auto_trade_router.py

@router.get("/auto-trade/configs")
async def get_auto_trade_configs(user_id: str) -> list[AutoTradeConfigResponse]:
    """Get all auto-trade configurations for the user."""

@router.put("/auto-trade/configs/{category}")
async def update_auto_trade_config(
    category: str, data: AutoTradeConfigUpdate, user_id: str
) -> AutoTradeConfigResponse:
    """Update auto-trade config for a category."""

@router.get("/auto-trade/pending")
async def get_pending_trades(
    user_id: str, status: PendingTradeStatus | None = None
) -> list[PendingAutoTradeResponse]:
    """Get pending auto-trades awaiting confirmation."""

@router.post("/auto-trade/pending/{pending_id}/approve")
async def approve_pending_trade(
    pending_id: str, user_id: str
) -> ApproveTradeResponse:
    """Approve a pending auto-trade, creating and activating the strategy."""

@router.post("/auto-trade/pending/{pending_id}/reject")
async def reject_pending_trade(
    pending_id: str, reason: str | None, user_id: str
) -> PendingAutoTradeResponse:
    """Reject a pending auto-trade."""

@router.post("/auto-trade/pending/approve-all")
async def approve_all_pending(user_id: str) -> BulkApproveResponse:
    """Approve all pending auto-trades."""

@router.post("/auto-trade/pending/reject-all")
async def reject_all_pending(user_id: str) -> BulkRejectResponse:
    """Reject all pending auto-trades."""
```

**Router: Strategy Templates**
```python
@router.get("/templates")
async def get_templates(user_id: str) -> list[StrategyTemplateResponse]:
    """Get all strategy templates for the user."""

@router.post("/templates")
async def create_template(
    data: StrategyTemplateCreate, user_id: str
) -> StrategyTemplateResponse:
    """Create a new strategy template."""

@router.get("/templates/{template_id}")
async def get_template(
    template_id: str, user_id: str
) -> StrategyTemplateResponse:
    """Get a specific template."""

@router.put("/templates/{template_id}")
async def update_template(
    template_id: str, data: StrategyTemplateUpdate, user_id: str
) -> StrategyTemplateResponse:
    """Update a template."""

@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, user_id: str) -> dict:
    """Delete a template."""

@router.post("/templates/{template_id}/create-strategy")
async def create_strategy_from_template(
    template_id: str,
    data: CreateFromTemplateRequest,
    user_id: str,
) -> UserStrategyResponse:
    """Create a strategy from a template."""
```

**Tasks:**
- [x] Create `backend/app/modules/algo/auto_trade_router.py`
- [x] Create template endpoints in auto_trade_router.py (combined with auto-trade router)
- [x] Create Pydantic schemas for all request/response types
- [x] Register routers in main app (`/auto-trade` prefix)
- [ ] Add API tests for all endpoints
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(algo): add API endpoints for auto-trade and templates`

#### 2.6.5 Celery Tasks

**Task: `process_auto_trades`**
```python
@celery_app.task(bind=True, name="worker.tasks.algo.process_auto_trades")
def process_auto_trades(self, category: str, symbols: list[str], date: str) -> dict:
    """
    Process auto-trades after daily recommendations are generated.

    Called by generate_daily_recommendations task after storing recommendations.

    For each user with auto-trade enabled for this category:
    1. Check daily limits (positions, capital)
    2. If confirmation_mode == AUTO:
       - Create strategy from template immediately
       - Activate strategy
    3. If confirmation_mode == NOTIFY:
       - Create pending auto-trade
       - Send notification to user

    Returns: Summary of processing results
    """
```

**Task: `expire_pending_auto_trades`**
```python
@celery_app.task(bind=True, name="worker.tasks.algo.expire_pending_auto_trades")
def expire_pending_auto_trades(self) -> dict:
    """
    Expire pending auto-trades that have passed their expiry time.

    Scheduled to run every hour.

    Returns: {expired_count: int, user_notifications: list}
    """
```

**Tasks:**
- [x] Create `process_auto_trades` task in `worker/worker/tasks/algo.py`
- [x] Create `expire_pending_auto_trades` task
- [x] Update `generate_daily_recommendations` to call `process_auto_trades` after completion
- [x] Add Celery Beat schedule for `expire_pending_auto_trades` (hourly)
- [ ] Add integration tests for Celery tasks
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(worker): add Celery tasks for auto-trade pipeline`

#### 2.6.6 Frontend: Auto-Trade Settings

**Page: `/settings/auto-trade`**

**Features:**
- Toggle auto-trade per category (momentum, breakout, value, sector)
- Confirmation mode selector (Auto/Notify/Disabled)
- Link strategy template per category
- Daily limits configuration
- Expiry hours setting

**Components:**
- `AutoTradeConfigCard` - Card for each category
- `TemplateSelector` - Dropdown to select/create template
- `LimitsForm` - Form for daily limits

**Tasks:**
- [x] Create `frontend/src/app/(dashboard)/settings/auto-trade/page.tsx`
- [x] Create `AutoTradeConfigCard` component
- [x] Create `TemplateSelector` component (integrated in AutoTradeConfigCard)
- [x] Add API functions in `frontend/src/lib/api.ts`
- [x] Run frontend audit: `npm audit`
- [ ] Commit: `feat(frontend): add auto-trade settings page`

#### 2.6.7 Frontend: Strategy Templates

**Page: `/algo/templates`**

**Features:**
- List of saved templates
- Create new template form
- Edit template (modal or page)
- Delete template with confirmation
- Set as default for category
- Duplicate template

**Components:**
- `TemplateCard` - Display template summary
- `TemplateForm` - Create/edit template form
- `TemplatePreview` - Preview what strategy will look like

**Tasks:**
- [x] Create `frontend/src/app/(dashboard)/algo/templates/page.tsx`
- [x] Create `TemplateCard` component
- [x] Create `TemplateForm` component
- [x] Add API functions for templates
- [x] Run frontend audit: `npm audit`
- [ ] Commit: `feat(frontend): add strategy templates management page`

#### 2.6.8 Frontend: Pending Auto-Trades Panel

**Component: `PendingAutoTradesPanel`**

Shows in Dashboard or as a notification drawer panel.

**Features:**
- List of pending auto-trades awaiting confirmation
- Show category, symbols, recommended strategy
- Expiry countdown timer
- Approve / Reject buttons per item
- Bulk approve all / reject all
- Click to expand and see full strategy details
- Empty state when no pending trades

**Tasks:**
- [x] Create `PendingAutoTradesPanel` component
- [x] Add to Dashboard page (collapsible section)
- [x] Add notification badge for pending count
- [x] Create `PendingTradeCard` component (integrated in PendingAutoTradesPanel)
- [x] Implement approve/reject API calls
- [x] Add toast notifications for actions
- [x] Run frontend audit: `npm audit`
- [ ] Commit: `feat(frontend): add pending auto-trades panel`

#### 2.6.9 Notifications Integration

**Tasks:**
- [x] Add notification type `AUTO_TRADE_PENDING` for new pending trades
- [x] Add notification type `AUTO_TRADE_EXECUTED` for auto-executed trades
- [x] Add notification type `AUTO_TRADE_EXPIRED` for expired pending trades
- [x] Add notification type `AUTO_TRADE_APPROVED` for approved pending trades
- [x] Add notification type `AUTO_TRADE_REJECTED` for rejected pending trades
- [x] Add ActivityType enums for auto-trade events
- [x] Add notification methods to `AlgoNotificationService`
- [ ] Integrate notifications with `PendingAutoTradeService` (TODO: wire up service calls)
- [ ] Include action buttons in notification UI (Frontend)
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(notifications): add auto-trade notification types`

#### 2.6.10 Testing & Deployment

**Tasks:**
- [ ] Write unit tests for AutoTradeService
- [ ] Write unit tests for StrategyTemplateService
- [ ] Write integration tests for auto-trade pipeline flow
- [ ] Write E2E tests for frontend auto-trade settings
- [ ] Run full CI suite:
  ```bash
  # Backend
  uv run ruff check
  uv run ruff format
  uv run pytest
  uv run bandit -r backend/

  # Frontend
  npm audit
  npm run lint
  npm run build
  ```
- [ ] Build containers: `podman-compose build`
- [ ] Deploy to staging: `podman-compose up -d`
- [ ] Verify functionality in staging environment
- [ ] Commit: `test(algo): add comprehensive tests for auto-trade pipeline`

#### 2.6.11 Multi-Factor Integration (Tech + Fundamental + Sentiment)

**Goal**: Wire together existing components to create a unified multi-factor scoring system for daily recommendations. Currently, `generate_daily_recommendations` uses only technical screeners, but we have fundamental analysis and news sentiment services that should be integrated.

**Current State (Disconnected):**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Screener (Technical Only) ─────────────> Daily Recommendations     │
│                                                                     │
│  RecommendationService (Tech + Fund) ───> Research Page (separate)  │
│                                                                     │
│  News Sentiment Analyzer ───────────────> News Page (standalone)    │
└─────────────────────────────────────────────────────────────────────┘
```

**Target State (Unified):**
```mermaid
flowchart TB
    subgraph Existing["📦 EXISTING COMPONENTS"]
        E1[StockScreener<br/>screener/screener.py]
        E2[RecommendationService<br/>research/recommendation_service.py]
        E3[KeywordSentimentAnalyzer<br/>shared/providers/news/sentiment.py]
        E4[YahooNewsProvider<br/>GoogleNewsRSSProvider]
    end

    subgraph NewService["🆕 MULTI-FACTOR SCORER"]
        MF1[MultiFactorScorer]
        MF2[get_technical_score]
        MF3[get_fundamental_score]
        MF4[get_sentiment_score]
        MF5[calculate_combined_score]
    end

    subgraph Output["📤 ENHANCED OUTPUT"]
        O1[Daily Recommendations<br/>with multi-factor scores]
        O2[Strategy Selection<br/>based on signal profile]
        O3[Position Direction<br/>long/short inference]
        O4[Confidence Score<br/>for position sizing]
    end

    E1 --> MF2
    E2 --> MF3
    E3 & E4 --> MF4
    MF2 & MF3 & MF4 --> MF5
    MF5 --> O1 & O2 & O3 & O4

    style Existing fill:#e3f2fd,stroke:#1976d2
    style NewService fill:#fff3e0,stroke:#ff9800
    style Output fill:#e8f5e9,stroke:#4caf50
```

**Existing Components to Leverage:**

| Component | Location | What It Provides |
|-----------|----------|------------------|
| `StockScreener` | `backend/app/modules/screener/screener.py` | Technical scores (momentum, breakout, MA, volume) |
| `RecommendationService.calculate_fundamental_score()` | `backend/app/modules/research/recommendation_service.py` | Fundamental scores (PE, PB, ROE, debt, margins) |
| `KeywordSentimentAnalyzer` | `shared/shared/providers/news/sentiment.py` | Sentiment scores (-1 to +1) |
| `YahooNewsProvider` / `GoogleNewsRSSProvider` | `shared/shared/providers/news/` | News articles with sentiment |

##### 2.6.11.1 Create MultiFactorScorer Service

**Service: `MultiFactorScorer`**
```python
# backend/app/modules/algo/multi_factor_scorer.py

from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

class SignalDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"

class ConfidenceLevel(str, Enum):
    HIGH = "high"       # 80+ combined score
    MEDIUM = "medium"   # 60-80 combined score
    LOW = "low"         # 40-60 combined score
    SKIP = "skip"       # Below 40 or conflicting signals

@dataclass
class MultiFactorScore:
    symbol: str
    technical_score: float          # 0-100 from screener
    fundamental_score: float        # 0-100 from RecommendationService
    sentiment_score: float          # -100 to +100 (scaled from -1 to 1)
    combined_score: float           # Weighted average
    direction: SignalDirection      # Inferred from signals
    confidence: ConfidenceLevel     # Based on score alignment
    recommended_strategy: str       # Inferred strategy type
    position_size_multiplier: float # 0.25 to 1.0 based on confidence
    reasons: list[str]              # Explanation of scoring
    skip_reason: str | None         # If confidence == SKIP


class MultiFactorScorer:
    """Combines technical, fundamental, and sentiment analysis."""

    def __init__(
        self,
        db: AsyncSession,
        screener_service: ScreenerService,
        recommendation_service: RecommendationService,
        research_service: ResearchService,  # For news
        weights: dict | None = None,
    ):
        self.db = db
        self.screener_service = screener_service
        self.recommendation_service = recommendation_service
        self.research_service = research_service

        # Default weights (customizable per user/category)
        self.weights = weights or {
            "technical": 0.40,
            "fundamental": 0.40,
            "sentiment": 0.20,
        }

    async def score_symbol(
        self,
        symbol: str,
        category: str,  # momentum, breakout, value, sector
        technical_data: dict | None = None,  # Pre-computed from screener
    ) -> MultiFactorScore:
        """Calculate multi-factor score for a single symbol."""

        # 1. Technical score (from screener or fetch)
        tech_score = await self._get_technical_score(symbol, category, technical_data)

        # 2. Fundamental score (from RecommendationService)
        fund_score, fund_reasons = await self._get_fundamental_score(symbol)

        # 3. Sentiment score (from news providers)
        sent_score, sent_reasons = await self._get_sentiment_score(symbol)

        # 4. Calculate weighted combined score
        combined = (
            tech_score * self.weights["technical"] +
            fund_score * self.weights["fundamental"] +
            ((sent_score + 100) / 2) * self.weights["sentiment"]  # Normalize -100,100 to 0,100
        )

        # 5. Infer direction based on signals
        direction = self._infer_direction(category, tech_score, fund_score, sent_score)

        # 6. Determine confidence level
        confidence = self._calculate_confidence(tech_score, fund_score, sent_score, direction)

        # 7. Recommend strategy type
        strategy = self._recommend_strategy(category, direction, tech_score, sent_score)

        # 8. Position size multiplier based on confidence
        size_mult = self._get_size_multiplier(confidence)

        return MultiFactorScore(
            symbol=symbol,
            technical_score=tech_score,
            fundamental_score=fund_score,
            sentiment_score=sent_score,
            combined_score=combined,
            direction=direction,
            confidence=confidence,
            recommended_strategy=strategy,
            position_size_multiplier=size_mult,
            reasons=fund_reasons + sent_reasons,
            skip_reason=self._get_skip_reason(confidence, tech_score, fund_score, sent_score),
        )

    async def score_recommendations(
        self,
        category: str,
        symbols: list[str],
        screener_results: list[dict],
    ) -> list[MultiFactorScore]:
        """Score all recommendations from a screener run."""

        # Build lookup from screener results
        tech_data = {r["symbol"]: r for r in screener_results}

        scores = []
        for symbol in symbols:
            score = await self.score_symbol(symbol, category, tech_data.get(symbol))
            scores.append(score)

        # Sort by combined score, filter out SKIP
        scores.sort(key=lambda s: s.combined_score, reverse=True)
        return scores

    def _infer_direction(
        self,
        category: str,
        tech: float,
        fund: float,
        sent: float
    ) -> SignalDirection:
        """Infer long/short/neutral based on signal alignment."""

        # Strong bullish alignment
        if tech >= 60 and fund >= 50 and sent > 20:
            return SignalDirection.LONG

        # Strong bearish alignment (for short-capable strategies)
        if tech <= 40 and sent < -30:
            return SignalDirection.SHORT

        # Value/pullback with good fundamentals but oversold
        if category == "value" and fund >= 60 and tech <= 40:
            return SignalDirection.LONG  # Buy the dip

        # Mixed signals
        return SignalDirection.NEUTRAL

    def _calculate_confidence(
        self,
        tech: float,
        fund: float,
        sent: float,
        direction: SignalDirection,
    ) -> ConfidenceLevel:
        """Calculate confidence based on signal alignment."""

        # Check for conflicting signals (red flag)
        if direction == SignalDirection.LONG and sent < -40:
            return ConfidenceLevel.SKIP  # Bullish tech but very bearish news

        if direction == SignalDirection.SHORT and fund >= 70:
            return ConfidenceLevel.SKIP  # Bearish signals but great fundamentals

        # Calculate alignment score
        combined = (tech + fund + (sent + 100) / 2) / 3

        if combined >= 75:
            return ConfidenceLevel.HIGH
        elif combined >= 55:
            return ConfidenceLevel.MEDIUM
        elif combined >= 40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.SKIP

    def _recommend_strategy(
        self,
        category: str,
        direction: SignalDirection,
        tech: float,
        sent: float,
    ) -> str:
        """Recommend strategy type based on signals."""

        if category == "momentum" and direction == SignalDirection.LONG:
            return "trend_following" if sent > 0 else "momentum_pullback"

        if category == "breakout":
            return "breakout_continuation" if tech >= 70 else "breakout_retest"

        if category == "value":
            return "mean_reversion" if sent < 0 else "value_momentum"

        if category == "sector":
            return "sector_rotation"

        return "balanced"  # Default

    def _get_size_multiplier(self, confidence: ConfidenceLevel) -> float:
        """Position size multiplier based on confidence."""
        return {
            ConfidenceLevel.HIGH: 1.0,
            ConfidenceLevel.MEDIUM: 0.7,
            ConfidenceLevel.LOW: 0.4,
            ConfidenceLevel.SKIP: 0.0,
        }[confidence]
```

**Tasks:**
- [ ] Create `MultiFactorScorer` in `backend/app/modules/algo/multi_factor_scorer.py`
- [ ] Implement `_get_technical_score()` using existing screener results
- [ ] Implement `_get_fundamental_score()` using `RecommendationService.calculate_fundamental_score()`
- [ ] Implement `_get_sentiment_score()` using `ResearchService.get_news()` and sentiment aggregation
- [ ] Implement direction inference logic (`_infer_direction()`)
- [ ] Implement confidence calculation (`_calculate_confidence()`)
- [ ] Implement strategy recommendation (`_recommend_strategy()`)
- [ ] Add unit tests for MultiFactorScorer
- [ ] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [ ] Commit: `feat(algo): implement MultiFactorScorer service`

##### 2.6.11.2 Update Daily Recommendations Task

**Update `generate_daily_recommendations` to use multi-factor scoring:**

```python
# worker/worker/tasks/screener.py

@celery_app.task(bind=True, name="worker.tasks.screener.generate_daily_recommendations")
def generate_daily_recommendations(self) -> dict:
    """Generate daily stock recommendations using multi-factor analysis.

    Enhanced flow:
    1. Run technical screeners (momentum, breakout, value, sector)
    2. For each result, enrich with fundamental + sentiment scores
    3. Re-rank by combined multi-factor score
    4. Store enhanced recommendations with all scores
    """

    for preset in presets:
        # Step 1: Run technical screener (existing)
        screener_results = _run_screener_sync(...)

        # Step 2: NEW - Enrich with multi-factor scores
        symbols = [r["symbol"] for r in screener_results]
        multi_factor_scores = _enrich_with_multi_factor(
            category=category,
            symbols=symbols,
            screener_results=screener_results,
        )

        # Step 3: Filter and re-rank
        enhanced_results = []
        for mf_score in multi_factor_scores:
            if mf_score.confidence == ConfidenceLevel.SKIP:
                continue  # Filter out low confidence

            enhanced_results.append({
                "symbol": mf_score.symbol,
                "score": mf_score.combined_score,  # Use combined score
                "technical_score": mf_score.technical_score,
                "fundamental_score": mf_score.fundamental_score,
                "sentiment_score": mf_score.sentiment_score,
                "direction": mf_score.direction.value,
                "confidence": mf_score.confidence.value,
                "recommended_strategy": mf_score.recommended_strategy,
                "position_size_multiplier": mf_score.position_size_multiplier,
                "reasons": mf_score.reasons,
            })

        # Step 4: Store enhanced recommendations
        _store_recommendations(today, category, enhanced_results)
```

**Tasks:**
- [ ] Update `generate_daily_recommendations` to call `MultiFactorScorer`
- [ ] Add helper function `_enrich_with_multi_factor()` in screener tasks
- [ ] Update `DailyRecommendation` model to store additional fields:
  - `technical_score`, `fundamental_score`, `sentiment_score`
  - `direction`, `confidence`, `recommended_strategy`
  - `position_size_multiplier`
- [ ] Create Alembic migration for new `DailyRecommendation` columns
- [ ] Update `_store_recommendations()` to save enhanced data
- [ ] Add integration tests for enhanced recommendation flow
- [ ] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [ ] Commit: `feat(screener): integrate multi-factor scoring into daily recommendations`

##### 2.6.11.3 Update AutoTradeService Integration

**Connect multi-factor scores to auto-trade pipeline:**

```python
# backend/app/modules/algo/auto_trade_service.py

class AutoTradeService:
    async def process_recommendations(
        self, category: str, symbols: list[str], recommendation_date: date
    ) -> dict:
        """Process recommendations using multi-factor scores."""

        # Get enhanced recommendations with multi-factor scores
        recommendations = await self._get_enhanced_recommendations(
            category, recommendation_date
        )

        for user_id, config in users_with_auto_trade.items():
            for rec in recommendations:
                # Skip if confidence too low for user's settings
                if not self._meets_confidence_threshold(rec, config):
                    continue

                # Use recommended strategy from multi-factor analysis
                strategy_type = rec.get("recommended_strategy")

                # Adjust position size based on confidence
                position_multiplier = rec.get("position_size_multiplier", 1.0)

                # Create pending trade with enhanced data
                await self.create_pending_trade(
                    user_id=user_id,
                    config=config,
                    symbol=rec["symbol"],
                    direction=rec.get("direction", "long"),
                    strategy_type=strategy_type,
                    position_multiplier=position_multiplier,
                    scores={
                        "technical": rec.get("technical_score"),
                        "fundamental": rec.get("fundamental_score"),
                        "sentiment": rec.get("sentiment_score"),
                        "combined": rec.get("score"),
                    },
                )
```

**Tasks:**
- [ ] Update `AutoTradeService.process_recommendations()` to use multi-factor data
- [ ] Add confidence threshold setting to `AutoTradeConfig` model
- [ ] Update `PendingAutoTrade` model to store multi-factor scores
- [ ] Implement `_meets_confidence_threshold()` method
- [ ] Use `position_size_multiplier` when creating strategies from templates
- [ ] Add tests for confidence-based filtering
- [ ] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [ ] Commit: `feat(algo): connect multi-factor scores to auto-trade pipeline`

##### 2.6.11.4 Frontend: Multi-Factor Score Display

**Update recommendation cards to show multi-factor breakdown:**

**Features:**
- Score breakdown chart (bar chart: Tech / Fund / Sentiment)
- Direction badge (LONG 🟢 / SHORT 🔴 / NEUTRAL ⚪)
- Confidence indicator (HIGH ⭐⭐⭐ / MEDIUM ⭐⭐ / LOW ⭐)
- Recommended strategy chip
- Position size indicator
- Tooltip with scoring reasons

**Tasks:**
- [ ] Create `MultiFactorScoreCard` component
- [ ] Add score breakdown visualization (mini bar chart)
- [ ] Add direction and confidence badges
- [ ] Update Daily Recommendations widget to show multi-factor data
- [ ] Update Pending Auto-Trades panel to show scores
- [ ] Run frontend audit: `npm audit`
- [ ] Commit: `feat(frontend): display multi-factor scores in recommendations`

##### 2.6.11.5 User Configuration: Scoring Weights

**Allow users to customize factor weights from the UI.**

**Page: `/settings/auto-trade/weights` or as a section in `/settings/auto-trade`**

**UI Mockup:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│  📊 Multi-Factor Scoring Weights                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Configure how recommendations are scored. Weights must total 100%.     │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  📈 Technical Analysis                              [====] 40%  │   │
│  │  ◄━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━►   │   │
│  │  Momentum, breakouts, moving averages, RSI, volume              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  📊 Fundamental Analysis                            [====] 40%  │   │
│  │  ◄━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━►   │   │
│  │  P/E, P/B, ROE, debt ratios, earnings growth, margins           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  📰 News Sentiment                                  [==  ] 20%  │   │
│  │  ◄━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━►   │   │
│  │  Recent news sentiment analysis (bullish/bearish/neutral)       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Total: [████████████████████████████████████████] 100% ✓              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  🎯 Quick Presets                                               │   │
│  │                                                                  │   │
│  │  [Technical Focus]  [Fundamental Focus]  [Balanced]             │   │
│  │       50/30/20          30/50/20          40/40/20              │   │
│  │                                                                  │   │
│  │  [Sentiment Aware]  [News Trader]  [Value Investor]             │   │
│  │       35/35/30         25/25/50        20/60/20                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  🎚️ Minimum Confidence Level                                    │   │
│  │                                                                  │   │
│  │  Only auto-trade when confidence is at least:                   │   │
│  │                                                                  │   │
│  │  ○ High (80+)     - Very selective, fewer trades                │   │
│  │  ● Medium (60-80) - Balanced approach (recommended)             │   │
│  │  ○ Low (40-60)    - More trades, lower conviction               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  📊 Live Preview                                                │   │
│  │                                                                  │   │
│  │  With current weights, today's top pick would be:               │   │
│  │                                                                  │   │
│  │  RELIANCE  Score: 78.5                                          │   │
│  │  ├─ Technical:    82 × 0.40 = 32.8                              │   │
│  │  ├─ Fundamental:  75 × 0.40 = 30.0                              │   │
│  │  └─ Sentiment:    +39 × 0.20 = 15.7 (scaled)                    │   │
│  │                                                                  │   │
│  │  Direction: LONG 🟢  Confidence: HIGH ⭐⭐⭐                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│                                    [Reset to Default]  [Save Changes]  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Component: `WeightConfigurationPanel`**
```typescript
// frontend/src/components/auto-trade/WeightConfigurationPanel.tsx

interface WeightConfig {
  technical: number;      // 0-100
  fundamental: number;    // 0-100
  sentiment: number;      // 0-100
}

interface WeightPreset {
  name: string;
  description: string;
  weights: WeightConfig;
  icon: string;
}

const PRESETS: WeightPreset[] = [
  {
    name: "Technical Focus",
    description: "Chart patterns & momentum",
    weights: { technical: 50, fundamental: 30, sentiment: 20 },
    icon: "📈"
  },
  {
    name: "Fundamental Focus",
    description: "Value & quality metrics",
    weights: { technical: 30, fundamental: 50, sentiment: 20 },
    icon: "📊"
  },
  {
    name: "Balanced",
    description: "Equal tech & fundamental",
    weights: { technical: 40, fundamental: 40, sentiment: 20 },
    icon: "⚖️"
  },
  {
    name: "Sentiment Aware",
    description: "Higher news influence",
    weights: { technical: 35, fundamental: 35, sentiment: 30 },
    icon: "📰"
  },
  {
    name: "News Trader",
    description: "Maximum sentiment weight",
    weights: { technical: 25, fundamental: 25, sentiment: 50 },
    icon: "🗞️"
  },
  {
    name: "Value Investor",
    description: "Fundamentals first",
    weights: { technical: 20, fundamental: 60, sentiment: 20 },
    icon: "💎"
  },
];

function WeightConfigurationPanel() {
  const [weights, setWeights] = useState<WeightConfig>({
    technical: 40,
    fundamental: 40,
    sentiment: 20,
  });
  const [minConfidence, setMinConfidence] = useState<'high' | 'medium' | 'low'>('medium');

  // Auto-normalize: when one slider changes, adjust others proportionally
  const handleWeightChange = (factor: keyof WeightConfig, newValue: number) => {
    const oldValue = weights[factor];
    const delta = newValue - oldValue;
    const remaining = 100 - newValue;

    // Distribute delta proportionally to other factors
    const otherFactors = Object.keys(weights).filter(k => k !== factor) as (keyof WeightConfig)[];
    const otherTotal = otherFactors.reduce((sum, k) => sum + weights[k], 0);

    if (otherTotal > 0) {
      const newWeights = { ...weights, [factor]: newValue };
      otherFactors.forEach(k => {
        newWeights[k] = Math.round((weights[k] / otherTotal) * remaining);
      });
      // Ensure exactly 100%
      const total = Object.values(newWeights).reduce((a, b) => a + b, 0);
      if (total !== 100) {
        newWeights[otherFactors[0]] += 100 - total;
      }
      setWeights(newWeights);
    }
  };

  const applyPreset = (preset: WeightPreset) => {
    setWeights(preset.weights);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Multi-Factor Scoring Weights</CardTitle>
        <CardDescription>
          Configure how recommendations are scored. Weights must total 100%.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Weight Sliders */}
        <WeightSlider
          label="Technical Analysis"
          icon="📈"
          description="Momentum, breakouts, moving averages, RSI, volume"
          value={weights.technical}
          onChange={(v) => handleWeightChange('technical', v)}
        />
        <WeightSlider
          label="Fundamental Analysis"
          icon="📊"
          description="P/E, P/B, ROE, debt ratios, earnings growth"
          value={weights.fundamental}
          onChange={(v) => handleWeightChange('fundamental', v)}
        />
        <WeightSlider
          label="News Sentiment"
          icon="📰"
          description="Recent news sentiment (bullish/bearish/neutral)"
          value={weights.sentiment}
          onChange={(v) => handleWeightChange('sentiment', v)}
        />

        {/* Total Indicator */}
        <TotalIndicator total={weights.technical + weights.fundamental + weights.sentiment} />

        {/* Presets */}
        <PresetGrid presets={PRESETS} onSelect={applyPreset} />

        {/* Confidence Selector */}
        <ConfidenceSelector value={minConfidence} onChange={setMinConfidence} />

        {/* Live Preview */}
        <LiveScorePreview weights={weights} />
      </CardContent>
    </Card>
  );
}
```

**API Schema Updates:**
```python
# backend/app/modules/algo/schemas.py

class WeightConfigUpdate(BaseModel):
    """Schema for updating multi-factor weights."""
    weight_technical: float = Field(ge=0, le=100, description="Technical analysis weight (0-100)")
    weight_fundamental: float = Field(ge=0, le=100, description="Fundamental analysis weight (0-100)")
    weight_sentiment: float = Field(ge=0, le=100, description="News sentiment weight (0-100)")
    min_confidence: Literal["high", "medium", "low"] = "medium"

    @validator("weight_sentiment")
    def weights_must_sum_to_100(cls, v, values):
        tech = values.get("weight_technical", 0)
        fund = values.get("weight_fundamental", 0)
        total = tech + fund + v
        if abs(total - 100) > 0.01:  # Allow tiny float errors
            raise ValueError(f"Weights must sum to 100, got {total}")
        return v

class WeightConfigResponse(BaseModel):
    """Response schema for weight configuration."""
    weight_technical: float
    weight_fundamental: float
    weight_sentiment: float
    min_confidence: str

    # Computed preview (optional)
    preview_symbol: str | None = None
    preview_scores: dict | None = None
```

**API Endpoints:**
```python
# backend/app/modules/algo/auto_trade_router.py

@router.get("/auto-trade/weights")
async def get_weight_config(user_id: str) -> WeightConfigResponse:
    """Get user's current multi-factor weight configuration."""

@router.put("/auto-trade/weights")
async def update_weight_config(
    data: WeightConfigUpdate, user_id: str
) -> WeightConfigResponse:
    """Update multi-factor weight configuration."""

@router.post("/auto-trade/weights/preview")
async def preview_with_weights(
    data: WeightConfigUpdate, user_id: str
) -> list[dict]:
    """Preview how current recommendations would score with given weights."""

@router.get("/auto-trade/weights/presets")
async def get_weight_presets() -> list[dict]:
    """Get available weight presets."""
```

**Model Update:**
```python
class AutoTradeConfig(Base):
    # ... existing fields ...

    # Multi-factor weights (stored as 0-100, converted to 0-1 for calculations)
    weight_technical: int = 40       # 0-100
    weight_fundamental: int = 40     # 0-100
    weight_sentiment: int = 20       # 0-100

    # Minimum confidence to auto-trade
    min_confidence: str = "medium"   # "high", "medium", "low"

    @property
    def weights_normalized(self) -> dict[str, float]:
        """Return weights as decimals (0-1) for calculations."""
        return {
            "technical": self.weight_technical / 100,
            "fundamental": self.weight_fundamental / 100,
            "sentiment": self.weight_sentiment / 100,
        }
```

**Tasks:**
- [ ] Add weight fields to `AutoTradeConfig` model (`weight_technical`, `weight_fundamental`, `weight_sentiment`, `min_confidence`)
- [ ] Create Alembic migration for new columns with default values (40/40/20)
- [ ] Create `WeightConfigUpdate` and `WeightConfigResponse` schemas
- [ ] Add API endpoints: `GET/PUT /auto-trade/weights`, `POST /auto-trade/weights/preview`
- [ ] Update `MultiFactorScorer` to accept custom weights from user config
- [ ] Create `WeightConfigurationPanel` React component
- [ ] Create `WeightSlider` component with percentage display
- [ ] Implement auto-normalize logic (sliders adjust proportionally)
- [ ] Create `PresetGrid` component with preset buttons
- [ ] Create `ConfidenceSelector` radio group component
- [ ] Create `LiveScorePreview` component showing real-time scoring preview
- [ ] Add input validation (weights must sum to 100)
- [ ] Add loading and error states
- [ ] Add toast notifications for save success/failure
- [ ] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [ ] Run frontend audit: `npm audit`
- [ ] Commit: `feat(algo): add user-configurable multi-factor weights UI`

##### 2.6.11.6 Testing & Deployment

**Tasks:**
- [ ] Write unit tests for `MultiFactorScorer`
- [ ] Write unit tests for direction inference logic
- [ ] Write unit tests for confidence calculation
- [ ] Write integration tests for enhanced daily recommendations
- [ ] Write integration tests for auto-trade with multi-factor filtering
- [ ] Test sentiment API rate limits and caching
- [ ] Run full CI suite:
  ```bash
  # Backend
  uv run ruff check
  uv run ruff format
  uv run pytest
  uv run bandit -r backend/

  # Worker
  cd worker && uv run pytest

  # Frontend
  npm audit
  npm run lint
  npm run build
  ```
- [ ] Build containers: `podman-compose build`
- [ ] Deploy to staging: `podman-compose up -d`
- [ ] Verify multi-factor scoring in staging
- [ ] Monitor sentiment API usage and caching efficiency
- [ ] Commit: `test(algo): add comprehensive tests for multi-factor integration`

#### 2.6.12 Custom Screener to Auto-Trade

**Goal**: Allow users to use their own custom screeners (not just daily presets) as the source for auto-trade. User creates a screener with their preferred filters → connects it to auto-trade → system runs it on schedule and creates strategies.

**Current Limitation:**
- Auto-trade only works with 4 preset categories (momentum, breakout, value, sector)
- User's saved custom screeners are NOT connected to auto-trade pipeline
- No way to schedule custom screener runs

**Enhanced Flow:**
```mermaid
flowchart TB
    subgraph Sources["📊 SCREENER SOURCES"]
        S1[Preset: Momentum]
        S2[Preset: Breakout]
        S3[Preset: Value]
        S4[Preset: Sector]
        S5[Custom: User's Screener 1]
        S6[Custom: User's Screener 2]
    end

    subgraph Config["⚙️ AUTO-TRADE CONFIG"]
        C1[Select Screener Source]
        C2[Run Frequency<br/>Daily/Hourly/Manual]
        C3[Strategy Template]
        C4[Multi-Factor Weights]
    end

    subgraph Pipeline["🔄 EXECUTION"]
        P1[Run Selected Screener]
        P2[Apply Multi-Factor Scoring]
        P3[Filter by Confidence]
        P4[Create Pending Trades]
    end

    S1 & S2 & S3 & S4 & S5 & S6 --> C1
    C1 & C2 & C3 & C4 --> P1
    P1 --> P2 --> P3 --> P4

    style Sources fill:#e3f2fd,stroke:#1976d2
    style Config fill:#fff3e0,stroke:#ff9800
    style Pipeline fill:#e8f5e9,stroke:#4caf50
```

##### 2.6.12.1 Saved Screener Model

**Model: `SavedScreener`** - User's custom screener configurations
```python
class SavedScreener(Base):
    __tablename__ = "saved_screeners"

    id: UUID
    user_id: UUID (FK users.id)
    name: str                        # "My Small Cap Momentum"
    description: str | None

    # Screener configuration
    universe: str = "nifty500"       # nifty50, nifty100, nifty500, all
    filters: JSON                    # List of filter configs
    min_score: float = 50.0
    top_n: int = 20

    # Auto-trade linkage
    is_auto_trade_enabled: bool = False
    auto_trade_config_id: UUID | None (FK auto_trade_configs.id)

    # Scheduling
    run_frequency: str = "daily"     # daily, hourly, manual
    run_time: Time | None = "09:20"  # For daily runs
    last_run_at: DateTime | None
    next_run_at: DateTime | None

    # Inferred strategy type (based on filters)
    inferred_strategy_type: str | None  # Computed from filter analysis

    created_at: DateTime
    updated_at: DateTime
```

**Tasks:**
- [x] Create `CustomScreener` model with auto-trade fields in `backend/app/modules/screener/models.py`
- [x] Create Alembic migration for screener auto-trade fields
- [x] Add `saved_screener_id` field to `AutoTradeConfig` model
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(screener): add auto-trade fields to CustomScreener model`

##### 2.6.12.2 Saved Screener Service

**Service: `SavedScreenerService`**
```python
class SavedScreenerService:
    """Service for managing saved screener configurations."""

    async def create_screener(
        self, user_id: str, data: SavedScreenerCreate
    ) -> SavedScreener:
        """Save a new custom screener configuration."""

    async def get_screeners(self, user_id: str) -> list[SavedScreener]:
        """Get all saved screeners for a user."""

    async def get_screener(
        self, user_id: str, screener_id: str
    ) -> SavedScreener | None:
        """Get a specific saved screener."""

    async def update_screener(
        self, user_id: str, screener_id: str, data: SavedScreenerUpdate
    ) -> SavedScreener:
        """Update a saved screener."""

    async def delete_screener(self, user_id: str, screener_id: str) -> bool:
        """Delete a saved screener."""

    async def run_screener(
        self, user_id: str, screener_id: str
    ) -> list[dict]:
        """Execute a saved screener and return results."""

    async def link_to_auto_trade(
        self, user_id: str, screener_id: str, auto_trade_config_id: str
    ) -> SavedScreener:
        """Link a saved screener to an auto-trade configuration."""

    async def infer_strategy_type(self, filters: list[dict]) -> str:
        """Analyze screener filters to suggest best strategy type."""
        # Example logic:
        # - Has MomentumFilter with bullish mode → "trend_following"
        # - Has BreakoutFilter → "breakout_continuation"
        # - Has MomentumFilter with bearish/oversold → "mean_reversion"
        # - Has VolumeFilter with spike → "volume_breakout"
```

**Strategy Inference Logic:**
```python
def infer_strategy_type(self, filters: list[dict]) -> str:
    """Infer best strategy type from screener filters."""

    filter_types = [f.get("filter_type") for f in filters]
    filter_params = {f.get("filter_type"): f.get("params", {}) for f in filters}

    # Check for momentum characteristics
    if "momentum" in filter_types:
        momentum_params = filter_params.get("momentum", {})
        if momentum_params.get("momentum_mode") == "bullish":
            if "breakout" in filter_types:
                return "breakout_momentum"
            return "trend_following"
        elif momentum_params.get("momentum_mode") == "bearish":
            return "mean_reversion"  # Oversold bounce

    # Check for breakout
    if "breakout" in filter_types:
        if "volume" in filter_types:
            volume_params = filter_params.get("volume", {})
            if volume_params.get("require_spike"):
                return "volume_breakout"
        return "breakout_continuation"

    # Check for value/fundamental focus
    if "fundamental" in filter_types:
        return "value_momentum"

    # Check for moving average based
    if "moving_average" in filter_types:
        ma_params = filter_params.get("moving_average", {})
        if ma_params.get("require_golden_cross"):
            return "ma_crossover"
        return "trend_following"

    return "balanced"  # Default
```

**Tasks:**
- [x] Add auto-trade methods to existing `ScreenerService` in `backend/app/modules/screener/service.py`
- [x] Implement CRUD operations with auto-trade fields in existing CustomScreener
- [x] Implement `run_custom_screener_for_auto_trade()` for scheduled runs
- [x] Implement `link_to_auto_trade()` for connecting to auto-trade config
- [x] Implement `infer_strategy_type()` using StrategyInferenceEngine
- [ ] Add unit tests for auto-trade screener methods
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(screener): add auto-trade methods to ScreenerService`

##### 2.6.12.3 API Endpoints for Saved Screeners

**Router: Saved Screeners**
```python
# backend/app/modules/screener/saved_screener_router.py

@router.get("/screeners/saved")
async def get_saved_screeners(user_id: str) -> list[SavedScreenerResponse]:
    """Get all saved screeners for the user."""

@router.post("/screeners/saved")
async def create_saved_screener(
    data: SavedScreenerCreate, user_id: str
) -> SavedScreenerResponse:
    """Save a new custom screener configuration."""

@router.get("/screeners/saved/{screener_id}")
async def get_saved_screener(
    screener_id: str, user_id: str
) -> SavedScreenerResponse:
    """Get a specific saved screener."""

@router.put("/screeners/saved/{screener_id}")
async def update_saved_screener(
    screener_id: str, data: SavedScreenerUpdate, user_id: str
) -> SavedScreenerResponse:
    """Update a saved screener."""

@router.delete("/screeners/saved/{screener_id}")
async def delete_saved_screener(screener_id: str, user_id: str) -> dict:
    """Delete a saved screener."""

@router.post("/screeners/saved/{screener_id}/run")
async def run_saved_screener(
    screener_id: str, user_id: str
) -> ScreenerRunResponse:
    """Execute a saved screener and return results."""

@router.post("/screeners/saved/{screener_id}/link-auto-trade")
async def link_screener_to_auto_trade(
    screener_id: str,
    data: LinkAutoTradeRequest,  # {auto_trade_config_id, run_frequency, run_time}
    user_id: str
) -> SavedScreenerResponse:
    """Link a saved screener to auto-trade configuration."""

@router.post("/screeners/saved/{screener_id}/unlink-auto-trade")
async def unlink_screener_from_auto_trade(
    screener_id: str, user_id: str
) -> SavedScreenerResponse:
    """Unlink a saved screener from auto-trade."""

@router.get("/screeners/saved/{screener_id}/infer-strategy")
async def infer_strategy_for_screener(
    screener_id: str, user_id: str
) -> StrategyInferenceResponse:
    """Get inferred strategy type based on screener filters."""
```

**Tasks:**
- [x] Add auto-trade endpoints to existing `backend/app/modules/screener/router.py`
- [x] Create Pydantic schemas: `LinkAutoTradeRequest`, `UnlinkAutoTradeResponse`, `StrategyInferenceResponse`
- [x] Add `run_frequency` schema enum (`RunFrequencyEnum`)
- [x] Router already registered in main app
- [ ] Add API tests for all endpoints
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(screener): add auto-trade endpoints to existing router`

##### 2.6.12.4 Scheduled Screener Runs

**Celery Tasks for Custom Screener Scheduling:**
```python
# worker/worker/tasks/screener.py

@celery_app.task(bind=True, name="worker.tasks.screener.run_scheduled_screeners")
def run_scheduled_screeners(self, frequency: str = "daily") -> dict:
    """Run all saved screeners scheduled for the given frequency.

    Args:
        frequency: "daily" or "hourly"

    For each screener with matching frequency:
    1. Run the screener
    2. Apply multi-factor scoring
    3. Create pending auto-trades (if linked)
    4. Update last_run_at and next_run_at
    """

    # Get all screeners with this frequency that are due to run
    screeners = _get_due_screeners(frequency)

    results = []
    for screener in screeners:
        try:
            # Run screener
            screener_results = _run_saved_screener(screener)

            # If linked to auto-trade, process results
            if screener.is_auto_trade_enabled and screener.auto_trade_config_id:
                auto_trade_result = _process_screener_for_auto_trade(
                    screener=screener,
                    results=screener_results,
                )
                results.append({
                    "screener_id": str(screener.id),
                    "screener_name": screener.name,
                    "stocks_found": len(screener_results),
                    "auto_trade_processed": True,
                    "pending_trades_created": auto_trade_result.get("pending_count", 0),
                })
            else:
                results.append({
                    "screener_id": str(screener.id),
                    "screener_name": screener.name,
                    "stocks_found": len(screener_results),
                    "auto_trade_processed": False,
                })

            # Update timestamps
            _update_screener_run_times(screener)

        except Exception as e:
            logger.exception(f"Error running screener {screener.id}: {e}")
            results.append({
                "screener_id": str(screener.id),
                "error": str(e),
            })

    return {
        "frequency": frequency,
        "screeners_processed": len(results),
        "results": results,
    }


@celery_app.task(bind=True, name="worker.tasks.screener.run_single_screener")
def run_single_screener(self, screener_id: str, user_id: str) -> dict:
    """Run a single saved screener on-demand.

    Triggered by user clicking "Run Now" button.
    """
    pass
```

**Celery Beat Schedule:**
```python
# worker/worker/celery_config.py

beat_schedule = {
    # ... existing schedules ...

    # Run daily custom screeners at 9:20 AM IST (before market open)
    "run-daily-custom-screeners": {
        "task": "worker.tasks.screener.run_scheduled_screeners",
        "schedule": crontab(hour=3, minute=50),  # 9:20 AM IST = 3:50 UTC
        "args": ("daily",),
    },

    # Run hourly custom screeners
    "run-hourly-custom-screeners": {
        "task": "worker.tasks.screener.run_scheduled_screeners",
        "schedule": crontab(minute=5),  # 5 minutes past every hour
        "args": ("hourly",),
    },
}
```

**Tasks:**
- [x] Create `run_scheduled_screeners` task in `worker/worker/tasks/screener.py`
- [x] Create `run_single_screener` task for on-demand runs
- [x] Implement `_get_due_screeners()` helper to find screeners ready to run
- [ ] Implement `_process_screener_for_auto_trade()` to create pending trades (TODO: integrate with PendingAutoTradeService)
- [x] Add Celery Beat schedules for daily and hourly runs in `worker/worker/celery_app.py`
- [ ] Add integration tests for scheduled screener tasks
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(worker): add scheduled custom screener execution`

##### 2.6.12.5 Update Auto-Trade Config for Custom Screeners

**Update `AutoTradeConfig` model:**
```python
class ScreenerSourceType(str, Enum):
    PRESET = "preset"       # Use daily preset recommendations
    CUSTOM = "custom"       # Use saved custom screener

class AutoTradeConfig(Base):
    # ... existing fields ...

    # Screener source selection
    screener_source_type: ScreenerSourceType = PRESET

    # If PRESET: which category (momentum, breakout, value, sector)
    preset_category: str | None = None

    # If CUSTOM: which saved screener
    saved_screener_id: UUID | None (FK saved_screeners.id)

    # The saved screener (relationship)
    saved_screener: SavedScreener | None = relationship(...)
```

**Tasks:**
- [x] Add `screener_source_type`, `preset_category`, `saved_screener_id` to `AutoTradeConfig`
- [x] Create Alembic migration for new tables (`20260223_1100_add_auto_trade_config_tables.py`)
- [x] Update `AutoTradeConfigCreate` and `AutoTradeConfigUpdate` schemas with new fields
- [ ] Update `AutoTradeService.process_recommendations()` to handle both source types (TODO: integrate with Celery task)
- [x] Add validation: if CUSTOM, `saved_screener_id` required
- [x] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [x] Commit: `feat(algo): update AutoTradeConfig for custom screener sources`

##### 2.6.12.6 Frontend: Save Screener Flow

**Update Screener Page to allow saving:**

**UI Flow:**
1. User creates/runs a screener with custom filters
2. "Save Screener" button appears
3. Save dialog with name, description
4. Option to "Enable Auto-Trade" with settings

**Save Screener Dialog:**
```
┌─────────────────────────────────────────────────────────────────┐
│  💾 Save Screener                                         [X]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Name: [My Momentum Screener________________]                   │
│                                                                 │
│  Description: [Finds high momentum stocks with volume___]       │
│               [spike in Nifty 500 universe______________]       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  📊 Screener Summary                                    │   │
│  │  Universe: Nifty 500                                    │   │
│  │  Filters: Momentum (bullish), Volume (spike), MA (200)  │   │
│  │  Min Score: 50 | Top N: 20                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ☐ Enable Auto-Trade for this screener                         │
│                                                                 │
│  (If checked, shows auto-trade options below)                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🤖 Auto-Trade Settings                                 │   │
│  │                                                          │   │
│  │  Run Frequency:                                          │   │
│  │  ○ Daily at [09:20] AM                                   │   │
│  │  ○ Hourly                                                │   │
│  │  ○ Manual only                                           │   │
│  │                                                          │   │
│  │  Strategy Template: [Select template ▼]                  │   │
│  │                                                          │   │
│  │  Inferred Strategy: trend_following                      │   │
│  │  (Based on your momentum + MA filters)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                              [Cancel]  [Save Screener]          │
└─────────────────────────────────────────────────────────────────┘
```

**Tasks:**
- [x] Add "Save Screener" button to Screener results page
- [x] Create `SaveScreenerDialog` component
- [x] Add auto-trade toggle with conditional settings
- [x] Show inferred strategy type based on filters
- [x] Add run frequency selector (daily/hourly/manual)
- [x] Add strategy template selector
- [x] Call API to save screener with auto-trade config
- [x] Run frontend audit: `npm audit`
- [ ] Commit: `feat(frontend): add save screener dialog with auto-trade option`

##### 2.6.12.7 Frontend: Saved Screeners Management

**Page: `/screener/saved`**

**Features:**
- List of saved screeners
- Run status (last run, next run)
- Auto-trade status badge
- Actions: Run Now, Edit, Delete, Link/Unlink Auto-Trade

**UI Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│  📋 Saved Screeners                                    [+ New Screener] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  📈 My Momentum Screener                        [Auto-Trade 🟢]  │   │
│  │  Universe: Nifty 500 | Filters: 3 | Min Score: 50               │   │
│  │  Last Run: Today 9:20 AM | Next Run: Tomorrow 9:20 AM           │   │
│  │  Inferred Strategy: trend_following                              │   │
│  │                                                                  │   │
│  │  [Run Now]  [Edit]  [View Results]  [⚙️ Auto-Trade Settings]    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  💎 Value + Quality Filter                      [Auto-Trade ⚪]  │   │
│  │  Universe: Nifty 100 | Filters: 5 | Min Score: 60               │   │
│  │  Last Run: Never | Schedule: Manual                              │   │
│  │  Inferred Strategy: value_momentum                               │   │
│  │                                                                  │   │
│  │  [Run Now]  [Edit]  [View Results]  [Enable Auto-Trade]         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  🚀 Breakout Hunter                             [Auto-Trade 🟢]  │   │
│  │  Universe: All | Filters: 4 | Min Score: 55                     │   │
│  │  Last Run: 1 hour ago | Next Run: In 55 mins (hourly)           │   │
│  │  Inferred Strategy: breakout_continuation                        │   │
│  │                                                                  │   │
│  │  [Run Now]  [Edit]  [View Results]  [⚙️ Auto-Trade Settings]    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Tasks:**
- [x] Create `frontend/src/app/(dashboard)/screener/saved/page.tsx`
- [x] Create `SavedScreenerCard` component
- [x] Add auto-trade status badge (enabled/disabled)
- [x] Add "Run Now" button with loading state
- [ ] Add "View Results" to show last run results (optional enhancement)
- [ ] Add auto-trade settings modal (optional enhancement)
- [x] Show inferred strategy type on each card
- [x] Show run schedule and countdown
- [x] Add API functions in `frontend/src/lib/api.ts`
- [x] Run frontend audit: `npm audit`
- [ ] Commit: `feat(frontend): add saved screeners management page`

##### 2.6.12.8 Frontend: Auto-Trade Source Selection

**Update Auto-Trade Settings to allow source selection:**

**UI Update:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│  🤖 Auto-Trade Configuration                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  📊 Screener Source                                                     │
│                                                                         │
│  Select where to get stock recommendations for auto-trading:            │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ○ Daily Recommendations (Presets)                              │   │
│  │    System-generated picks from preset screeners                 │   │
│  │                                                                  │   │
│  │    Category: [Momentum ▼]                                        │   │
│  │    Options: Momentum | Breakout | Value | Sector                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ● My Custom Screener                                           │   │
│  │    Use your saved screener with custom filters                  │   │
│  │                                                                  │   │
│  │    Screener: [My Momentum Screener ▼]                           │   │
│  │    Run Frequency: Daily at 9:20 AM                               │   │
│  │    Inferred Strategy: trend_following                            │   │
│  │                                                                  │   │
│  │    [Manage Saved Screeners →]                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  📈 Strategy Template                                                   │
│  [My Momentum Strategy Template ▼]                                      │
│                                                                         │
│  📊 Multi-Factor Weights                                                │
│  Technical: 40% | Fundamental: 40% | Sentiment: 20%                     │
│  [Configure Weights →]                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Tasks:**
- [ ] Update Auto-Trade Settings page with source selection (optional enhancement)
- [ ] Add radio buttons for Preset vs Custom screener (optional enhancement)
- [ ] Add category dropdown for preset selection (optional enhancement)
- [ ] Add saved screener dropdown for custom selection (optional enhancement)
- [ ] Show inferred strategy when custom screener selected (optional enhancement)
- [x] Add "Manage Saved Screeners" link
- [ ] Update API calls to save source selection (optional enhancement)
- [x] Run frontend audit: `npm audit`
- [ ] Commit: `feat(frontend): add screener source selection to auto-trade settings`

##### 2.6.12.9 Testing & Deployment

**Tasks:**
- [ ] Write unit tests for `SavedScreenerService`
- [ ] Write unit tests for strategy inference logic
- [ ] Write integration tests for scheduled screener runs
- [ ] Write integration tests for custom screener → auto-trade flow
- [ ] Test different run frequencies (daily, hourly, manual)
- [ ] Test strategy inference for various filter combinations
- [ ] Run full CI suite:
  ```bash
  # Backend
  uv run ruff check
  uv run ruff format
  uv run pytest
  uv run bandit -r backend/

  # Worker
  cd worker && uv run pytest

  # Frontend
  npm audit
  npm run lint
  npm run build
  ```
- [ ] Build containers: `podman-compose build`
- [ ] Deploy to staging: `podman-compose up -d`
- [ ] Verify custom screener to auto-trade flow in staging
- [ ] Test Celery Beat schedules for daily/hourly runs
- [ ] Commit: `test(screener): add comprehensive tests for custom screener auto-trade`

---

### 2.7 Algo Trading Time Window
> 🌿 **Branch:** `phase-2/algo-time-window`
> **Status:** 🔲 Not Started

**Goal**: Allow users to restrict when algo strategies execute trades. Example: Only trade between 9:45 AM and 3:15 PM IST.

#### Time Window Architecture

```mermaid
flowchart LR
    subgraph Config["⚙️ Time Window Config"]
        TW1[trading_start_time: 09:45]
        TW2[trading_end_time: 15:15]
        TW3[timezone: Asia/Kolkata]
        TW4[active_days: Mon-Fri]
    end

    subgraph Executor["🤖 Strategy Executor"]
        EX1{Is current time<br/>within window?}
        EX2[Generate Signals]
        EX3[Place Orders]
        EX4[Skip Execution<br/>Log reason]
    end

    subgraph Scenarios["📋 Use Cases"]
        SC1[Avoid first 15 mins<br/>volatility]
        SC2[Exit before<br/>market close]
        SC3[Trade only during<br/>specific sessions]
        SC4[Different windows<br/>per strategy]
    end

    Config --> Executor
    EX1 -->|Yes| EX2 --> EX3
    EX1 -->|No| EX4

    style Config fill:#e3f2fd,stroke:#1976d2
    style Executor fill:#e8f5e9,stroke:#4caf50
    style Scenarios fill:#fff3e0,stroke:#ff9800
```

#### 2.7.1 Model Updates

**Update `UserStrategy` model:**
```python
class UserStrategy(Base):
    # ... existing fields ...

    # Trading time window (new fields)
    trading_start_time: Time | None = None    # e.g., 09:45:00
    trading_end_time: Time | None = None      # e.g., 15:15:00
    trading_timezone: str = "Asia/Kolkata"    # Timezone for time comparison
    active_trading_days: JSON = [0,1,2,3,4]   # Monday=0 to Friday=4

    # If time window is set, only execute during this window
    # If None, execute whenever market is open (existing behavior)
```

**Tasks:**
- [ ] Add time window fields to `UserStrategy` model
- [ ] Create Alembic migration for new columns
- [ ] Update `UserStrategy` schemas to include time window fields
- [ ] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [ ] Commit: `feat(algo): add trading time window fields to UserStrategy`

#### 2.7.2 Time Window Validation

**Create `TimeWindowValidator` class:**
```python
class TimeWindowValidator:
    """Validates if current time is within trading window."""

    def is_within_window(
        self,
        start_time: time | None,
        end_time: time | None,
        timezone: str = "Asia/Kolkata",
        active_days: list[int] | None = None,
    ) -> tuple[bool, str]:
        """
        Check if current time is within the trading window.

        Returns: (is_valid, reason)
        - (True, "") if within window or no window set
        - (False, "Before trading window (09:45)") if before start
        - (False, "After trading window (15:15)") if after end
        - (False, "Not an active trading day") if wrong day
        """

    def time_until_window_opens(
        self,
        start_time: time,
        timezone: str = "Asia/Kolkata",
    ) -> timedelta:
        """Calculate time until window opens."""

    def time_until_window_closes(
        self,
        end_time: time,
        timezone: str = "Asia/Kolkata",
    ) -> timedelta:
        """Calculate time until window closes."""
```

**Tasks:**
- [ ] Create `TimeWindowValidator` in `backend/app/modules/algo/time_window.py`
- [ ] Handle timezone conversions properly (use `zoneinfo`)
- [ ] Handle edge cases (overnight windows, different timezones)
- [ ] Add comprehensive unit tests
- [ ] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [ ] Commit: `feat(algo): implement TimeWindowValidator`

#### 2.7.3 Executor Integration

**Update `StrategyExecutor` in trading-engine:**
```python
class StrategyExecutor:
    async def execute(self, config: StrategyConfig, ...) -> ExecutionResult:
        # Check time window BEFORE executing
        if config.trading_start_time or config.trading_end_time:
            validator = TimeWindowValidator()
            is_valid, reason = validator.is_within_window(
                start_time=config.trading_start_time,
                end_time=config.trading_end_time,
                timezone=config.trading_timezone,
                active_days=config.active_trading_days,
            )

            if not is_valid:
                return ExecutionResult(
                    status=ExecutionStatus.SKIPPED,
                    skip_reason=f"Outside trading window: {reason}",
                )

        # Continue with normal execution...
```

**Tasks:**
- [ ] Update `StrategyConfig` dataclass to include time window fields
- [ ] Update `StrategyExecutor.execute()` to check time window
- [ ] Add `SKIPPED` status to `ExecutionStatus` enum if not exists
- [ ] Log skipped executions with reason
- [ ] Add tests for executor time window checks
- [ ] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [ ] Commit: `feat(trading-engine): integrate time window checks in executor`

#### 2.7.4 API Updates

**Update strategy endpoints:**
```python
class StrategyCreate(BaseModel):
    # ... existing fields ...

    # Trading time window
    trading_start_time: time | None = None
    trading_end_time: time | None = None
    trading_timezone: str = "Asia/Kolkata"
    active_trading_days: list[int] = [0, 1, 2, 3, 4]  # Mon-Fri

class StrategyUpdate(BaseModel):
    # ... existing fields ...

    # Trading time window
    trading_start_time: time | None = None
    trading_end_time: time | None = None
    trading_timezone: str | None = None
    active_trading_days: list[int] | None = None
```

**Tasks:**
- [ ] Update `StrategyCreate` schema with time window fields
- [ ] Update `StrategyUpdate` schema with time window fields
- [ ] Update `StrategyResponse` schema to include time window
- [ ] Validate time window (start < end, valid timezone)
- [ ] Add API tests for time window validation
- [ ] Run CI checks: `uv run ruff check && uv run ruff format && uv run pytest && uv run bandit -r backend/`
- [ ] Commit: `feat(algo): update API schemas for time window support`

#### 2.7.5 Frontend: Time Window Configuration

**Update Strategy Form:**
Add a new section "Trading Time Window" with:
- Enable time window toggle
- Start time picker (HH:MM)
- End time picker (HH:MM)
- Timezone selector (default: Asia/Kolkata)
- Active days checkboxes (Mon, Tue, Wed, Thu, Fri, Sat, Sun)
- Preset buttons: "Market Hours", "Avoid Open/Close", "Morning Session", "Afternoon Session"

**Presets:**
| Preset | Start | End | Description |
|--------|-------|-----|-------------|
| Market Hours | 09:15 | 15:30 | Full trading day |
| Avoid Open/Close | 09:45 | 15:00 | Skip volatile first/last 15-30 mins |
| Morning Session | 09:15 | 12:00 | Trade only in morning |
| Afternoon Session | 13:00 | 15:30 | Trade only in afternoon |

**Tasks:**
- [ ] Create `TimeWindowSection` component for strategy form
- [ ] Add time pickers for start/end time
- [ ] Add timezone selector dropdown
- [ ] Add active days checkboxes
- [ ] Add preset buttons for common configurations
- [ ] Show current status indicator (In Window / Outside Window)
- [ ] Run frontend audit: `npm audit`
- [ ] Commit: `feat(frontend): add time window configuration to strategy form`

#### 2.7.6 Strategy Status Display

**Update strategy cards/tables to show:**
- Time window badge (e.g., "09:45 - 15:15")
- Current status: "In Window" (green) / "Outside Window" (grey)
- Next execution time if outside window
- Countdown to window open/close

**Tasks:**
- [ ] Update `StrategyCard` component to show time window
- [ ] Add status indicator component
- [ ] Add countdown timer for window status
- [ ] Run frontend audit: `npm audit`
- [ ] Commit: `feat(frontend): display time window status on strategy cards`

#### 2.7.7 Testing & Deployment

**Tasks:**
- [ ] Write unit tests for TimeWindowValidator
- [ ] Write integration tests for executor with time window
- [ ] Test timezone edge cases (DST transitions, different TZs)
- [ ] Write E2E tests for frontend time window configuration
- [ ] Run full CI suite:
  ```bash
  # Backend
  uv run ruff check
  uv run ruff format
  uv run pytest
  uv run bandit -r backend/

  # Trading Engine
  cd trading-engine && uv run pytest

  # Frontend
  npm audit
  npm run lint
  npm run build
  ```
- [ ] Build containers: `podman-compose build`
- [ ] Deploy to staging: `podman-compose up -d`
- [ ] Verify time window functionality in staging
- [ ] Commit: `test(algo): add comprehensive tests for time window feature`

---

## 📦 PHASE 3: Advanced Features (Future)

### 3.1 Additional Brokers
> 🌿 **Branch:** `phase-3/multi-broker`
- [ ] Dhan integration
- [ ] Zerodha/Kite integration
- [ ] Broker comparison/fallback
- [ ] Multi-broker order routing

### 3.2 Advanced Order Types
> 🌿 **Branch:** `phase-3/advanced-orders`
- [ ] Bracket Orders
- [ ] Cover Orders
- [ ] GTT (Good Till Triggered)
- [ ] Basket Orders
- [ ] Iceberg Orders

### 3.3 Options Trading
> 🌿 **Branch:** `phase-3/options`
- [ ] Options chain data
- [ ] Option Greeks calculation (Delta, Gamma, Theta, Vega)
- [ ] Options strategies (Straddle, Strangle, Iron Condor, Spreads)
- [ ] Options P&L calculator
- [ ] IV percentile and IV rank
- [ ] Options strategy builder

### 3.4 Advanced Algo Features
> 🌿 **Branch:** `phase-3/advanced-algo`
- [ ] Strategy marketplace (share/discover strategies)
- [ ] Visual strategy builder (no-code)
- [ ] Multi-timeframe analysis
- [ ] Portfolio optimization (Markowitz, Black-Litterman)

#### 3.4.1 Machine Learning for Trading

**Overview**: Extend the rule-based strategy framework with ML-powered signal generation. Top quantitative firms (Renaissance Technologies, Two Sigma, Citadel, D.E. Shaw) extensively use ML for alpha generation.

**ML Strategy Architecture:**
```python
class MLStrategy(Strategy):
    """Base class for ML-powered trading strategies."""
    model: Any  # sklearn, lightgbm, pytorch model
    feature_pipeline: FeaturePipeline

    @abstractmethod
    def extract_features(self, data: DataFrame) -> DataFrame:
        """Extract features from market data for ML model."""
        pass

    def generate_signals(self, data: DataFrame) -> List[Signal]:
        features = self.extract_features(data)
        predictions = self.model.predict(features)
        return self._predictions_to_signals(predictions)
```

**Supervised ML Models (Production-Ready):**

| Model | Use Case | Maturity | Priority |
|-------|----------|----------|----------|
| XGBoost/LightGBM/CatBoost | Return classification, signal strength | Production-ready | High |
| Random Forests | Feature importance, ensemble predictions | Production-ready | High |
| LSTM/GRU (RNN) | Time-series prediction, sequential patterns | Production-ready | Medium |
| Transformers | NLP sentiment, complex temporal patterns | Production-ready | Medium |
| Autoencoders | Risk factor extraction, dimensionality reduction | Research-grade | Low |
| CNNs | Pattern recognition in candlestick images | Research-grade | Low |

**Tasks - Gradient Boosting Models:**
- [ ] Create `MLStrategy` abstract base class extending `Strategy`
- [ ] Implement `XGBoostStrategy` for return classification
  - Features: Technical indicators, price patterns, volume metrics
  - Target: Next-day return direction (up/down/flat)
  - Configurable prediction threshold
- [ ] Implement `LightGBMStrategy` for signal strength prediction
- [ ] Create feature engineering pipeline
  - Technical indicators (RSI, MACD, BB, ATR, etc.)
  - Price-based features (returns, volatility, momentum)
  - Volume features (relative volume, OBV)
  - Calendar features (day of week, month, quarter)
- [ ] Model training pipeline with walk-forward validation
- [ ] Model versioning and experiment tracking (MLflow/Weights & Biases)
- [ ] A/B testing framework for strategy comparison

**Tasks - Deep Learning Models:**
- [ ] Implement `LSTMStrategy` for time-series prediction
  - Sequence length configuration
  - Multi-step ahead forecasting
  - Attention mechanism integration
- [ ] Implement `TransformerStrategy` for temporal patterns
- [ ] Create `CNNStrategy` for candlestick pattern recognition
  - Convert OHLCV to image representation
  - Based on research: Sezer & Ozbahoglu (2018)
- [ ] GPU inference optimization for real-time predictions
- [ ] Model ensemble framework (combine multiple models)

**Tasks - NLP & Sentiment Analysis:**
- [ ] News sentiment analysis using pre-trained models
  - FinBERT for financial text
  - Earnings call transcript analysis
- [ ] SEC filing sentiment extraction
- [ ] Social media sentiment (Twitter/X, StockTwits)
- [ ] Event-driven signals from news
- [ ] Sentiment aggregation and signal generation

**Industry Reference - What Top Firms Use:**
- **Renaissance Technologies**: Statistical arbitrage + proprietary ML (Medallion Fund: ~66% CAGR)
- **Two Sigma**: Alternative data + supervised ML + RL for allocation
- **Citadel**: Full spectrum ML, RL for execution optimization
- **D.E. Shaw**: NLP, alternative data, complex ML ensembles
- **WorldQuant**: 101 Formulaic Alphas + ML feature engineering

**Resources:**
- Book: "Machine Learning for Algorithmic Trading, 2nd Edition" by Stefan Jansen
  - GitHub: https://github.com/stefan-jansen/machine-learning-for-trading
  - Covers: Linear models, trees, deep learning, RL for trading
- Paper: WorldQuant "101 Formulaic Alphas" (Kakushadze 2016)
- Library: TA-Lib for technical indicator computation

#### 3.4.2 Reinforcement Learning for Trading

**Overview**: Train agents that learn optimal trading policies through interaction with the market environment. More experimental than supervised ML but used by top firms for execution optimization and portfolio allocation.

**RL Trading Flow Diagram:**
```mermaid
flowchart TB
    subgraph Environment["🌍 Market Environment"]
        MarketState[Market State<br/>prices, positions, indicators]
        Reward[Reward Function<br/>returns, Sharpe, risk-adjusted]
    end

    subgraph Agent["🤖 RL Trading Agent"]
        StateEncoder[State Encoder<br/>features from market data]
        PolicyNetwork[Policy Network<br/>action selection]
        ValueNetwork[Value Network<br/>state value estimation]
    end

    subgraph Actions["📊 Trading Actions"]
        Buy[Buy / Long]
        Sell[Sell / Short]
        Hold[Hold / No Action]
        PositionSize[Position Sizing]
    end

    subgraph Training["🔄 Training Loop"]
        Experience[Experience Replay]
        Optimization[Policy Optimization]
        Evaluation[Backtest Evaluation]
    end

    MarketState --> StateEncoder
    StateEncoder --> PolicyNetwork
    StateEncoder --> ValueNetwork
    PolicyNetwork --> Actions
    Actions --> Environment
    Environment --> Reward
    Reward --> Training
    Training --> Agent

    style Environment fill:#e3f2fd,stroke:#1976d2
    style Agent fill:#e8f5e9,stroke:#4caf50
    style Actions fill:#fff3e0,stroke:#ff9800
    style Training fill:#f3e5f5,stroke:#9c27b0
```

**RL Algorithms for Trading:**

| Algorithm | Type | Use Case | Complexity |
|-----------|------|----------|------------|
| DQN (Deep Q-Network) | Value-based | Discrete actions (buy/sell/hold) | Medium |
| PPO (Proximal Policy Optimization) | Policy-based | Continuous position sizing | High |
| A2C/A3C (Actor-Critic) | Hybrid | Complex action spaces | High |
| SAC (Soft Actor-Critic) | Off-policy | Sample-efficient learning | High |
| TD3 (Twin Delayed DDPG) | Off-policy | Continuous control | High |

**Tasks - RL Environment:**
- [ ] Create `TradingEnvironment` compatible with OpenAI Gym interface
  ```python
  class TradingEnvironment(gym.Env):
      """Custom trading environment for RL agents."""

      def __init__(self, data: DataFrame, initial_balance: float):
          self.action_space = spaces.Discrete(3)  # Buy, Sell, Hold
          self.observation_space = spaces.Box(...)  # Market features

      def step(self, action) -> Tuple[obs, reward, done, info]:
          """Execute action and return new state."""
          pass

      def reset(self) -> obs:
          """Reset environment to initial state."""
          pass
  ```
- [ ] Implement realistic transaction costs and slippage
- [ ] Support multiple reward functions:
  - [ ] Simple returns
  - [ ] Risk-adjusted returns (Sharpe ratio)
  - [ ] Sortino ratio (downside risk)
  - [ ] Maximum drawdown penalty
  - [ ] Custom composite rewards
- [ ] Multi-asset environment support
- [ ] Integration with paper trading broker

**Tasks - RL Agents:**
- [ ] Implement DQN agent for discrete trading decisions
  - Experience replay buffer
  - Target network for stability
  - Epsilon-greedy exploration
- [ ] Implement PPO agent for continuous position sizing
  - Clipped surrogate objective
  - Generalized Advantage Estimation (GAE)
- [ ] Implement A2C/A3C for parallel training
- [ ] State representation engineering:
  - [ ] Price history (normalized)
  - [ ] Technical indicators
  - [ ] Current position and P&L
  - [ ] Time features (market hours remaining)
- [ ] Action space design:
  - [ ] Discrete: Buy/Sell/Hold
  - [ ] Continuous: Position size as percentage
  - [ ] Multi-discrete: Asset + action

**Tasks - RL Training Infrastructure:**
- [ ] Walk-forward training with periodic retraining
- [ ] Hyperparameter optimization (Optuna/Ray Tune)
- [ ] Training stability monitoring
- [ ] Policy checkpointing and versioning
- [ ] Tensorboard integration for training visualization
- [ ] Distributed training support (Ray RLlib)

**Tasks - RL Evaluation & Safety:**
- [ ] Backtesting trained policies
- [ ] Out-of-sample performance validation
- [ ] Policy behavior analysis:
  - [ ] Action distribution visualization
  - [ ] State-action heatmaps
  - [ ] Risk metrics during evaluation
- [ ] Maximum position limits (hard constraints)
- [ ] Drawdown-based early stopping
- [ ] Comparison with rule-based baseline strategies

**RL Challenges & Considerations:**
- **Non-stationarity**: Markets change over time, policies may become stale
- **Sample efficiency**: RL requires lots of data; consider synthetic data (GANs)
- **Reward hacking**: Agent may find unintended ways to maximize reward
- **Overfitting**: Easy to overfit to historical patterns
- **Evaluation difficulty**: Hard to distinguish skill from luck

**Research Papers:**
- "Deep Reinforcement Learning for Automated Stock Trading" (2020)
- "Reinforcement Learning for Optimal Execution" (2019)
- "Time-series Generative Adversarial Networks" - for synthetic data (NeurIPS 2019)
- "Autoencoder Asset Pricing Models" - Gu, Kelly, Xiu (2019)

**Libraries & Frameworks:**
- Stable-Baselines3: Production-ready RL algorithms
- Ray RLlib: Scalable RL library
- FinRL: RL library specifically for finance
- OpenAI Gym: Environment interface standard

#### 3.4.3 ML/RL Implementation Priority

**Recommended Implementation Order:**

| Phase | Approach | Prerequisites | Risk Level |
|-------|----------|---------------|------------|
| 1 | XGBoost/LightGBM classification | Backtesting framework | Low |
| 2 | Feature engineering pipeline | Phase 1 complete | Low |
| 3 | LSTM time-series prediction | Deep learning infra | Medium |
| 4 | NLP sentiment signals | Text data pipeline | Medium |
| 5 | DQN for discrete trading | RL environment | High |
| 6 | PPO for position sizing | Phase 5 validated | High |
| 7 | Multi-agent RL | Advanced RL expertise | Very High |

**Key Insight**: Research shows hybrid approaches (traditional indicators + ML) often outperform pure ML models, especially without massive computational resources. Start with ensemble methods before attempting deep RL.

### 3.5 Mobile App
> 🌿 **Branch:** `phase-3/mobile`
- [ ] React Native app
- [ ] Push notifications
- [ ] Quick order entry
- [ ] Algo monitoring on the go

### 3.6 Social & Community
> 🌿 **Branch:** `phase-3/social`
- [ ] Copy trading (follow successful traders)
- [ ] Strategy performance leaderboard
- [ ] Trading journal with notes
- [ ] Community chat/discussions

---

## ⚙️ Configuration Reference

### Environment Variables

```env
# ===================
# APPLICATION
# ===================
PROJECT_NAME="Portfolio Management System"
DEBUG=false
SECRET_KEY=your-secret-key

# ===================
# DATABASE
# ===================
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/portfolio

# ===================
# REDIS
# ===================
REDIS_URL=redis://localhost:6379/0

# ===================
# TRADING MODE
# ===================
TRADING_MODE=paper          # paper | live
DEFAULT_MARKET=IN           # IN | US

# ===================
# DATA PROVIDERS
# ===================
DATA_PROVIDER=yahoo         # yahoo | nse | angelone
POLYGON_API_KEY=            # For US stocks (optional)

# ===================
# BROKER (Phase 2)
# ===================
BROKER_TYPE=paper           # paper | angelone | dhan

# Angel One credentials (required if BROKER_TYPE=angelone)
ANGEL_API_KEY=
ANGEL_CLIENT_ID=
ANGEL_PASSWORD=
ANGEL_TOTP_SECRET=

# ===================
# RISK MANAGEMENT
# ===================
MAX_DAILY_LOSS=10000        # Stop trading if daily loss exceeds
MAX_POSITION_SIZE_PCT=10    # Max 10% of portfolio in one stock
MAX_TRADES_PER_DAY=50       # Maximum trades per day
AUTO_SQUARE_OFF_TIME=15:15  # Auto square-off intraday positions

# ===================
# NOTIFICATIONS
# ===================
# Email Configuration
NOTIFICATION_EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp              # smtp | sendgrid | ses
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=
EMAIL_SMTP_PASSWORD=
EMAIL_FROM=alerts@yourapp.com
SENDGRID_API_KEY=                # If using SendGrid

# WhatsApp Configuration
NOTIFICATION_WHATSAPP_ENABLED=false
WHATSAPP_PROVIDER=twilio         # twilio | whatsapp_business
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=            # e.g., whatsapp:+14155238886

# SMS Configuration (optional)
NOTIFICATION_SMS_ENABLED=false
SMS_PROVIDER=twilio              # twilio | msg91
MSG91_AUTH_KEY=

# Push Notifications (optional - for mobile)
NOTIFICATION_PUSH_ENABLED=false
FCM_SERVER_KEY=                  # Firebase Cloud Messaging

# WebSocket (real-time UI)
NOTIFICATION_WEBSOCKET_ENABLED=true

# Default notification preferences for new users
DEFAULT_NOTIFY_ORDERS=["ui", "email"]
DEFAULT_NOTIFY_ALERTS=["ui", "email", "whatsapp"]
DEFAULT_NOTIFY_SIGNALS=["ui"]
DEFAULT_NOTIFY_RISK=["ui", "email", "whatsapp"]  # Critical - all channels
```

---

## 📁 Final Directory Structure

```
portfolio-management-system/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── redis.py
│   │   │   └── security.py
│   │   ├── providers/              # Abstraction layer
│   │   │   ├── data/
│   │   │   │   ├── base.py         # DataProvider interface
│   │   │   │   ├── yahoo.py
│   │   │   │   ├── nse.py
│   │   │   │   ├── angelone.py     # Phase 2
│   │   │   │   └── factory.py
│   │   │   ├── broker/
│   │   │   │   ├── base.py         # Broker interface
│   │   │   │   ├── paper.py
│   │   │   │   ├── angelone.py     # Phase 2
│   │   │   │   └── factory.py
│   │   │   └── notification/       # 📢 NOTIFICATION PROVIDERS
│   │   │       ├── base.py         # NotificationProvider interface
│   │   │       ├── email.py        # Email (SMTP/SendGrid/SES)
│   │   │       ├── whatsapp.py     # WhatsApp (Twilio)
│   │   │       ├── sms.py          # SMS (Twilio/MSG91)
│   │   │       ├── websocket.py    # Real-time UI notifications
│   │   │       ├── push.py         # Push (FCM/APNs) - future
│   │   │       ├── telegram.py     # Telegram bot - future
│   │   │       └── factory.py
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── portfolio/          # Includes ledger + gains (Phase 2)
│   │   │   │   ├── ledger_service.py   # Transaction ledger
│   │   │   │   └── gains_service.py    # Capital gains tracking
│   │   │   ├── trading/
│   │   │   ├── analysis/
│   │   │   ├── data/
│   │   │   ├── watchlist/
│   │   │   ├── signals/            # Signal generation
│   │   │   ├── backtest/           # Backtesting framework
│   │   │   ├── risk/               # Risk management
│   │   │   ├── alerts/             # Alerts & notifications
│   │   │   ├── broker/             # Includes API logging (Phase 2)
│   │   │   │   └── logging_service.py  # Broker API logs
│   │   │   ├── activity/           # 📋 ACTIVITY LOG (Phase 2)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py       # ActivityLog model
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py      # ActivityService
│   │   │   │   └── router.py       # GET /activity endpoints
│   │   │   └── algo/               # 🤖 ALGO TRADING ENGINE
│   │   │       ├── __init__.py
│   │   │       ├── strategies/     # Strategy implementations
│   │   │       │   ├── base.py     # Abstract Strategy class
│   │   │       │   ├── momentum.py
│   │   │       │   ├── mean_reversion.py
│   │   │       │   ├── trend_following.py
│   │   │       │   └── multi_factor.py
│   │   │       ├── executor.py     # Strategy executor
│   │   │       ├── scheduler.py    # Strategy scheduler
│   │   │       ├── position_sizer.py
│   │   │       ├── universe.py     # Universe selection
│   │   │       ├── models.py
│   │   │       ├── router.py
│   │   │       └── schemas.py
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── strategies/             # Strategy-specific tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/
│   │   │   ├── portfolio/
│   │   │   ├── trading/
│   │   │   ├── charts/
│   │   │   ├── watchlist/
│   │   │   ├── signals/
│   │   │   ├── algo/               # 🤖 ALGO TRADING UI
│   │   │   │   ├── strategies/     # Strategy management
│   │   │   │   ├── performance/    # Strategy performance
│   │   │   │   └── signals/        # Signal feed
│   │   │   ├── backtest/           # Backtesting UI
│   │   │   ├── reports/            # 📊 REPORTS UI (Phase 2)
│   │   │   │   ├── page.tsx        # Reports overview
│   │   │   │   ├── statement/      # Account statement/ledger
│   │   │   │   ├── gains/          # Capital gains report
│   │   │   │   ├── api-logs/       # Broker API logs
│   │   │   │   └── activity/       # Activity feed
│   │   │   └── settings/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── charts/
│   │   │   ├── trading/
│   │   │   ├── portfolio/
│   │   │   ├── algo/               # Algo-specific components
│   │   │   ├── reports/            # 📊 REPORTS COMPONENTS (Phase 2)
│   │   │   │   ├── StatementTable.tsx
│   │   │   │   ├── GainsSummary.tsx
│   │   │   │   ├── APILogsTable.tsx
│   │   │   │   └── ActivityTimeline.tsx
│   │   │   └── notifications/      # 📢 NOTIFICATION COMPONENTS
│   │   │       ├── NotificationBell.tsx
│   │   │       ├── NotificationCenter.tsx
│   │   │       ├── Toast.tsx
│   │   │       └── NotificationSettings.tsx
│   │   └── lib/
│   │       ├── api/
│   │       └── websocket.ts        # WebSocket for real-time notifications
│   └── package.json
├── worker/
│   └── worker/
│       ├── tasks/
│       │   ├── market_data.py
│       │   ├── portfolio.py
│       │   ├── signals.py
│       │   ├── risk.py
│       │   ├── alerts.py
│       │   ├── algo.py             # 🤖 ALGO EXECUTION TASKS
│       │   └── notifications.py    # 📢 NOTIFICATION TASKS
│       └── celery_app.py
├── docs/
│   ├── PROJECT_PLAN.md
│   ├── india-trading-apis.md
│   ├── algo-trading-factors.md
│   └── strategy-guide.md           # How to create strategies
└── docker-compose.yml
```

---

## 🗓️ Implementation Timeline

| Week | Focus | Branch | Deliverables |
|------|-------|--------|--------------|
| 1 | Infrastructure | `phase-1/infrastructure` | Data/Broker/Notification abstraction, Symbol system |
| 2 | Indian Market | `phase-1/indian-market` | NSE data provider, Instrument master |
| 3 | Trading + Risk | `phase-1/trading-risk` | Order types, Position mgmt, Risk limits |
| 3-4 | Frontend | `phase-1/frontend` | Dashboard, Portfolio, Order entry, Charts |
| 4-5 | Notifications | `phase-1/notifications` | Email, WhatsApp, WebSocket, Notification UI |
| 5 | Signals + Backtest | `phase-1/signals-backtest` | Signal engine, Backtesting framework |
| 5-6 | **Algo Trading** | `phase-1/algo-trading` | Strategy framework, Built-in strategies, Executor |
| 6-7 | Testing + Polish | `phase-1/testing` | E2E tests, Bug fixes, Algo validation |
| 8-9 | **UX Improvements** | `phase-1/ux-improvements` | Trade from charts, Keyboard shortcuts, Accessibility |
| 9-10 | Angel One | `phase-2/angelone` | Angel One API integration |
| 10-11 | Live Safety | `phase-2/live-safety` | Live trading safety features |

---

## ✅ Phase 1 Completion Criteria

**Status**: ✅ Phase 1 Complete (v1.0.0 released)

Before moving to Phase 2, ensure:

1. **Paper Trading Works End-to-End** ✅
   - [x] Can search and add symbols to watchlist
   - [x] Can place all order types (market, limit, SL)
   - [x] Orders execute at realistic prices
   - [x] Positions update correctly
   - [x] P&L calculation is accurate
   - [x] Trade history is maintained

2. **Risk Management Active** ✅
   - [x] Position size limits enforced
   - [x] Daily loss limit stops trading
   - [x] Auto square-off works

3. **Algo Trading Functional** ✅
   - [x] At least 3 strategies implemented and tested
   - [x] Strategy executor runs without errors
   - [x] Scheduler triggers strategies correctly
   - [x] Signals convert to orders properly
   - [x] Kill switch stops all algo trading
   - [x] Circuit breakers trigger on losses
   - [x] Backtest results match paper trading (within tolerance)

4. **Notifications Working** ⚠️ Partial
   - [ ] Email notifications deliver correctly *(Phase 2)*
   - [ ] WhatsApp notifications work (if configured) *(Phase 2)*
   - [x] Real-time UI notifications appear
   - [x] User can configure notification preferences
   - [x] Critical alerts (risk breaches) always notify
   - [ ] Quiet hours respected *(Phase 2)*

5. **Frontend Functional** ✅
   - [x] Dashboard shows portfolio summary
   - [x] Can view and manage positions
   - [x] Order entry and confirmation work
   - [x] Charts display with indicators
   - [x] Algo dashboard shows strategy status
   - [x] Can enable/disable strategies
   - [x] Notification bell with unread count
   - [x] Notification settings page works

6. **Testing Complete** ✅
   - [x] Core services have unit tests
   - [x] API endpoints tested
   - [x] Paper trading validated against expected behavior
   - [x] Strategy backtests pass validation
   - [x] Algo execution tested in simulated market conditions
   - [ ] Notification delivery tested for all channels *(Phase 2)*

7. **UX Improvements Complete** ✅
   - [x] Trade from Analysis page works
   - [x] Keyboard shortcuts functional
   - [x] Error boundaries prevent app crashes
   - [x] Toast notifications show for key actions
   - [x] Skip links and focus states for accessibility
   - [x] ARIA labels on icon-only buttons

---

## Notes

### Why This Approach?

1. **Risk Mitigation**: Paper trading + algo testing proves the system works before risking real money
2. **Clean Architecture**: Abstraction means broker/data/notification change = config change
3. **Indian Market First**: Focus on NSE/BSE since that's the target market
4. **Algo-First**: Build algo trading from day one, not as an afterthought
5. **Notifications Built-in**: Critical for trading - know immediately when something happens
6. **Incremental Delivery**: Each week delivers usable features

### Key Decisions Made

- **Angel One as primary broker**: Free API, no charges, good documentation
- **PostgreSQL + TimescaleDB**: Time-series optimized for market data
- **Redis**: Caching and Celery broker
- **Next.js frontend**: Modern, fast, good DX
- **Celery workers**: Background jobs for data updates, signals, algo execution, notifications
- **Strategy abstraction**: Easy to add new strategies without changing core code
- **Notification abstraction**: Easy to add new channels (Telegram, Discord, etc.) later