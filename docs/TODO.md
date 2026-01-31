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
| FastAPI Backend | ✅ Done | Basic structure ready |
| PostgreSQL + TimescaleDB | ✅ Done | Docker configured |
| Redis | ✅ Done | Docker configured |
| Celery Workers | ✅ Done | Basic tasks exist |
| Authentication | ✅ Done | JWT-based auth |
| Portfolio Models | ✅ Done | Positions, Trades |
| Order Models | ✅ Done | Orders with status |
| Paper Trading Service | ✅ Done | Basic implementation |
| Technical Analysis | ✅ Done | RSI, MACD, BB, ATR |
| yfinance Integration | ✅ Done | US stocks working |
| Frontend | ✅ Done | Dashboard, Portfolio, Orders, Watchlist, Signals, Backtest pages |
| Indian Stock Data | ✅ Done | NSE provider with 2220+ stocks, industry data for Nifty 500 |
| Abstracted Data Layer | ✅ Done | DataProvider + YahooDataProvider + NSEDataProvider + Factory |
| Abstracted Broker Layer | ✅ Done | Broker + PaperBroker + Factory |
| Symbol System | ✅ Done | Symbol + SymbolMapper for multi-exchange |
| Notification Abstraction | ✅ Done | NotificationProvider + types defined |
| Instrument Master | ✅ Done | 2220+ NSE stocks with ISIN, industry, series |
| Instrument Sync | ✅ Done | Weekly scheduled sync + manual API endpoints |
| Market Status | ✅ Done | NSE trading hours awareness |
| Signal Engine | ✅ Done | 4 strategies (RSI, MACD, MA Crossover, Bollinger) with HOLD support |
| Backtesting | ✅ Done | BacktestRunner with full metrics (Sharpe, Sortino, Max DD, Win Rate) |
| Risk Management | ✅ Done | Position limits, sector concentration, SL/TP enforcement, auto square-off |
| Stock Screener | ✅ Done | Preset screeners, daily recommendations, performance tracking, UI with Sheet component |
| Alerts/Notifications Impl | ❌ Missing | Providers need implementation |


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

#### 1.10.6 Screener → Algo Integration
Allow screener results to feed into algo trading.

**Tasks:**
- [ ] "Create Strategy from Results" action
  - Takes top N screener results
  - Creates custom universe with those symbols
  - Links to strategy creation dialog
- [ ] Dynamic screener-based universe
  - Universe type: "screener"
  - Re-runs screener daily to update symbols
  - Algo trades whatever passes the screen
- [ ] Screener alerts
  - "Alert me when X stocks pass this screener"
  - "Alert when RELIANCE scores above 80 on momentum"

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

### 1.11 Research Module (Week 8)
> 🌿 **Branch:** `phase-1/research`

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

#### 1.11.1 Fundamental Data Integration
Extend data providers to include fundamental metrics.

**Tasks:**
- [ ] Extend `YahooDataProvider` with fundamental data methods
  - `get_fundamentals(symbol)` - P/E, P/B, EPS, Revenue, etc.
  - `get_financials(symbol)` - Income statement, balance sheet
  - `get_dividends(symbol)` - Dividend history and yield
- [ ] Create fundamental data schemas
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
- [ ] Cache fundamental data (refresh daily after market close)

#### 1.11.2 Fundamental Screener Filters
Add fundamental analysis filters to the screener engine.

**Tasks:**
- [ ] Create `FundamentalFilter` class
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
- [ ] Create preset fundamental screeners:
  - **Value Screener**: P/E < 15, P/B < 2, Dividend > 2%
  - **Growth Screener**: EPS growth > 20%, Revenue growth > 15%
  - **Dividend Screener**: Dividend yield > 3%, consistent payout
  - **Quality Screener**: ROE > 15%, Debt/Equity < 0.5
- [ ] Update screener API to support fundamental filters

#### 1.11.3 News Integration
Integrate news feeds for market and stock-level news.

**Tasks:**
- [ ] Create news provider abstraction
  ```python
  class BaseNewsProvider(ABC):
      @abstractmethod
      async def get_stock_news(symbol: str, limit: int) -> list[NewsArticle]

      @abstractmethod
      async def get_market_news(limit: int) -> list[NewsArticle]

      @abstractmethod
      async def get_sector_news(sector: str, limit: int) -> list[NewsArticle]
  ```
- [ ] Implement news providers (choose based on API availability):
  - Option A: `NewsAPIProvider` (newsapi.org - free tier: 100 req/day)
  - Option B: `YahooNewsProvider` (scrape Yahoo Finance news)
  - Option C: `GoogleNewsProvider` (Google News RSS feeds)
- [ ] Create news schemas
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
- [ ] Basic sentiment scoring (keyword-based initially)
  - Bullish keywords: "surge", "breakout", "record high", "beat estimates"
  - Bearish keywords: "crash", "plunge", "miss", "downgrade", "sell-off"

#### 1.11.4 Stock Research Page
Dedicated deep-dive page for comprehensive stock analysis.

**Tasks:**
- [ ] Create `/research/[symbol]` page route
- [ ] **Header Section**
  - Stock name, symbol, current price, change %
  - Quick action buttons (Add to Watchlist, Trade, Set Alert)
  - Last updated timestamp
- [ ] **Technical Analysis Tab**
  - TradingView chart embed or custom chart
  - Key technical indicators (RSI, MACD, Moving Averages)
  - Support/resistance levels
  - Technical signal summary (Buy/Sell/Hold)
- [ ] **Fundamental Analysis Tab**
  - Key ratios: P/E, P/B, EPS, ROE, D/E
  - Revenue and earnings trends (mini charts)
  - Dividend history
  - Comparison to sector averages
- [ ] **News & Sentiment Tab**
  - Recent news articles (last 7 days)
  - Sentiment indicator (overall bullish/bearish)
  - News volume chart (articles per day)
- [ ] **Peer Comparison Tab**
  - Industry peers table
  - Comparative metrics (P/E, Market Cap, Performance)
  - Relative strength ranking
- [ ] **Notes Section**
  - User can save personal research notes
  - Notes stored per symbol per user

#### 1.11.5 Daily Research Digest
Automated daily market intelligence summary.

**Tasks:**
- [ ] Create daily digest Celery task (runs at market close)
- [ ] Digest components:
  - **Market Summary**: Index performance (Nifty, BankNifty, Sensex)
  - **Top Gainers/Losers**: Top 5 each with % change and reason
  - **Sector Performance**: Heatmap data for all sectors
  - **Volume Leaders**: Unusual volume activity
  - **Breakout Candidates**: From breakout screener
  - **News Highlights**: Top 5 market-moving news
- [ ] API endpoint `GET /research/digest` to fetch daily digest
- [ ] Frontend Dashboard widget showing digest summary
- [ ] Optional: Email digest to subscribed users

#### 1.11.6 Sector Heatmap
Visual sector performance analysis.

**Tasks:**
- [ ] Create sector performance API
  - `GET /research/sectors` - All sectors with daily/weekly/monthly performance
  - `GET /research/sectors/{sector}` - Stocks in sector with performance
- [ ] Frontend sector heatmap component
  - Color-coded by performance (green = up, red = down)
  - Click to drill down into sector stocks
  - Toggle timeframe (1D, 1W, 1M, 3M, 1Y)
- [ ] Sector rotation analysis
  - Track sector momentum over time
  - Identify rotating leadership

#### 1.11.7 Research API Endpoints
Expose research functionality via REST API.

**Tasks:**
- [ ] Create research router (`/api/v1/research`)
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

  # User research notes
  GET /research/notes             # User's saved notes
  POST /research/notes            # Save research note
  DELETE /research/notes/{id}     # Delete note
  ```
- [ ] Register research router in main API router


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

#### 1.12.11 Branded Loading States
Visual polish for professional appearance.

**Tasks:**
- [ ] Create branded loading spinner
  - App logo animation
  - Consistent with brand colors
- [ ] Full-page loading state for initial load
- [ ] Skeleton screens for all data-loading components
  - Dashboard cards
  - Tables
  - Charts
- [ ] Progress indicators for long operations
  - Backtest progress
  - Bulk operations

#### 1.12.12 Drag-and-Drop Reordering
Customization for watchlists and portfolios.

**Tasks:**
- [ ] Watchlist symbol reordering
  - Drag symbols to reorder
  - Persist order to backend
- [ ] Watchlist list reordering
  - Reorder watchlists in sidebar
- [ ] Dashboard widget reordering (future)
  - Drag widgets to rearrange
  - Resize widgets

#### 1.12.13 Chart Comparison & Overlay
Enhanced technical analysis capabilities.

**Tasks:**
- [ ] Symbol comparison overlay
  - Add multiple symbols to same chart
  - Normalized/percentage view
  - Toggle symbols on/off
- [ ] Index comparison
  - Compare stock to Nifty 50
  - Relative strength display
- [ ] Custom comparison groups
  - Save groups of symbols
  - Quick switch between comparisons

#### 1.12.14 Theme-Aware Charts
Visual consistency between app theme and charts.

**Tasks:**
- [ ] Dynamic chart colors based on theme
  - Read CSS variables for colors
  - Apply to chart background, grid, text
- [ ] Profit/loss colors match app theme
  - Use `--profit` and `--loss` variables
- [ ] Indicator colors theme-aware
  - Configurable indicator palette
- [ ] Chart theme persistence
  - Save chart theme preference

#### 1.12.15 Backtest Results Comparison
Better strategy evaluation through comparison.

**Tasks:**
- [ ] Save backtest results to database
  - Store results with timestamp
  - Tag results with notes
- [ ] Backtest history list
  - View past backtest results
  - Filter by strategy, symbol, date
- [ ] Side-by-side comparison view
  - Compare 2-4 backtests
  - Metrics comparison table
  - Overlaid equity curves
- [ ] Export backtest results
  - CSV export
  - PDF report generation


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

    subgraph LiveTrading["🚀 Live Trading"]
        RealMoney[Real Money Trades]
        RealPnL[Real P&L]
        RealPositions[Real Positions]
    end

    Phase1Complete --> ConfigChange
    ConfigChange --> AngelOne
    AngelOne --> SafetyLayer
    SafetyLayer --> LiveTrading

    style Phase1Complete fill:#e8f5e9,stroke:#4caf50
    style ConfigChange fill:#fff3e0,stroke:#ff9800
    style AngelOne fill:#e3f2fd,stroke:#1976d2
    style SafetyLayer fill:#ffebee,stroke:#c62828
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
│   │   │   ├── portfolio/
│   │   │   ├── trading/
│   │   │   ├── analysis/
│   │   │   ├── data/
│   │   │   ├── watchlist/
│   │   │   ├── signals/            # Signal generation
│   │   │   ├── backtest/           # Backtesting framework
│   │   │   ├── risk/               # Risk management
│   │   │   ├── alerts/             # Alerts & notifications
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
│   │   │   └── settings/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── charts/
│   │   │   ├── trading/
│   │   │   ├── portfolio/
│   │   │   ├── algo/               # Algo-specific components
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

Before moving to Phase 2, ensure:

1. **Paper Trading Works End-to-End**
   - [ ] Can search and add symbols to watchlist
   - [ ] Can place all order types (market, limit, SL)
   - [ ] Orders execute at realistic prices
   - [ ] Positions update correctly
   - [ ] P&L calculation is accurate
   - [ ] Trade history is maintained

2. **Risk Management Active**
   - [ ] Position size limits enforced
   - [ ] Daily loss limit stops trading
   - [ ] Auto square-off works

3. **Algo Trading Functional**
   - [ ] At least 3 strategies implemented and tested
   - [ ] Strategy executor runs without errors
   - [ ] Scheduler triggers strategies correctly
   - [ ] Signals convert to orders properly
   - [ ] Kill switch stops all algo trading
   - [ ] Circuit breakers trigger on losses
   - [ ] Backtest results match paper trading (within tolerance)

4. **Notifications Working**
   - [ ] Email notifications deliver correctly
   - [ ] WhatsApp notifications work (if configured)
   - [ ] Real-time UI notifications appear
   - [ ] User can configure notification preferences
   - [ ] Critical alerts (risk breaches) always notify
   - [ ] Quiet hours respected

5. **Frontend Functional**
   - [ ] Dashboard shows portfolio summary
   - [ ] Can view and manage positions
   - [ ] Order entry and confirmation work
   - [ ] Charts display with indicators
   - [ ] Algo dashboard shows strategy status
   - [ ] Can enable/disable strategies
   - [ ] Notification bell with unread count
   - [ ] Notification settings page works

6. **Testing Complete**
   - [ ] Core services have unit tests
   - [ ] API endpoints tested
   - [ ] Paper trading validated against expected behavior
   - [ ] Strategy backtests pass validation
   - [ ] Algo execution tested in simulated market conditions
   - [ ] Notification delivery tested for all channels

7. **UX Improvements Complete**
   - [ ] Trade from Analysis page works
   - [ ] Keyboard shortcuts functional
   - [ ] Error boundaries prevent app crashes
   - [ ] Toast notifications show for key actions
   - [ ] Skip links and focus states for accessibility
   - [ ] ARIA labels on icon-only buttons

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