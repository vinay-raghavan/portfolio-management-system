"""Broker provider abstraction layer.

This module re-exports from the shared package for backward compatibility.
"""

from shared.providers.broker import Broker, BrokerFactory, PaperBroker, get_broker

__all__ = [
    "Broker",
    "PaperBroker",
    "BrokerFactory",
    "get_broker",
]
