"""Yahoo Finance data provider implementation."""

import logging
from datetime import UTC, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import yfinance as yf

from ..schemas import (
    OHLCV,
    DividendData,
    DividendRecord,
    FinancialData,
    FinancialStatement,
    FundamentalData,
    InstrumentInfo,
    MarketSession,
    Quote,
    SearchResult,
)
from ..symbols import Exchange, SymbolMapper
from .base import DataProvider

logger = logging.getLogger(__name__)

# Timezone definitions
IST = ZoneInfo("Asia/Kolkata")
EST = ZoneInfo("America/New_York")

# NSE market hours (IST)
NSE_PRE_MARKET_OPEN = time(9, 0)
NSE_PRE_MARKET_CLOSE = time(9, 8)
NSE_MARKET_OPEN = time(9, 15)
NSE_MARKET_CLOSE = time(15, 30)

# US market hours (EST)
US_PRE_MARKET_OPEN = time(4, 0)
US_MARKET_OPEN = time(9, 30)
US_MARKET_CLOSE = time(16, 0)
US_POST_MARKET_CLOSE = time(20, 0)


class YahooDataProvider(DataProvider):
    """Data provider using Yahoo Finance (yfinance).

    Supports global markets including:
    - US stocks (NYSE, NASDAQ)
    - Indian stocks (NSE: .NS suffix, BSE: .BO suffix)
    - Other international markets
    """

    name = "yahoo"

    def __init__(self, default_exchange: Exchange = Exchange.NSE):
        """Initialize Yahoo data provider.

        Args:
            default_exchange: Default exchange for symbol normalization
        """
        self.default_exchange = default_exchange

    def normalize_symbol(self, symbol: str) -> str:
        """Convert symbol to Yahoo Finance format."""
        symbol = symbol.upper().strip()

        # Index symbols start with ^ and should be passed as-is
        if symbol.startswith("^"):
            return symbol

        # Already in Yahoo format
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            return symbol

        # Add suffix based on default exchange
        if self.default_exchange == Exchange.NSE:
            return f"{symbol}.NS"
        elif self.default_exchange == Exchange.BSE:
            return f"{symbol}.BO"

        return symbol

    def get_market_session(self) -> MarketSession:
        """Determine current market session based on exchange and time."""
        if self.default_exchange in (Exchange.NSE, Exchange.BSE):
            now = datetime.now(IST)
            if now.weekday() >= 5:
                return MarketSession.CLOSED
            current_time = now.time()
            if NSE_PRE_MARKET_OPEN <= current_time < NSE_MARKET_OPEN:
                return MarketSession.PRE_MARKET
            elif NSE_MARKET_OPEN <= current_time <= NSE_MARKET_CLOSE:
                return MarketSession.REGULAR
            else:
                return MarketSession.CLOSED
        else:
            now = datetime.now(EST)
            if now.weekday() >= 5:
                return MarketSession.CLOSED
            current_time = now.time()
            if US_PRE_MARKET_OPEN <= current_time < US_MARKET_OPEN:
                return MarketSession.PRE_MARKET
            elif US_MARKET_OPEN <= current_time <= US_MARKET_CLOSE:
                return MarketSession.REGULAR
            elif US_MARKET_CLOSE < current_time <= US_POST_MARKET_CLOSE:
                return MarketSession.POST_MARKET
            else:
                return MarketSession.CLOSED

    def _parse_extended_hours(self, info: dict) -> dict:
        """Extract extended hours data from ticker info."""
        result = {}

        pre_market_price = info.get("preMarketPrice")
        if pre_market_price:
            result["pre_market_price"] = Decimal(str(pre_market_price))
            pre_market_change = info.get("preMarketChange")
            if pre_market_change is not None:
                result["pre_market_change"] = Decimal(str(pre_market_change))
            pre_market_change_pct = info.get("preMarketChangePercent")
            if pre_market_change_pct is not None:
                result["pre_market_change_percent"] = Decimal(str(pre_market_change_pct * 100))
            pre_market_time = info.get("preMarketTime")
            if pre_market_time:
                result["pre_market_time"] = datetime.fromtimestamp(pre_market_time, tz=UTC)

        post_market_price = info.get("postMarketPrice")
        if post_market_price:
            result["post_market_price"] = Decimal(str(post_market_price))
            post_market_change = info.get("postMarketChange")
            if post_market_change is not None:
                result["post_market_change"] = Decimal(str(post_market_change))
            post_market_change_pct = info.get("postMarketChangePercent")
            if post_market_change_pct is not None:
                result["post_market_change_percent"] = Decimal(str(post_market_change_pct * 100))
            post_market_time = info.get("postMarketTime")
            if post_market_time:
                result["post_market_time"] = datetime.fromtimestamp(post_market_time, tz=UTC)

        return result

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for a symbol including extended hours data."""
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            price = info.get("regularMarketPrice") or info.get("currentPrice")
            if not price:
                return None

            prev_close = info.get("regularMarketPreviousClose", 0)
            change = Decimal(str(price)) - Decimal(str(prev_close)) if prev_close else None
            change_pct = (
                (change / Decimal(str(prev_close)) * 100) if change and prev_close else None
            )

            extended_hours = self._parse_extended_hours(info)

            return Quote(
                symbol=SymbolMapper.normalize(symbol),
                price=Decimal(str(price)),
                open=Decimal(str(info.get("regularMarketOpen", 0))) or None,
                high=Decimal(str(info.get("regularMarketDayHigh", 0))) or None,
                low=Decimal(str(info.get("regularMarketDayLow", 0))) or None,
                close=Decimal(str(prev_close)) if prev_close else None,
                previous_close=Decimal(str(prev_close)) if prev_close else None,
                volume=info.get("regularMarketVolume"),
                change=change,
                change_percent=change_pct,
                bid=Decimal(str(info.get("bid", 0))) or None,
                ask=Decimal(str(info.get("ask", 0))) or None,
                market_session=self.get_market_session(),
                **extended_hours,
            )
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    async def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
        include_extended_hours: bool = False,
    ) -> list[OHLCV]:
        """Get historical OHLCV data for a symbol.

        Args:
            symbol: Stock symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)
            include_extended_hours: If True, includes pre-market and post-market data

        Returns:
            List of OHLCV data points
        """
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period=period, interval=interval, prepost=include_extended_hours)

            if hist.empty:
                return []

            data_points = []
            for idx, row in hist.iterrows():
                data_points.append(
                    OHLCV(
                        timestamp=idx.to_pydatetime(),
                        open=Decimal(str(row["Open"])),
                        high=Decimal(str(row["High"])),
                        low=Decimal(str(row["Low"])),
                        close=Decimal(str(row["Close"])),
                        volume=int(row["Volume"]),
                    )
                )

            return data_points
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return []

    async def search_symbols(self, query: str) -> list[SearchResult]:
        """Search for symbols matching a query."""
        try:
            ticker = yf.Ticker(query)
            info = ticker.info

            if info.get("symbol"):
                return [
                    SearchResult(
                        symbol=info.get("symbol", query).replace(".NS", "").replace(".BO", ""),
                        name=info.get("longName") or info.get("shortName") or "",
                        exchange=info.get("exchange", ""),
                        instrument_type=info.get("quoteType", "EQ"),
                    )
                ]
            return []
        except Exception as e:
            logger.debug(f"Search failed for {query}: {e}")
            return []

    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        """Get detailed instrument information."""
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            if not info.get("symbol"):
                return None

            return InstrumentInfo(
                symbol=SymbolMapper.normalize(symbol),
                name=info.get("longName") or info.get("shortName") or "",
                exchange=info.get("exchange", ""),
                instrument_type=info.get("quoteType", "EQ"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                isin=info.get("isin"),
            )
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            return None

    async def is_market_open(self) -> bool:
        """Check if the market is currently open."""
        if self.default_exchange in (Exchange.NSE, Exchange.BSE):
            now = datetime.now(IST)
            if now.weekday() >= 5:
                return False
            current_time = now.time()
            return NSE_MARKET_OPEN <= current_time <= NSE_MARKET_CLOSE
        return True

    # =========================================================================
    # Research / Fundamental Data Methods
    # =========================================================================

    async def get_fundamentals(self, symbol: str) -> FundamentalData | None:
        """Get fundamental analysis data for a stock.

        Fetches valuation ratios, earnings, profitability, and other metrics
        from Yahoo Finance.
        """
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            if not info.get("symbol"):
                return None

            return FundamentalData(
                symbol=SymbolMapper.normalize(symbol),
                # Valuation ratios
                pe_ratio=info.get("trailingPE"),
                forward_pe=info.get("forwardPE"),
                pb_ratio=info.get("priceToBook"),
                ps_ratio=info.get("priceToSalesTrailing12Months"),
                peg_ratio=info.get("pegRatio"),
                # Earnings
                eps=info.get("trailingEps"),
                eps_forward=info.get("forwardEps"),
                eps_growth_yoy=info.get("earningsQuarterlyGrowth"),
                # Revenue
                revenue=info.get("totalRevenue"),
                revenue_per_share=info.get("revenuePerShare"),
                revenue_growth_yoy=info.get("revenueGrowth"),
                # Profitability
                profit_margin=info.get("profitMargins"),
                operating_margin=info.get("operatingMargins"),
                gross_margin=info.get("grossMargins"),
                # Returns
                roe=info.get("returnOnEquity"),
                roa=info.get("returnOnAssets"),
                # Dividends
                dividend_yield=info.get("dividendYield"),
                dividend_rate=info.get("dividendRate"),
                payout_ratio=info.get("payoutRatio"),
                # Balance sheet
                market_cap=info.get("marketCap"),
                enterprise_value=info.get("enterpriseValue"),
                book_value=info.get("bookValue"),
                debt_to_equity=info.get("debtToEquity"),
                current_ratio=info.get("currentRatio"),
                quick_ratio=info.get("quickRatio"),
                # Other
                beta=info.get("beta"),
                shares_outstanding=info.get("sharesOutstanding"),
                float_shares=info.get("floatShares"),
                # Classification
                sector=info.get("sector"),
                industry=info.get("industry"),
                # Metadata
                currency=info.get("currency"),
                fiscal_year_end=info.get("fiscalYearEnd"),
                last_updated=datetime.now(UTC),
            )
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {symbol}: {e}")
            return None

    async def get_financials(self, symbol: str) -> FinancialData | None:
        """Get financial statements data (income statement, balance sheet, cash flow).

        Fetches quarterly and annual financial statements from Yahoo Finance.
        """
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)

            # Get financial statements (returns DataFrames)
            income_stmt = ticker.quarterly_income_stmt
            balance_sheet = ticker.quarterly_balance_sheet
            cash_flow = ticker.quarterly_cashflow

            if income_stmt.empty and balance_sheet.empty and cash_flow.empty:
                return None

            statements = []
            # Process each period (columns are dates)
            all_periods = set()
            if not income_stmt.empty:
                all_periods.update(income_stmt.columns)
            if not balance_sheet.empty:
                all_periods.update(balance_sheet.columns)
            if not cash_flow.empty:
                all_periods.update(cash_flow.columns)

            for period_date in sorted(all_periods, reverse=True)[:8]:  # Last 8 quarters
                stmt = FinancialStatement(
                    period=period_date.strftime("%Y-Q%q")
                    if hasattr(period_date, "strftime")
                    else str(period_date),
                    period_end_date=period_date.to_pydatetime()
                    if hasattr(period_date, "to_pydatetime")
                    else None,
                )

                # Income statement items
                if not income_stmt.empty and period_date in income_stmt.columns:
                    col = income_stmt[period_date]
                    stmt.total_revenue = self._safe_float(col, "Total Revenue")
                    stmt.cost_of_revenue = self._safe_float(col, "Cost Of Revenue")
                    stmt.gross_profit = self._safe_float(col, "Gross Profit")
                    stmt.operating_income = self._safe_float(col, "Operating Income")
                    stmt.net_income = self._safe_float(col, "Net Income")
                    stmt.ebitda = self._safe_float(col, "EBITDA")

                # Balance sheet items
                if not balance_sheet.empty and period_date in balance_sheet.columns:
                    col = balance_sheet[period_date]
                    stmt.total_assets = self._safe_float(col, "Total Assets")
                    stmt.total_liabilities = self._safe_float(
                        col, "Total Liabilities Net Minority Interest"
                    )
                    stmt.total_equity = self._safe_float(col, "Stockholders Equity")
                    stmt.total_debt = self._safe_float(col, "Total Debt")
                    stmt.cash_and_equivalents = self._safe_float(col, "Cash And Cash Equivalents")

                # Cash flow items
                if not cash_flow.empty and period_date in cash_flow.columns:
                    col = cash_flow[period_date]
                    stmt.operating_cash_flow = self._safe_float(col, "Operating Cash Flow")
                    stmt.capital_expenditure = self._safe_float(col, "Capital Expenditure")
                    stmt.free_cash_flow = self._safe_float(col, "Free Cash Flow")

                statements.append(stmt)

            info = ticker.info
            return FinancialData(
                symbol=SymbolMapper.normalize(symbol),
                statements=statements,
                currency=info.get("currency"),
                last_updated=datetime.now(UTC),
            )
        except Exception as e:
            logger.error(f"Error fetching financials for {symbol}: {e}")
            return None

    def _safe_float(self, series, key: str) -> float | None:
        """Safely extract a float value from a pandas Series."""
        try:
            if key in series.index:
                val = series[key]
                if val is not None and not (hasattr(val, "isna") and val.isna()):
                    return float(val)
        except (KeyError, TypeError, ValueError):
            pass
        return None

    async def get_dividends(self, symbol: str) -> DividendData | None:
        """Get dividend history and metrics for a stock.

        Fetches dividend history and current dividend metrics from Yahoo Finance.
        """
        try:
            yahoo_symbol = self.normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            # Get dividend history (returns a pandas Series)
            div_history = ticker.dividends

            # Build dividend records from history
            history = []
            if not div_history.empty:
                for date, amount in div_history.items():
                    history.append(
                        DividendRecord(
                            ex_date=date.to_pydatetime(),
                            amount=float(amount),
                            currency=info.get("currency"),
                        )
                    )
                # Sort by date descending (most recent first)
                history.sort(key=lambda x: x.ex_date, reverse=True)

            # Calculate dividend growth rate (5-year CAGR) if enough history
            dividend_growth_rate = None
            if len(history) >= 20:  # At least 5 years of quarterly dividends
                recent_year = sum(d.amount for d in history[:4])  # Last 4 dividends
                five_years_ago = sum(
                    d.amount for d in history[16:20]
                )  # 4 dividends from 5 years ago
                if five_years_ago > 0 and recent_year > 0:
                    dividend_growth_rate = ((recent_year / five_years_ago) ** 0.2 - 1) * 100

            # Get ex-dividend date
            ex_div_timestamp = info.get("exDividendDate")
            ex_dividend_date = None
            if ex_div_timestamp:
                ex_dividend_date = datetime.fromtimestamp(ex_div_timestamp, tz=UTC)

            return DividendData(
                symbol=SymbolMapper.normalize(symbol),
                dividend_yield=info.get("dividendYield"),
                dividend_rate=info.get("dividendRate"),
                payout_ratio=info.get("payoutRatio"),
                ex_dividend_date=ex_dividend_date,
                history=history[:40],  # Last 40 dividends (~10 years quarterly)
                five_year_avg_yield=info.get("fiveYearAvgDividendYield"),
                dividend_growth_rate=dividend_growth_rate,
                last_updated=datetime.now(UTC),
            )
        except Exception as e:
            logger.error(f"Error fetching dividends for {symbol}: {e}")
            return None
