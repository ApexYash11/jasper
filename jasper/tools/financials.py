from typing import Any, List, Dict
import asyncio
import json
import os
import time
import aiosqlite
from .exceptions import DataProviderError
from ..core.config import JASPER_HOME

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


# ---------------------------------------------------------------------------
# Disk-backed persistent cache (L2) — survives process restarts
# Uses aiosqlite for truly async, concurrency-safe reads/writes.
# Best-effort: failures degrade silently to avoid blocking queries.
# ---------------------------------------------------------------------------
_DISK_CACHE_DB = JASPER_HOME / "cache.db"
_DISK_CACHE_DB.parent.mkdir(parents=True, exist_ok=True)


async def _disk_cache_get(key: str):
    try:
        async with aiosqlite.connect(str(_DISK_CACHE_DB)) as db:
            async with db.execute(
                "SELECT ts, data FROM cache WHERE key = ?", (key,)
            ) as cur:
                row = await cur.fetchone()
                if row:
                    ts, data = row
                    if (time.monotonic() - ts) < _CACHE_TTL:
                        return json.loads(data)
                    await db.execute("DELETE FROM cache WHERE key = ?", (key,))
                    await db.commit()
    except Exception:
        return None


async def _disk_cache_set(key: str, data) -> None:
    try:
        async with aiosqlite.connect(str(_DISK_CACHE_DB)) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, ts REAL, data TEXT)"
            )
            await db.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?)",
                (key, time.monotonic(), json.dumps(data, default=str)),
            )
            await db.commit()
    except Exception:
        pass  # disk cache is best-effort


# --- Financial Data Router ---
# Aggregates multiple data providers to ensure reliability.
# Providers are tried in order; the first successful response wins.
class FinancialDataRouter:
    def __init__(self, providers: List[Any]):
        self.providers = providers
        self._call_counts: Dict[str, int] = {}

    def _increment_call_count(self, provider_name: str) -> None:
        self._call_counts[provider_name] = self._call_counts.get(provider_name, 0) + 1

    async def check_provider_health(self) -> Dict[str, bool]:
        """Ping each provider to check availability."""
        results = {}
        for provider in self.providers:
            name = type(provider).__name__
            method = getattr(provider, "income_statement", None)
            if method is None:
                results[name] = False
                continue
            try:
                await asyncio.wait_for(method("AAPL"), timeout=10)
                results[name] = True
            except Exception:
                results[name] = False
        return results

    def get_call_counts(self) -> Dict[str, int]:
        """Return per-provider API call counts for this session."""
        return dict(self._call_counts)

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
                    result = await method(symbol)
                    self._increment_call_count(type(provider).__name__)
                    return result
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
                # L1: In-memory cache (fast)
                entry = _cache.get(cache_key)
                if entry is not None and (time.monotonic() - entry[0]) < _CACHE_TTL:
                    return entry[1]
                # L2: Disk cache (persistent across restarts)
                disk = await _disk_cache_get(cache_key)
                if disk is not None:
                    _cache[cache_key] = (time.monotonic(), disk)
                    return disk
                # Cache miss — fetch while holding the lock.
                # Other tasks for the same key block here; when they enter, the
                # result will be in the cache.
                result = await self._fetch_from_providers(method_name, ticker, label)
                _cache[cache_key] = (time.monotonic(), result)
                await _disk_cache_set(cache_key, result)
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
