"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from worker.config import settings

# Create Celery app
celery_app = Celery(
    "portfolio_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "worker.tasks.market_data",
        "worker.tasks.analysis",
        "worker.tasks.portfolio",
        "worker.tasks.alerts",
        "worker.tasks.instruments",
        "worker.tasks.trading",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "refresh-market-data-every-minute": {
        "task": "worker.tasks.market_data.refresh_market_data",
        "schedule": 60.0,  # Every minute
    },
    "update-portfolio-values-every-5-minutes": {
        "task": "worker.tasks.portfolio.update_all_portfolio_values",
        "schedule": 300.0,  # Every 5 minutes
    },
    "check-price-alerts-every-minute": {
        "task": "worker.tasks.alerts.check_price_alerts",
        "schedule": 60.0,  # Every minute
    },
    "calculate-daily-analytics-at-midnight": {
        "task": "worker.tasks.analysis.calculate_daily_analytics",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight UTC
    },
    # Instrument master sync - daily at 6 AM IST (00:30 UTC)
    "sync-nse-equity-master-daily": {
        "task": "worker.tasks.instruments.sync_nse_equity_master",
        "schedule": crontab(hour=0, minute=30),  # Daily at 00:30 UTC
    },
    "sync-nse-indices-daily": {
        "task": "worker.tasks.instruments.sync_nse_indices",
        "schedule": crontab(hour=0, minute=35),  # Daily at 00:35 UTC
    },
    "sync-nse-fo-master-daily": {
        "task": "worker.tasks.instruments.sync_nse_fo_master",
        "schedule": crontab(hour=0, minute=40),  # Daily at 00:40 UTC
    },
    # Weekly full instrument sync - Sunday 6 AM IST (00:30 UTC)
    "sync-instruments-weekly": {
        "task": "worker.tasks.instruments.sync_instruments_weekly",
        "schedule": crontab(hour=0, minute=30, day_of_week=0),  # Sunday 00:30 UTC
    },
    # Trading tasks - SL/TP checking every minute during market hours
    "check-sl-tp-orders-every-minute": {
        "task": "worker.tasks.trading.check_sl_tp_orders",
        "schedule": 60.0,  # Every minute
    },
    # GTT order checking every minute during market hours
    "check-gtt-orders-every-minute": {
        "task": "worker.tasks.trading.check_gtt_orders",
        "schedule": 60.0,  # Every minute
    },
    # Pending trigger orders (SL/SL-M) every 30 seconds
    "check-trigger-orders-every-30-seconds": {
        "task": "worker.tasks.trading.check_pending_trigger_orders",
        "schedule": 30.0,  # Every 30 seconds
    },
    # Auto square-off intraday positions at 3:15 PM IST (9:45 UTC)
    "auto-square-off-intraday": {
        "task": "worker.tasks.trading.auto_square_off_intraday",
        "schedule": crontab(hour=9, minute=45),  # 3:15 PM IST = 9:45 UTC
    },
    # Process AMO (After Market Orders) at market open - 9:15 AM IST (3:45 UTC)
    "process-amo-orders-at-market-open": {
        "task": "worker.tasks.trading.process_amo_orders",
        "schedule": crontab(hour=3, minute=45),  # 9:15 AM IST = 3:45 UTC
    },
}
