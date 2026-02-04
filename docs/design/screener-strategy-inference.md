# Design Document: Intelligent Screener-to-Strategy Integration

**Author:** AI Assistant  
**Date:** 2026-02-04  
**Status:** Draft  
**Branch:** `feature/screener-strategy-inference`

## 1. Overview

### 1.1 Problem Statement

Currently, the screener and algo trading modules are loosely connected:
- Screener filters stocks based on technical criteria (momentum, volume, breakouts, etc.)
- Users manually select a pre-defined strategy to apply to screened stocks
- Strategy parameters use defaults, ignoring the screening context

This creates a disconnect: the screener knows *why* stocks were selected, but this intelligence isn't used to configure the trading strategy.

### 1.2 Proposed Solution

Introduce a **Strategy Inference Engine** that:
1. Analyzes screener filter configurations
2. Recommends the optimal strategy type based on filter patterns
3. Derives strategy parameters from filter thresholds
4. Allows user overrides before strategy creation

## 2. Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SCREENER-STRATEGY FLOW                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌───────────────────┐    ┌───────────────────┐   │
│  │   Screener   │───►│ Strategy Inference │───►│  Strategy Creator │   │
│  │   Results    │    │      Engine        │    │   (with params)   │   │
│  └──────────────┘    └───────────────────┘    └───────────────────┘   │
│        │                      │                         │              │
│        │ filters              │ recommendation          │ strategy     │
│        │ symbols              │ + reasoning             │              │
│        │ metadata             │                         ▼              │
│        │                      │                  ┌──────────────┐      │
│        │                      │                  │  UserStrategy │      │
│        │                      │                  │  (database)   │      │
│        │                      │                  └──────────────┘      │
│        │                      │                                        │
│        ▼                      ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Frontend UI                                   │  │
│  │  ┌─────────────┐  ┌──────────────────┐  ┌───────────────────┐  │  │
│  │  │ Screener    │  │ Recommended      │  │ Create Strategy   │  │  │
│  │  │ Results     │  │ Strategy Card    │  │ Button            │  │  │
│  │  │ Table       │  │ (editable params)│  │                   │  │  │
│  │  └─────────────┘  └──────────────────┘  └───────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 New Components

#### 2.2.1 Strategy Inference Engine
**Location:** `backend/app/modules/algo/strategy_inference.py`

Core class that maps screener filters to strategy recommendations.

#### 2.2.2 API Endpoint
**Location:** `backend/app/modules/screener/router.py`

New endpoint: `POST /api/screener/infer-strategy`

#### 2.2.3 Schemas
**Location:** `backend/app/modules/algo/schemas.py`

New schemas for inference request/response.

## 3. Filter-to-Strategy Mapping

### 3.1 Mapping Rules

| Filter Combination | Strategy Type | Rationale |
|-------------------|---------------|-----------|
| MomentumFilter(bullish) + VolumeFilter(spike) | `vwap_momentum` | Momentum with volume confirmation |
| BreakoutFilter + VolumeFilter(spike) | `vwap_momentum` | Breakout plays need momentum |
| MomentumFilter(near_52w_high) + MA(stacked) | `ma_crossover` | Trend following |
| ConsolidationFilter + MA(above_trend) | `bollinger_bands` | Range-bound, wait for squeeze |
| MomentumFilter(oversold/RSI<30) | `rsi` | Mean reversion |
| SectorPerformance + Momentum | `price_action_volume_swing` | Swing trading |

### 3.2 Parameter Derivation

Strategy parameters are derived from filter thresholds:

```python
# Example: RSI strategy from MomentumFilter
if momentum_filter.rsi_oversold:
    rsi_params["oversold_threshold"] = momentum_filter.rsi_oversold
if momentum_filter.rsi_overbought:
    rsi_params["overbought_threshold"] = momentum_filter.rsi_overbought
```

## 4. API Design

### 4.1 Infer Strategy Endpoint

**Request:**
```json
POST /api/screener/infer-strategy
{
  "screener_run_id": "uuid",  // Optional: use completed run
  "filters": [                 // Optional: provide filters directly
    {"filter_type": "momentum", "params": {...}, "weight": 2.0}
  ]
}
```

**Response:**
```json
{
  "recommended_strategy": {
    "strategy_type": "vwap_momentum",
    "strategy_name": "VWAP Momentum",
    "description": "Multi-indicator momentum scoring",
    "suggested_params": {
      "ema_fast": 5,
      "ema_medium": 9,
      "buy_threshold": 3,
      "atr_multiplier": 2.0
    },
    "confidence": 0.85,
    "reasoning": [
      "Momentum filter with bullish mode detected",
      "Volume spike requirement suggests breakout confirmation needed",
      "Recommended wider stops (ATR 2.0x) for momentum plays"
    ]
  },
  "alternative_strategies": [
    {
      "strategy_type": "ma_crossover",
      "confidence": 0.65,
      "reasoning": ["Also suitable for trend-following"]
    }
  ],
  "filter_analysis": {
    "primary_intent": "momentum",
    "secondary_intent": "breakout",
    "risk_profile": "moderate"
  }
}
```

### 4.2 Create Smart Strategy Endpoint

**Request:**
```json
POST /api/screener/create-smart-strategy
{
  "screener_run_id": "uuid",
  "name": "My Momentum Strategy",
  "description": "Auto-configured from screener",
  "strategy_type": "vwap_momentum",      // From inference or user override
  "strategy_params": {...},               // From inference or user override
  "product_type": "INTRADAY",
  "position_sizing_method": "PERCENT_OF_PORTFOLIO",
  "position_size_value": 5.0
}
```

**Response:**
```json
{
  "strategy": { /* UserStrategy object */ },
  "universe": { /* Created universe */ },
  "inference_used": {
    "strategy_type": "vwap_momentum",
    "params_auto_derived": ["ema_fast", "buy_threshold"],
    "params_user_overridden": ["atr_multiplier"]
  }
}
```

## 5. Data Models

### 5.1 StrategyRecommendation (Pydantic)

```python
class StrategyRecommendation(BaseModel):
    strategy_type: str
    strategy_name: str
    description: str
    suggested_params: dict
    confidence: float  # 0.0 - 1.0
    reasoning: list[str]

class InferenceResult(BaseModel):
    recommended_strategy: StrategyRecommendation
    alternative_strategies: list[StrategyRecommendation]
    filter_analysis: FilterAnalysis
```

### 5.2 FilterAnalysis

```python
class FilterAnalysis(BaseModel):
    primary_intent: Literal["momentum", "mean_reversion", "breakout", "trend_following", "swing"]
    secondary_intent: str | None
    risk_profile: Literal["conservative", "moderate", "aggressive"]
    detected_patterns: list[str]
```

## 6. Implementation Plan

### Phase 1: Core Inference Engine
1. Create `strategy_inference.py` with mapping logic
2. Implement filter analysis functions
3. Add parameter derivation logic

### Phase 2: API Integration
1. Add new schemas
2. Create `/infer-strategy` endpoint
3. Create `/create-smart-strategy` endpoint
4. Update existing `/create-strategy` to optionally use inference

### Phase 3: Frontend (Future)
1. Add "Recommended Strategy" card to screener results
2. Parameter editor with inference suggestions
3. One-click strategy creation

## 7. Testing Strategy

### 7.1 Unit Tests
- Test each filter type → strategy mapping
- Test parameter derivation logic
- Test confidence scoring

### 7.2 Integration Tests
- Test full flow: screener run → inference → strategy creation
- Test with various filter combinations

## 8. Future Enhancements

1. **ML-based inference**: Train on successful strategy-filter combinations
2. **Backtesting integration**: Auto-backtest recommended strategy before creation
3. **Dynamic parameter tuning**: Adjust params based on market conditions
4. **User feedback loop**: Learn from user overrides to improve recommendations
```

