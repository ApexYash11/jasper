"""
Unit tests for Jasper critical fixes.

Tests cover:
  - Exception hierarchy (errors.py)
  - Logger no longer prints to stdout (logger.py)
  - Executor dispatches income_statement AND balance_sheet (executor.py)
  - FinancialDataRouter.fetch_balance_sheet (financials.py)
  - AlphaVantageClient.balance_sheet API call (alpha_vantage.py)
  - YFinanceClient uses run_in_executor (yfinance.py)
  - Config demo key warning text (config.py)
  - Version command uses importlib.metadata (cli/main.py)
  - Export persists report to disk (cli/main.py)
  - PDF template uses conditional status classes (template)
"""

import asyncio
import io
import json
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


# ─────────────────────────────────────────────
# 1. Exception hierarchy
# ─────────────────────────────────────────────
class TestExceptionHierarchy:
    def test_base_exception_exists(self):
        from jasper.core.errors import JasperError
        assert issubclass(JasperError, Exception)

    def test_all_subclasses_inherit_jasper_error(self):
        from jasper.core.errors import (
            JasperError,
            EntityExtractionError,
            PlannerError,
            DataFetchError,
            SynthesisError,
            ValidationError,
            ConfigurationError,
        )
        for cls in (EntityExtractionError, PlannerError, DataFetchError,
                    SynthesisError, ValidationError, ConfigurationError):
            assert issubclass(cls, JasperError), f"{cls.__name__} must inherit JasperError"

    def test_can_catch_specific_via_base(self):
        from jasper.core.errors import JasperError, PlannerError
        with pytest.raises(JasperError):
            raise PlannerError("bad plan")


# ─────────────────────────────────────────────
# 2. Logger does NOT print to stdout
# ─────────────────────────────────────────────
class TestLogger:
    def test_log_does_not_print_to_stdout(self, capsys):
        from jasper.observability.logger import SessionLogger
        logger = SessionLogger()
        logger.log("TEST_EVENT", {"key": "value"})
        captured = capsys.readouterr()
        assert captured.out == "", "Logger must not print to stdout"

    def test_rich_logger_overrides_correctly(self, capsys):
        """RichLogger should update Live panel, not print."""
        from jasper.cli.main import RichLogger
        live_mock = MagicMock()
        live_mock.update = MagicMock()
        rl = RichLogger(live=live_mock)
        rl.log("PLANNER_STARTED", {})
        captured = capsys.readouterr()
        assert captured.out == "", "RichLogger must not print to stdout"


# ─────────────────────────────────────────────
# 3. Executor dispatches both tool types
# ─────────────────────────────────────────────
class TestExecutorDispatch:
    def _make_executor(self, mock_router):
        from jasper.agent.executor import Executor
        from jasper.observability.logger import SessionLogger
        return Executor(financial_router=mock_router, logger=SessionLogger())

    def _make_state(self):
        from jasper.core.state import Jasperstate
        return Jasperstate(query="test")

    def _make_task(self, tool_name, ticker="AAPL"):
        from jasper.core.state import Task
        return Task(
            id="t1",
            description=f"Fetch {tool_name} for {ticker}",
            tool_name=tool_name,
            tool_args={"ticker": ticker},
        )

    @pytest.mark.asyncio
    async def test_income_statement_dispatched(self):
        mock_router = MagicMock()
        mock_router.fetch_income_statement = AsyncMock(return_value=[
            {"fiscalDateEnding": "2024-09-30", "totalRevenue": "100000"}
        ])
        executor = self._make_executor(mock_router)
        state = self._make_state()
        task = self._make_task("income_statement")

        await executor.execute_task(state, task)

        mock_router.fetch_income_statement.assert_awaited_once_with("AAPL")
        assert task.status == "completed"

    @pytest.mark.asyncio
    async def test_financial_statement_alias_dispatched(self):
        """financial_statement is an alias for income_statement."""
        mock_router = MagicMock()
        mock_router.fetch_income_statement = AsyncMock(return_value=[
            {"fiscalDateEnding": "2024-09-30", "totalRevenue": "100000"}
        ])
        executor = self._make_executor(mock_router)
        state = self._make_state()
        task = self._make_task("financial_statement")

        await executor.execute_task(state, task)

        mock_router.fetch_income_statement.assert_awaited_once_with("AAPL")
        assert task.status == "completed"

    @pytest.mark.asyncio
    async def test_balance_sheet_dispatched(self):
        mock_router = MagicMock()
        mock_router.fetch_balance_sheet = AsyncMock(return_value=[
            {"fiscalDateEnding": "2024-09-30", "totalAssets": "300000"}
        ])
        executor = self._make_executor(mock_router)
        state = self._make_state()
        task = self._make_task("balance_sheet")

        await executor.execute_task(state, task)

        mock_router.fetch_balance_sheet.assert_awaited_once_with("AAPL")
        assert task.status == "completed"

    @pytest.mark.asyncio
    async def test_unknown_tool_sets_failed_status(self):
        mock_router = MagicMock()
        executor = self._make_executor(mock_router)
        state = self._make_state()
        task = self._make_task("cash_flow_statement")  # not yet implemented

        await executor.execute_task(state, task)

        assert task.status == "failed"
        assert "cash_flow_statement" in (task.error or "")

    @pytest.mark.asyncio
    async def test_missing_ticker_sets_failed_status(self):
        from jasper.core.state import Task
        mock_router = MagicMock()
        executor = self._make_executor(mock_router)
        state = self._make_state()
        task = Task(
            id="t2",
            description="Fetch income statement",
            tool_name="income_statement",
            tool_args={},  # no ticker
        )

        await executor.execute_task(state, task)

        assert task.status == "failed"
        assert "ticker" in (task.error or "").lower()

    @pytest.mark.asyncio
    async def test_failed_task_result_stored_in_state(self):
        """Successful tasks must store result in state.task_results."""
        mock_router = MagicMock()
        data = [{"fiscalDateEnding": "2024-09-30", "totalRevenue": "999"}]
        mock_router.fetch_income_statement = AsyncMock(return_value=data)
        executor = self._make_executor(mock_router)
        state = self._make_state()
        task = self._make_task("income_statement")

        await executor.execute_task(state, task)

        assert "t1" in state.task_results
        assert state.task_results["t1"] == data


# ─────────────────────────────────────────────
# 4. FinancialDataRouter
# ─────────────────────────────────────────────
class TestFinancialDataRouter:
    @pytest.mark.asyncio
    async def test_fetch_income_statement_first_provider_wins(self):
        from jasper.tools.financials import FinancialDataRouter
        p1 = MagicMock()
        p1.income_statement = AsyncMock(return_value=[{"fiscalDateEnding": "2024"}])
        p2 = MagicMock()
        p2.income_statement = AsyncMock()

        router = FinancialDataRouter(providers=[p1, p2])
        result = await router.fetch_income_statement("AAPL")

        assert result[0]["fiscalDateEnding"] == "2024"
        p2.income_statement.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fetch_income_statement_falls_back_on_error(self):
        from jasper.tools.financials import FinancialDataRouter
        p1 = MagicMock()
        p1.income_statement = AsyncMock(side_effect=Exception("AV failed"))
        p2 = MagicMock()
        p2.income_statement = AsyncMock(return_value=[{"fiscalDateEnding": "2024"}])

        router = FinancialDataRouter(providers=[p1, p2])
        result = await router.fetch_income_statement("AAPL")

        assert result[0]["fiscalDateEnding"] == "2024"

    @pytest.mark.asyncio
    async def test_fetch_balance_sheet_exists(self):
        from jasper.tools.financials import FinancialDataRouter
        p1 = MagicMock()
        p1.balance_sheet = AsyncMock(return_value=[{"fiscalDateEnding": "2024", "totalAssets": "1000"}])

        router = FinancialDataRouter(providers=[p1])
        result = await router.fetch_balance_sheet("AAPL")

        p1.balance_sheet.assert_awaited_once_with("AAPL")
        assert result[0]["totalAssets"] == "1000"

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_data_provider_error(self):
        from jasper.tools.financials import FinancialDataRouter
        from jasper.tools.exceptions import DataProviderError
        p1 = MagicMock()
        p1.income_statement = AsyncMock(side_effect=Exception("p1 failed"))
        p2 = MagicMock()
        p2.income_statement = AsyncMock(side_effect=Exception("p2 failed"))

        router = FinancialDataRouter(providers=[p1, p2])
        with pytest.raises(DataProviderError):
            await router.fetch_income_statement("FAKE")

    @pytest.mark.asyncio
    async def test_provider_without_method_is_skipped(self):
        """Providers without the requested method are silently skipped."""
        from jasper.tools.financials import FinancialDataRouter
        p1 = MagicMock(spec=[])  # no balance_sheet attribute
        p2 = MagicMock()
        p2.balance_sheet = AsyncMock(return_value=[{"fiscalDateEnding": "2024"}])

        router = FinancialDataRouter(providers=[p1, p2])
        result = await router.fetch_balance_sheet("AAPL")
        assert result[0]["fiscalDateEnding"] == "2024"


# ─────────────────────────────────────────────
# 5. AlphaVantageClient
# ─────────────────────────────────────────────
class TestAlphaVantageClient:
    @pytest.mark.asyncio
    async def test_income_statement_parses_annual_reports(self):
        import httpx
        from jasper.tools.providers.alpha_vantage import AlphaVantageClient

        fake_response = httpx.Response(
            200,
            json={"annualReports": [{"fiscalDateEnding": "2023-12-31", "totalRevenue": "5000"}]},
            request=httpx.Request("GET", "https://test"),
        )
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=fake_response)):
            client = AlphaVantageClient(api_key="test")
            result = await client.income_statement("AAPL")

        assert result[0]["totalRevenue"] == "5000"

    @pytest.mark.asyncio
    async def test_balance_sheet_parses_annual_reports(self):
        import httpx
        from jasper.tools.providers.alpha_vantage import AlphaVantageClient

        fake_response = httpx.Response(
            200,
            json={"annualReports": [{"fiscalDateEnding": "2023-12-31", "totalAssets": "300000"}]},
            request=httpx.Request("GET", "https://test"),
        )
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=fake_response)):
            client = AlphaVantageClient(api_key="test")
            result = await client.balance_sheet("AAPL")

        assert result[0]["totalAssets"] == "300000"

    @pytest.mark.asyncio
    async def test_rate_limit_note_raises_error(self):
        import httpx
        from jasper.tools.providers.alpha_vantage import AlphaVantageClient
        from jasper.tools.exceptions import DataProviderError

        fake_response = httpx.Response(
            200,
            json={"Note": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."},
            request=httpx.Request("GET", "https://test"),
        )
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=fake_response)):
            client = AlphaVantageClient(api_key="demo")
            with pytest.raises(DataProviderError, match="rate-limited"):
                await client.income_statement("AAPL")

    @pytest.mark.asyncio
    async def test_missing_annual_reports_raises_error(self):
        import httpx
        from jasper.tools.providers.alpha_vantage import AlphaVantageClient
        from jasper.tools.exceptions import DataProviderError

        fake_response = httpx.Response(
            200,
            json={"Error Message": "Invalid API call"},
            request=httpx.Request("GET", "https://test"),
        )
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=fake_response)):
            client = AlphaVantageClient(api_key="test")
            with pytest.raises(DataProviderError):
                await client.income_statement("FAKE")


# ─────────────────────────────────────────────
# 6. YFinanceClient uses run_in_executor
# ─────────────────────────────────────────────
class TestYFinanceClientAsync:
    def test_income_statement_uses_run_in_executor(self):
        import inspect
        from jasper.tools.providers.yfinance import YFinanceClient
        src = inspect.getsource(YFinanceClient.income_statement)
        assert "run_in_executor" in src, \
            "income_statement must use run_in_executor to avoid blocking the event loop"

    def test_balance_sheet_uses_run_in_executor(self):
        import inspect
        from jasper.tools.providers.yfinance import YFinanceClient
        src = inspect.getsource(YFinanceClient.balance_sheet)
        assert "run_in_executor" in src, \
            "balance_sheet must use run_in_executor to avoid blocking the event loop"

    def test_deprecated_quarterly_financials_not_used(self):
        import inspect
        from jasper.tools.providers.yfinance import YFinanceClient
        src = inspect.getsource(YFinanceClient.income_statement)
        # The old direct attribute access (not the getattr fallback) should be gone
        assert "stock.quarterly_financials" not in src, \
            "Deprecated stock.quarterly_financials must not be used directly"

    @pytest.mark.asyncio
    async def test_income_statement_returns_list_of_dicts(self):
        """Integration-style test with mocked yfinance Ticker."""
        import pandas as pd
        from jasper.tools.providers.yfinance import YFinanceClient

        # Build a fake DataFrame that mimics yfinance output
        fake_df = pd.DataFrame(
            {
                pd.Timestamp("2024-09-30"): {
                    "Total Revenue": 100_000_000,
                    "Net Income": 20_000_000,
                    "Gross Profit": 45_000_000,
                    "Operating Income": 30_000_000,
                },
                pd.Timestamp("2024-06-30"): {
                    "Total Revenue": 90_000_000,
                    "Net Income": 18_000_000,
                    "Gross Profit": 40_000_000,
                    "Operating Income": 27_000_000,
                },
            }
        )

        mock_ticker = MagicMock()
        mock_ticker.quarterly_income_stmt = fake_df

        with patch("jasper.tools.providers.yfinance.yf.Ticker", return_value=mock_ticker):
            # Patch run_in_executor to run synchronously in tests
            async def fake_executor(_, fn, *args):
                if args:
                    return fn(*args)
                return fn()

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = fake_executor
                client = YFinanceClient()
                result = await client.income_statement("AAPL")

        assert isinstance(result, list)
        assert len(result) == 2
        assert "fiscalDateEnding" in result[0]
        assert "totalRevenue" in result[0]


# ─────────────────────────────────────────────
# 7. Config — demo key warning is explicit
# ─────────────────────────────────────────────
class TestConfig:
    def test_demo_key_warning_mentions_ibm(self):
        import warnings
        from jasper.core.config import get_financial_api_key

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ALPHA_VANTAGE_API_KEY", None)
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                key = get_financial_api_key()
                assert key == "demo"
                assert len(w) == 1
                warning_text = str(w[0].message)
                assert "IBM" in warning_text, \
                    "Demo key warning must mention IBM to alert users about dummy data"

    def test_real_key_no_warning(self):
        import warnings
        from jasper.core.config import get_financial_api_key

        with patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "REAL_KEY_123"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                key = get_financial_api_key()
                assert key == "REAL_KEY_123"
                assert len(w) == 0, "No warning should be raised when a real key is set"


# ─────────────────────────────────────────────
# 8. Version command uses importlib.metadata
# ─────────────────────────────────────────────
class TestVersionCommand:
    def test_version_command_uses_importlib_metadata(self):
        import inspect
        from jasper.cli.main import version_command
        src = inspect.getsource(version_command)
        assert "importlib.metadata" in src or "pkg_version" in src, \
            "version_command must use importlib.metadata, not open('pyproject.toml')"
        assert "open(\"pyproject.toml\")" not in src, \
            "version_command must not read pyproject.toml via relative path"

    def test_version_command_fallback_exists(self):
        import inspect
        from jasper.cli.main import version_command
        src = inspect.getsource(version_command)
        assert "except" in src, "version_command must have a fallback for when metadata fails"


# ─────────────────────────────────────────────
# 9. Export — cross-process persistence
# ─────────────────────────────────────────────
class TestExportPersistence:
    def test_save_and_load_report_roundtrip(self, tmp_path):
        from jasper.core.state import FinalReport, ReportMode
        from jasper.cli import main as cli_main

        report = FinalReport(
            query="Test Apple revenue",
            report_mode=ReportMode.FINANCIAL_EVIDENCE,
            synthesis_text="Apple had revenue of $100B",
            is_valid=True,
            confidence_score=0.9,
            tickers=["AAPL"],
            data_sources=["yfinance"],
        )

        # Patch the cache path to a temp dir
        with patch.object(cli_main, "_LAST_REPORT_PATH", tmp_path / "last_report.json"):
            with patch.object(cli_main, "_CACHE_DIR", tmp_path):
                cli_main._save_report_to_disk(report)
                loaded = cli_main._load_report_from_disk()

        assert loaded is not None
        assert loaded.query == "Test Apple revenue"
        assert loaded.tickers == ["AAPL"]
        assert loaded.confidence_score == pytest.approx(0.9)

    def test_load_returns_none_when_no_cache(self, tmp_path):
        from jasper.cli import main as cli_main
        with patch.object(cli_main, "_LAST_REPORT_PATH", tmp_path / "nonexistent.json"):
            result = cli_main._load_report_from_disk()
        assert result is None


# ─────────────────────────────────────────────
# 10. PDF template — conditional status classes
# ─────────────────────────────────────────────
class TestPDFTemplate:
    def _load_template_source(self) -> str:
        from importlib import resources
        path = resources.files("jasper").joinpath("templates/report.html.jinja")
        return path.read_text(encoding="utf-8")

    def test_data_retrieval_not_hardcoded_success(self):
        src = self._load_template_source()
        # The old bad pattern was an unconditional hardcoded SUCCESS badge.
        # Now it must be inside a Jinja2 conditional block.
        # Check that "status-passed">SUCCESS" only appears after an {% if/elif %} tag,
        # not as a bare unconditional line.
        assert "{% elif completed_count == total_count %}" in src, \
            "DATA RETRIEVAL must use a conditional Jinja2 block, not a hardcoded SUCCESS"
        assert "{% if total_count == 0 %}" in src, \
            "DATA RETRIEVAL must handle the zero-tasks case"

    def test_audit_trail_uses_conditional_status(self):
        src = self._load_template_source()
        # Must have a conditional for task status
        assert "task.status == 'completed'" in src, \
            "Audit trail must conditionally apply status-passed/status-failed based on task.status"

    def test_status_warning_css_exists(self):
        from importlib import resources
        css_path = resources.files("jasper").joinpath("styles/report_v1.css")
        css = css_path.read_text(encoding="utf-8")
        assert ".status-warning" in css, \
            "status-warning CSS class must be defined for partial data retrieval display"
