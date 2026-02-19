"""Broker API logging service for tracking API calls.

Records all broker API interactions for debugging and audit purposes.
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.broker.models import BrokerAPILog

logger = logging.getLogger(__name__)

# Patterns to mask sensitive data in request/response
SENSITIVE_PATTERNS = [
    (re.compile(r"(access_token[\"']?\s*[:=]\s*[\"']?)[^\"',}\s]+", re.I), r"\1***MASKED***"),
    (re.compile(r"(secret[_]?key[\"']?\s*[:=]\s*[\"']?)[^\"',}\s]+", re.I), r"\1***MASKED***"),
    (re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)[^\"',}\s]+", re.I), r"\1***MASKED***"),
    (re.compile(r"(api[_]?key[\"']?\s*[:=]\s*[\"']?)[^\"',}\s]+", re.I), r"\1***MASKED***"),
    (re.compile(r"(token[\"']?\s*[:=]\s*[\"']?)[^\"',}\s]+", re.I), r"\1***MASKED***"),
    (re.compile(r"(authorization[\"']?\s*[:=]\s*[\"']?)[^\"',}\s]+", re.I), r"\1***MASKED***"),
]


def mask_sensitive_data(data: Any) -> Any:
    """Mask sensitive information in request/response data."""
    if data is None:
        return None

    if isinstance(data, dict):
        return {k: mask_sensitive_data(v) for k, v in data.items()}

    if isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]

    if isinstance(data, str):
        result = data
        for pattern, replacement in SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    return data


class BrokerLoggingService:
    """Service for logging and querying broker API calls."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_request(
        self,
        user_id: str,
        broker_type: str,
        endpoint: str,
        method: str,
        action: str,
        request_data: dict | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> BrokerAPILog:
        """Log an outgoing broker API request.

        Returns the log entry so it can be updated with the response.
        """
        log_entry = BrokerAPILog(
            user_id=user_id,
            broker_type=broker_type,
            endpoint=endpoint,
            method=method,
            action=action,
            request_data=mask_sensitive_data(request_data),
            reference_type=reference_type,
            reference_id=reference_id,
            request_at=datetime.now(UTC),
            is_success=False,  # Will be updated on response
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def log_response(
        self,
        log_id: str,
        status_code: int | None,
        response_data: dict | None,
        is_success: bool,
        error_message: str | None = None,
        latency_ms: int | None = None,
    ) -> BrokerAPILog | None:
        """Update a log entry with response details."""
        result = await self.db.execute(select(BrokerAPILog).where(BrokerAPILog.id == log_id))
        log_entry = result.scalar_one_or_none()

        if not log_entry:
            logger.warning(f"Log entry {log_id} not found for response update")
            return None

        log_entry.status_code = status_code
        log_entry.response_data = mask_sensitive_data(response_data)
        log_entry.is_success = is_success
        log_entry.error_message = error_message
        log_entry.latency_ms = latency_ms
        log_entry.response_at = datetime.now(UTC)

        return log_entry

    async def log_complete(
        self,
        user_id: str,
        broker_type: str,
        endpoint: str,
        method: str,
        action: str,
        status_code: int | None,
        is_success: bool,
        latency_ms: int | None = None,
        request_data: dict | None = None,
        response_data: dict | None = None,
        error_message: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
    ) -> BrokerAPILog:
        """Log a complete API call (request + response) in one go."""
        now = datetime.now(UTC)
        log_entry = BrokerAPILog(
            user_id=user_id,
            broker_type=broker_type,
            endpoint=endpoint,
            method=method,
            action=action,
            request_data=mask_sensitive_data(request_data),
            status_code=status_code,
            response_data=mask_sensitive_data(response_data),
            is_success=is_success,
            error_message=error_message,
            latency_ms=latency_ms,
            reference_type=reference_type,
            reference_id=reference_id,
            request_at=now,
            response_at=now,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def get_api_logs(
        self,
        user_id: str,
        broker_type: str | None = None,
        action: str | None = None,
        is_success: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[BrokerAPILog], int]:
        """Get paginated API logs with filters.

        Returns (logs, total_count).
        """
        query = select(BrokerAPILog).where(BrokerAPILog.user_id == user_id)

        if broker_type:
            query = query.where(BrokerAPILog.broker_type == broker_type)
        if action:
            query = query.where(BrokerAPILog.action == action)
        if is_success is not None:
            query = query.where(BrokerAPILog.is_success == is_success)
        if start_date:
            query = query.where(BrokerAPILog.request_at >= start_date)
        if end_date:
            query = query.where(BrokerAPILog.request_at <= end_date)

        # Get total count
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(BrokerAPILog.request_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def get_api_stats(
        self,
        user_id: str,
        broker_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Get API statistics (success rates, avg latency by broker/action)."""
        from sqlalchemy import Integer

        query = select(
            BrokerAPILog.broker_type,
            BrokerAPILog.action,
            func.count().label("total_calls"),
            func.sum(func.cast(BrokerAPILog.is_success, Integer)).label("successful_calls"),
            func.avg(BrokerAPILog.latency_ms).label("avg_latency_ms"),
            func.min(BrokerAPILog.latency_ms).label("min_latency_ms"),
            func.max(BrokerAPILog.latency_ms).label("max_latency_ms"),
        ).where(BrokerAPILog.user_id == user_id)

        if broker_type:
            query = query.where(BrokerAPILog.broker_type == broker_type)
        if start_date:
            query = query.where(BrokerAPILog.request_at >= start_date)
        if end_date:
            query = query.where(BrokerAPILog.request_at <= end_date)

        query = query.group_by(BrokerAPILog.broker_type, BrokerAPILog.action)

        result = await self.db.execute(query)
        rows = result.all()

        # Process results
        stats_by_broker: dict[str, dict] = {}
        for row in rows:
            broker = row.broker_type
            if broker not in stats_by_broker:
                stats_by_broker[broker] = {
                    "broker_type": broker,
                    "total_calls": 0,
                    "successful_calls": 0,
                    "actions": [],
                }

            stats_by_broker[broker]["total_calls"] += row.total_calls
            stats_by_broker[broker]["successful_calls"] += row.successful_calls or 0
            stats_by_broker[broker]["actions"].append(
                {
                    "action": row.action,
                    "total_calls": row.total_calls,
                    "successful_calls": row.successful_calls or 0,
                    "success_rate": (row.successful_calls or 0) / row.total_calls * 100
                    if row.total_calls > 0
                    else 0,
                    "avg_latency_ms": round(row.avg_latency_ms, 2) if row.avg_latency_ms else None,
                    "min_latency_ms": row.min_latency_ms,
                    "max_latency_ms": row.max_latency_ms,
                }
            )

        # Calculate overall success rates
        for broker_stats in stats_by_broker.values():
            total = broker_stats["total_calls"]
            successful = broker_stats["successful_calls"]
            broker_stats["success_rate"] = successful / total * 100 if total > 0 else 0

        return {
            "brokers": list(stats_by_broker.values()),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        }

    async def get_log_by_id(self, user_id: str, log_id: str) -> BrokerAPILog | None:
        """Get a single log entry by ID."""
        result = await self.db.execute(
            select(BrokerAPILog).where(
                BrokerAPILog.id == log_id,
                BrokerAPILog.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
