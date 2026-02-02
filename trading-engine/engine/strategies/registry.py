"""Strategy registry for dynamic strategy loading and management.

This module re-exports the StrategyRegistry from the shared package.
"""

from shared.strategies.registry import StrategyRegistry

__all__ = ["StrategyRegistry"]
