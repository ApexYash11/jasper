import httpx
from typing import Optional, Dict, Any
from tools.exceptions import DataProviderError

class AlphaVantageClient:
  BASE_URL = "https://www.alphavantage.co/query"

  def __init__(self, api_key: str):
    self.api_key = api_key

  async def income_statement(self, ticker: str) -> Dict[str, Any]:
    """Fetch income statement data for a given ticker symbol."""
    params = {
      "function": "INCOME_STATEMENT",
      "symbol": ticker,
      "apikey": self.api_key
    }
    async with httpx.AsyncClient(timeout=10) as client:
      r = await client.get(self.BASE_URL, params=params)

    if r.status_code != 200:
      raise DataProviderError("Alpha Vantage HTTP error")

    data = r.json()
    if "annualReports" not in data:
      raise DataProviderError("Alpha Vantage malformed response")
    
    return data["annualReports"]


