"""Fyers broker provider implementation.

Provides order execution, position management, and account information
through Fyers API v3 for Indian markets (NSE, BSE).
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from ..schemas import (
    Funds,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    ProductType,
)
from .base import Broker

logger = logging.getLogger(__name__)


class FyersBroker(Broker):
    """Broker using Fyers API v3.

    Supports order placement, modification, cancellation,
    position tracking, and account management for NSE/BSE.

    Note: Requires valid Fyers access token obtained via OAuth flow.
    """

    name = "fyers"
    is_paper = False

    def __init__(
        self,
        access_token: str | None = None,
        client_id: str | None = None,
        log_path: str = "",
    ):
        """Initialize Fyers broker.

        Args:
            access_token: Fyers access token (from OAuth flow)
            client_id: Fyers client/app ID
            log_path: Optional path for Fyers SDK logs
        """
        self.client_id = client_id or ""
        self.access_token = access_token
        self.log_path = log_path
        self._fyers = None
        self._connected = False

    def _get_fyers_client(self):
        """Lazily create Fyers API client."""
        if self._fyers is None:
            if not self.access_token:
                raise ValueError("Fyers access token not configured. Complete OAuth flow first.")
            try:
                from fyers_apiv3 import fyersModel

                self._fyers = fyersModel.FyersModel(
                    token=self.access_token,
                    is_async=False,
                    client_id=self.client_id,
                    log_path=self.log_path,
                )
            except ImportError as e:
                logger.error(f"fyers-apiv3 package not installed: {e}")
                raise ImportError(
                    "fyers-apiv3 package is required. Install with: pip install fyers-apiv3"
                ) from e
        return self._fyers

    def set_access_token(self, access_token: str) -> None:
        """Set access token and reset client."""
        self.access_token = access_token
        self._fyers = None

    async def connect(self) -> bool:
        """Establish connection to Fyers."""
        try:
            fyers = self._get_fyers_client()
            # Verify connection by getting profile
            response = fyers.get_profile()
            if response.get("code") == 200:
                self._connected = True
                logger.info("Fyers broker connected")
                return True
            logger.error(f"Fyers connection failed: {response}")
            return False
        except Exception as e:
            logger.error(f"Fyers connection error: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Fyers."""
        self._connected = False
        self._fyers = None
        logger.info("Fyers broker disconnected")

    async def is_connected(self) -> bool:
        """Check if connected to Fyers."""
        return self._connected and self.access_token is not None

    def normalize_symbol(self, symbol: str) -> str:
        """Convert symbol to Fyers format."""
        symbol = symbol.upper().strip()
        if ":" in symbol:
            return symbol
        return f"NSE:{symbol}-EQ"

    def _map_order_type(self, order_type: OrderType) -> int:
        """Map OrderType to Fyers order type code."""
        mapping = {
            OrderType.MARKET: 2,
            OrderType.LIMIT: 1,
            OrderType.STOP_LOSS: 3,
            OrderType.STOP_LOSS_MARKET: 4,
        }
        return mapping.get(order_type, 2)

    def _map_product_type(self, product_type: ProductType) -> str:
        """Map ProductType to Fyers product type."""
        mapping = {
            ProductType.DELIVERY: "CNC",
            ProductType.CNC: "CNC",
            ProductType.INTRADAY: "INTRADAY",
            ProductType.MIS: "INTRADAY",
            ProductType.MARGIN: "MARGIN",
        }
        return mapping.get(product_type, "CNC")

    def _parse_order_status(self, status: int) -> OrderStatus:
        """Parse Fyers order status to OrderStatus enum."""
        status_map = {
            1: OrderStatus.PENDING,
            2: OrderStatus.FILLED,
            3: OrderStatus.REJECTED,
            4: OrderStatus.CANCELLED,
            5: OrderStatus.PENDING,
            6: OrderStatus.PARTIALLY_FILLED,
        }
        return status_map.get(status, OrderStatus.PENDING)

    async def place_order(
        self,
        user_id: str,
        order: OrderRequest,
    ) -> OrderResponse:
        """Place an order through Fyers.

        Note: user_id is ignored as Fyers uses the authenticated session.
        """
        now = datetime.now(UTC)
        try:
            fyers = self._get_fyers_client()
            fyers_symbol = self.normalize_symbol(order.symbol)

            # Map side to Fyers format (1 = BUY, -1 = SELL)
            side = 1 if order.side == OrderSide.BUY else -1

            order_data = {
                "symbol": fyers_symbol,
                "qty": order.quantity,
                "type": self._map_order_type(order.order_type),
                "side": side,
                "productType": self._map_product_type(order.product_type),
                "limitPrice": float(order.price) if order.price else 0,
                "stopPrice": float(order.trigger_price) if order.trigger_price else 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": False,
            }

            response = fyers.place_order(order_data)

            if response.get("code") != 200:
                error_msg = response.get("message", "Order placement failed")
                logger.error(f"Fyers order error: {response}")
                return OrderResponse(
                    order_id="",
                    status=OrderStatus.REJECTED,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    message=error_msg,
                    placed_at=now,
                )

            order_id = response.get("id", "")
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.OPEN,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                placed_at=now,
            )

        except Exception as e:
            logger.error(f"Error placing Fyers order: {e}")
            return OrderResponse(
                order_id="",
                status=OrderStatus.REJECTED,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                message=str(e),
                placed_at=now,
            )

    async def cancel_order(self, user_id: str, order_id: str) -> bool:
        """Cancel an existing order."""
        try:
            fyers = self._get_fyers_client()
            data = {"id": order_id}
            response = fyers.cancel_order(data)

            if response.get("code") != 200:
                logger.error(f"Fyers cancel order error: {response}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error cancelling Fyers order {order_id}: {e}")
            return False

    async def modify_order(
        self,
        user_id: str,
        order_id: str,
        quantity: int | None = None,
        price: Decimal | None = None,
        trigger_price: Decimal | None = None,
    ) -> OrderResponse:
        """Modify an existing order."""
        try:
            fyers = self._get_fyers_client()

            modify_data = {"id": order_id}
            if quantity is not None:
                modify_data["qty"] = quantity
            if price is not None:
                modify_data["limitPrice"] = float(price)
            if trigger_price is not None:
                modify_data["stopPrice"] = float(trigger_price)

            response = fyers.modify_order(modify_data)

            if response.get("code") != 200:
                logger.error(f"Fyers modify order error: {response}")
                return OrderResponse(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    symbol="",
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    quantity=0,
                    message=response.get("message", "Modify failed"),
                )

            # Fetch updated order details
            order_status = await self.get_order_status(user_id, order_id)
            if order_status:
                return order_status

            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.OPEN,
                symbol="",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=quantity or 0,
                price=price,
            )

        except Exception as e:
            logger.error(f"Error modifying Fyers order {order_id}: {e}")
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                symbol="",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=0,
                message=str(e),
            )

    async def get_order_status(self, user_id: str, order_id: str) -> OrderResponse | None:
        """Get order details by ID."""
        try:
            fyers = self._get_fyers_client()
            response = fyers.orderbook()

            if response.get("code") != 200 or not response.get("orderBook"):
                logger.error(f"Fyers get order error: {response}")
                return None

            # Find the specific order
            for order_data in response["orderBook"]:
                if order_data.get("id") == order_id:
                    return self._parse_order_response(order_data)

            return None

        except Exception as e:
            logger.error(f"Error fetching Fyers order {order_id}: {e}")
            return None

    def _parse_order_response(self, order_data: dict) -> OrderResponse:
        """Parse Fyers order data to OrderResponse object."""
        side = OrderSide.BUY if order_data.get("side") == 1 else OrderSide.SELL
        order_type_map = {
            1: OrderType.LIMIT,
            2: OrderType.MARKET,
            3: OrderType.STOP_LOSS,
            4: OrderType.STOP_LOSS_MARKET,
        }
        order_type = order_type_map.get(order_data.get("type", 2), OrderType.MARKET)
        symbol = order_data.get("symbol", "").split(":")[-1].split("-")[0]

        return OrderResponse(
            order_id=order_data.get("id", ""),
            status=self._parse_order_status(order_data.get("status", 1)),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=order_data.get("qty", 0),
            filled_quantity=order_data.get("filledQty", 0),
            price=Decimal(str(order_data.get("limitPrice", 0))) or None,
            filled_price=Decimal(str(order_data.get("tradedPrice", 0))) or None,
        )

    async def get_positions(self, user_id: str) -> list[Position]:
        """Get all open positions."""
        try:
            fyers = self._get_fyers_client()
            response = fyers.positions()

            if response.get("code") != 200:
                logger.error(f"Fyers positions error: {response}")
                return []

            positions = []
            for pos_data in response.get("netPositions", []):
                symbol = pos_data.get("symbol", "").split(":")[-1].split("-")[0]
                qty = pos_data.get("netQty", 0)
                if qty == 0:
                    continue

                avg_price = Decimal(str(pos_data.get("avgPrice", 0)))
                current_price = Decimal(str(pos_data.get("ltp", 0)))
                unrealized_pnl = Decimal(str(pos_data.get("unrealizedProfit", 0)))

                positions.append(
                    Position(
                        symbol=symbol,
                        quantity=Decimal(str(abs(qty))),
                        avg_cost=avg_price,
                        current_price=current_price,
                        unrealized_pnl=unrealized_pnl,
                        realized_pnl=Decimal(str(pos_data.get("realizedProfit", 0))),
                    )
                )

            return positions

        except Exception as e:
            logger.error(f"Error fetching Fyers positions: {e}")
            return []

    async def get_funds(self, user_id: str) -> Funds:
        """Get account funds/balance."""
        try:
            fyers = self._get_fyers_client()
            response = fyers.funds()

            if response.get("code") != 200:
                logger.error(f"Fyers funds error: {response}")
                return Funds(
                    available_cash=Decimal("0"),
                    used_margin=Decimal("0"),
                    total_balance=Decimal("0"),
                )

            fund_data = response.get("fund_limit", [{}])[0]

            available = Decimal(str(fund_data.get("availableMargin", 0)))
            used = Decimal(str(fund_data.get("utilizedMargin", 0)))
            total = Decimal(str(fund_data.get("equityAmount", 0)))

            return Funds(
                available_cash=available,
                used_margin=used,
                total_balance=total,
            )

        except Exception as e:
            logger.error(f"Error fetching Fyers funds: {e}")
            return Funds(
                available_cash=Decimal("0"),
                used_margin=Decimal("0"),
                total_balance=Decimal("0"),
            )

    async def get_holdings(self, user_id: str) -> list[Position]:
        """Get all holdings (delivery positions)."""
        try:
            fyers = self._get_fyers_client()
            response = fyers.holdings()

            if response.get("code") != 200:
                logger.error(f"Fyers holdings error: {response}")
                return []

            holdings = []
            for holding_data in response.get("holdings", []):
                symbol = holding_data.get("symbol", "").split(":")[-1].split("-")[0]
                qty = holding_data.get("quantity", 0)
                if qty == 0:
                    continue

                avg_cost = Decimal(str(holding_data.get("costPrice", 0)))
                current_price = Decimal(str(holding_data.get("ltp", 0)))
                pnl = Decimal(str(holding_data.get("pl", 0)))

                holdings.append(
                    Position(
                        symbol=symbol,
                        quantity=Decimal(str(qty)),
                        avg_cost=avg_cost,
                        current_price=current_price,
                        unrealized_pnl=pnl,
                        realized_pnl=Decimal("0"),
                    )
                )

            return holdings

        except Exception as e:
            logger.error(f"Error fetching Fyers holdings: {e}")
            return []
