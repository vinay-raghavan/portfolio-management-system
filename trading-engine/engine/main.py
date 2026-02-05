"""Trading Engine - FastAPI Application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import strategies module to trigger registration via decorators
# This ensures all strategies are registered when the app starts
import engine.strategies  # noqa: F401
from engine.config import settings
from shared.strategies import register_all_prebuilt_strategies
from engine.core.redis import close_redis_pool
from engine.routes import execution_router, health_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Trading Engine...")

    # Register prebuilt composite strategies (e.g., rsi_macd_confluence, etc.)
    prebuilt = register_all_prebuilt_strategies()
    logger.info(f"Registered {len(prebuilt)} prebuilt composite strategies")

    # Load circuit breaker states from DB to Redis on startup
    try:
        from engine.algo.safety import CircuitBreakerPersistence
        from engine.core.database import get_db_context
        from engine.core.redis import get_redis_pool

        redis = await get_redis_pool()
        cb_persistence = CircuitBreakerPersistence(redis)

        async with get_db_context() as db:
            loaded = await cb_persistence.load_all_active_strategies(db)
            logger.info(f"Loaded {len(loaded)} circuit breaker states from DB")
    except Exception as e:
        logger.warning(f"Failed to load circuit breaker states on startup: {e}")

    yield

    logger.info("Shutting down Trading Engine...")
    await close_redis_pool()


app = FastAPI(
    title="Trading Engine",
    description="Portfolio Management System - Strategy Execution Service",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(execution_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "trading-engine",
        "version": "0.1.0",
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
