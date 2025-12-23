"""Execution routes for strategy running."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from engine.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["execution"])


def verify_internal_key(x_internal_key: Annotated[str | None, Header()] = None) -> str:
    """Verify the internal API key."""
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )
    return x_internal_key


InternalKeyDep = Annotated[str, Depends(verify_internal_key)]


@router.post("/run-scheduled")
async def run_scheduled_strategies(_key: InternalKeyDep):
    """
    Run all scheduled strategies that are due.

    Called by Celery worker every 30 seconds.
    """
    # TODO: Implement after executor is migrated
    logger.info("Running scheduled strategies")
    return {"executed": 0, "results": [], "message": "Not yet implemented"}


@router.post("/execute/{strategy_id}")
async def execute_strategy(
    strategy_id: str,
    _key: InternalKeyDep,
    symbols_override: str | None = None,
):
    """
    Execute a specific strategy.

    Called by backend API for manual triggers.
    """
    # TODO: Implement after executor is migrated
    symbols = symbols_override.split(",") if symbols_override else None
    logger.info(f"Executing strategy {strategy_id} with symbols: {symbols}")
    return {
        "status": "pending",
        "strategy_id": strategy_id,
        "message": "Not yet implemented",
    }


@router.get("/kill-switch/{user_id}")
async def get_kill_switch_status(user_id: str, _key: InternalKeyDep):
    """Get kill switch status for a user."""
    # TODO: Implement after safety module is migrated
    return {"user_id": user_id, "is_active": False, "message": "Not yet implemented"}


@router.post("/kill-switch/{user_id}/activate")
async def activate_kill_switch(user_id: str, _key: InternalKeyDep):
    """Activate kill switch for a user."""
    # TODO: Implement after safety module is migrated
    logger.warning(f"Activating kill switch for user {user_id}")
    return {"user_id": user_id, "activated": True, "message": "Not yet implemented"}


@router.post("/kill-switch/{user_id}/deactivate")
async def deactivate_kill_switch(user_id: str, _key: InternalKeyDep):
    """Deactivate kill switch for a user."""
    # TODO: Implement after safety module is migrated
    logger.info(f"Deactivating kill switch for user {user_id}")
    return {"user_id": user_id, "deactivated": True, "message": "Not yet implemented"}


@router.get("/circuit-breaker/{strategy_id}")
async def get_circuit_breaker_status(strategy_id: str, _key: InternalKeyDep):
    """Get circuit breaker status for a strategy."""
    # TODO: Implement after safety module is migrated
    return {
        "strategy_id": strategy_id,
        "is_triggered": False,
        "message": "Not yet implemented",
    }

