# Release Notes

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

