import httpx
from typing import Dict, List
from ..exceptions import DataProviderError


class AlphaVantageClient:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15)
        return self._client

    async def _fetch(self, params: dict) -> dict:
        client = await self._get_client()
        r = await client.get(self.BASE_URL, params=params)
        if r.status_code != 200:
            raise DataProviderError(
                f"Alpha Vantage HTTP {r.status_code} for {params.get('symbol')}"
            )
        data = r.json()
        if "Note" in data:
            raise DataProviderError(f"Alpha Vantage rate-limited: {data['Note']}")
        if "Information" in data:
            raise DataProviderError(f"Alpha Vantage info: {data['Information']}")
        return data

    async def income_statement(self, ticker: str) -> List[Dict]:
        """Fetch annual + quarterly income statement reports from Alpha Vantage."""
        data = await self._fetch(
            {
                "function": "INCOME_STATEMENT",
                "symbol": ticker,
                "apikey": self.api_key,
            }
        )
        reports = []
        reports.extend(data.get("annualReports", []))
        reports.extend(data.get("quarterlyReports", []))
        if not reports:
            raise DataProviderError(
                f"Alpha Vantage malformed income_statement response for {ticker}"
            )
        return reports

    async def balance_sheet(self, ticker: str) -> List[Dict]:
        """Fetch annual + quarterly balance sheet reports from Alpha Vantage."""
        data = await self._fetch(
            {
                "function": "BALANCE_SHEET",
                "symbol": ticker,
                "apikey": self.api_key,
            }
        )
        reports = []
        reports.extend(data.get("annualReports", []))
        reports.extend(data.get("quarterlyReports", []))
        if not reports:
            raise DataProviderError(
                f"Alpha Vantage malformed balance_sheet response for {ticker}"
            )
        return reports

    async def cash_flow(self, ticker: str) -> List[Dict]:
        """Fetch annual + quarterly cash flow statements from Alpha Vantage."""
        data = await self._fetch(
            {
                "function": "CASH_FLOW",
                "symbol": ticker,
                "apikey": self.api_key,
            }
        )
        reports = []
        reports.extend(data.get("annualReports", []))
        reports.extend(data.get("quarterlyReports", []))
        if not reports:
            raise DataProviderError(
                f"Alpha Vantage malformed cash_flow response for {ticker}"
            )
        return reports

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
