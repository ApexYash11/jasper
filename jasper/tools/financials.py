from typing import Any, List
from .exceptions import DataProviderError


class FinancialDataError(Exception):
    """Custom exception for financial data retrieval errors."""


# --- Financial Data Router ---
# Aggregates multiple data providers to ensure reliability.
# Providers are tried in order; the first successful response wins.
class FinancialDataRouter:
    def __init__(self, providers: List[Any]):
        self.providers = providers

    async def _fetch_with_fallback(
        self, method_name: str, ticker: str, label: str
    ):
        """Generic fallback loop: try each provider's method in order."""
        errors = []
        for provider in self.providers:
            method = getattr(provider, method_name, None)
            if method is None:
                continue
            try:
                return await method(ticker)
            except Exception as e:
                errors.append(f"{type(provider).__name__}: {e}")

        raise DataProviderError(
            f"All providers failed to fetch {label} for {ticker}. "
            f"Details: {'; '.join(errors)}. "
            f"Verify the ticker is valid (e.g. AAPL, RELIANCE.NS, INFY.NS)."
        )

    async def fetch_income_statement(self, ticker: str):
        return await self._fetch_with_fallback(
            "income_statement", ticker, "income statement"
        )

    async def fetch_balance_sheet(self, ticker: str):
        return await self._fetch_with_fallback(
            "balance_sheet", ticker, "balance sheet"
        )
