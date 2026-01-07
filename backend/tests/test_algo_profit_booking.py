"""Tests for algo profit booking endpoints."""
import pytest

from app.modules.portfolio.schemas import ProfitBookingRule, ProfitBookingRules


@pytest.mark.asyncio
async def test_profit_booking_schema():
    """Test profit booking schema validation."""
    # Test valid rules
    rules = ProfitBookingRules(
        enabled=True,
        rules=[
            ProfitBookingRule(target_pct=5.0, quantity_pct=25),
            ProfitBookingRule(target_pct=10.0, quantity_pct=50),
        ],
        executed=[],
    )
    assert rules.enabled is True
    assert len(rules.rules) == 2
    assert rules.rules[0].target_pct == 5.0
    assert rules.rules[0].quantity_pct == 25

    # Test model dump
    data = rules.model_dump()
    assert data["enabled"] is True
    assert len(data["rules"]) == 2

    # Test model validation
    validated = ProfitBookingRules.model_validate(data)
    assert validated.enabled is True
    assert len(validated.rules) == 2

