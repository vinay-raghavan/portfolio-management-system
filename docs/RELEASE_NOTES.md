# Release Notes

## v1.5.0 (2026-02-26)

### 🕐 Algo Trading Time Window (Section 2.7)

This release adds the ability to restrict when algo strategies can execute trades, helping users avoid volatile market periods or focus on specific trading sessions.

**Core Features:**

- **Time Window Configuration**: Set start/end times for strategy execution (e.g., 9:45 AM - 3:15 PM IST)
- **Timezone Support**: Full IANA timezone support (default: Asia/Kolkata)
- **Active Trading Days**: Select which days of the week the strategy can trade
- **Real-time Status Indicator**: Strategy cards show "In Window" (green) or "Outside Window" (grey) status
- **Preset Configurations**: Quick presets for Market Hours, Avoid Open/Close, Morning/Afternoon sessions

**Backend Changes:**

- Added `trading_start_time`, `trading_end_time`, `trading_timezone`, `active_trading_days` fields to `UserStrategy` model
- Created `TimeWindowValidator` utility class in shared package
- Integrated time window checks in `StrategyExecutor.execute()` - strategies outside window return `SKIPPED` status

**Frontend Changes:**

- New `TimeWindowSection` component with time pickers, timezone selector, and day checkboxes
- Strategy cards display time window badge and real-time status indicator
- StrategyDialog and StrategyDetails integration

**Bug Fixes:**

- Fixed time window config not being passed to `StrategyConfig` in scheduled/manual execution routes

**Technical Details:**

- Alembic migration: `20260225_1000_add_trading_time_window_fields.py`
- 17 commits across backend, shared, trading-engine, and frontend
- PR: [#83](https://github.com/vinay-raghavan/portfolio-management-system/pull/83)

---

## v1.4.2 (2026-02-25)

### 🐛 Bug Fixes - Ledger Data Integrity

This patch release fixes critical data integrity issues in the transaction ledger system.

**Fixes:**

- **Automatic DEPOSIT Ledger Entry**: New users now get an automatic DEPOSIT transaction recorded in the ledger when their funds are initialized, ensuring proper audit trail from day one
- **Duplicate Transaction Prevention**: Added unique index `ix_txn_ledger_unique_ref` on `(reference_type, reference_id, transaction_type)` to prevent duplicate ledger entries
- **Backfill Script Fix**: Added `NOT EXISTS` check to `backfill_ledger.py` to prevent duplicate entries when re-running the script

**Technical Changes:**

- `FundsService.initialize_funds()` now accepts optional `LedgerService` to record initial DEPOSIT
- `AuthService` injects `LedgerService` into `FundsService` during user registration
- Portfolio router endpoints updated to inject `LedgerService` into `FundsService`:
  - `get_funds`, `deposit_funds`, `withdraw_funds`, `reset_funds`

**Impact:**
- All new users have proper ledger audit trail starting with initial deposit
- Enables consistent ledger reconciliation (cash_balance = starting_capital + sum(transactions))
- Prevents duplicate transactions from causing incorrect balance calculations

---

## v1.4.1 (2026-02-25)

### 🐛 Bug Fixes - Multi-Factor Scoring Pipeline

This patch release fixes critical issues in the multi-factor scoring pipeline that prevented proper data fetching and scoring.

**Fixes:**

- **News/Sentiment Symbol Normalization**: YahooNewsProvider now correctly adds `.NS` suffix for Indian stocks, enabling proper news fetching and sentiment scoring
- **Fundamental Data Auto-Fetch**: MultiFactorScorer now automatically fetches fundamental data from RecommendationService when not provided, ensuring scores reflect real data
- **Fundamentals Provider Fix**: Screener service now uses Yahoo provider for fundamentals instead of the user's trading provider (e.g., Fyers), which doesn't have fundamentals API
- **Pending Trades UI Fix**: Changed frontend status filter from `'PENDING'` (uppercase) to `'pending'` (lowercase) to match backend `PendingTradeStatus` enum
- **Strategy Naming Convention**: Strategies created from screener recommendations now use `{screener_name}_{YYYYMMDD}` format (e.g., `minervini_nifty50_20260225`) instead of generic `custom_{YYYYMMDD}`

**Impact:**
- Combined scores now reflect real fundamental and sentiment data (63-77) instead of defaults (47-50)
- Fundamentals fetch improved from 0/N to N/N symbols
- Pending trades UI now loads correctly
- Strategies are now easily identifiable by their source screener

---

## v1.4.0 (2026-02-24)

### 🚀 Phase 2 Features

This release completes several Phase 2 components including the recommendation auto-trade pipeline, Redis caching, reporting infrastructure, and frontend reports.

---

### 🤖 Recommendation Auto-Trade Pipeline (Section 2.6)

Fully automated flow from screener recommendations to algo execution with minimal user intervention.

**Core Features:**
- **Auto-Trade Configuration**: Per-user, per-category auto-trade settings (momentum, breakout, value, sector)
- **Strategy Templates**: Reusable strategy configurations with position sizing, risk limits, and trading windows
- **Pending Trade Queue**: User confirmation layer with approve/reject/expire workflow
- **Multi-Factor Scoring**: Combined technical (40%) + fundamental (40%) + sentiment (20%) analysis
  - Signal direction inference (LONG/SHORT/NEUTRAL)
  - Confidence levels (HIGH/MEDIUM/LOW/SKIP)
  - Position size multipliers based on confidence
  - Customizable weights via UI
- **Custom Screener Integration**: Link saved screeners to auto-trade with scheduling
- **Exit-Only Symbol Management**: Symbols dropped from screener but with open positions are tracked separately and only allow SELL signals until positions close

**New API Endpoints:**
- `GET/PUT /algo/auto-trade/configs` - Auto-trade configuration management
- `GET/POST /algo/auto-trade/pending/*` - Pending trade approval workflow
- `CRUD /algo/templates` - Strategy template management
- `GET/PUT /algo/auto-trade/weights` - Multi-factor weight configuration

**New Frontend Pages:**
- `/settings/auto-trade` - Auto-trade configuration with weight sliders, presets, confidence selectors
- `/algo/templates` - Strategy template management
- Dashboard integration with `AlgoCarousel` combining Summary + Pending Trades tabs

---

### ⚡ Redis Caching (Section 2.4.3)

Comprehensive caching layer for improved performance.

**Features:**
- Cache service with TTL management
- Market data caching
- User session caching
- Strategy execution result caching

---

### 📊 Reporting Infrastructure (Section 2.4)

Complete reporting backend with ledger, capital gains, and activity tracking.

**Features:**
- **Transaction Ledger**: Full cash flow history with running balances
- **Capital Gains Tracking**: Short-term and long-term gains calculation with tax reports
- **Broker API Logging**: Request/response logging with latency tracking
- **Activity Log**: Comprehensive audit trail of all user and system events

---

### 📱 Reports Frontend (Section 2.5)

New "Reports" section in the sidebar with comprehensive reporting pages.

**New Pages:**
- `/reports` - Overview with summary cards and quick links
- `/reports/statement` - Account statement with filtering and export
- `/reports/gains` - Capital gains report with STCG/LTCG breakdown
- `/reports/api-logs` - Broker API interaction logs
- `/reports/activity` - Activity timeline with filtering

---

### 🐛 Bug Fixes

- **Trailing Stop Initialization**: Fixed trailing stop not being initialized from strategy defaults when opening positions
- **Migration Conflicts**: Fixed down_revision to use correct revision ID
- **Chart Symbol Comparison**: Fixed multi-chart candle interval issues
- **Daily Digest Widget**: Fixed refresh button with visual feedback
- **SQLAlchemy Enum Serialization**: Fixed enum serialization in auto-trade schemas

---

### 🔒 Security & Infrastructure

- **Docker Hardening**: Multi-stage builds with Chainguard production images
- **Security Dependency Upgrades**: Updated packages to address CVEs
- **npm Audit**: Addressed frontend security vulnerabilities

---

### ✨ UX Improvements

- **Keyboard Shortcuts**: Enhanced navigation and trading shortcuts
- **Accessibility**: Improved ARIA labels and focus states
- **Error Handling**: Better error boundaries and recovery
- **Recommendations Carousel**: Expandable 3-column analysis view
- **AlgoCarousel**: Combined Summary + Pending Trades on dashboard

---

### 📦 Installation

See [README.md](../README.md) for quick start instructions.

### 🗺️ Roadmap (Phase 2 Remaining)

- [ ] Angel One broker integration
- [ ] Email/WhatsApp notifications
- [ ] Live trading safety features
- [ ] E2E tests for auto-trade pipeline

---

## v1.0.0 (2026-02-13)

### 🎉 Initial Release

The first stable release of Portfolio Management System - a comprehensive algorithmic trading platform for Indian markets (NSE/BSE) with paper trading, technical analysis, and automated strategy execution.

### ✨ Highlights

- **468 files** with ~100,751 insertions
- Full Phase 1 completion with paper trading capabilities
- Production-ready for paper trading; Fyers live integration available

---

### 📊 Dashboard

- **Unified Dashboard**: Portfolio summary, funds overview, algo status, market overview
- **Recommendations Carousel**: Auto-scrolling combined screener + research picks
  - 5 items per slide with expandable detailed analysis
  - 3-column expansion: Filter Scores, Technical Signals, Detailed Analysis
  - Auto-scroll every 5 seconds with manual navigation
- **Sector Heatmap**: Visual sector performance with drill-down to individual stocks
- **Recent Trades**: Trade history widget with P&L tracking
- **Top Movers**: Real-time gainers and losers

### 🤖 Algorithmic Trading Engine

- **Strategy Framework**
  - Built-in strategies: RSI, MACD, MA Crossover, Bollinger Bands, Supertrend
  - Intraday strategies: VWAP Reversion, ORB (Opening Range Breakout), Gap-Go
  - Custom strategy support via `Strategy` base class
- **Execution Engine**
  - Strategy executor with scheduling (15-min intervals)
  - Signal-to-order conversion with position sizing
  - Multi-strategy portfolio support
- **Safety Controls**
  - Kill switch (emergency stop all trading)
  - Circuit breakers (auto-stop on losses)
  - Daily loss limits
  - Position size limits
  - Auto square-off at EOD

### 📈 Stock Screener

- **Preset Screeners**
  - Momentum: High volume, RSI 50-70, near 52-week high
  - Breakout: Breaking 20-day range, volume spike
  - Consolidation: Tight range, declining volume
  - Pullback: RSI oversold, above 200-day MA
  - Sector Rotation: Strongest sectors + top stocks
- **Daily Recommendations**
  - Auto-generated picks at market open
  - Performance tracking (1D/1W/1M returns)
  - Win rate analytics
- **Algo Integration**
  - Create strategy from screener results
  - Dynamic screener-based universes
  - Screener alerts (notify when stocks pass filters)

### 🔬 Research Module

- **Fundamental Analysis**
  - Key ratios: P/E, P/B, EPS, ROE, Debt/Equity
  - Revenue and earnings trends
  - Peer comparison within sector
- **News Integration**
  - Multi-source: Finnhub, Yahoo Finance, Google RSS
  - Sentiment scoring (Bullish/Bearish/Neutral)
  - Stock-specific and market news
- **Sector Heatmap**
  - Color-coded performance visualization
  - Timeframe toggle (1D, 1W, 1M, 3M, 1Y)
  - Click to drill down into sector stocks
- **Daily Research Digest**
  - Market summary and index performance
  - Top gainers/losers
  - Volume leaders
  - Breakout candidates

### 💹 Trading

- **Paper Trading Broker**
  - Full order lifecycle simulation
  - Realistic price execution
  - Stop Loss / Take Profit / Trailing Stop
  - Funds management (add/withdraw)
- **Fyers Live Integration**
  - OAuth2 authentication
  - Data provider (quotes, historical data)
  - Broker (order placement, positions, funds)
- **Order Types**
  - Market, Limit, Stop Loss, Stop Loss Market
  - AMO (After Market Orders) support
  - Order modification and cancellation

### 📉 Backtesting

- **BacktestRunner** with comprehensive metrics
  - Total/Annualized returns
  - Sharpe Ratio, Sortino Ratio
  - Maximum Drawdown
  - Win Rate, Profit Factor
- **Walk-forward validation**
- **Visual equity curves**

### 🛡️ Risk Management

- Position size limits (% of portfolio)
- Sector concentration limits
- Daily P&L limits
- Auto square-off for intraday positions
- Stop Loss enforcement on all trades

### 🎨 User Experience

- **Keyboard Shortcuts**
  - Navigation: G+D (Dashboard), G+P (Portfolio), G+A (Analysis)
  - Trading: B (Buy), S (Sell), N (New order)
  - Chart: +/- (Zoom), 1-9 (Timeframes)
- **Accessibility**
  - Skip links for screen readers
  - ARIA labels on all interactive elements
  - Focus states and keyboard navigation
- **Error Handling**
  - Error boundaries prevent app crashes
  - Graceful degradation with retry options
- **Toast Notifications**
  - Order status updates
  - Alert triggers
  - System notifications

### 🏗️ Infrastructure

- **Containerized Architecture**
  - Frontend: Next.js 14 on port 3001
  - Backend API: FastAPI on port 8010
  - Trading Engine: FastAPI on port 8011
  - Worker: Celery for background tasks
- **Database**: PostgreSQL 15 + TimescaleDB
- **Cache**: Redis 7 for caching and Celery broker
- **Provider Abstraction**
  - DataProvider: Yahoo, NSE, Fyers
  - BrokerProvider: Paper, Fyers
  - NewsProvider: Finnhub, Yahoo, Google RSS

---

### 🗺️ Roadmap (Phase 2)

- [ ] Angel One broker integration
- [ ] Email/WhatsApp notifications
- [ ] Live trading safety features
- [ ] Mobile app (React Native)

---

### 📦 Installation

See [README.md](../README.md) for quick start instructions.

### 🐛 Known Issues

- Email/WhatsApp notifications not yet implemented (console provider only)
- Some fundamental data may be delayed depending on data source

### 🙏 Credits

Built with FastAPI, Next.js, PostgreSQL, Redis, TradingView Charts, and shadcn/ui.

