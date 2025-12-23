"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.modules.algo.internal_router import router as algo_internal_router
from app.modules.signals.strategies.prebuilt import register_all_prebuilt_strategies

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan handler."""
    # Startup
    if not settings.SKIP_DB_INIT:
        await init_db()

    # Register prebuilt composite strategies
    prebuilt = register_all_prebuilt_strategies()
    logger.info(f"Registered {len(prebuilt)} prebuilt composite strategies")

    yield
    # Shutdown


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Portfolio Management System API",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Include internal API router (for worker-to-backend communication)
# These endpoints should only be accessible from within the Docker network
app.include_router(algo_internal_router, prefix="/internal/algo", tags=["Internal - Algo"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}
