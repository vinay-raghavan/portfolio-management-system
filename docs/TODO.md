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

---

## � Git Branching Strategy

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

---

## �🎯 PHASE 1: Paper Trading Platform (Weeks 1-6)

**Goal**: Complete trading platform with simulated execution using free data APIs

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