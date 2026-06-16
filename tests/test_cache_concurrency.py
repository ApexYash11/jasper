import asyncio
from unittest.mock import AsyncMock

import pytest

from jasper.tools.financials import FinancialDataRouter, _cache, _cache_locks


@pytest.mark.asyncio
async def test_fetch_with_fallback_no_duplicate_api_calls():
    """Regression: concurrent fetches for same ticker must result in one API call, not N."""
    _cache.clear()

    call_count = 0

    async def mock_income(symbol):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.02)
        return [{"fiscalDateEnding": "2024-01-01", "totalRevenue": "1000"}]

    mock_provider = AsyncMock()
    mock_provider.income_statement = mock_income

    router = FinancialDataRouter([mock_provider])

    async def fetch():
        return await router._fetch_with_fallback(
            "income_statement", "AAPL", "income statement"
        )

    results = await asyncio.gather(*[fetch() for _ in range(10)])

    assert call_count == 1, f"Expected 1 API call, got {call_count} (race condition)"
    assert all(r == results[0] for r in results), "All results must be identical"

    _cache.clear()
    _cache_locks.clear()
