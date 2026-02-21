import httpx
from typing import Dict, List
from ..exceptions import DataProviderError


# --- Alpha Vantage Client ---
# Handles direct communication with the Alpha Vantage API.
# All requests are made asynchronously and will not block the event loop.
class AlphaVantageClient:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _fetch(self, params: dict) -> dict:
        """Shared HTTP fetch helper with consistent error handling."""
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self.BASE_URL, params=params)
        if r.status_code != 200:
            raise DataProviderError(
                f"Alpha Vantage HTTP {r.status_code} for {params.get('symbol')}"
            )
        data = r.json()
        # Detect API-level errors (e.g. rate limit, invalid key)
        if "Note" in data:
            raise DataProviderError(
                f"Alpha Vantage rate-limited: {data['Note']}"
            )
        if "Information" in data:
            raise DataProviderError(
                f"Alpha Vantage info: {data['Information']}"
            )
        return data

    async def income_statement(self, ticker: str) -> List[Dict]:
        """Fetch annual income statement reports from Alpha Vantage."""
        data = await self._fetch({
            "function": "INCOME_STATEMENT",
            "symbol": ticker,
            "apikey": self.api_key,
        })
        if "annualReports" not in data:
            raise DataProviderError(
                f"Alpha Vantage malformed income_statement response for {ticker}"
            )
        return data["annualReports"]

    async def balance_sheet(self, ticker: str) -> List[Dict]:
        """Fetch annual balance sheet reports from Alpha Vantage."""
        data = await self._fetch({
            "function": "BALANCE_SHEET",
            "symbol": ticker,
            "apikey": self.api_key,
        })
        if "annualReports" not in data:
            raise DataProviderError(
                f"Alpha Vantage malformed balance_sheet response for {ticker}"
            )
        return data["annualReports"]
