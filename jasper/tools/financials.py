import httpx 
from typing import Dict, Any, List
from .exceptions import DataProviderError

class FinancialDataError(Exception):
    """Custom exception for financial data retrieval errors."""
    pass


# --- Financial Data Router ---
# Aggregates multiple data providers to ensure reliability
class FinancialDataRouter:
    def __init__(self, providers: List[Any]):
        self.providers = providers

    async def fetch_income_statement(self, ticker: str) -> Dict:
        errors = []
        for provider in self.providers:
            try:
                return await provider.income_statement(ticker)
            except Exception as e:
                errors.append(str(e))

        error_details = "; ".join(errors)
        raise DataProviderError(
            f"All providers failed to fetch income statement for {ticker}. "
            f"Details: {error_details}. "
            f"Verify the ticker is valid (e.g., AAPL, RELIANCE.NS, INFY.NS)."
        )


class FinancialClient:
    def __init__(self, timeout: float = 10.0):
        self.client = httpx.AsyncClient(timeout=timeout)

    async def fetch_financial_statement(self, entity: str) -> Dict[str, Any]:
        """Fetch financial statement data for a given entity."""
        try:
            # Placeholder URL; replace with actual financial data API endpoint
            url = f"https://api.example.com/financials/{entity}"
            request = httpx.Request("GET", url)
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("Not Found", request=request, response=response)  # Placeholder for demonstration
        except httpx.HTTPStatusError as e:
            raise FinancialDataError(f"Failed to fetch data for {entity}: {e}") from e