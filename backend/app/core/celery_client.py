"""Celery client for sending tasks from the API.

This module provides a Celery app instance configured to send tasks
to the worker via Redis. It's used by the API to queue async tasks.
"""

from celery import Celery

from app.core.config import settings

# Create a Celery client app for sending tasks
# This doesn't need to include task modules - it just sends tasks
celery_client = Celery(
    "portfolio_api_client",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configure the client
celery_client.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

