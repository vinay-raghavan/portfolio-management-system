"""Funds reconciliation tasks.

Periodic tasks to ensure user_funds table is in sync with actual positions.
This catches any discrepancies caused by failed transactions or bugs.
"""

import logging
from decimal import Decimal

from celery import shared_task
from sqlalchemy import text

from worker.database import get_sync_session

logger = logging.getLogger(__name__)

# Margin percentages by product type
MARGIN_PERCENTAGES = {
    "DELIVERY": Decimal("1.0"),
    "INTRADAY": Decimal("0.25"),
    "MARGIN": Decimal("0.50"),
    "SLB": Decimal("0.50"),
}


@shared_task(name="funds.reconcile_all_users")
def reconcile_all_users_funds() -> dict:
    """Reconcile funds for all users with algo positions.

    Runs periodically to catch and fix any discrepancies between
    user_funds.margin_used and actual open positions.

    Returns:
        dict: Summary of reconciliation results
    """
    logger.info("Starting funds reconciliation for all users")

    with get_sync_session() as session:
        # Get all users with algo positions
        result = session.execute(
            text("""
                SELECT DISTINCT user_id
                FROM algo_positions
                WHERE status = 'OPEN'
            """)
        )
        user_ids = [row[0] for row in result.fetchall()]

    reconciled = 0
    errors = 0

    for user_id in user_ids:
        try:
            result = reconcile_user_funds.delay(str(user_id))
            reconciled += 1
        except Exception as e:
            logger.error(f"Failed to queue reconciliation for user {user_id}: {e}")
            errors += 1

    logger.info(f"Funds reconciliation queued: {reconciled} users, {errors} errors")
    return {"queued": reconciled, "errors": errors}


@shared_task(name="funds.reconcile_user")
def reconcile_user_funds(user_id: str) -> dict:
    """Reconcile funds for a specific user.

    Calculates expected margin_used from open positions and updates
    if there's a discrepancy.

    Args:
        user_id: User ID to reconcile

    Returns:
        dict: Reconciliation result
    """
    logger.info(f"Reconciling funds for user {user_id[:8]}...")

    with get_sync_session() as session:
        # Calculate expected margin from open positions
        # Use COALESCE to handle positions without product_type
        result = session.execute(
            text("""
                SELECT
                    COALESCE(SUM(
                        entry_price * remaining_quantity *
                        CASE COALESCE(product_type::text, 'INTRADAY')
                            WHEN 'DELIVERY' THEN 1.0
                            WHEN 'INTRADAY' THEN 0.25
                            WHEN 'MARGIN' THEN 0.50
                            WHEN 'SLB' THEN 0.50
                            ELSE 0.25
                        END
                    ), 0) as expected_margin
                FROM algo_positions
                WHERE user_id = :user_id AND status = 'OPEN'
            """),
            {"user_id": user_id},
        )
        expected_margin = Decimal(str(result.scalar() or 0))

        # Get current margin_used
        result = session.execute(
            text("SELECT margin_used FROM user_funds WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        row = result.fetchone()
        if not row:
            logger.warning(f"No user_funds record for user {user_id[:8]}")
            return {"status": "no_funds_record", "user_id": user_id}

        current_margin = Decimal(str(row[0]))
        discrepancy = current_margin - expected_margin

        if abs(discrepancy) > Decimal("1.0"):  # Allow ₹1 tolerance for rounding
            logger.warning(
                f"Margin discrepancy for user {user_id[:8]}: "
                f"current={current_margin:.2f}, expected={expected_margin:.2f}, "
                f"diff={discrepancy:.2f}"
            )

            # Fix the discrepancy
            session.execute(
                text("""
                    UPDATE user_funds
                    SET margin_used = :expected, updated_at = NOW()
                    WHERE user_id = :user_id
                """),
                {"expected": expected_margin, "user_id": user_id},
            )
            session.commit()

            logger.info(
                f"Fixed margin for user {user_id[:8]}: {current_margin:.2f} -> {expected_margin:.2f}"
            )
            return {
                "status": "fixed",
                "user_id": user_id,
                "old_margin": float(current_margin),
                "new_margin": float(expected_margin),
                "discrepancy": float(discrepancy),
            }

        return {
            "status": "ok",
            "user_id": user_id,
            "margin_used": float(current_margin),
        }
