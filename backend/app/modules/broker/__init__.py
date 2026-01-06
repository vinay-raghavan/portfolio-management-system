"""Broker integration module for live trading.

This module re-exports the broker abstraction from the providers layer.
Use app.providers.broker for direct access to broker functionality.
"""

from app.providers.broker import Broker, BrokerFactory, PaperBroker, get_broker

# Legacy alias for backward compatibility
BrokerInterface = Broker

__all__ = [
    "Broker",
    "BrokerInterface",  # Legacy alias
    "BrokerFactory",
    "get_broker",
    "PaperBroker",
]
