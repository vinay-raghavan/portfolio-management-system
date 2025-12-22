"""Price alert tasks."""

import logging

from redis import Redis

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.alerts.check_price_alerts")
def check_price_alerts(self) -> dict:
    """Check all price alerts and trigger notifications."""
    logger.info("Checking price alerts")

    redis_client = Redis.from_url(settings.REDIS_URL)

    # Get all alert keys
    alert_keys = redis_client.keys("alert:*")

    if not alert_keys:
        return {"status": "no_alerts", "triggered": 0}

    triggered = 0

    for key in alert_keys:
        try:
            alert_data = redis_client.hgetall(key)
            if not alert_data:
                continue

            symbol = alert_data.get(b"symbol", b"").decode()
            target_price = float(alert_data.get(b"target_price", b"0"))
            alert_type = alert_data.get(b"type", b"above").decode()

            # Get current price
            current_price_str = redis_client.get(f"price:{symbol}")
            if not current_price_str:
                continue

            current_price = float(current_price_str)

            # Check if alert should trigger
            should_trigger = False
            if (
                alert_type == "above"
                and current_price >= target_price
                or alert_type == "below"
                and current_price <= target_price
            ):
                should_trigger = True

            if should_trigger:
                # Queue notification task
                send_alert_notification.delay(
                    key.decode(),
                    symbol,
                    current_price,
                    target_price,
                    alert_type,
                )
                triggered += 1

                # Remove or mark alert as triggered
                redis_client.hset(key, "triggered", "true")

        except Exception as e:
            logger.error(f"Error checking alert {key}: {e}")

    logger.info(f"Checked alerts. Triggered: {triggered}")
    return {"status": "success", "triggered": triggered}


@celery_app.task(bind=True, name="worker.tasks.alerts.send_alert_notification")
def send_alert_notification(
    self,
    alert_id: str,
    symbol: str,
    current_price: float,
    target_price: float,
    alert_type: str,
) -> dict:
    """Send notification for a triggered alert."""
    logger.info(f"Sending alert notification for {symbol}")

    # This would integrate with:
    # - Email service
    # - Push notifications
    # - WebSocket for real-time updates

    message = (
        f"Price Alert: {symbol} is now ${current_price:.2f} "
        f"({'above' if alert_type == 'above' else 'below'} target ${target_price:.2f})"
    )

    logger.info(message)

    return {
        "status": "success",
        "alert_id": alert_id,
        "message": message,
    }


@celery_app.task(bind=True, name="worker.tasks.alerts.create_price_alert")
def create_price_alert(
    self,
    user_id: str,
    symbol: str,
    target_price: float,
    alert_type: str = "above",
) -> dict:
    """Create a new price alert."""
    import uuid

    alert_id = f"alert:{uuid.uuid4()}"

    redis_client = Redis.from_url(settings.REDIS_URL)
    redis_client.hset(
        alert_id,
        mapping={
            "user_id": user_id,
            "symbol": symbol.upper(),
            "target_price": target_price,
            "type": alert_type,
            "triggered": "false",
        },
    )

    # Add symbol to tracked symbols
    redis_client.sadd("tracked_symbols", symbol.upper())

    logger.info(f"Created price alert {alert_id} for {symbol} at ${target_price}")

    return {"status": "success", "alert_id": alert_id}
