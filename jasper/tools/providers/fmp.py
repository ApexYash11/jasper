import httpx
from typing import Dict, List, Optional
from ..exceptions import DataProviderError


class FMPClient:
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15)
        return self._client

    async def _fetch(self, path: str, params: dict) -> list:
        client = await self._get_client()
        r = await client.get(
            f"{self.BASE_URL}{path}", params={"apikey": self.api_key, **params}
        )
        if r.status_code != 200:
            raise DataProviderError(f"FMP HTTP {r.status_code} for {params}")
        data = r.json()
        if isinstance(data, dict) and "Error Message" in data:
            raise DataProviderError(f"FMP error: {data['Error Message']}")
        if not isinstance(data, list) or not data:
            raise DataProviderError(f"FMP: empty response for {path}")
        return data

    async def income_statement(self, ticker: str) -> List[Dict]:
        data = await self._fetch(f"/income-statement/{ticker}", {"limit": 5})
        return [
            {
                "fiscalDateEnding": d.get("date", ""),
                "totalRevenue": str(d.get("revenue", 0)),
                "netIncome": str(d.get("netIncome", 0)),
                "grossProfit": str(d.get("grossProfit", 0)),
            }
            for d in data
        ]

    async def balance_sheet(self, ticker: str) -> List[Dict]:
        data = await self._fetch(f"/balance-sheet-statement/{ticker}", {"limit": 5})
        return [
            {
                "fiscalDateEnding": d.get("date", ""),
                "totalAssets": str(d.get("totalAssets", 0)),
                "totalLiabilities": str(d.get("totalLiabilities", 0)),
                "totalEquity": str(d.get("totalStockholdersEquity", 0)),
            }
            for d in data
        ]

    async def cash_flow(self, ticker: str) -> List[Dict]:
        data = await self._fetch(f"/cash-flow-statement/{ticker}", {"limit": 5})
        return [
            {
                "fiscalDateEnding": d.get("date", ""),
                "operatingCashflow": str(d.get("operatingCashFlow", 0)),
                "capitalExpenditures": str(d.get("capitalExpenditure", 0)),
            }
            for d in data
        ]

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
