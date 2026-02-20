"""FastAPI application entry point."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.strategies import register_all_prebuilt_strategies

from app.api.router import api_router
from app.core.config import settings
from app.core.database import init_db

# Configure logging from LOG_LEVEL environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_level_value = getattr(logging, log_level, logging.INFO)
logging.basicConfig(
    level=log_level_value,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

# Explicitly set level for app loggers to ensure DEBUG propagates
logging.getLogger("app").setLevel(log_level_value)
logging.getLogger("app.core.cache").setLevel(log_level_value)

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

# NOTE: Internal algo endpoints are now handled by the trading-engine service
# The worker communicates directly with trading-engine at http://trading-engine:8001/internal/


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}
