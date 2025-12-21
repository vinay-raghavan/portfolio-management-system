# Indian Trading APIs Documentation

This document provides an overview of Indian broker APIs for integrating live trading capabilities into the portfolio management system.

## Quick Comparison - API Features

| Broker | API Name | API Cost | Python SDK | WebSocket | F&O Support |
|--------|----------|----------|------------|-----------|-------------|
| **Zerodha** | Kite Connect | ₹2,000/month | ✅ pykiteconnect | ✅ | ✅ |
| **Upstox** | Upstox API v2 | Free | ✅ upstox-python-sdk | ✅ | ✅ |
| **Groww** | Groww Trade API | ₹499/month | ✅ groww-api | ✅ | ✅ |
| **Angel One** | SmartAPI | Free | ✅ smartapi-python | ✅ | ✅ |
| **5paisa** | Xstream API | Free | ✅ py5paisa | ✅ | ✅ |
| **Fyers** | Fyers API v3 | Free | ✅ fyers-apiv3 | ✅ | ✅ |
| **Dhan** | DhanHQ API | Free | ✅ dhanhq | ✅ | ✅ |
| **ICICI Direct** | Breeze API | Free | ✅ breeze-connect | ✅ | ✅ |

---

## Account & Brokerage Charges (2025)

| Broker | Account Opening | Demat AMC | Equity Delivery | Intraday/F&O | Options |
|--------|-----------------|-----------|-----------------|--------------|---------|
| **Zerodha** | Free | ₹300/year | **Free** | ₹20/order | ₹20/order |
| **Upstox** | Free | ₹0-₹150/year* | **Free** | ₹20/order | ₹20/order |
| **Groww** | Free | **Free** | ₹20/order or 0.05% | ₹20/order | ₹20/order |
| **Angel One** | Free | **Free** | **Free** | ₹20/order | ₹20/order |
| **5paisa** | Free | ₹0** | ₹20/order | ₹20/order | ₹20/order |
| **Fyers** | Free | ₹0*** | **Free** | ₹20/order | ₹20/order |
| **Dhan** | Free | **Free** | **Free** | ₹20/order | ₹20/order |
| **ICICI Direct** | Free | ₹0-₹750**** | 0.55% | 0.05% | ₹20/lot |

### Notes:
- \* Upstox: AMC varies based on account type (BSDA may have lower/no AMC)
- \*\* 5paisa: Zero AMC for BSDA accounts; regular accounts may have charges
- \*\*\* Fyers: Recently introduced AMC for some accounts (check current policy)
- \*\*\*\* ICICI Direct: AMC waived with Prime plans or minimum trading

### Other Common Charges (All Brokers)

| Charge Type | Typical Amount | Description |
|-------------|----------------|-------------|
| **STT (Securities Transaction Tax)** | 0.1% (delivery), 0.025% (intraday) | Government tax on transactions |
| **Exchange Transaction Charges** | 0.00345% (NSE), 0.00345% (BSE) | Exchange fees |
| **SEBI Turnover Fees** | ₹10 per crore | Regulatory fee |
| **GST** | 18% on brokerage | Tax on brokerage + transaction charges |
| **Stamp Duty** | 0.015% (buy side) | State government tax |
| **DP Charges** | ₹13-18 per scrip | Charged when selling from demat |

---

## Total Cost Comparison (for Algo Trading)

### Best for Budget-Conscious Algo Traders:
| Priority | Broker | Monthly Cost | Why? |
|----------|--------|--------------|------|
| 1️⃣ | **Dhan** | ₹0 | Free API, Free AMC, Free delivery |
| 2️⃣ | **Angel One** | ₹0 | Free API, Free AMC, Free delivery |
| 3️⃣ | **Fyers** | ₹0 | Free API, Free delivery |
| 4️⃣ | **Upstox** | ₹0-150/year | Free API, minimal AMC |
| 5️⃣ | **5paisa** | ₹0-300/year | Free API |

### Best for Serious/Professional Algo Traders:
| Priority | Broker | Monthly Cost | Why? |
|----------|--------|--------------|------|
| 1️⃣ | **Zerodha** | ₹2,000 | Best reliability, documentation, community |
| 2️⃣ | **Dhan** | ₹0 | Fast execution, modern API |
| 3️⃣ | **Angel One** | ₹0 | Good balance of free + features |

---

## 1. Zerodha Kite Connect

**Best for**: Most reliable, extensive documentation, industry standard

### Installation
```bash
pip install kiteconnect
```

### Authentication
```python
from kiteconnect import KiteConnect

kite = KiteConnect(api_key="your_api_key")

# Step 1: Get login URL
login_url = kite.login_url()  # Redirect user here

# Step 2: After login, exchange request_token for access_token
data = kite.generate_session("request_token", api_secret="your_api_secret")
kite.set_access_token(data["access_token"])
```

### Place Order
```python
order_id = kite.place_order(
    variety=kite.VARIETY_REGULAR,
    exchange=kite.EXCHANGE_NSE,
    tradingsymbol="RELIANCE",
    transaction_type=kite.TRANSACTION_TYPE_BUY,
    quantity=1,
    product=kite.PRODUCT_CNC,
    order_type=kite.ORDER_TYPE_MARKET
)
```

### WebSocket Streaming
```python
from kiteconnect import KiteTicker

kws = KiteTicker("api_key", "access_token")

def on_ticks(ws, ticks):
    print("Ticks:", ticks)

kws.on_ticks = on_ticks
kws.connect()
```

**Docs**: https://kite.trade/docs/connect/v3/

---

## 2. Upstox API v2

**Best for**: Free API, good documentation

### Installation
```bash
pip install upstox-python-sdk
```

### Authentication (OAuth2)
```python
import upstox_client

configuration = upstox_client.Configuration()
configuration.access_token = 'your_access_token'

api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
```

### Place Order
```python
body = upstox_client.PlaceOrderRequest(
    quantity=1,
    product="D",  # D=Delivery, I=Intraday
    validity="DAY",
    price=0,
    instrument_token="NSE_EQ|INE002A01018",  # Reliance
    order_type="MARKET",
    transaction_type="BUY",
    disclosed_quantity=0,
    trigger_price=0,
    is_amo=False
)
response = api_instance.place_order(body)
```

**Docs**: https://upstox.com/developer/api-documentation/

---

## 3. Angel One SmartAPI

**Best for**: Free, beginner-friendly

### Installation
```bash
pip install smartapi-python
```

### Authentication
```python
from SmartApi import SmartConnect

obj = SmartConnect(api_key="your_api_key")
data = obj.generateSession("client_id", "password", "totp")
auth_token = data['data']['jwtToken']
```

### Place Order
```python
order_params = {
    "variety": "NORMAL",
    "tradingsymbol": "RELIANCE-EQ",
    "symboltoken": "2885",
    "transactiontype": "BUY",
    "exchange": "NSE",
    "ordertype": "MARKET",
    "producttype": "DELIVERY",
    "duration": "DAY",
    "quantity": "1"
}
order_id = obj.placeOrder(order_params)
```

**Docs**: https://smartapi.angelbroking.com/docs

---

## 4. Groww Trade API

**Best for**: Retail-friendly, affordable

### Installation
```bash
pip install groww-api
```

### Authentication
```python
from groww_api import GrowwApi

api = GrowwApi(api_key="your_api_key", api_secret="your_api_secret")
api.generate_session(request_token="request_token")
```

### Place Order
```python
order = api.place_order(
    trading_symbol="RELIANCE",
    exchange="NSE",
    transaction_type="BUY",
    order_type="MARKET",
    quantity=1,
    product="CNC"
)
```

**Docs**: https://groww.in/trade-api/docs/python-sdk

---

## 5. Fyers API v3

**Best for**: Good for options trading

### Installation
```bash
pip install fyers-apiv3
```

### Authentication
```python
from fyers_apiv3 import fyersModel

client_id = "your_app_id"
secret_key = "your_secret_key"
redirect_uri = "your_redirect_uri"

session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    response_type="code",
    grant_type="authorization_code"
)
auth_url = session.generate_authcode()
```

**Docs**: https://myapi.fyers.in/docsv3

---

## 6. Dhan HQ API

**Best for**: Fast execution, modern API design

### Installation
```bash
pip install dhanhq
```

### Authentication
```python
from dhanhq import dhanhq

dhan = dhanhq("client_id", "access_token")
```

### Place Order
```python
order = dhan.place_order(
    security_id='1333',  # HDFC Bank
    exchange_segment=dhan.NSE,
    transaction_type=dhan.BUY,
    quantity=1,
    order_type=dhan.MARKET,
    product_type=dhan.CNC,
    price=0
)
```

**Docs**: https://dhanhq.co/docs/v2/

---

## 7. 5paisa Xstream API

**Best for**: Low brokerage, institutional-grade

### Installation
```bash
pip install py5paisa
```

### Authentication
```python
from py5paisa import FivePaisaClient

cred = {
    "APP_NAME": "your_app_name",
    "APP_SOURCE": "your_app_source",
    "USER_ID": "your_user_id",
    "PASSWORD": "your_password",
    "USER_KEY": "your_user_key",
    "ENCRYPTION_KEY": "your_encryption_key"
}
client = FivePaisaClient(cred=cred)
client.get_access_token()
```

**Docs**: https://xstream.5paisa.com/dev-docs

---

## 8. ICICI Direct Breeze API

**Best for**: Bank-backed, trusted platform

### Installation
```bash
pip install breeze-connect
```

### Authentication
```python
from breeze_connect import BreezeConnect

breeze = BreezeConnect(api_key="your_api_key")
breeze.generate_session(api_secret="your_api_secret", session_token="your_session_token")
```

### Place Order
```python
order = breeze.place_order(
    stock_code="RELIANCE",
    exchange_code="NSE",
    product="cash",
    action="buy",
    order_type="market",
    quantity="1",
    validity="day"
)
```

**Docs**: https://api.icicidirect.com/breezeapi/documents/

---

## Integration Architecture

### Unified Broker Interface

To support multiple brokers, implement a common interface:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"

class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"

class ProductType(Enum):
    CNC = "CNC"      # Delivery
    MIS = "MIS"      # Intraday
    NRML = "NRML"    # F&O Normal

class BrokerInterface(ABC):
    """Abstract base class for all broker integrations"""

    @abstractmethod
    def connect(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with broker"""
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        exchange: str,
        transaction_type: TransactionType,
        quantity: int,
        order_type: OrderType,
        product_type: ProductType,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Place an order"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        pass

    @abstractmethod
    def get_positions(self) -> list:
        """Get current positions"""
        pass

    @abstractmethod
    def get_holdings(self) -> list:
        """Get holdings/portfolio"""
        pass

    @abstractmethod
    def get_order_history(self, order_id: str) -> Dict[str, Any]:
        """Get order status and history"""
        pass

    @abstractmethod
    def get_quote(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get live quote for a symbol"""
        pass
```

### Implementation Example (Zerodha)

```python
class ZerodhaBroker(BrokerInterface):
    def __init__(self):
        self.kite = None

    def connect(self, credentials: Dict[str, str]) -> bool:
        from kiteconnect import KiteConnect
        self.kite = KiteConnect(api_key=credentials['api_key'])
        data = self.kite.generate_session(
            credentials['request_token'],
            api_secret=credentials['api_secret']
        )
        self.kite.set_access_token(data['access_token'])
        return True

    def place_order(self, symbol, exchange, transaction_type, quantity,
                    order_type, product_type, price=None, trigger_price=None):
        return self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=symbol,
            transaction_type=transaction_type.value,
            quantity=quantity,
            product=product_type.value,
            order_type=order_type.value,
            price=price,
            trigger_price=trigger_price
        )
    # ... implement other methods
```

### Broker Factory

```python
class BrokerFactory:
    """Factory to create broker instances"""

    _brokers = {
        'zerodha': ZerodhaBroker,
        'upstox': UpstoxBroker,
        'angelone': AngelOneBroker,
        'groww': GrowwBroker,
        'fyers': FyersBroker,
        'dhan': DhanBroker,
        '5paisa': FivePaisaBroker,
        'icici': ICICIBroker,
    }

    @classmethod
    def get_broker(cls, broker_name: str) -> BrokerInterface:
        broker_class = cls._brokers.get(broker_name.lower())
        if not broker_class:
            raise ValueError(f"Unsupported broker: {broker_name}")
        return broker_class()
```

---

## Environment Configuration

Store credentials securely in `.env`:

```env
# Zerodha
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret

# Angel One
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_ID=your_client_id
ANGEL_PASSWORD=your_password
ANGEL_TOTP_SECRET=your_totp_secret

# Upstox
UPSTOX_API_KEY=your_api_key
UPSTOX_API_SECRET=your_api_secret

# Add other brokers as needed
```

---

## Recommended Setup for This Project

1. **Primary Broker**: Zerodha (most reliable, best docs)
2. **Backup/Free Option**: Angel One SmartAPI or Dhan
3. **Paper Trading**: Use sandbox/test credentials

### Installation Commands
```bash
# Install all broker SDKs
pip install kiteconnect smartapi-python upstox-python-sdk dhanhq fyers-apiv3 py5paisa breeze-connect groww-api

# Or add to requirements.txt
```

---

## Important Notes

1. **TOTP Authentication**: Most brokers require TOTP for automated login. Use `pyotp` library.
2. **Rate Limits**: Respect API rate limits (typically 3-10 requests/second)
3. **Market Hours**: NSE/BSE trading hours: 9:15 AM - 3:30 PM IST
4. **Testing**: Always test with small quantities first
5. **Regulatory**: Ensure compliance with SEBI regulations for algo trading

