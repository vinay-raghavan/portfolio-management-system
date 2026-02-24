"""Main API router that includes all module routers."""

from fastapi import APIRouter

from app.modules.activity.router import router as activity_router
from app.modules.algo.auto_trade_router import router as auto_trade_router
from app.modules.algo.router import router as algo_router
from app.modules.analysis.router import router as analysis_router
from app.modules.auth.router import router as auth_router
from app.modules.backtest.router import router as backtest_router
from app.modules.broker.router import router as broker_router
from app.modules.data.router import router as data_router
from app.modules.instruments.router import router as instruments_router
from app.modules.portfolio.router import router as portfolio_router
from app.modules.research.router import router as research_router
from app.modules.risk.router import router as risk_router
from app.modules.screener.router import router as screener_router
from app.modules.settings.router import router as settings_router
from app.modules.signals.router import router as signals_router
from app.modules.trading.router import router as trading_router
from app.modules.watchlist.router import router as watchlist_router

api_router = APIRouter()

# Include module routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(broker_router, prefix="/brokers", tags=["Broker Integration"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(trading_router, prefix="/orders", tags=["Trading"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(signals_router, prefix="/signals", tags=["Signals"])
api_router.include_router(backtest_router, prefix="/backtest", tags=["Backtesting"])
api_router.include_router(data_router, prefix="/stocks", tags=["Market Data"])
api_router.include_router(watchlist_router, prefix="/watchlist", tags=["Watchlist"])
api_router.include_router(instruments_router, prefix="/instruments", tags=["Instruments"])
api_router.include_router(risk_router, prefix="/risk", tags=["Risk Management"])
api_router.include_router(algo_router, prefix="/algo", tags=["Algo Trading"])
api_router.include_router(auto_trade_router, prefix="/auto-trade", tags=["Auto-Trade"])
api_router.include_router(screener_router, prefix="/screener", tags=["Stock Screener"])
api_router.include_router(research_router, prefix="/research", tags=["Stock Research"])
api_router.include_router(settings_router, prefix="/settings", tags=["User Settings"])
api_router.include_router(activity_router, prefix="/activity", tags=["Activity Log"])
