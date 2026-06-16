from typing import Any, List, Dict
import asyncio
import os
import time
from .exceptions import DataProviderError

# Alias so existing executor code that catches FinancialDataError still works
FinancialDataError = DataProviderError


# ---------------------------------------------------------------------------
# In-memory TTL cache — avoids redundant API calls within/across sessions
# Default TTL: 15 minutes (configurable via env var JASPER_CACHE_TTL_SECS)
# ---------------------------------------------------------------------------
_CACHE_TTL = int(os.getenv("JASPER_CACHE_TTL_SECS", "900"))  # 15 min default

_cache: Dict[str, tuple] = {}  # key -> (timestamp, data)
_cache_locks: Dict[str, asyncio.Lock] = {}


def _get_cache_lock(key: str) -> asyncio.Lock:
    if key not in _cache_locks:
        _cache_locks[key] = asyncio.Lock()
    return _cache_locks[key]


# Common exchange-symbol aliases for popular Indian equities.
_TICKER_ALIASES: Dict[str, str] = {
    "ICICIBANK": "ICICIBANK.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "RELIANCE": "RELIANCE.NS",
    "INFY": "INFY.NS",
    "TCS": "TCS.NS",
    "SBIN": "SBIN.NS",
    "ITC": "ITC.NS",
    "LT": "LT.NS",
}


def _ticker_candidates(ticker: str) -> List[str]:
    """Build ordered symbol candidates for provider lookups."""
    raw = (ticker or "").strip()
    if not raw:
        return []

    # Normalize spaces so "ICICI BANK" can map to ICICIBANK aliases.
    compact = raw.replace(" ", "")
    upper = compact.upper()

    candidates: List[str] = []

    def _add(sym: str) -> None:
        if sym and sym not in candidates:
            candidates.append(sym)

    _add(raw)
    if compact != raw:
        _add(compact)

    alias = _TICKER_ALIASES.get(upper)
    if alias:
        _add(alias)

    # Conservative fallback for likely Indian plain symbols lacking an exchange suffix.
    if "." not in upper and (upper.endswith("BANK") or upper in _TICKER_ALIASES):
        _add(f"{upper}.NS")

    return candidates


async def _cache_get_async(key: str):
    """Return cached value if still fresh, else None (evicting stale entries)."""
    async with _get_cache_lock(key):
        entry = _cache.get(key)
        if entry is None:
            return None
        if (time.monotonic() - entry[0]) < _CACHE_TTL:
            return entry[1]
        del _cache[key]  # evict stale entry to prevent unbounded growth
        return None


async def _cache_set_async(key: str, data) -> None:
    """Store data in the in-memory cache."""
    async with _get_cache_lock(key):
        _cache[key] = (time.monotonic(), data)


# --- Financial Data Router ---
# Aggregates multiple data providers to ensure reliability.
# Providers are tried in order; the first successful response wins.
class FinancialDataRouter:
    def __init__(self, providers: List[Any]):
        self.providers = providers

    async def _fetch_from_providers(self, method_name: str, ticker: str, label: str):
        """Try each provider in order until one succeeds. No caching."""
        errors = []
        symbol_candidates = _ticker_candidates(ticker)
        if not symbol_candidates:
            raise DataProviderError(f"Invalid ticker '{ticker}' for {label} fetch")

        for provider in self.providers:
            method = getattr(provider, method_name, None)
            if method is None:
                continue
            for symbol in symbol_candidates:
                try:
                    return await method(symbol)
                except Exception as e:
                    errors.append(f"{type(provider).__name__}({symbol}): {e}")

        raise DataProviderError(
            f"All providers failed to fetch {label} for {ticker}. "
            f"Tried symbols: {', '.join(symbol_candidates)}. "
            f"Details: {'; '.join(errors)}. "
            f"Verify the ticker is valid (e.g. AAPL, RELIANCE.NS, INFY.NS)."
        )

    async def _fetch_with_fallback(self, method_name: str, ticker: str, label: str):
        """Generic fallback loop with in-memory caching: try each provider in order.

        Uses per-key asyncio.Lock to ensure that concurrent tasks fetching the same
        ticker produce only one API call — the rest block and get the cached result.
        """
        use_cache = method_name != "realtime_quote"
        cache_key = f"{method_name}:{ticker.upper()}"

        if use_cache:
            async with _get_cache_lock(cache_key):
                # Check cache under lock (fast path for cached data)
                entry = _cache.get(cache_key)
                if entry is not None and (time.monotonic() - entry[0]) < _CACHE_TTL:
                    return entry[1]
                # Cache miss — fetch while holding the lock.
                # Other tasks for the same key block here; when they enter, the
                # result will be in the cache.
                result = await self._fetch_from_providers(method_name, ticker, label)
                _cache[cache_key] = (time.monotonic(), result)
                return result

        return await self._fetch_from_providers(method_name, ticker, label)

    async def fetch_income_statement(self, ticker: str):
        return await self._fetch_with_fallback(
            "income_statement", ticker, "income statement"
        )

    async def fetch_balance_sheet(self, ticker: str):
        return await self._fetch_with_fallback("balance_sheet", ticker, "balance sheet")

    async def fetch_cash_flow(self, ticker: str):
        return await self._fetch_with_fallback(
            "cash_flow", ticker, "cash flow statement"
        )

    async def fetch_realtime_quote(self, ticker: str):
        return await self._fetch_with_fallback(
            "realtime_quote", ticker, "real-time quote"
        )
