"""Broker integration module for live trading.

This module provides:
1. Broker abstraction layer (re-exported from providers)
2. API routes for broker OAuth integration
3. Database models for encrypted credential storage
"""

from app.providers.broker import Broker, BrokerFactory, PaperBroker, get_broker

from .models import BrokerCredential, BrokerType
from .router import router
from .service import BrokerService

# Legacy alias for backward compatibility
BrokerInterface = Broker

__all__ = [
    "Broker",
    "BrokerCredential",
    "BrokerInterface",  # Legacy alias
    "BrokerFactory",
    "BrokerService",
    "BrokerType",
    "get_broker",
    "PaperBroker",
    "router",
]
