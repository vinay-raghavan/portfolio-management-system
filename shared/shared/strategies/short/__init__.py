"""Short selling strategies.

These strategies generate SELL signals with OPEN_SHORT intent,
designed for use with INTRADAY or SLB product types.
"""

from shared.strategies.short.momentum_short import MomentumShortStrategy

__all__ = ["MomentumShortStrategy"]
