"""Health check routes."""

from fastapi import APIRouter

from engine.core.health import check_all_health, check_critical_health, is_ready
from engine.providers.data.factory import check_data_provider_health

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic health check for Docker healthcheck."""
    return {"status": "healthy", "service": "trading-engine"}


@router.get("/ready")
async def ready():
    """Readiness check for Kubernetes/orchestration.

    Checks critical dependencies (database and redis).
    """
    health_status = await check_critical_health()
    ready_status = await is_ready()

    return {
        "ready": ready_status,
        "checks": health_status,
    }


@router.get("/health/full")
async def full_health():
    """Full health check including all providers.

    Includes database, redis, and data provider health.
    """
    health_status = await check_all_health()
    ready_status = await is_ready()

    return {
        "ready": ready_status,
        "checks": health_status,
    }


@router.get("/health/data-provider")
async def data_provider_health():
    """Data provider health check.

    Checks if the configured data provider is accessible and responding.
    """
    health = await check_data_provider_health()
    return health


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint (placeholder)."""
    # TODO: Implement Prometheus metrics
    return {"message": "metrics endpoint"}
