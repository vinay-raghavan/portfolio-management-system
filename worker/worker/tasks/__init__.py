"""Celery tasks package."""

# Import all task modules to register them with Celery
from worker.tasks import funds_reconciliation  # noqa: F401
