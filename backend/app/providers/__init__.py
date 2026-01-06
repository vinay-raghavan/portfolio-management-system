"""Provider abstraction layer for data, broker, and notifications.

This module re-exports providers from the shared package for backward compatibility.
New code should import directly from shared.providers.
"""

# Re-export from shared package
from shared.providers import (
    OHLCV,
    Broker,
    BrokerFactory,
    DataProvider,
    DataProviderFactory,
    Exchange,
    Funds,
    InstrumentInfo,
    MarketSession,
    NSEDataProvider,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperBroker,
    Position,
    ProductType,
    Quote,
    SearchResult,
    Segment,
    Symbol,
    SymbolMapper,
    YahooDataProvider,
    get_broker,
    get_data_provider,
)

# Notification providers are local to backend (not shared)
from app.providers.notification.factory import NotificationProviderFactory

__all__ = [
    # Broker
    "Broker",
    "BrokerFactory",
    "get_broker",
    "PaperBroker",
    # Data
    "DataProvider",
    "DataProviderFactory",
    "get_data_provider",
    "YahooDataProvider",
    "NSEDataProvider",
    # Schemas
    "Funds",
    "InstrumentInfo",
    "MarketSession",
    "OHLCV",
    "OrderRequest",
    "OrderResponse",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "Position",
    "ProductType",
    "Quote",
    "SearchResult",
    # Symbols
    "Exchange",
    "Segment",
    "Symbol",
    "SymbolMapper",
    # Notifications (backend-only)
    "NotificationProviderFactory",
]
