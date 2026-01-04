import yfinance as yf
from typing import Dict, List
from datetime import datetime
from ..exceptions import DataProviderError


# --- YFinance Client ---
# Handles direct communication with yfinance for global stock data
class YFinanceClient:
    """
    YFinance provider for global stocks (US, India, etc.)
    Supports tickers like: AAPL, RELIANCE.NS, INFY.NS, etc.
    """
    
    def __init__(self):
        pass

    async def income_statement(self, ticker: str) -> List[Dict]:
        """Fetch income statement data from yfinance."""
        try:
            stock = yf.Ticker(ticker)
            
            # Get quarterly income statement
            quarterly_financials = stock.quarterly_financials
            
            if quarterly_financials is None or quarterly_financials.empty:
                raise DataProviderError(f"No income statement data for {ticker}")
            
            # Convert to list of dicts (annual reports format for compatibility)
            result = []
            for date_key, row in quarterly_financials.items():
                # Convert date to string safely - works with both pandas Timestamp and datetime
                date_str = str(date_key).split()[0] if isinstance(date_key, (datetime, type(None))) else str(date_key).split()[0]
                report = {
                    "fiscalDateEnding": date_str,
                    "totalRevenue": str(row.get("Total Revenue", 0)),
                    "totalOperatingExpense": str(row.get("Total Operating Expense", 0)),
                    "netIncome": str(row.get("Net Income", 0)),
                }
                result.append(report)
            
            if not result:
                raise DataProviderError(f"Empty income statement for {ticker}")
            
            return result
            
        except Exception as e:
            if isinstance(e, DataProviderError):
                raise
            raise DataProviderError(f"YFinance failed for {ticker}: {str(e)}")

    async def balance_sheet(self, ticker: str) -> List[Dict]:
        """Fetch balance sheet data from yfinance."""
        try:
            stock = yf.Ticker(ticker)
            balance = stock.quarterly_balance_sheet
            
            if balance is None or balance.empty:
                raise DataProviderError(f"No balance sheet data for {ticker}")
            
            result = []
            for date_key, row in balance.items():
                # Convert date to string safely - works with both pandas Timestamp and datetime
                date_str = str(date_key).split()[0] if isinstance(date_key, (datetime, type(None))) else str(date_key).split()[0]
                report = {
                    "fiscalDateEnding": date_str,
                    "totalAssets": str(row.get("Total Assets", 0)),
                    "totalLiabilities": str(row.get("Total Liab", 0)),
                    "totalEquity": str(row.get("Total Stockholder Equity", 0)),
                    "totalDebt": str(row.get("Long-Term Debt", 0)),
                }
                result.append(report)
            
            if not result:
                raise DataProviderError(f"Empty balance sheet for {ticker}")
            
            return result
            
        except Exception as e:
            if isinstance(e, DataProviderError):
                raise
            raise DataProviderError(f"YFinance failed for {ticker}: {str(e)}")
