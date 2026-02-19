"""Tests for BrokerLoggingService."""

import pytest

from app.core.security import get_password_hash
from app.modules.auth.models import User
from app.modules.broker.logging_service import BrokerLoggingService, mask_sensitive_data
from app.modules.broker.models import BrokerAPILog


class TestMaskSensitiveData:
    """Tests for sensitive data masking.

    The mask_sensitive_data function uses regex patterns to mask sensitive values
    in strings, handling formats like 'access_token=value' or '"password": "value"'.
    """

    def test_mask_access_token_in_string(self):
        """Test masking access_token in a string format."""
        data = "access_token=secret123"
        masked = mask_sensitive_data(data)
        assert "secret123" not in masked
        assert "***MASKED***" in masked

    def test_mask_password_in_json_string(self):
        """Test masking password in JSON-like string."""
        data = '"password": "mypassword"'
        masked = mask_sensitive_data(data)
        assert "mypassword" not in masked
        assert "***MASKED***" in masked

    def test_mask_api_key_in_string(self):
        """Test masking API key in string."""
        data = "api_key=abc123"
        masked = mask_sensitive_data(data)
        assert "abc123" not in masked
        assert "***MASKED***" in masked

    def test_mask_token_in_nested_dict_string(self):
        """Test masking token in nested dict with string values."""
        data = {"auth": "token=secret123"}
        masked = mask_sensitive_data(data)
        assert "secret123" not in masked["auth"]
        assert "***MASKED***" in masked["auth"]

    def test_mask_none_data(self):
        """Test masking returns None for None input."""
        assert mask_sensitive_data(None) is None

    def test_mask_plain_string_unchanged(self):
        """Test that plain strings without sensitive patterns are unchanged."""
        data = "just a normal string"
        assert mask_sensitive_data(data) == data

    def test_mask_dict_with_normal_values(self):
        """Test dict with non-sensitive string values passes through."""
        data = {"symbol": "RELIANCE", "quantity": 10}
        masked = mask_sensitive_data(data)
        assert masked["symbol"] == "RELIANCE"
        assert masked["quantity"] == 10

    def test_mask_list_data(self):
        """Test masking in list data."""
        data = ["token=secret1", "token=secret2"]
        masked = mask_sensitive_data(data)
        assert "secret1" not in masked[0]
        assert "secret2" not in masked[1]


class TestBrokerLoggingService:
    """Tests for BrokerLoggingService operations."""

    @pytest.fixture
    async def test_user(self, db_session):
        """Create a test user."""
        user = User(
            email="broker_log_test@example.com",
            password_hash=get_password_hash("testpass123"),
            full_name="Broker Log Test User",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    def logging_service(self, db_session):
        """Create BrokerLoggingService instance."""
        return BrokerLoggingService(db_session)

    @pytest.mark.asyncio
    async def test_log_request(self, logging_service, test_user):
        """Test logging a broker API request."""
        log = await logging_service.log_request(
            user_id=test_user.id,
            broker_type="fyers",
            endpoint="/api/v3/orders",
            method="POST",
            action="place_order",
            request_data={"symbol": "RELIANCE", "qty": 10},
        )

        assert log is not None
        assert log.user_id == test_user.id
        assert log.broker_type == "fyers"
        assert log.action == "place_order"
        assert log.is_success is False  # Not yet completed

    @pytest.mark.asyncio
    async def test_log_response(self, logging_service, test_user, db_session):
        """Test logging a broker API response."""
        # First create a request log
        log = await logging_service.log_request(
            user_id=test_user.id,
            broker_type="fyers",
            endpoint="/api/v3/orders",
            method="POST",
            action="place_order",
        )
        await db_session.flush()

        # Now log the response
        updated_log = await logging_service.log_response(
            log_id=log.id,
            status_code=200,
            response_data={"order_id": "123456", "status": "PLACED"},
            is_success=True,
            latency_ms=150,
        )

        assert updated_log.status_code == 200
        assert updated_log.is_success is True
        assert updated_log.latency_ms == 150
        assert updated_log.response_at is not None

    @pytest.mark.asyncio
    async def test_log_complete(self, logging_service, test_user):
        """Test logging complete request-response cycle."""
        log = await logging_service.log_complete(
            user_id=test_user.id,
            broker_type="paper",
            endpoint="/orders",
            method="POST",
            action="place_order",
            status_code=200,
            is_success=True,
            request_data={"symbol": "TCS", "qty": 5},
            response_data={"order_id": "paper-123"},
            latency_ms=50,
        )

        assert log.broker_type == "paper"
        assert log.is_success is True
        assert log.latency_ms == 50
        assert log.request_at is not None
        assert log.response_at is not None

    @pytest.mark.asyncio
    async def test_get_api_logs_pagination(self, logging_service, test_user, db_session):
        """Test getting paginated API logs."""
        # Create multiple logs
        for i in range(5):
            log = BrokerAPILog(
                user_id=test_user.id,
                broker_type="fyers",
                endpoint=f"/api/v3/endpoint{i}",
                method="GET",
                action=f"action_{i}",
                is_success=True,
            )
            db_session.add(log)
        await db_session.flush()

        logs, total = await logging_service.get_api_logs(
            user_id=test_user.id,
            page=1,
            page_size=3,
        )

        assert len(logs) == 3
        assert total == 5
