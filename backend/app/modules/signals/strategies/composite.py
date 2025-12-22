"""Composite strategy for combining multiple indicators with configurable logic."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

import pandas as pd

from app.modules.signals.models import SignalType
from app.modules.signals.strategies.base import BaseStrategy, SignalData
from app.modules.signals.strategies.registry import StrategyRegistry


class CombineLogic(str, Enum):
    """Logic for combining multiple strategy signals."""
    AND = "AND"  # All strategies must agree
    OR = "OR"    # Any strategy triggers
    MAJORITY = "MAJORITY"  # Majority vote
    WEIGHTED = "WEIGHTED"  # Weighted by strength/confidence


@dataclass
class StrategyComponent:
    """A component strategy within a composite strategy."""
    strategy_name: str
    params: dict = field(default_factory=dict)
    weight: float = 1.0  # Weight for WEIGHTED logic
    required: bool = False  # If True, this strategy must agree in AND/MAJORITY


class CompositeStrategy(BaseStrategy):
    """Strategy that combines multiple indicators/strategies.
    
    Allows combining strategies like RSI + MACD with configurable logic:
    - AND: All strategies must give same signal
    - OR: Any strategy trigger is sufficient  
    - MAJORITY: More than half must agree
    - WEIGHTED: Signal based on weighted combination
    
    Example:
        composite = CompositeStrategy(
            name="rsi_macd_confluence",
            components=[
                StrategyComponent("rsi", {"oversold_threshold": 30}),
                StrategyComponent("macd", {}, weight=1.5),
            ],
            combine_logic=CombineLogic.AND
        )
    """
    
    default_timeframe = "1d"
    
    def __init__(
        self,
        name: str,
        description: str,
        components: list[StrategyComponent],
        combine_logic: CombineLogic = CombineLogic.AND,
        min_agreement_pct: float = 0.5,  # For MAJORITY logic
        min_combined_strength: float = 0.5,
        min_combined_confidence: float = 0.5,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize composite strategy.
        
        Args:
            name: Unique strategy name
            description: Human-readable description
            components: List of component strategies
            combine_logic: How to combine signals (AND/OR/MAJORITY/WEIGHTED)
            min_agreement_pct: Minimum agreement for MAJORITY (default 50%)
            min_combined_strength: Minimum combined signal strength
            min_combined_confidence: Minimum combined confidence
            atr_period: ATR period for stop loss
            atr_multiplier: ATR multiplier for stop loss
            risk_reward_ratio: Risk/reward ratio
        """
        self.name = name
        self.description = description
        self.components = components
        self.combine_logic = combine_logic
        self.min_agreement_pct = min_agreement_pct
        self.min_combined_strength = min_combined_strength
        self.min_combined_confidence = min_combined_confidence
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.risk_reward_ratio = Decimal(str(risk_reward_ratio))
        
        # Cache for component strategy instances
        self._component_instances: list[BaseStrategy] = []
        self._initialized = False
    
    def _initialize_components(self) -> None:
        """Lazily initialize component strategy instances."""
        if self._initialized:
            return
            
        for component in self.components:
            strategy = StrategyRegistry.get_strategy(
                component.strategy_name, 
                component.params
            )
            if strategy:
                self._component_instances.append(strategy)
        
        self._initialized = True
    
    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "name": self.name,
            "components": [
                {
                    "strategy": c.strategy_name,
                    "params": c.params,
                    "weight": c.weight,
                    "required": c.required,
                }
                for c in self.components
            ],
            "combine_logic": self.combine_logic.value,
            "min_agreement_pct": self.min_agreement_pct,
            "min_combined_strength": self.min_combined_strength,
            "min_combined_confidence": self.min_combined_confidence,
            "atr_period": self.atr_period,
            "atr_multiplier": float(self.atr_multiplier),
            "risk_reward_ratio": float(self.risk_reward_ratio),
        }
    
    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate combined signals from all component strategies."""
        self._initialize_components()
        
        if not self._component_instances:
            return []
        
        # Collect signals from all components
        component_signals: list[tuple[StrategyComponent, list[SignalData]]] = []
        for component, strategy in zip(self.components, self._component_instances):
            signals = strategy.generate_signals(df, symbol)
            component_signals.append((component, signals))
        
        # Combine signals based on logic
        return self._combine_signals(df, symbol, component_signals)
    
    def _combine_signals(
        self,
        df: pd.DataFrame,
        symbol: str,
        component_signals: list[tuple[StrategyComponent, list[SignalData]]],
    ) -> list[SignalData]:
        """Combine signals from multiple strategies based on combine logic."""
        from ta.volatility import AverageTrueRange
        
        # Extract primary signals (first signal from each strategy)
        signals_by_type: dict[SignalType, list[tuple[StrategyComponent, SignalData]]] = {
            SignalType.BUY: [],
            SignalType.SELL: [],
            SignalType.HOLD: [],
        }
        
        all_indicators: dict[str, Any] = {}
        
        for component, signals in component_signals:
            if signals:
                signal = signals[0]  # Take first signal
                signals_by_type[signal.signal_type].append((component, signal))
                # Collect all indicators
                if signal.indicators:
                    prefix = component.strategy_name
                    for key, value in signal.indicators.items():
                        all_indicators[f"{prefix}_{key}"] = value

