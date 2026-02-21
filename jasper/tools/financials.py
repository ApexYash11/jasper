from typing import Any, List, Dict
import time
from .exceptions import DataProviderError


class FinancialDataError(Exception):
    """Custom exception for financial data retrieval errors."""


# ---------------------------------------------------------------------------
# In-memory TTL cache — avoids redundant API calls within/across sessions
# Default TTL: 15 minutes (configurable via env var JASPER_CACHE_TTL_SECS)
# ---------------------------------------------------------------------------
import os as _os
_CACHE_TTL = int(_os.getenv("JASPER_CACHE_TTL_SECS", "900"))  # 15 min default

_cache: Dict[str, tuple] = {}  # key -> (timestamp, data)


def _cache_get(key: str):
    """Return cached value if still fresh, else None (evicting stale entries)."""
    entry = _cache.get(key)
    if entry is None:
        return None
    if (time.monotonic() - entry[0]) < _CACHE_TTL:
        return entry[1]
    del _cache[key]  # evict stale entry to prevent unbounded growth
    return None


def _cache_set(key: str, data) -> None:
    """Store data in the in-memory cache."""
    _cache[key] = (time.monotonic(), data)


# --- Financial Data Router ---
# Aggregates multiple data providers to ensure reliability.
# Providers are tried in order; the first successful response wins.
class FinancialDataRouter:
    def __init__(self, providers: List[Any]):
        self.providers = providers

    async def _fetch_with_fallback(
        self, method_name: str, ticker: str, label: str
    ):
        """Generic fallback loop with in-memory caching: try each provider in order."""
        # Real-time quotes must never be served from a stale cache
        use_cache = method_name != "realtime_quote"
        cache_key = f"{method_name}:{ticker.upper()}"
        if use_cache:
            cached = _cache_get(cache_key)
            if cached is not None:
                return cached

        errors = []
        for provider in self.providers:
            method = getattr(provider, method_name, None)
            if method is None:
                continue
            try:
                result = await method(ticker)
                if use_cache:
                    _cache_set(cache_key, result)
                return result
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

    async def fetch_cash_flow(self, ticker: str):
        return await self._fetch_with_fallback(
            "cash_flow", ticker, "cash flow statement"
        )

    async def fetch_realtime_quote(self, ticker: str):
        return await self._fetch_with_fallback(
            "realtime_quote", ticker, "real-time quote"
        )
