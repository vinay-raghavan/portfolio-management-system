"""Research API routes."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, OptionalUser
from app.modules.data.service import get_user_data_provider
from app.modules.research.schemas import DividendsResponse, FundamentalsResponse
from app.modules.research.service import ResearchService

router = APIRouter()


@router.get("/{symbol}/fundamentals", response_model=FundamentalsResponse)
async def get_fundamentals(
    symbol: str,
    db: DbSession,
    current_user: OptionalUser,
) -> FundamentalsResponse:
    """Get fundamental analysis data for a stock.

    Includes valuation ratios (P/E, P/B, P/S, PEG), earnings metrics,
    revenue, profitability margins, returns (ROE, ROA), and balance sheet metrics.

    Uses the user's preferred data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = ResearchService(provider=provider)
    fundamentals = await service.get_fundamentals(symbol)

    if fundamentals is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not get fundamentals for symbol: {symbol}",
        )

    return FundamentalsResponse(
        symbol=fundamentals.symbol,
        pe_ratio=fundamentals.pe_ratio,
        forward_pe=fundamentals.forward_pe,
        pb_ratio=fundamentals.pb_ratio,
        ps_ratio=fundamentals.ps_ratio,
        peg_ratio=fundamentals.peg_ratio,
        eps=fundamentals.eps,
        eps_forward=fundamentals.eps_forward,
        eps_growth_yoy=fundamentals.eps_growth_yoy,
        revenue=fundamentals.revenue,
        revenue_growth_yoy=fundamentals.revenue_growth_yoy,
        profit_margin=fundamentals.profit_margin,
        operating_margin=fundamentals.operating_margin,
        gross_margin=fundamentals.gross_margin,
        roe=fundamentals.roe,
        roa=fundamentals.roa,
        dividend_yield=fundamentals.dividend_yield,
        dividend_rate=fundamentals.dividend_rate,
        payout_ratio=fundamentals.payout_ratio,
        market_cap=fundamentals.market_cap,
        enterprise_value=fundamentals.enterprise_value,
        book_value=fundamentals.book_value,
        debt_to_equity=fundamentals.debt_to_equity,
        current_ratio=fundamentals.current_ratio,
        beta=fundamentals.beta,
        sector=fundamentals.sector,
        industry=fundamentals.industry,
        last_updated=fundamentals.last_updated,
    )


@router.get("/{symbol}/dividends", response_model=DividendsResponse)
async def get_dividends(
    symbol: str,
    db: DbSession,
    current_user: OptionalUser,
) -> DividendsResponse:
    """Get dividend history and metrics for a stock.

    Includes current yield, dividend rate, payout ratio, ex-dividend date,
    5-year average yield, dividend growth rate, and historical dividend records.

    Uses the user's preferred data provider if authenticated.
    Falls back to Yahoo Finance for unauthenticated requests.
    """
    provider = None
    if current_user:
        provider = await get_user_data_provider(db, current_user.id)

    service = ResearchService(provider=provider)
    dividends = await service.get_dividends(symbol)

    if dividends is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not get dividend data for symbol: {symbol}",
        )

    return DividendsResponse(
        symbol=dividends.symbol,
        dividend_yield=dividends.dividend_yield,
        dividend_rate=dividends.dividend_rate,
        payout_ratio=dividends.payout_ratio,
        ex_dividend_date=dividends.ex_dividend_date,
        five_year_avg_yield=dividends.five_year_avg_yield,
        dividend_growth_rate=dividends.dividend_growth_rate,
        history=[
            {
                "ex_date": d.ex_date,
                "payment_date": d.payment_date,
                "amount": d.amount,
                "currency": d.currency,
            }
            for d in dividends.history
        ],
        last_updated=dividends.last_updated,
    )

