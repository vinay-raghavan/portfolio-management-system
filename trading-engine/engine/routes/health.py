"""Health check routes."""

from fastapi import APIRouter

from engine.core.health import check_all_health, is_ready

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic health check for Docker healthcheck."""
    return {"status": "healthy", "service": "trading-engine"}


@router.get("/ready")
async def ready():
    """Readiness check for Kubernetes/orchestration."""
    health_status = await check_all_health()
    ready_status = await is_ready()

    return {
        "ready": ready_status,
        "checks": health_status,
    }


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint (placeholder)."""
    # TODO: Implement Prometheus metrics
    return {"message": "metrics endpoint"}

