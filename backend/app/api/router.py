"""Main API router that includes all module routers."""

from fastapi import APIRouter

from app.modules.analysis.router import router as analysis_router
from app.modules.auth.router import router as auth_router
from app.modules.backtest.router import router as backtest_router
from app.modules.data.router import router as data_router
from app.modules.instruments.router import router as instruments_router
from app.modules.portfolio.router import router as portfolio_router
from app.modules.risk.router import router as risk_router
from app.modules.signals.router import router as signals_router
from app.modules.trading.router import router as trading_router
from app.modules.watchlist.router import router as watchlist_router

api_router = APIRouter()

# Include module routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(trading_router, prefix="/orders", tags=["Trading"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(signals_router, prefix="/signals", tags=["Signals"])
api_router.include_router(backtest_router, prefix="/backtest", tags=["Backtesting"])
api_router.include_router(data_router, prefix="/stocks", tags=["Market Data"])
api_router.include_router(watchlist_router, prefix="/watchlist", tags=["Watchlist"])
api_router.include_router(instruments_router, prefix="/instruments", tags=["Instruments"])
api_router.include_router(risk_router, prefix="/risk", tags=["Risk Management"])
