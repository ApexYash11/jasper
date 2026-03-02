import asyncio
import yfinance as yf
from typing import Dict, List
from ..exceptions import DataProviderError


# --- YFinance Client ---
# Handles direct communication with yfinance for global stock data.
# All synchronous yfinance calls are offloaded to a thread-pool via
# run_in_executor so they never block the asyncio event loop.
class YFinanceClient:
    """
    YFinance provider for global stocks (US, India, etc.)
    Supports tickers like: AAPL, RELIANCE.NS, INFY.NS, etc.
    """

    def __init__(self):
        pass

    @staticmethod
    def _safe_str(value, fallback="0") -> str:
        """Convert a pandas/numpy value to a plain string, handling NaN/None."""
        if value is None:
            return fallback
        try:
            import math
            if math.isnan(float(value)):
                return fallback
        except (TypeError, ValueError):
            pass
        return str(value)

    @staticmethod
    def _row_get(row, *keys) -> str:
        """Try multiple column name variants (handles locale/version differences)."""
        for key in keys:
            val = row.get(key)
            if val is not None:
                return YFinanceClient._safe_str(val)
        return "0"

    async def income_statement(self, ticker: str) -> List[Dict]:
        """Fetch income statement data from yfinance (non-blocking)."""
        try:
            loop = asyncio.get_running_loop()
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)
            # Use current API attr; fall back to legacy alias if needed
            quarterly = await loop.run_in_executor(
                None,
                lambda: getattr(stock, "quarterly_income_stmt",
                                getattr(stock, "quarterly_financials", None))
            )

            if quarterly is None or quarterly.empty:
                raise DataProviderError(f"No income statement data for {ticker}")

            result = []
            for date_key, row in quarterly.items():
                date_str = str(date_key).split()[0]
                result.append({
                    "fiscalDateEnding": date_str,
                    "totalRevenue": self._row_get(row, "Total Revenue", "TotalRevenue"),
                    "totalOperatingExpense": self._row_get(
                        row, "Total Operating Expense", "Operating Expense"
                    ),
                    "netIncome": self._row_get(row, "Net Income", "NetIncome"),
                    "grossProfit": self._row_get(row, "Gross Profit", "GrossProfit"),
                    "operatingIncome": self._row_get(
                        row, "Operating Income", "OperatingIncome"
                    ),
                })

            if not result:
                raise DataProviderError(f"Empty income statement for {ticker}")

            return result

        except Exception as e:
            if isinstance(e, DataProviderError):
                raise
            raise DataProviderError(f"YFinance income_statement failed for {ticker}: {str(e)}")

    async def balance_sheet(self, ticker: str) -> List[Dict]:
        """Fetch balance sheet data from yfinance (non-blocking)."""
        try:
            loop = asyncio.get_running_loop()
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)
            balance = await loop.run_in_executor(
                None, lambda: stock.quarterly_balance_sheet
            )

            if balance is None or balance.empty:
                raise DataProviderError(f"No balance sheet data for {ticker}")

            result = []
            for date_key, row in balance.items():
                date_str = str(date_key).split()[0]
                result.append({
                    "fiscalDateEnding": date_str,
                    "totalAssets": self._row_get(
                        row, "Total Assets", "TotalAssets"
                    ),
                    "totalLiabilities": self._row_get(
                        row,
                        "Total Liab",
                        "Total Liabilities Net Minority Interest",
                        "TotalLiabilitiesNetMinorityInterest",
                    ),
                    "totalEquity": self._row_get(
                        row,
                        "Total Stockholder Equity",
                        "Stockholders Equity",
                        "StockholdersEquity",
                    ),
                    "totalDebt": self._row_get(
                        row, "Long-Term Debt", "Long Term Debt", "LongTermDebt"
                    ),
                    "cashAndEquivalents": self._row_get(
                        row,
                        "Cash And Cash Equivalents",
                        "Cash",
                        "CashAndCashEquivalents",
                    ),
                })

            if not result:
                raise DataProviderError(f"Empty balance sheet for {ticker}")

            return result

        except Exception as e:
            if isinstance(e, DataProviderError):
                raise
            raise DataProviderError(f"YFinance balance_sheet failed for {ticker}: {str(e)}")

    async def cash_flow(self, ticker: str) -> List[Dict]:
        """Fetch quarterly cash flow statement from yfinance (non-blocking)."""
        try:
            loop = asyncio.get_running_loop()
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)
            cf = await loop.run_in_executor(
                None,
                lambda: getattr(stock, "quarterly_cashflow",
                                getattr(stock, "cashflow", None))
            )

            if cf is None or cf.empty:
                raise DataProviderError(f"No cash flow data for {ticker}")

            result = []
            for date_key, row in cf.items():
                date_str = str(date_key).split()[0]
                result.append({
                    "fiscalDateEnding": date_str,
                    "operatingCashflow": self._row_get(
                        row,
                        "Cash Flow From Continuing Operating Activities",
                        "Operating Cash Flow",
                        "Total Cash From Operating Activities",
                    ),
                    "capitalExpenditures": self._row_get(
                        row,
                        "Capital Expenditure",
                        "Capital Expenditures",
                        "Purchases Of Property Plant And Equipment",
                    ),
                    "freeCashFlow": self._row_get(
                        row, "Free Cash Flow"
                    ),
                    "netInvestingActivities": self._row_get(
                        row,
                        "Net Cash Used For Investing Activities",
                        "Total Cashflows From Investing Activities",
                    ),
                    "netFinancingActivities": self._row_get(
                        row,
                        "Net Cash Used Provided By Financing Activities",
                        "Total Cash From Financing Activities",
                    ),
                })

            if not result:
                raise DataProviderError(f"Empty cash flow for {ticker}")
            return result

        except Exception as e:
            if isinstance(e, DataProviderError):
                raise
            raise DataProviderError(f"YFinance cash_flow failed for {ticker}: {str(e)}")

    async def realtime_quote(self, ticker: str) -> Dict:
        """Fetch real-time quote and key valuation metrics from yfinance (non-blocking)."""
        try:
            loop = asyncio.get_running_loop()
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)
            info = await loop.run_in_executor(None, lambda: stock.info)

            if not info or not isinstance(info, dict):
                raise DataProviderError(f"No quote/info data available for {ticker}")

            # Some invalid symbols return a dict-shaped payload with nearly all fields missing.
            # Treat this as a provider failure so router-level symbol fallback can continue.
            critical_markers = [
                info.get("currentPrice"),
                info.get("regularMarketPrice"),
                info.get("longName"),
                info.get("shortName"),
                info.get("marketCap"),
            ]
            if all(v in (None, "", "N/A") for v in critical_markers):
                raise DataProviderError(f"No actionable quote fields for {ticker}")

            def _get(key: str, fallback: str = "N/A") -> str:
                val = info.get(key)
                return YFinanceClient._safe_str(val, fallback=fallback)

            # Return a single flat dict (not a list — validator handles this)
            return {
                "fiscalDateEnding": "current",
                "ticker": ticker,
                "name": _get("longName"),
                "sector": _get("sector"),
                "currentPrice": _get("currentPrice", fallback=_get("regularMarketPrice")),
                "previousClose": _get("previousClose"),
                "marketCap": _get("marketCap"),
                "peRatioTTM": _get("trailingPE"),
                "forwardPE": _get("forwardPE"),
                "priceToBook": _get("priceToBook"),
                "evToEbitda": _get("enterpriseToEbitda"),
                "dividendYield": _get("dividendYield"),
                "week52High": _get("fiftyTwoWeekHigh"),
                "week52Low": _get("fiftyTwoWeekLow"),
                "volume": _get("volume"),
                "beta": _get("beta"),
                "epsTTM": _get("trailingEps"),
                "returnOnEquity": _get("returnOnEquity"),
                "returnOnAssets": _get("returnOnAssets"),
                "grossMargins": _get("grossMargins"),
                "operatingMargins": _get("operatingMargins"),
                "revenueGrowth": _get("revenueGrowth"),
                "earningsGrowth": _get("earningsGrowth"),
            }

        except Exception as e:
            if isinstance(e, DataProviderError):
                raise
            raise DataProviderError(f"YFinance realtime_quote failed for {ticker}: {str(e)}")
