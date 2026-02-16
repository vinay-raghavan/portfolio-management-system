"""Strategy registry for dynamic strategy loading and management."""

import inspect
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)

# Metadata keys that are stored alongside strategy params but shouldn't be passed to __init__
METADATA_KEYS = {
    "source",
    "filters_used",
    "product_type",
    "inferred_params",
    "initial_symbols",
}


class StrategyRegistry:
    """Registry for managing available trading strategies.

    Provides a centralized way to register, retrieve, and list strategies.
    Strategies are registered by name and can be instantiated on demand.
    """

    _strategies: dict[str, type["BaseStrategy"]] = {}

    @classmethod
    def register(cls, strategy_class: type["BaseStrategy"]) -> type["BaseStrategy"]:
        """Register a strategy class.

        Can be used as a decorator:
            @StrategyRegistry.register
            class MyStrategy(BaseStrategy):
                ...

        Args:
            strategy_class: Strategy class to register

        Returns:
            The same strategy class (for decorator usage)
        """
        name = strategy_class.name
        if name in cls._strategies:
            logger.warning(f"Strategy '{name}' is being overwritten in registry")
        cls._strategies[name] = strategy_class
        logger.info(f"Registered strategy: {name}")
        return strategy_class

    @classmethod
    def get(cls, name: str) -> "BaseStrategy | None":
        """Get a strategy instance by name.

        Args:
            name: Strategy name

        Returns:
            Strategy instance or None if not found
        """
        strategy_class = cls._strategies.get(name)
        if strategy_class:
            return strategy_class()
        return None

    @classmethod
    def get_strategy(cls, name: str, params: dict | None = None) -> "BaseStrategy | None":
        """Get a strategy instance by name with optional parameters.

        Args:
            name: Strategy name
            params: Optional parameters to pass to the strategy (may contain metadata keys
                   like 'source', 'filters_used', 'inferred_params' that will be filtered out)

        Returns:
            Strategy instance or None if not found
        """
        strategy_class = cls._strategies.get(name)
        if strategy_class:
            if params:
                # Extract inferred_params if present (these are the actual strategy params)
                inferred = params.get("inferred_params", {})

                # Filter out metadata keys and merge with inferred params
                filtered_params = {k: v for k, v in params.items() if k not in METADATA_KEYS}

                # Inferred params take precedence (they're the ones extracted for the strategy)
                if inferred:
                    filtered_params.update(inferred)

                # Get valid parameter names from the strategy class __init__
                sig = inspect.signature(strategy_class.__init__)
                valid_params = set(sig.parameters.keys()) - {"self"}

                # Only pass parameters that the strategy accepts
                final_params = {k: v for k, v in filtered_params.items() if k in valid_params}

                logger.debug(
                    f"Creating strategy '{name}' with params: {final_params} "
                    f"(filtered from {params})"
                )

                return strategy_class(**final_params)
            return strategy_class()
        return None

    @classmethod
    def get_class(cls, name: str) -> type["BaseStrategy"] | None:
        """Get a strategy class by name.

        Args:
            name: Strategy name

        Returns:
            Strategy class or None if not found
        """
        return cls._strategies.get(name)

    @classmethod
    def list_strategies(cls) -> list[dict]:
        """List all registered strategies with their info.

        Returns:
            List of strategy info dictionaries
        """
        strategies = []
        for name, strategy_class in cls._strategies.items():
            instance = strategy_class()
            strategies.append(
                {
                    "name": name,
                    "description": strategy_class.description,
                    "default_timeframe": strategy_class.default_timeframe,
                    "parameters": instance.get_parameters(),
                }
            )
        return strategies

    @classmethod
    def get_all(cls) -> list["BaseStrategy"]:
        """Get instances of all registered strategies.

        Returns:
            List of strategy instances
        """
        return [strategy_class() for strategy_class in cls._strategies.values()]

    @classmethod
    def get_names(cls) -> list[str]:
        """Get names of all registered strategies.

        Returns:
            List of strategy names
        """
        return list(cls._strategies.keys())

    @classmethod
    def has_strategy(cls, name: str) -> bool:
        """Check if a strategy with the given name is registered.

        Args:
            name: Strategy name to check

        Returns:
            True if strategy exists, False otherwise
        """
        return name in cls._strategies

    @classmethod
    def clear(cls) -> None:
        """Clear all registered strategies. Mainly for testing."""
        cls._strategies.clear()

    @classmethod
    def get_parameter_schema(cls, name: str) -> list[dict] | None:
        """Get parameter schema for a strategy.

        Returns a list of parameter definitions with types, defaults, and constraints.

        Args:
            name: Strategy name

        Returns:
            List of parameter schema dicts or None if strategy not found
        """
        strategy_class = cls._strategies.get(name)
        if not strategy_class:
            return None

        # Get the __init__ signature
        sig = inspect.signature(strategy_class.__init__)
        params = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Determine type from annotation or default value
            param_type = "float"  # default
            default_value = None
            min_value = None
            max_value = None

            if param.default is not inspect.Parameter.empty:
                default_value = param.default
                if isinstance(default_value, bool):
                    param_type = "bool"
                elif isinstance(default_value, int):
                    param_type = "int"
                elif isinstance(default_value, float):
                    param_type = "float"
                elif isinstance(default_value, str):
                    param_type = "str"

            # Set reasonable bounds based on common parameter patterns
            if param_type == "int":
                if "period" in param_name.lower():
                    min_value, max_value = 2, 200
                elif "threshold" in param_name.lower():
                    min_value, max_value = 0, 100
                else:
                    min_value, max_value = 1, 1000
            elif param_type == "float":
                if "multiplier" in param_name.lower():
                    min_value, max_value = 0.1, 10.0
                elif "ratio" in param_name.lower():
                    min_value, max_value = 0.5, 10.0
                elif "percent" in param_name.lower() or "pct" in param_name.lower():
                    min_value, max_value = 0.0, 100.0
                else:
                    min_value, max_value = 0.0, 100.0

            # Generate description from parameter name
            description = param_name.replace("_", " ").title()

            params.append(
                {
                    "name": param_name,
                    "type": param_type,
                    "default": default_value,
                    "min_value": min_value,
                    "max_value": max_value,
                    "options": None,
                    "description": description,
                }
            )

        return params
