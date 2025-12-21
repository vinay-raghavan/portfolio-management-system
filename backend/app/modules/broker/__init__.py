"""Broker integration module for live trading.

This module re-exports the broker abstraction from the providers layer.
Use app.providers.broker for direct access to broker functionality.
"""

from app.providers.broker.base import Broker
from app.providers.broker.factory import BrokerFactory, get_broker
from app.providers.broker.paper import PaperBroker

# Legacy alias for backward compatibility
BrokerInterface = Broker

__all__ = [
    "Broker",
    "BrokerInterface",  # Legacy alias
    "BrokerFactory",
    "get_broker",
    "PaperBroker",
]

