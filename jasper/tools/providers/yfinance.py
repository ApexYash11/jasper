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
            loop = asyncio.get_event_loop()
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
            loop = asyncio.get_event_loop()
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
