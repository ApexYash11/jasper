import asyncio
import uuid
from unittest.mock import MagicMock

import pytest

from jasper.agent.executor import Executor
from jasper.core.state import Jasperstate, Task


@pytest.mark.asyncio
async def test_executor_fetches_correct_ticker_per_task():
    """Regression: concurrent tasks must fetch their own ticker, not the last one."""
    fetch_calls = []

    router = MagicMock()

    async def mock_income(ticker):
        fetch_calls.append(ticker)
        return [{"fiscalDateEnding": "2024-01-01", "totalRevenue": "1000"}]

    router.fetch_income_statement = mock_income

    executor = Executor(router)
    state = Jasperstate(query="test")
    state.max_retries = 0

    tasks = [
        Task(
            id=str(uuid.uuid4()),
            description=f"Fetch {t}",
            tool_name="income_statement",
            tool_args={"ticker": t},
            status="pending",
        )
        for t in ["AAPL", "MSFT", "GOOG"]
    ]
    state.plan = tasks

    await asyncio.gather(*[executor.execute_task(state, t) for t in tasks])

    assert sorted(fetch_calls) == ["AAPL", "GOOG", "MSFT"]
    assert fetch_calls.count("AAPL") == 1
    assert fetch_calls.count("MSFT") == 1
    assert fetch_calls.count("GOOG") == 1
