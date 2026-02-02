"""Strategy registry for dynamic strategy loading and management."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


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
            params: Optional parameters to pass to the strategy

        Returns:
            Strategy instance or None if not found
        """
        strategy_class = cls._strategies.get(name)
        if strategy_class:
            if params:
                return strategy_class(**params)
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
