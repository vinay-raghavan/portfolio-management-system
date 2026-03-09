"""Trading Engine - FastAPI Application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.strategies import register_all_prebuilt_strategies

# Import strategies module to trigger registration via decorators
# This ensures all strategies are registered when the app starts
import engine.strategies  # noqa: F401
from engine.config import settings
from engine.core.redis import close_redis_pool
from engine.routes import execution_router, health_router, intraday_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def load_user_composite_strategies(db) -> int:
    """Load user-created composite strategies from database and register them.

    User-created composite strategies are stored in the database with their
    configuration. This function loads them and registers them with the
    StrategyRegistry so they can be executed.

    Returns:
        Number of composite strategies loaded
    """
    from shared.strategies.composite import CompositeStrategyFactory
    from shared.strategies.registry import StrategyRegistry
    from sqlalchemy import select

    from engine.models.algo import UserStrategy

    # Find all strategies with names starting with "composite_"
    result = await db.execute(
        select(UserStrategy).where(UserStrategy.strategy_name.like("composite_%"))
    )
    composite_strategies = result.scalars().all()

    loaded = 0
    for strategy in composite_strategies:
        strategy_name = strategy.strategy_name
        params = strategy.strategy_params or {}

        # Skip if already registered (e.g., prebuilt strategies)
        if StrategyRegistry.has_strategy(strategy_name):
            continue

        # Extract components and combine logic from params
        components = params.get("components", [])
        combine_logic = params.get("combine_logic", "AND")
        min_agreement_pct = params.get("min_agreement_pct", 0.5)

        if not components:
            logger.warning(f"Skipping composite strategy '{strategy_name}' - no components defined")
            continue

        try:
            # Create and register the composite strategy
            composite = CompositeStrategyFactory.create(
                name=strategy_name,
                description=strategy.description or f"User composite strategy: {strategy.name}",
                components=components,
                combine_logic=combine_logic,
                min_agreement_pct=min_agreement_pct,
            )
            CompositeStrategyFactory.register(composite)
            loaded += 1
            logger.info(f"Registered user composite strategy: {strategy_name}")
        except Exception as e:
            logger.warning(f"Failed to register composite strategy '{strategy_name}': {e}")

    return loaded


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Trading Engine...")

    # Register prebuilt composite strategies (e.g., rsi_macd_confluence, etc.)
    prebuilt = register_all_prebuilt_strategies()
    logger.info(f"Registered {len(prebuilt)} prebuilt composite strategies")

    # Load user-created composite strategies from database
    try:
        from engine.core.database import get_db_context

        async with get_db_context() as db:
            user_composites = await load_user_composite_strategies(db)
            logger.info(f"Registered {user_composites} user composite strategies from database")
    except Exception as e:
        logger.warning(f"Failed to load user composite strategies on startup: {e}")

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
app.include_router(intraday_router)


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

    # Binding to 0.0.0.0 is intentional for Docker container access
    uvicorn.run(app, host="0.0.0.0", port=8001)  # nosec B104
