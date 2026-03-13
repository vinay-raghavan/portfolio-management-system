# Release Notes

## v1.5.4 (2026-03-13)

### 🧠 Market-Adaptive Screener & Capital Safety

This release introduces intelligent market regime detection that automatically adapts screening filters based on market conditions, along with critical capital validation improvements to prevent over-leveraging.

**New Features:**

#### Market Regime Detection
- **Composite Scoring System**: Scores market from -100 (strongly bearish) to +100 (strongly bullish) based on:
  - **NIFTY 50 Trend (35%)**: Price vs 50/200 DMA, MA alignment, position in 52-week range
  - **Market Breadth (25%)**: Advance/decline analysis (placeholder for future enhancement)
  - **Momentum (25%)**: RSI and ROC indicators on NIFTY 50
  - **Volatility (15%)**: India VIX levels (low VIX = bullish, high VIX = bearish)
- **Five Regime Classifications**: Strongly Bullish, Bullish, Neutral, Bearish, Strongly Bearish
- **Real-time Detection**: Uses Yahoo Finance data provider for live index data

#### Adaptive Screener (ADAPTIVE Preset)
- **Automatic Filter Switching**: Applies bullish or bearish filters based on detected regime
- **Bullish Filters (Minervini Trend Template)**:
  - Price > 50 DMA > 200 DMA (uptrend structure)
  - RS Rating > 70, within 25% of 52-week high
  - Volume surge confirmation
- **Bearish Filters (Inverse Minervini)**:
  - Price < 50 DMA < 200 DMA (downtrend structure)
  - Relative weakness, near 52-week low
  - Relaxed filtering to find SHORT candidates in bear markets
- **Side Auto-Detection**: Returns "LONG" candidates in bullish regime, "SHORT" candidates in bearish

#### Strict Capital Validation
- **Block Orders on Broker Disconnect**: Previously allowed orders when broker was None
- **Block Orders on Funds Fetch Failure**: Previously allowed orders when get_funds() failed
- **Negative Cash Block**: Prevents new BUY orders when `available_cash < 0`
- **Negative Cash Short Block**: Prevents new SHORT positions when `available_cash < 0`
- **SLB Margin Enforcement**: 30% margin check for SLB short positions

**Bug Fixes:**

- **SLB Margin**: Corrected SLB margin from 50% to 30% (per SEBI guidelines)
- **INTRADAY Margin**: Fixed margin staying at 25% (was incorrectly changed to 30%)
- **Yahoo Provider**: Fixed `get_historical()` to use `period` parameter instead of `days`
- **Data Provider Import**: Fixed method name from `get_historical_data` to `get_historical`
- **Auto-Trade Direction**: Fixed SHORT signal execution with correct product types

**New Files:**

- `backend/app/modules/screener/market_regime.py` - Market regime detection module
- `MarketRegimeDetector` class with scoring algorithms
- `MarketRegime` enum (STRONGLY_BULLISH to STRONGLY_BEARISH)
- `MarketRegimeData` dataclass with all scores and reasons

**Testing:**

- All 399 backend tests pass
- All 81 trading-engine tests pass
- Market regime detection validated against live NIFTY data
- Adaptive screener verified for both bullish and bearish conditions

---

## v1.5.3 (2026-03-09)

### 🩳 Short Selling & Intraday Enhancements

This release adds comprehensive short selling support including INTRADAY auto-square-off, short-specific strategies, SLB (Securities Lending & Borrowing) for multi-day shorts, unified funds calculation, and enhanced auto-trade configuration.

**New Features:**

#### INTRADAY Auto Square-Off (Section 2.9.1)
- **Auto square-off task**: Automatically closes all INTRADAY positions at 3:15 PM IST before market close
- **Safety check task**: Verifies no intraday positions remain after market close (3:35 PM IST)
- **Square-off endpoint**: `POST /internal/square-off-intraday` for manual triggering
- **Position count endpoint**: `GET /internal/intraday-positions-count` for monitoring
- Retry logic for failed square-offs (critical for risk management)
- Funds properly updated on square-off (margin release + P&L credit)

#### Short-Specific Strategies (Section 2.9.2)
- **SignalIntent enum**: New signal classification (OPEN_LONG, CLOSE_LONG, OPEN_SHORT, CLOSE_SHORT)
- **SignalDirection enum**: Strategy-level direction control (LONG, SHORT, BOTH)
- **MomentumShortStrategy**: Generates SHORT signals based on bearish momentum:
  - Price below EMA200 (long-term downtrend)
  - RSI overbought (reversal setup)
  - MACD bearish crossover
  - ADX strong downtrend (-DI > +DI)
- **Executor validation**: Blocks OPEN_SHORT signals when product_type doesn't allow shorting

#### SLB Support Foundation (Section 2.9.3)
- **SLB ProductType**: Added to all product type enums (backend, trading-engine, shared)
- **SLBPosition model**: Tracks borrowing details, fees, return dates, status
- **Broker interface**: Added `get_slb_availability()`, `borrow_securities()`, `return_securities()` methods
- **SLB worker tasks**:
  - `accrue_slb_fees`: Daily fee accrual after market close
  - `check_slb_expiry`: Warn users about approaching return dates
  - `auto_close_expiring_slb`: Force close positions on expiry day

#### Unified Funds Calculation (Section 2.9.4)
- **Consistent formula** across all product types:
  - `cash_balance = starting_balance + realized_pnl`
  - `margin_used = SUM(blocked margin for open positions)`
  - `available_cash = cash_balance - margin_used`
- **starting_balance column**: Added to `user_funds` for accurate P&L tracking
- **SLB funds handling**: Full support for SLB buy/sell with 50% margin

#### Auto-Trade Enhancements (Section 2.9.5)
- **product_type field**: Configure DELIVERY, INTRADAY, MARGIN, or SLB per auto-trade config
- **signal_direction field**: Restrict to LONG, SHORT, or BOTH directions
- **Frontend UI**: Product Type and Signal Direction selectors in saved screener dialog
- **Validation**: SHORT/BOTH disabled when DELIVERY or MARGIN selected

#### Short Position Exit Logic (Section 2.9.6)
- **Stop Loss**: Triggers when price >= stop (price rises against short)
- **Take Profit**: Triggers when price <= target (price falls in favor)
- **Trailing Stop**: Tracks lowest price, triggers when price rises
- **Profit Lock**: Lock price moves DOWN to protect profits

**Bug Fixes:**

- **Exit condition time window**: Fixed bug where exit conditions (SL/TP/trailing stop) were checked outside strategy's trading window
- **Position product_type**: Store product_type on position at open time to prevent margin mismatch when strategy settings change
- **Double P&L counting**: Fixed duplicate `update_realized_pnl` calls that caused incorrect cash_balance
- **Funds widget**: Fixed missing `starting_balance`, `realized_pnl`, `unrealized_pnl` fields in FundsResponse

**Database Migrations:**

- `add_product_type_to_positions`: Product type column on algo_positions
- `backfill_position_product_type`: Populate from strategy settings
- `add_signal_direction`: Signal direction on user_strategies
- `add_slb_positions`: SLB position tracking table
- `add_starting_balance`: Starting balance on user_funds
- `add_auto_trade_config_fields`: Product type/direction on auto_trade_configs

**New Files:**

- `worker/worker/tasks/intraday.py` - INTRADAY square-off tasks
- `worker/worker/tasks/slb.py` - SLB fee accrual and expiry tasks
- `trading-engine/engine/routes/intraday.py` - Square-off endpoints
- `shared/shared/strategies/short/momentum_short.py` - Bearish momentum strategy

**Testing:**

- All 399 backend tests pass
- All 81 trading-engine tests pass
- Auto square-off tested successfully (3 positions closed at 3:15 PM)
- Funds calculation verified for all product types

---

## v1.5.2 (2026-03-05)

### 🔧 Funds Calculation Fix & Sentiment Display

This release fixes critical bugs in margin trading accounting and adds visual sentiment indicators to the Daily Digest.

**Bug Fixes:**

- **Funds Calculation**: Fixed `total_balance` and `available_margin` formulas that were double-counting margin
  - `total_balance` was incorrectly `cash_balance + margin_used` (now `cash_balance + collateral`)
  - `available_margin` was double-subtracting `margin_used` (now `available_cash + collateral`)
- **Profit Lock Ratcheting**: Profit lock now "ratchets up" as higher profit booking thresholds are crossed
  - Previously, profit lock was only set once at the first threshold
  - Now it updates at each subsequent threshold (1% → 2% → 5% → 10%) to protect more profit
- **Profit Booking Rules Parsing**: Enhanced to support both legacy (list) and new (object) formats

**Features:**

- **Sentiment Score Display**: Added comprehensive sentiment visualization to Daily Digest widget
  - Numerical score with +/- sign (e.g., `-0.079`)
  - Visual gauge bar from -1.0 (bearish) to +1.0 (bullish)
  - Component breakdown showing Indices (40%), Breadth (30%), News (30%) contributions
  - Category labels: Strong Bullish/Bullish/Slightly Bullish/Neutral/Slightly Bearish/Bearish/Strong Bearish
  - Emoji indicators for quick sentiment recognition

**Improvements:**

- Changed margin operation logs from DEBUG to INFO level for better transaction visibility
- Fixed high-severity minimatch ReDoS vulnerability in frontend dependencies

**Accounting Model (Corrected):**

```
cash_balance    = Deposits - Withdrawals + Realized P&L
margin_used     = Σ(remaining_qty × entry_price × margin_rate) for open positions
available_cash  = cash_balance - margin_used
total_balance   = cash_balance + collateral
available_margin = available_cash + collateral
```

**Technical Details:**

- 4 commits: profit lock ratcheting, sentiment display, funds calculation fix, dependency update
- Files changed: `database_provider.py`, `schemas.py`, `position_tracker.py`, `DigestWidget.tsx`

---

## v1.5.1 (2026-02-26)

### 🔒 Profit-Lock Stop Loss & Margin Fix

This release adds the ability to lock profits by moving stop loss to a profit level once a threshold is reached, plus fixes margin tracking for open positions.

**Core Features:**

- **Profit-Lock Stop Loss**: When enabled, stop loss automatically moves to a profit level once the position hits the profit threshold
- **Position-Level Toggle**: Override strategy-level profit lock settings for individual positions
- **Hybrid Buffer Approach**: Uses trailing stop percentage as a buffer below the activation price

**Backend Changes:**

- Added `profit_lock_enabled`, `profit_lock_activated`, `profit_lock_price` fields to position tracking
- New API endpoints: `GET/PATCH /algo/positions/{id}/profit-lock`
- `ProfitLockConfig` and `ProfitLockUpdate` schemas in portfolio module

**Frontend Changes:**

- New `AlgoProfitLockDialog` component for per-position profit lock configuration
- Integrated in PnLDashboard position actions menu
- Real-time status display showing lock activation and price

**Bug Fixes:**

- **Margin Blocking Fix**: Fixed bug where margin wasn't blocked when opening positions in `executor.py`
- Margin is now correctly tracked for all product types (DELIVERY 100%, INTRADAY 25%, MARGIN 50%)

**Technical Details:**

- 10 files changed, 321 insertions
- PR: [#85](https://github.com/vinay-raghavan/portfolio-management-system/pull/85)

---

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

