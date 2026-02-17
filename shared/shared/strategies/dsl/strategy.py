"""DSLStrategy class implementing BaseStrategy for DSL-based strategies.

This module provides the DSLStrategy class that evaluates DSL rules
against market data to generate trading signals.
"""

from decimal import Decimal

import pandas as pd

from shared.models.signals import SignalData, SignalType
from shared.strategies.base import BaseStrategy
from shared.strategies.dsl.executor import DSLExecutionError, DSLExecutor
from shared.strategies.dsl.parser import parse_condition
from shared.strategies.dsl.schemas import DSLAction, DSLStrategyDefinition
from shared.strategies.dsl.validator import validate_dsl_strategy


class DSLStrategy(BaseStrategy):
    """Strategy that executes DSL-defined rules.

    This strategy takes a DSL definition (YAML/JSON structure) and
    evaluates the rules against market data to generate signals.
    """

    name = "dsl"
    description = "Custom DSL-based strategy"
    default_timeframe = "1d"

    def __init__(self, definition: DSLStrategyDefinition):
        """Initialize with a DSL strategy definition.

        Args:
            definition: Validated DSL strategy definition
        """
        self.definition = definition
        self.name = f"dsl_{definition.name.lower().replace(' ', '_')}"
        self.description = definition.description or f"DSL Strategy: {definition.name}"
        self.default_timeframe = definition.timeframe

        # Pre-parse all conditions for efficiency
        self._entry_conditions = [
            (rule, parse_condition(rule.condition)) for rule in definition.rules.entry
        ]
        self._filter_conditions = [parse_condition(f) for f in definition.rules.filters]

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate signals from DSL rules.

        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol

        Returns:
            List of SignalData objects
        """
        if len(df) < 2:
            return []

        try:
            executor = DSLExecutor(df)

            # Check filters first - all must pass
            for filter_ast in self._filter_conditions:
                if not executor.evaluate(filter_ast):
                    return []

            # Evaluate entry rules
            signals = []
            for rule, condition_ast in self._entry_conditions:
                try:
                    if executor.evaluate(condition_ast):
                        signal = self._create_signal(executor, symbol, rule)
                        if signal:
                            signals.append(signal)
                except DSLExecutionError:
                    # Skip rule if execution fails
                    continue

            return signals

        except DSLExecutionError:
            return []

    def _create_signal(self, executor: DSLExecutor, symbol: str, rule) -> SignalData | None:
        """Create a signal from a matched rule."""
        current_price = executor.get_current_price()

        # Determine signal type
        if rule.action == DSLAction.BUY:
            signal_type = SignalType.BUY
        elif rule.action == DSLAction.SELL:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        # Calculate stop loss and take profit from exit config
        exit_config = self.definition.rules.exit
        stop_loss_pct = Decimal(str(exit_config.stop_loss_pct)) / 100
        take_profit_pct = Decimal(str(exit_config.take_profit_pct)) / 100

        if signal_type == SignalType.BUY:
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        elif signal_type == SignalType.SELL:
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)
        else:
            stop_loss = None
            take_profit = None

        # Calculate risk/reward ratio
        risk_reward = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else Decimal("2.0")

        return SignalData(
            symbol=symbol,
            signal_type=signal_type,
            strength=Decimal(str(rule.strength)),
            confidence=Decimal(str(rule.confidence)),
            price_at_signal=current_price,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward,
            indicators={"dsl_rule": rule.condition[:50]},
            notes=f"DSL rule matched: {rule.condition[:100]}",
        )

    def get_parameters(self) -> dict:
        """Return the strategy's parameters."""
        return {
            "name": self.definition.name,
            "version": self.definition.version,
            "timeframe": self.definition.timeframe,
            "entry_rules_count": len(self.definition.rules.entry),
            "filters_count": len(self.definition.rules.filters),
            "stop_loss_pct": self.definition.rules.exit.stop_loss_pct,
            "take_profit_pct": self.definition.rules.exit.take_profit_pct,
        }


def create_dsl_strategy(definition_dict: dict) -> DSLStrategy:
    """Create a DSLStrategy from a dictionary definition.

    Args:
        definition_dict: Dictionary with DSL strategy definition

    Returns:
        Configured DSLStrategy instance

    Raises:
        ValueError: If validation fails
    """
    definition = DSLStrategyDefinition(**definition_dict)
    result = validate_dsl_strategy(definition)

    if not result.valid:
        error_msgs = [e.message for e in result.errors]
        raise ValueError(f"Invalid DSL strategy: {'; '.join(error_msgs)}")

    return DSLStrategy(definition)
