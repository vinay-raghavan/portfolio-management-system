# Portfolio Management System - System Design Document

## 1. Overview

An automated personal financial portfolio management system that performs comprehensive market analysis, executes trades (simulated initially), and maximizes returns through intelligent decision-making.

### 1.1 Key Objectives
- Multi-market support (US, India, etc.)
- Comprehensive fundamental and technical analysis
- Automated trading with simulation mode
- Modern, intuitive user interface
- Risk-aware portfolio optimization

---

## 2. System Architecture

### 2.1 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14 + React 18 | SSR, App Router, excellent DX |
| **UI Components** | shadcn/ui + Tailwind CSS | Modern, accessible, customizable |
| **Charts** | TradingView Lightweight Charts + Recharts | Professional financial charts |
| **Backend** | Python FastAPI | Async, high-performance, great for ML |
| **Task Queue** | Celery + Redis | Distributed task processing |
| **Database** | PostgreSQL + TimescaleDB | Time-series optimized for market data |
| **Cache** | Redis | Real-time data caching |
| **Document Store** | MongoDB | News, reports, unstructured data |
| **ML/Analysis** | pandas, numpy, scikit-learn, ta-lib | Industry standard for quantitative analysis |

### 2.2 Core Modules

```
portfolio-management-system/
├── frontend/                    # Next.js application
│   ├── app/                     # App router pages
│   ├── components/              # React components
│   └── lib/                     # Utilities & API clients
├── backend/
│   ├── api/                     # FastAPI routes
│   ├── core/                    # Core business logic
│   │   ├── data/                # Data ingestion services
│   │   ├── analysis/            # Analysis engines
│   │   ├── trading/             # Trading engine
│   │   └── portfolio/           # Portfolio management
│   ├── models/                  # Database models
│   ├── services/                # External service integrations
│   └── ml/                      # Machine learning models
├── workers/                     # Celery background workers
├── tests/                       # Test suites
└── docker/                      # Container configurations
```

---

## 3. Data Sources & Ingestion

### 3.1 Market Data Providers

| Provider | Data Type | Markets | Cost |
|----------|-----------|---------|------|
| **Yahoo Finance (yfinance)** | Prices, fundamentals | Global | Free |
| **Alpha Vantage** | Technical indicators, forex | Global | Free tier available |
| **Polygon.io** | Real-time US data | US | Paid |
| **NSE India API** | Indian market data | India | Free |
| **Financial Modeling Prep** | Fundamentals, ratios | Global | Free tier |
| **News API / Finnhub** | News, sentiment | Global | Free tier |

### 3.2 Data Categories

1. **Price Data**: OHLCV (Open, High, Low, Close, Volume)
2. **Fundamental Data**: Financial statements, ratios, earnings
3. **Technical Indicators**: RSI, MACD, Bollinger Bands, etc.
4. **News & Sentiment**: Headlines, articles, social sentiment
5. **Economic Data**: GDP, inflation, interest rates, employment
6. **Geopolitical Events**: Elections, policy changes, conflicts

---

## 4. Analysis Engines

### 4.1 Technical Analysis Module

```python
# Key indicators to implement
TECHNICAL_INDICATORS = {
    "trend": ["SMA", "EMA", "MACD", "ADX", "Parabolic SAR"],
    "momentum": ["RSI", "Stochastic", "CCI", "Williams %R", "ROC"],
    "volatility": ["Bollinger Bands", "ATR", "Keltner Channels"],
    "volume": ["OBV", "VWAP", "Accumulation/Distribution"],
    "patterns": ["Head & Shoulders", "Double Top/Bottom", "Triangles"]
}
```

### 4.2 Fundamental Analysis Module

```python
# Key metrics to analyze
FUNDAMENTAL_METRICS = {
    "valuation": ["P/E", "P/B", "P/S", "EV/EBITDA", "PEG"],
    "profitability": ["ROE", "ROA", "ROIC", "Gross Margin", "Net Margin"],
    "growth": ["Revenue Growth", "EPS Growth", "Book Value Growth"],
    "health": ["Current Ratio", "Debt/Equity", "Interest Coverage"],
    "efficiency": ["Asset Turnover", "Inventory Turnover", "Receivables Turnover"]
}
```

### 4.3 Sentiment Analysis Module

- News headline sentiment (NLP-based)
- Social media sentiment (Twitter/X, Reddit)
- Analyst recommendations aggregation
- Insider trading activity
- Institutional holdings changes

### 4.4 Risk Analysis Module

- Value at Risk (VaR)
- Beta calculation
- Sharpe Ratio
- Maximum Drawdown
- Correlation analysis

---

## 5. Trading Engine

### 5.1 Signal Generation

Multi-factor scoring system combining:
- Technical signals (40% weight)
- Fundamental score (30% weight)
- Sentiment score (15% weight)
- Risk metrics (15% weight)

### 5.2 Strategy Framework

```python
class TradingStrategy(ABC):
    @abstractmethod
    def generate_signals(self, market_data: MarketData) -> List[Signal]:
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: Signal, portfolio: Portfolio) -> float:
        pass
```

**Built-in Strategies:**
1. **Momentum Strategy**: Buy strength, sell weakness
2. **Mean Reversion**: Buy oversold, sell overbought
3. **Value Investing**: Buy undervalued fundamentals
4. **Trend Following**: Follow established trends
5. **Multi-Factor**: Combine multiple strategies

### 5.3 Order Management

```python
@dataclass
class Order:
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP_LOSS", "TAKE_PROFIT"]
    quantity: float
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
```

### 5.4 Trade Simulator

Paper trading engine that:
- Simulates order execution with realistic slippage
- Tracks virtual portfolio performance
- Calculates realistic fees and taxes
- Provides performance analytics

---

## 6. Portfolio Engine

### 6.1 Position Management
- Real-time position tracking
- Cost basis calculation (FIFO, LIFO, Average)
- Unrealized/Realized P&L tracking
- Dividend tracking and reinvestment

### 6.2 Portfolio Optimization
- Modern Portfolio Theory (MPT) implementation
- Efficient Frontier calculation
- Risk parity allocation
- Black-Litterman model support

### 6.3 Auto-Rebalancing
- Threshold-based rebalancing triggers
- Calendar-based rebalancing
- Tax-loss harvesting opportunities

---

## 7. User Interface

### 7.1 Dashboard Views

1. **Portfolio Overview**
   - Total portfolio value, Daily/Weekly/Monthly P&L
   - Asset allocation pie chart, Top performers and laggards

2. **Stock Analysis**
   - Interactive price charts (candlestick, line)
   - Technical indicator overlays, Fundamental metrics display

3. **Trading Console**
   - Active signals, Order entry, Trade history

4. **Watchlist & Reports**
   - Custom watchlists, Performance analytics, Tax reports

---

## 8. Database Schema (Core Tables)

```sql
-- Portfolio positions
CREATE TABLE positions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(10) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    avg_cost DECIMAL(18, 4) NOT NULL
);

-- Trade history
CREATE TABLE trades (
    id UUID PRIMARY KEY,
    symbol VARCHAR(20), side VARCHAR(4),
    quantity DECIMAL(18, 8), price DECIMAL(18, 4),
    executed_at TIMESTAMPTZ NOT NULL
);

-- Price data (TimescaleDB hypertable)
CREATE TABLE price_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DECIMAL, high DECIMAL, low DECIMAL, close DECIMAL,
    volume BIGINT
);
```

---

## 9. Development Phases

| Phase | Duration | Focus |
|-------|----------|-------|
| **Phase 1** | Weeks 1-3 | Foundation (Next.js + FastAPI, DB, Data ingestion) |
| **Phase 2** | Weeks 4-6 | Analysis Engine (Technical, Fundamental, Charts) |
| **Phase 3** | Weeks 7-9 | Trading Engine (Simulator, Signals, Orders) |
| **Phase 4** | Weeks 10-11 | Portfolio Management (P&L, Analytics) |
| **Phase 5** | Weeks 12+ | Advanced (ML, Multi-market, Live trading) |

---

## 10. Key Dependencies

**Backend**: FastAPI, SQLAlchemy, Celery, yfinance, pandas, ta-lib, scikit-learn
**Frontend**: Next.js 14, React 18, TanStack Query, Tailwind, TradingView Charts

---

## 11. Security & Deployment

- JWT authentication, API key encryption
- Rate limiting, Audit logging, 2FA
- Frontend on Vercel, Backend on Docker/K8s
- PostgreSQL + TimescaleDB, Redis cache, MongoDB for documents
