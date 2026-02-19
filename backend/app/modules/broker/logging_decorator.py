"""Decorator for automatically logging broker API calls.

Use @log_broker_api to wrap broker methods for automatic logging.
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


def log_broker_api(
    action: str,
    broker_type: str | None = None,
    endpoint: str | None = None,
    method: str = "POST",
) -> Callable:
    """Decorator to automatically log broker API calls.

    Args:
        action: The action being performed (e.g., "place_order", "cancel_order")
        broker_type: Override broker type (defaults to self.broker_type if available)
        endpoint: Override endpoint (defaults to action name)
        method: HTTP method (default: POST)

    Usage:
        @log_broker_api(action="place_order")
        async def place_order(self, user_id: str, order: OrderRequest) -> OrderResponse:
            ...

    The decorated method's class must have:
        - self.db: AsyncSession (for database access)
        - self.broker_type: str (optional, can be overridden by decorator arg)

    The decorated method's first positional argument (after self) must be user_id.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self: Any, user_id: str, *args: Any, **kwargs: Any) -> Any:
            # Import here to avoid circular imports
            from app.modules.broker.logging_service import BrokerLoggingService

            # Get db session from self
            db: AsyncSession = getattr(self, "db", None)
            if db is None:
                # No db session, just call the function without logging
                return await func(self, user_id, *args, **kwargs)

            # Determine broker type
            _broker_type = broker_type or getattr(self, "broker_type", "unknown")
            _endpoint = endpoint or action

            # Create logging service
            logging_service = BrokerLoggingService(db)

            # Prepare request data (safe subset of kwargs)
            request_data = {
                k: v
                for k, v in kwargs.items()
                if isinstance(v, (str, int, float, bool, dict, list))
            }

            # Extract reference info if available
            reference_type = kwargs.get("reference_type")
            reference_id = kwargs.get("reference_id")

            # Log the request
            log_entry = await logging_service.log_request(
                user_id=user_id,
                broker_type=_broker_type,
                endpoint=_endpoint,
                method=method,
                action=action,
                request_data=request_data if request_data else None,
                reference_type=reference_type,
                reference_id=reference_id,
            )

            # Execute the function and measure time
            start_time = time.perf_counter()
            error_message = None
            is_success = False
            response_data = None
            status_code = None

            try:
                result = await func(self, user_id, *args, **kwargs)
                is_success = True

                # Try to extract response data
                if isinstance(result, dict):
                    response_data = result
                    status_code = result.get("code") or result.get("status_code")
                elif hasattr(result, "model_dump"):
                    response_data = result.model_dump()
                elif hasattr(result, "__dict__"):
                    response_data = {
                        k: v
                        for k, v in result.__dict__.items()
                        if isinstance(v, (str, int, float, bool, dict, list))
                    }

                return result

            except Exception as e:
                is_success = False
                error_message = str(e)
                raise

            finally:
                # Calculate latency
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                # Log the response
                await logging_service.log_response(
                    log_id=log_entry.id,
                    status_code=status_code,
                    response_data=response_data,
                    is_success=is_success,
                    error_message=error_message,
                    latency_ms=latency_ms,
                )

        return wrapper

    return decorator
