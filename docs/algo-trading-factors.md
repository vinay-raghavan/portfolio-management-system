# Algorithmic Trading Factors & Models

This document outlines the key factors and models used in algorithmic trading strategies that can be implemented in the portfolio management system.

## 1. Factor-Based Investing (Fundamental Factors)

### Core Equity Factors (MSCI Framework)

| Factor | Description | Rationale |
|--------|-------------|-----------|
| **Value** | Stocks trading below intrinsic value (low P/E, P/B, P/S) | Mean reversion to fair value |
| **Momentum** | Stocks with strong recent performance | Trend continuation, behavioral biases |
| **Quality** | High profitability, low leverage, stable earnings | Lower risk, sustainable returns |
| **Low Volatility** | Stocks with lower price volatility | Risk-adjusted outperformance |
| **Size** | Small-cap stocks | Higher growth potential, liquidity premium |
| **High Yield** | Stocks with high dividend yields | Income generation, quality signal |

### Alternative Risk Premia (ARP)

- **Carry**: Earning yield differential between assets
- **Defensive**: Low-beta, quality characteristics
- **Value**: Price relative to fundamentals
- **Momentum**: Trend-following across asset classes

## 2. Technical Analysis Indicators

### Trend Indicators

| Indicator | Formula/Description | Signal |
|-----------|---------------------|--------|
| **SMA (Simple Moving Average)** | Average of last N prices | Price above SMA = bullish |
| **EMA (Exponential Moving Average)** | Weighted average favoring recent prices | Faster response to price changes |
| **MACD** | EMA(12) - EMA(26) with signal line EMA(9) | Crossovers indicate trend changes |

### Momentum Indicators

| Indicator | Range | Interpretation |
|-----------|-------|----------------|
| **RSI (Relative Strength Index)** | 0-100 | <30 oversold, >70 overbought |
| **Stochastic Oscillator** | 0-100 | Momentum and overbought/oversold |
| **Rate of Change (ROC)** | Unbounded | Momentum strength |

### Volatility Indicators

| Indicator | Description | Use Case |
|-----------|-------------|----------|
| **Bollinger Bands** | SMA ± 2 standard deviations | Volatility breakouts, mean reversion |
| **ATR (Average True Range)** | Average of true ranges | Position sizing, stop-loss placement |
| **VIX** | Implied volatility index | Market fear gauge |

### Volume Indicators

- **Volume SMA**: Average volume for trend confirmation
- **OBV (On-Balance Volume)**: Cumulative volume flow
- **VWAP**: Volume-weighted average price

## 3. Signal Generation Strategies

### Trend Following
```
BUY: Price > SMA(50) AND MACD > Signal Line AND RSI < 70
SELL: Price < SMA(50) AND MACD < Signal Line AND RSI > 30
```

### Mean Reversion
```
BUY: Price < Lower Bollinger Band AND RSI < 30
SELL: Price > Upper Bollinger Band AND RSI > 70
```

### Momentum
```
BUY: 12-month return > 0 AND 1-month return > 0
SELL: 12-month return < 0 OR 1-month return < 0
```

## 4. Risk Management Factors

### Position Sizing
- **Kelly Criterion**: Optimal bet size based on edge and odds
- **Volatility-based**: Position size inversely proportional to ATR
- **Fixed fractional**: Risk fixed percentage per trade

### Portfolio Metrics
- **Sharpe Ratio**: Risk-adjusted return (excess return / volatility)
- **Sortino Ratio**: Downside risk-adjusted return
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Beta**: Sensitivity to market movements
- **Alpha**: Excess return over benchmark

## 5. Implementation in This System

### Currently Implemented
- Moving Averages (SMA, EMA)
- MACD with signal line
- RSI (14-period)
- Bollinger Bands
- ATR (14-period)
- Volume SMA

### Planned Enhancements
- Multi-factor scoring system
- Backtesting framework
- Risk-adjusted position sizing
- Portfolio optimization (mean-variance)
- Machine learning signal enhancement

## 6. Data Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| yfinance | Price, volume, fundamentals | Real-time (delayed) |
| Polygon.io | Real-time quotes, trades | Real-time |
| Alpha Vantage | Technical indicators | Real-time |

## References

- MSCI Factor Investing Framework
- AQR Factor Research
- Quantpedia Strategy Database
- Academic: Fama-French Factor Models

