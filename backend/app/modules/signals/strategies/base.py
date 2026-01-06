"""Base strategy abstract class for signal generation.

This module re-exports the BaseStrategy and SignalData from the shared package.
"""

from shared.models.signals import SignalData
from shared.strategies.base import BaseStrategy

__all__ = ["BaseStrategy", "SignalData"]
