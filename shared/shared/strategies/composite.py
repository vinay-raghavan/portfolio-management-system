"""Composite strategy for combining multiple indicators with configurable logic."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

import pandas as pd

from shared.models.signals import SignalData, SignalType
from shared.strategies.base import BaseStrategy
from shared.strategies.registry import StrategyRegistry


class CombineLogic(str, Enum):
    """Logic for combining multiple strategy signals."""

    AND = "AND"  # All strategies must agree
    OR = "OR"  # Any strategy triggers
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
    """

    default_timeframe = "1d"

    def __init__(
        self,
        name: str,
        description: str,
        components: list[StrategyComponent],
        combine_logic: CombineLogic = CombineLogic.AND,
        min_agreement_pct: float = 0.5,
        min_combined_strength: float = 0.5,
        min_combined_confidence: float = 0.5,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        """Initialize composite strategy."""
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
        self._component_instances: list[BaseStrategy] = []
        self._initialized = False

    def _initialize_components(self) -> None:
        """Lazily initialize component strategy instances."""
        if self._initialized:
            return
        for component in self.components:
            strategy = StrategyRegistry.get_strategy(component.strategy_name, component.params)
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
        component_signals: list[tuple[StrategyComponent, list[SignalData]]] = []
        for component, strategy in zip(self.components, self._component_instances, strict=False):
            signals = strategy.generate_signals(df, symbol)
            component_signals.append((component, signals))
        return self._combine_signals(df, symbol, component_signals)

    def _combine_signals(
        self,
        df: pd.DataFrame,
        symbol: str,
        component_signals: list[tuple[StrategyComponent, list[SignalData]]],
    ) -> list[SignalData]:
        """Combine signals from multiple strategies based on combine logic."""
        from ta.volatility import AverageTrueRange

        signals_by_type: dict[SignalType, list[tuple[StrategyComponent, SignalData]]] = {
            SignalType.BUY: [],
            SignalType.SELL: [],
            SignalType.HOLD: [],
        }
        all_indicators: dict[str, Any] = {}

        for component, signals in component_signals:
            if signals:
                signal = signals[0]
                signals_by_type[signal.signal_type].append((component, signal))
                if signal.indicators:
                    prefix = component.strategy_name
                    for key, value in signal.indicators.items():
                        all_indicators[f"{prefix}_{key}"] = value

        current_price = self._to_decimal(df["Close"].iloc[-1])
        if current_price is None:
            return []

        atr = None
        if len(df) >= self.atr_period:
            atr_indicator = AverageTrueRange(
                df["High"], df["Low"], df["Close"], window=self.atr_period
            )
            atr_value = atr_indicator.average_true_range().iloc[-1]
            if not pd.isna(atr_value):
                atr = self._to_decimal(atr_value)

        final_signal_type, strength, confidence, notes = self._determine_signal(
            signals_by_type, len(component_signals)
        )

        if final_signal_type in (SignalType.BUY, SignalType.SELL):
            stop_loss = self.calculate_stop_loss(
                current_price, final_signal_type, atr, self.atr_multiplier
            )
            take_profit = self.calculate_take_profit(
                current_price, stop_loss, final_signal_type, self.risk_reward_ratio
            )
            return [
                SignalData(
                    symbol=symbol,
                    signal_type=final_signal_type,
                    strength=strength,
                    confidence=confidence,
                    price_at_signal=current_price,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=self.risk_reward_ratio,
                    indicators=all_indicators,
                    notes=notes,
                )
            ]
        return [
            SignalData(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                strength=strength,
                confidence=confidence,
                price_at_signal=current_price,
                indicators=all_indicators,
                notes=notes,
            )
        ]

    def _determine_signal(
        self,
        signals_by_type: dict[SignalType, list[tuple[StrategyComponent, SignalData]]],
        total_components: int,
    ) -> tuple[SignalType, Decimal, Decimal, str]:
        """Determine the final signal based on combine logic."""
        buy_signals = signals_by_type[SignalType.BUY]
        sell_signals = signals_by_type[SignalType.SELL]

        if self.combine_logic == CombineLogic.AND:
            return self._combine_and(buy_signals, sell_signals, total_components)
        elif self.combine_logic == CombineLogic.OR:
            return self._combine_or(buy_signals, sell_signals)
        elif self.combine_logic == CombineLogic.MAJORITY:
            return self._combine_majority(buy_signals, sell_signals, total_components)
        else:  # WEIGHTED
            return self._combine_weighted(buy_signals, sell_signals)

    def _combine_and(
        self,
        buy_signals: list[tuple[StrategyComponent, SignalData]],
        sell_signals: list[tuple[StrategyComponent, SignalData]],
        total: int,
    ) -> tuple[SignalType, Decimal, Decimal, str]:
        """AND logic: All strategies must agree."""
        if len(buy_signals) == total:
            strength = self._avg_strength(buy_signals)
            confidence = self._avg_confidence(buy_signals)
            strategies = [c.strategy_name for c, _ in buy_signals]
            return (SignalType.BUY, strength, confidence, f"All agree: BUY ({', '.join(strategies)})")
        if len(sell_signals) == total:
            strength = self._avg_strength(sell_signals)
            confidence = self._avg_confidence(sell_signals)
            strategies = [c.strategy_name for c, _ in sell_signals]
            return (SignalType.SELL, strength, confidence, f"All agree: SELL ({', '.join(strategies)})")
        return SignalType.HOLD, Decimal("0.5"), Decimal("0.5"), "No unanimous agreement"

    def _combine_or(
        self,
        buy_signals: list[tuple[StrategyComponent, SignalData]],
        sell_signals: list[tuple[StrategyComponent, SignalData]],
    ) -> tuple[SignalType, Decimal, Decimal, str]:
        """OR logic: Any strategy trigger is sufficient."""
        if buy_signals and sell_signals:
            buy_strength = self._max_strength(buy_signals)
            sell_strength = self._max_strength(sell_signals)
            if buy_strength >= sell_strength:
                best = max(buy_signals, key=lambda x: float(x[1].strength))
                return (SignalType.BUY, best[1].strength, best[1].confidence, f"BUY from {best[0].strategy_name}")
            else:
                best = max(sell_signals, key=lambda x: float(x[1].strength))
                return (SignalType.SELL, best[1].strength, best[1].confidence, f"SELL from {best[0].strategy_name}")
        elif buy_signals:
            best = max(buy_signals, key=lambda x: float(x[1].strength))
            return (SignalType.BUY, best[1].strength, best[1].confidence, f"BUY from {best[0].strategy_name}")
        elif sell_signals:
            best = max(sell_signals, key=lambda x: float(x[1].strength))
            return (SignalType.SELL, best[1].strength, best[1].confidence, f"SELL from {best[0].strategy_name}")
        return SignalType.HOLD, Decimal("0.5"), Decimal("0.5"), "No signals triggered"

    def _combine_majority(
        self,
        buy_signals: list[tuple[StrategyComponent, SignalData]],
        sell_signals: list[tuple[StrategyComponent, SignalData]],
        total: int,
    ) -> tuple[SignalType, Decimal, Decimal, str]:
        """MAJORITY logic: More than threshold must agree."""
        min_agreement = int(total * self.min_agreement_pct) + 1
        if len(buy_signals) >= min_agreement:
            strength = self._avg_strength(buy_signals)
            confidence = self._avg_confidence(buy_signals) * Decimal(str(len(buy_signals) / total))
            return (SignalType.BUY, strength, confidence, f"Majority BUY ({len(buy_signals)}/{total})")
        if len(sell_signals) >= min_agreement:
            strength = self._avg_strength(sell_signals)
            confidence = self._avg_confidence(sell_signals) * Decimal(str(len(sell_signals) / total))
            return (SignalType.SELL, strength, confidence, f"Majority SELL ({len(sell_signals)}/{total})")
        return (SignalType.HOLD, Decimal("0.5"), Decimal("0.5"), f"No majority (need {min_agreement}/{total})")

    def _combine_weighted(
        self,
        buy_signals: list[tuple[StrategyComponent, SignalData]],
        sell_signals: list[tuple[StrategyComponent, SignalData]],
    ) -> tuple[SignalType, Decimal, Decimal, str]:
        """WEIGHTED logic: Signal based on weighted combination."""
        buy_weight = sum(c.weight * float(s.strength) for c, s in buy_signals)
        sell_weight = sum(c.weight * float(s.strength) for c, s in sell_signals)
        total_weight = buy_weight + sell_weight
        if total_weight == 0:
            return SignalType.HOLD, Decimal("0.5"), Decimal("0.5"), "No weighted signals"
        if buy_weight > sell_weight and buy_weight >= self.min_combined_strength:
            strength = Decimal(str(buy_weight / (buy_weight + sell_weight + 0.001))).quantize(Decimal("0.0001"))
            confidence = self._avg_confidence(buy_signals)
            return (SignalType.BUY, strength, confidence, f"Weighted BUY ({buy_weight:.2f} vs {sell_weight:.2f})")
        elif sell_weight > buy_weight and sell_weight >= self.min_combined_strength:
            strength = Decimal(str(sell_weight / (buy_weight + sell_weight + 0.001))).quantize(Decimal("0.0001"))
            confidence = self._avg_confidence(sell_signals)
            return (SignalType.SELL, strength, confidence, f"Weighted SELL ({sell_weight:.2f} vs {buy_weight:.2f})")
        return SignalType.HOLD, Decimal("0.5"), Decimal("0.5"), "Weighted signals inconclusive"

    def _avg_strength(self, signals: list[tuple[StrategyComponent, SignalData]]) -> Decimal:
        """Calculate average strength from signals."""
        if not signals:
            return Decimal("0.5")
        total = sum(float(s.strength) for _, s in signals)
        return Decimal(str(total / len(signals))).quantize(Decimal("0.0001"))

    def _avg_confidence(self, signals: list[tuple[StrategyComponent, SignalData]]) -> Decimal:
        """Calculate average confidence from signals."""
        if not signals:
            return Decimal("0.5")
        total = sum(float(s.confidence) for _, s in signals)
        return Decimal(str(total / len(signals))).quantize(Decimal("0.0001"))

    def _max_strength(self, signals: list[tuple[StrategyComponent, SignalData]]) -> Decimal:
        """Get maximum strength from signals."""
        if not signals:
            return Decimal("0")
        return max(s.strength for _, s in signals)


class CompositeStrategyFactory:
    """Factory for creating and registering composite strategies."""

    @staticmethod
    def create(
        name: str,
        description: str,
        components: list[dict],
        combine_logic: str = "AND",
        **kwargs,
    ) -> CompositeStrategy:
        """Create a composite strategy from configuration."""
        component_list = []
        for comp in components:
            component_list.append(
                StrategyComponent(
                    strategy_name=comp["strategy"],
                    params=comp.get("params", {}),
                    weight=comp.get("weight", 1.0),
                    required=comp.get("required", False),
                )
            )
        logic = CombineLogic(combine_logic.upper())
        return CompositeStrategy(
            name=name,
            description=description,
            components=component_list,
            combine_logic=logic,
            **kwargs,
        )

    @staticmethod
    def register(strategy: CompositeStrategy) -> CompositeStrategy:
        """Register a composite strategy with the registry."""
        strategy_class = type(
            f"Composite_{strategy.name}",
            (CompositeStrategy,),
            {"name": strategy.name, "description": strategy.description},
        )
        strategy_class._config = {
            "components": strategy.components,
            "combine_logic": strategy.combine_logic,
            "min_agreement_pct": strategy.min_agreement_pct,
            "min_combined_strength": strategy.min_combined_strength,
            "min_combined_confidence": strategy.min_combined_confidence,
            "atr_period": strategy.atr_period,
            "atr_multiplier": strategy.atr_multiplier,
            "risk_reward_ratio": strategy.risk_reward_ratio,
        }

        original_init = CompositeStrategy.__init__

        def new_init(self, **params):
            config = strategy_class._config.copy()
            config.update(params)
            original_init(
                self,
                name=strategy_class.name,
                description=strategy_class.description,
                components=config["components"],
                combine_logic=config["combine_logic"],
                min_agreement_pct=config["min_agreement_pct"],
                min_combined_strength=config["min_combined_strength"],
                min_combined_confidence=config["min_combined_confidence"],
                atr_period=config["atr_period"],
                atr_multiplier=float(config["atr_multiplier"]),
                risk_reward_ratio=float(config["risk_reward_ratio"]),
            )

        strategy_class.__init__ = new_init
        StrategyRegistry.register(strategy_class)
        return strategy

