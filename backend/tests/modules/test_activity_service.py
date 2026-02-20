"""Tests for ActivityService."""

import pytest

from app.core.security import get_password_hash
from app.modules.activity.models import ActivityCategory, ActivitySeverity, ActivityType
from app.modules.activity.service import ActivityService
from app.modules.auth.models import User


class TestActivityService:
    """Tests for ActivityService operations."""

    @pytest.fixture
    async def test_user(self, db_session):
        """Create a test user."""
        user = User(
            email="activity_test@example.com",
            password_hash=get_password_hash("testpass123"),
            full_name="Activity Test User",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    def activity_service(self, db_session):
        """Create ActivityService instance."""
        return ActivityService(db_session)

    @pytest.mark.asyncio
    async def test_log_activity(self, activity_service, test_user):
        """Test logging an activity."""
        activity = await activity_service.log_activity(
            user_id=test_user.id,
            activity_type=ActivityType.ORDER_PLACED,
            category=ActivityCategory.TRADING,
            title="Order Placed",
            description="Buy 10 RELIANCE @ ₹2,500",
            entity_type="order",
            entity_id="order-123",
            extra_data={"symbol": "RELIANCE", "quantity": 10, "price": 2500},
        )

        assert activity is not None
        assert activity.user_id == test_user.id
        assert activity.activity_type == ActivityType.ORDER_PLACED.value
        assert activity.category == ActivityCategory.TRADING.value
        assert activity.title == "Order Placed"
        assert activity.is_read is False

    @pytest.mark.asyncio
    async def test_log_activity_with_severity(self, activity_service, test_user):
        """Test logging an activity with severity."""
        activity = await activity_service.log_activity(
            user_id=test_user.id,
            activity_type=ActivityType.RISK_LIMIT_BREACHED,
            category=ActivityCategory.RISK,
            title="Risk Limit Breached",
            description="Daily loss limit exceeded",
            severity=ActivitySeverity.CRITICAL,
        )

        assert activity.severity == ActivitySeverity.CRITICAL.value

    @pytest.mark.asyncio
    async def test_get_activities_pagination(self, activity_service, test_user):
        """Test getting paginated activities."""
        # Create multiple activities
        for i in range(5):
            await activity_service.log_activity(
                user_id=test_user.id,
                activity_type=ActivityType.LOGIN,
                category=ActivityCategory.AUTH,
                title=f"Login {i + 1}",
                description=f"User logged in - session {i + 1}",
            )

        activities, total, unread = await activity_service.get_activities(
            user_id=test_user.id,
            page=1,
            page_size=3,
        )

        assert len(activities) == 3
        assert total == 5
        assert unread == 5

    @pytest.mark.asyncio
    async def test_get_activities_filter_by_category(self, activity_service, test_user):
        """Test filtering activities by category."""
        await activity_service.log_activity(
            user_id=test_user.id,
            activity_type=ActivityType.LOGIN,
            category=ActivityCategory.AUTH,
            title="Login",
            description="User logged in",
        )
        await activity_service.log_activity(
            user_id=test_user.id,
            activity_type=ActivityType.ORDER_PLACED,
            category=ActivityCategory.TRADING,
            title="Order",
            description="Order placed",
        )

        activities, total, _ = await activity_service.get_activities(
            user_id=test_user.id,
            category=ActivityCategory.TRADING.value,
        )

        assert total == 1
        assert activities[0].category == ActivityCategory.TRADING.value

    @pytest.mark.asyncio
    async def test_get_unread_count(self, activity_service, test_user):
        """Test getting unread count."""
        for i in range(3):
            await activity_service.log_activity(
                user_id=test_user.id,
                activity_type=ActivityType.LOGIN,
                category=ActivityCategory.AUTH,
                title=f"Activity {i + 1}",
                description="Description",
            )

        count = await activity_service.get_unread_count(user_id=test_user.id)
        assert count == 3

    @pytest.mark.asyncio
    async def test_mark_as_read_specific(self, activity_service, test_user, db_session):
        """Test marking specific activities as read."""
        activities = []
        for i in range(3):
            act = await activity_service.log_activity(
                user_id=test_user.id,
                activity_type=ActivityType.LOGIN,
                category=ActivityCategory.AUTH,
                title=f"Activity {i + 1}",
                description="Description",
            )
            activities.append(act)
        await db_session.flush()

        # Mark first two as read
        marked = await activity_service.mark_as_read(
            user_id=test_user.id,
            activity_ids=[activities[0].id, activities[1].id],
        )

        assert marked == 2
        unread = await activity_service.get_unread_count(user_id=test_user.id)
        assert unread == 1

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, activity_service, test_user, db_session):
        """Test marking all activities as read."""
        for i in range(5):
            await activity_service.log_activity(
                user_id=test_user.id,
                activity_type=ActivityType.LOGIN,
                category=ActivityCategory.AUTH,
                title=f"Activity {i + 1}",
                description="Description",
            )
        await db_session.flush()

        marked = await activity_service.mark_as_read(
            user_id=test_user.id,
            mark_all=True,
        )

        assert marked == 5
        unread = await activity_service.get_unread_count(user_id=test_user.id)
        assert unread == 0
