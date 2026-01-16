"""Broker providers for order execution.

This module provides abstract and concrete broker implementations
for executing trades across different brokers.
"""

from .base import Broker
from .factory import (
    BrokerFactory,
    get_broker,
    set_config_getter,
    set_default_broker_type,
)
from .funds_provider import FundsProvider
from .fyers import FyersBroker
from .fyers_auth import FyersAuthHandler, FyersCredentials, create_auth_handler_from_env
from .paper import PaperBroker, set_initial_balance

# Register Fyers broker
BrokerFactory.register("fyers", FyersBroker)

__all__ = [
    "Broker",
    "BrokerFactory",
    "FundsProvider",
    "FyersAuthHandler",
    "FyersBroker",
    "FyersCredentials",
    "PaperBroker",
    "create_auth_handler_from_env",
    "get_broker",
    "set_config_getter",
    "set_default_broker_type",
    "set_initial_balance",
]
