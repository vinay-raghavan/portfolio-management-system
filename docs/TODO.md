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
│   │   └── testing            # Week 6-7: Testing & polish
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
| 1 | 6-7 | `phase-1/testing` | Unit tests, E2E tests, Validation |
| 2 | 8 | `phase-2/angelone` | Angel One API integration |
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

        subgraph Week7["Week 7: Testing"]
            W7A[Unit + E2E Tests]
            W7B[Algo Validation]
            W7C[Notification Testing]
        end

        Week1 --> Week2 --> Week3 --> Week4 --> Week5 --> Week6 --> Week7
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
| Frontend | 🟡 Partial | Basic dashboard only |
| Indian Stock Data | ❌ Missing | Need NSE/BSE support |
| Abstracted Data Layer | ❌ Missing | Need provider pattern |
| Abstracted Broker Layer | ❌ Missing | Need provider pattern |
| Backtesting | ❌ Missing | Not implemented |
| Risk Management | ❌ Missing | Not implemented |
| Alerts/Notifications | ❌ Missing | Not implemented |


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
- [ ] Create `DataProvider` abstract base class
  - `get_quote(symbol) -> Quote`
  - `get_historical(symbol, period, interval) -> List[OHLCV]`
  - `search_symbols(query) -> List[Symbol]`
  - `get_instrument_info(symbol) -> InstrumentInfo`
- [ ] Migrate existing yfinance code to `YahooDataProvider`
- [ ] Create `NSEDataProvider` using free NSE APIs
- [ ] Create `DataProviderFactory` for runtime selection
- [ ] Add `DATA_PROVIDER` config setting

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
- [ ] Create `Broker` abstract base class
  - `place_order(order) -> OrderResponse`
  - `cancel_order(order_id) -> bool`
  - `modify_order(order_id, changes) -> OrderResponse`
  - `get_order_status(order_id) -> OrderStatus`
  - `get_positions() -> List[Position]`
  - `get_funds() -> Funds`
- [ ] Migrate existing paper trading to `PaperBroker`
- [ ] Create `BrokerFactory` for runtime selection
- [ ] Add `BROKER_TYPE` config setting (paper/live)

#### 1.1.3 Unified Symbol System
Handle different symbol formats across exchanges.

**Tasks:**
- [ ] Create `Symbol` model with exchange-specific tokens
  - `symbol` (display name: "RELIANCE")
  - `exchange` (NSE, BSE, NYSE, NASDAQ)
  - `token` (exchange-specific ID)
  - `isin` (for Indian stocks)
- [ ] Create symbol mapper for Indian stocks
- [ ] Handle Yahoo format (RELIANCE.NS) vs broker format (RELIANCE-EQ)

---

### 1.2 Indian Market Data (Week 2)
> 🌿 **Branch:** `phase-1/indian-market`

#### 1.2.1 NSE Data Provider
Free NSE data for Indian stocks.

**Tasks:**
- [ ] Implement NSE data fetching
  - [ ] Get live quotes from NSE website/API
  - [ ] Get historical data from NSE archives
  - [ ] Get index data (Nifty 50, Bank Nifty)
- [ ] Handle market hours (9:15 AM - 3:30 PM IST)
- [ ] Cache frequently accessed data in Redis
- [ ] Rate limiting to avoid blocks

#### 1.2.2 Instrument Master Database
Store all tradeable instruments.

**Tasks:**
- [ ] Create `Instrument` model
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
- [ ] Daily job to download instrument master
- [ ] Search endpoint for instruments
- [ ] Filter by segment (Equity, F&O, etc.)

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
- [ ] Extend order types
  - [ ] Market Order
  - [ ] Limit Order
  - [ ] Stop Loss (SL)
  - [ ] Stop Loss Market (SL-M)
- [ ] Order validation
  - [ ] Check market hours
  - [ ] Validate price vs LTP (circuit limits)
  - [ ] Validate quantity (lot size for F&O)
  - [ ] Check available funds/margin
- [ ] Order lifecycle events
  - [ ] PENDING → OPEN → FILLED/CANCELLED/REJECTED
  - [ ] Partial fills tracking
- [ ] GTT orders (simulated for paper trading)

#### 1.3.2 Position Management
Enhanced position tracking.

**Tasks:**
- [ ] Separate delivery vs intraday positions
- [ ] Track P&L (realized + unrealized)
- [ ] Day-wise P&L tracking
- [ ] Average price calculation (FIFO method)
- [ ] Position limits and warnings

#### 1.3.3 Funds & Margins
Track virtual funds for paper trading.

**Tasks:**
- [ ] Create `Funds` model
  ```python
  class Funds:
      user_id: str
      cash_balance: Decimal      # Available cash
      margin_used: Decimal       # Blocked for positions
      margin_available: Decimal  # Cash - Used
      collateral: Decimal        # Stock collateral (future)
  ```
- [ ] Initialize new users with virtual cash
- [ ] Update funds on trade execution
- [ ] Margin calculation for F&O (basic)

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
- [ ] Max position size per stock (% of portfolio)
- [ ] Max sector concentration
- [ ] Stop loss enforcement (auto square-off)
- [ ] Take profit enforcement

#### 1.4.2 Daily Risk Limits
**Tasks:**
- [ ] Max daily loss limit (stop trading for day)
- [ ] Max number of trades per day
- [ ] Max intraday exposure
- [ ] Alert when approaching limits

#### 1.4.3 Market Hours & Auto Square-off
**Tasks:**
- [ ] Define market hours per exchange
- [ ] Block orders outside market hours (or queue them)
- [ ] Auto square-off intraday positions at 3:15 PM
- [ ] Pre-market/After-market order handling

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

#### 1.5.1 Dashboard
**Tasks:**
- [ ] Portfolio summary widget
  - Total value, day P&L, overall P&L
- [ ] Top gainers/losers
- [ ] Recent trades
- [ ] Market overview (Nifty, Bank Nifty, Sensex)

#### 1.5.2 Portfolio View
**Tasks:**
- [ ] Holdings table (symbol, qty, avg cost, LTP, P&L, %)
- [ ] Sector allocation pie chart
- [ ] Performance chart (value over time)
- [ ] Export to CSV

#### 1.5.3 Trading Interface
**Tasks:**
- [ ] Order entry form
  - Buy/Sell toggle
  - Market/Limit selector
  - Quantity, Price, Stop Loss, Target
- [ ] Order confirmation modal
- [ ] Order book (pending orders)
- [ ] Trade history

#### 1.5.4 Charts
**Tasks:**
- [ ] Candlestick chart (TradingView Lightweight Charts or similar)
- [ ] Technical indicators overlay (moving averages, Bollinger)
- [ ] Volume bars
- [ ] Drawing tools (basic)

#### 1.5.5 Watchlist
**Tasks:**
- [ ] Multiple watchlists support
- [ ] Add/remove symbols
- [ ] Live price updates
- [ ] Quick buy/sell from watchlist

#### 1.5.6 Alerts Configuration
**Tasks:**
- [ ] Price alerts (above/below threshold)
- [ ] Order execution alerts
- [ ] Daily P&L summary alerts
- [ ] Strategy signal alerts
- [ ] Risk limit breach alerts

---

### 1.6 Notification System (Week 4-5)
> 🌿 **Branch:** `phase-1/notifications`

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

#### 1.7.1 Signal Engine
**Tasks:**
- [ ] Define Signal schema
  ```python
  class Signal:
      symbol: str
      signal_type: str  # BUY, SELL, HOLD
      strength: float   # 0.0 to 1.0
      strategy: str     # Which strategy generated it
      indicators: dict  # Supporting data
      generated_at: datetime
  ```
- [ ] Strategy runner framework
- [ ] Built-in strategies:
  - [ ] RSI Oversold/Overbought
  - [ ] MACD Crossover
  - [ ] Moving Average Crossover
  - [ ] Bollinger Band Squeeze
- [ ] Signal persistence and history

#### 1.7.2 Backtesting Framework
**Tasks:**
- [ ] Historical data loader
- [ ] Strategy backtester
  - Apply strategy to historical data
  - Track simulated trades
  - Calculate returns
- [ ] Performance metrics
  - Total return, CAGR
  - Sharpe ratio, Sortino ratio
  - Max drawdown
  - Win rate, Profit factor
- [ ] Backtest results visualization

#### 1.7.3 Paper Trading Verification
**Tasks:**
- [ ] Run strategies on paper trading
- [ ] Compare paper results with backtest
- [ ] Track slippage and execution quality
- [ ] Generate paper trading reports

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

#### 1.8.1 Strategy Framework
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
- [ ] Create `Strategy` abstract base class
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
- [ ] Create strategy registry for dynamic loading
- [ ] Strategy configuration via YAML/JSON
- [ ] Strategy versioning and history

#### 1.8.2 Built-in Strategies

**Momentum Strategies:**
- [ ] **RSI Strategy**
  - Buy when RSI < 30 (oversold)
  - Sell when RSI > 70 (overbought)
  - Configurable thresholds
- [ ] **MACD Crossover**
  - Buy on bullish crossover (MACD crosses above signal)
  - Sell on bearish crossover
  - Histogram confirmation option
- [ ] **Breakout Strategy**
  - Buy on breakout above N-day high
  - Sell on breakdown below N-day low
  - Volume confirmation

**Mean Reversion Strategies:**
- [ ] **Bollinger Band Strategy**
  - Buy when price touches lower band
  - Sell when price touches upper band
  - Mean reversion to middle band
- [ ] **Moving Average Reversion**
  - Buy when price is N% below MA
  - Sell when price is N% above MA

**Trend Following Strategies:**
- [ ] **Moving Average Crossover**
  - Buy when fast MA crosses above slow MA
  - Sell when fast MA crosses below slow MA
  - Configurable periods (e.g., 9/21, 20/50, 50/200)
- [ ] **Supertrend Strategy**
  - Buy on supertrend flip to bullish
  - Sell on supertrend flip to bearish

**Multi-Factor Strategies:**
- [ ] **Combined Technical Strategy**
  - Requires multiple indicators to align
  - Weighted scoring system
  - Configurable factor weights

#### 1.8.3 Strategy Executor
Runs strategies and executes orders automatically.

**Tasks:**
- [ ] Create `StrategyExecutor` class
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
- [ ] Order queue with rate limiting
- [ ] Execution logging and audit trail
- [ ] Error handling and recovery
- [ ] Dry-run mode (generate signals but don't execute)

#### 1.8.4 Strategy Scheduler
Schedule strategies to run at specific times/intervals.

**Tasks:**
- [ ] Create `StrategySchedule` model
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
- [ ] Celery Beat integration for scheduling
- [ ] Market hours awareness (only run during trading hours)
- [ ] Pre-market and post-market strategy support
- [ ] Manual trigger option

#### 1.8.5 Universe Selection
Define which stocks a strategy trades.

**Tasks:**
- [ ] Create `Universe` model
  ```python
  class Universe:
      id: str
      name: str              # "Nifty 50", "Bank Nifty", "Custom"
      symbols: List[str]
      filter_criteria: dict  # Market cap, sector, liquidity
  ```
- [ ] Pre-built universes:
  - [ ] Nifty 50
  - [ ] Nifty Next 50
  - [ ] Bank Nifty
  - [ ] F&O stocks
  - [ ] Sectoral indices
- [ ] Custom universe builder
- [ ] Dynamic universe (e.g., top 10 by volume)

#### 1.8.6 Position Sizing & Money Management
Automated position sizing based on risk.

**Tasks:**
- [ ] Position sizing methods:
  - [ ] Fixed quantity
  - [ ] Fixed amount (₹ per trade)
  - [ ] Percentage of portfolio
  - [ ] Risk-based (% of portfolio at risk)
  - [ ] Kelly criterion
  - [ ] Volatility-adjusted (ATR-based)
- [ ] Create `PositionSizer` class
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
- [ ] Maximum position limits
- [ ] Sector/correlation limits

#### 1.8.7 Algo Trading Dashboard (Frontend)

**Tasks:**
- [ ] Strategy management page
  - List of strategies (active/inactive)
  - Enable/disable toggle
  - Strategy configuration
- [ ] Strategy performance view
  - P&L by strategy
  - Win rate, Sharpe ratio
  - Drawdown chart
- [ ] Signals view
  - Real-time signal feed
  - Signal history
  - Signal to order mapping
- [ ] Algo order book
  - Orders placed by algo
  - Execution status
  - Manual override option
- [ ] Strategy builder (future)
  - Drag-and-drop indicator selection
  - Condition builder
  - Backtest before deploy

#### 1.8.8 Algo Trading Safety Controls

**Tasks:**
- [ ] **Kill Switch**
  - One-click disable all algos
  - Cancel all pending algo orders
  - Optional: square off all algo positions
- [ ] **Circuit Breakers**
  - Max daily loss per strategy
  - Max consecutive losses
  - Max drawdown limit
  - Auto-disable when triggered
- [ ] **Rate Limits**
  - Max orders per minute
  - Max orders per day
  - Cooldown after order
- [ ] **Monitoring & Alerts**
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

### 2.2 Live Trading Safety
> 🌿 **Branch:** `phase-2/live-safety`

#### 2.2.1 Kill Switch
**Tasks:**
- [ ] Emergency stop button (cancel all orders, square off)
- [ ] API failure detection and auto-stop
- [ ] Connectivity monitoring

#### 2.2.2 Order Confirmation
**Tasks:**
- [ ] Double confirmation for large orders
- [ ] SMS/Email confirmation (optional)
- [ ] Daily trade limit warnings

#### 2.2.3 Audit Trail
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
- [ ] Machine learning signals
  - [ ] Price prediction models
  - [ ] Sentiment analysis (news, social)
  - [ ] Pattern recognition
- [ ] Reinforcement learning agents
- [ ] Portfolio optimization (Markowitz, Black-Litterman)

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
| 8 | Angel One | `phase-2/angelone` | Angel One API integration |
| 8-9 | Live Safety | `phase-2/live-safety` | Live trading safety features |

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