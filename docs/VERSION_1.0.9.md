# Jasper v1.0.9 — Detailed Release Notes

## Overview

v1.0.9 is a stability and correctness release. It resolves all 8 critical bugs identified in the v1.0.9 codebase analysis, introduces a public Python API (#23), adds a comprehensive 33-test unit suite, and fixes 4 Pylance type errors that were present in the codebase. No breaking changes to the CLI interface.

---

## Critical Bug Fixes

---

### #6 — Executor crashes on `balance_sheet` / `financial_statement` tools

**Root cause:** `execute_task()` only had a branch for `income_statement`. Any plan task with `tool_name = "balance_sheet"` or `"financial_statement"` fell through to an unhandled `else` clause that raised a bare `ValueError`, which propagated uncaught through `controller.run()` and crashed the entire pipeline instead of marking just that task as failed.

**File changed:** `jasper/agent/executor.py`

**What changed:**

1. Added two module-level dispatch sets so all known tool aliases are normalised in one place:
   ```python
   _INCOME_TOOLS  = {"income_statement", "financial_statement"}
   _BALANCE_TOOLS = {"balance_sheet"}
   ```

2. Extracted all retry logic out of `execute_task()` into a new private helper `_execute_with_retries(state, task, fetch_coro_factory)`. This helper:
   - Runs the coroutine supplied by `fetch_coro_factory`
   - On `FinancialDataError`: increments an attempt counter and retries up to `state.max_retries` times, logging each attempt
   - On structural errors (`KeyError`, `TypeError`, `ValueError`): marks the task `"failed"` immediately without retrying (these are deterministic failures)
   - On success: stores result in `state.task_results[task.id]` and sets `task.status = "completed"`

3. `execute_task()` now dispatches cleanly:
   ```python
   if tool in _INCOME_TOOLS:
       await self._execute_with_retries(state, task,
           lambda: self.financial_router.fetch_income_statement(ticker))
   elif tool in _BALANCE_TOOLS:
       await self._execute_with_retries(state, task,
           lambda: self.financial_router.fetch_balance_sheet(ticker))
   else:
       raise ValueError(f"Unknown tool '{tool}'...")
   ```
   Unknown tools set `task.status = "failed"` with a descriptive error message rather than crashing the pipeline.

4. Added a `_validate_financial_data(data)` guard that checks:
   - Lists must contain only `dict` items
   - Every dict must have a `fiscalDateEnding` key
   - Bare `dict` responses must be non-empty

---

### #7 — yfinance blocks the async event loop

**Root cause:** `yf.Ticker(ticker)` and all subsequent pandas DataFrame attribute accesses (`.quarterly_financials`, `.quarterly_balance_sheet`) are synchronous, blocking calls. Running them directly inside an `async def` method stalls the entire asyncio event loop, freezing the Rich `Live` display and preventing other coroutines from running.

Additionally, the `.quarterly_financials` attribute was [deprecated in yfinance 0.2.x](https://github.com/ranaroussi/yfinance/releases) in favour of `.quarterly_income_stmt`.

**File changed:** `jasper/tools/providers/yfinance.py`

**What changed:**

1. Every synchronous yfinance call is now offloaded to a thread pool via `run_in_executor`:
   ```python
   loop = asyncio.get_event_loop()
   stock = await loop.run_in_executor(None, yf.Ticker, ticker)
   quarterly = await loop.run_in_executor(
       None,
       lambda: getattr(stock, "quarterly_income_stmt",
                       getattr(stock, "quarterly_financials", None))
   )
   ```
   The `getattr` chain tries the new attribute name first, falls back to the legacy alias — so the code works across both old and new yfinance versions.

2. Added two static helper methods to handle locale/version differences in pandas column names:
   ```python
   @staticmethod
   def _safe_str(value, fallback="0") -> str:
       """Convert pandas/numpy value to str, handling NaN/None."""
       ...

   @staticmethod
   def _row_get(row, *keys) -> str:
       """Try multiple column name variants (locale-robust)."""
       for key in keys:
           val = row.get(key)
           if val is not None:
               return YFinanceClient._safe_str(val)
       return "0"
   ```
   Column name variants are passed in priority order, e.g.:
   ```python
   "totalRevenue": self._row_get(row, "Total Revenue", "TotalRevenue"),
   ```

3. `balance_sheet()` method added alongside `income_statement()` — also fully async using the same `run_in_executor` pattern, reading from `.quarterly_balance_sheet`.

---

### #8 — Alpha Vantage `demo` key silently returns IBM data for all tickers

**Root cause:** The `demo` API key is a permanent fixture in Alpha Vantage's system that always returns IBM's data regardless of the `symbol` parameter sent. With no warning, every query for `AAPL`, `TSLA`, etc. would return IBM financial statements and the user would have no idea the data was wrong.

**Files changed:** `jasper/core/config.py`, `jasper/cli/main.py`

**What changed:**

1. `get_financial_api_key()` in `config.py` now emits a `UserWarning` with a full box when the key is `"demo"`:
   ```
   ╔══ ALPHA VANTAGE DEMO KEY ACTIVE ══════════════════════════════╗
   ║  WARNING: No ALPHA_VANTAGE_API_KEY set in .env               ║
   ║  The 'demo' key ALWAYS returns IBM (ticker: IBM) data,        ║
   ║  regardless of the ticker you query.                          ║
   ║  Data shown will NOT correspond to your queried company.      ║
   ║  → Get a free key at https://www.alphavantage.co/support/     ║
   ╚═══════════════════════════════════════════════════════════════╝
   ```

2. `ask_command()` in `cli/main.py` checks `os.getenv("ALPHA_VANTAGE_API_KEY")` and prints a visible Rich-formatted banner **before** research begins:
   ```python
   if not os.getenv("ALPHA_VANTAGE_API_KEY"):
       console.print(
           "[bold yellow]⚠  DEMO MODE:[/bold yellow]"
           " No ALPHA_VANTAGE_API_KEY set. Alpha Vantage will return IBM data "
           "for ALL tickers. Falling back to yfinance where possible."
       )
   ```

---

### #9 — `errors.py` was completely empty

**Root cause:** `jasper/core/errors.py` existed as a placeholder file with zero content. Every module that imported from it would get nothing, and there was no shared exception hierarchy — each component either used built-in exceptions or defined ad-hoc local classes.

**File changed:** `jasper/core/errors.py`

**What changed:** Implemented a full domain exception hierarchy rooted at `JasperError`:

```python
class JasperError(Exception):
    """Base exception for all Jasper domain errors."""

class EntityExtractionError(JasperError): ...
class PlannerError(JasperError): ...
class DataFetchError(JasperError): ...
class SynthesisError(JasperError): ...
class ValidationError(JasperError): ...
class ConfigurationError(JasperError): ...
```

Each subclass maps to one pipeline stage. Callers can now catch `JasperError` for broad handling or a specific subclass for targeted recovery.

---

### #11 — `SessionLogger.log()` printed raw JSON to stdout

**Root cause:** The original implementation called `print(json.dumps(record))` inside `log()`. Every logged event (PLAN_CREATED, TASK_STARTED, TASK_COMPLETED, etc.) dumped a JSON blob to stdout. This completely broke the Rich `Live` display — Rich captures stdout for its live panel, so the JSON lines would corrupt the terminal rendering mid-session.

**File changed:** `jasper/observability/logger.py`

**What changed:**

1. Removed the `print()` call entirely.
2. Added a module-level `logging.FileHandler` that writes to `~/.jasper/logs/session.log`:
   ```python
   _log_dir = os.path.join(os.path.expanduser("~"), ".jasper", "logs")
   os.makedirs(_log_dir, exist_ok=True)
   _file_logger = logging.getLogger("jasper.session")
   if not _file_logger.handlers:
       _handler = logging.FileHandler(
           os.path.join(_log_dir, "session.log"), encoding="utf-8"
       )
       _handler.setFormatter(logging.Formatter("%(message)s"))
       _file_logger.addHandler(_handler)
       _file_logger.setLevel(logging.DEBUG)
       _file_logger.propagate = False  # Don't bubble up to root logger
   ```
3. `SessionLogger.log()` now calls `_file_logger.debug(json.dumps(record))` — writes structured JSON to the log file, never to the terminal.
4. The `RichLogger` subclass in `cli/main.py` overrides `log()` to update the Rich `Live` panel UI, and calls `super().log()` to still persist events to file.

---

### #15 — Test version hardcoded to `1.0.7`, agent test imported nothing real

**Root cause:** `tests/test_cli_integration.py` had three places asserting `jasper.__version__ == "1.0.7"` even though the package had been bumped to `1.0.8`. Additionally, `test_agent_modules()` imported the module files but never actually imported or asserted on any of the agent classes — the test body was essentially a no-op.

**File changed:** `tests/test_cli_integration.py`

**What changed:**

1. All three version string occurrences updated: `"1.0.7"` → `"1.0.8"` (then bumped again to `"1.0.9"` in the same release).
2. `test_agent_modules()` now actually imports each of the five agent classes and asserts they are callable:
   ```python
   from jasper.agent.planner import Planner
   from jasper.agent.executor import Executor
   from jasper.agent.validator import validator
   from jasper.agent.synthesizer import Synthesizer
   from jasper.agent.entity_extractor import EntityExtractor
   from jasper.agent.reflector import Reflector

   assert callable(Planner)
   assert callable(Executor)
   # etc.
   ```

---

### #16 — `jasper export` fails when run in a new terminal; `jasper version` crashes outside repo

**Root cause (export):** The `_last_report` variable in `cli/main.py` is module-level. When `jasper ask` finishes and the process exits, `_last_report` is garbage collected. Running `jasper export` in a new terminal starts a fresh process where `_last_report is None`, so the export command immediately exits with "No report to export."

**Root cause (version):** `version_command()` previously imported `__version__` from a relative path. When Jasper is run as an installed package (not from the source directory), the relative import resolves but the `egg-info` version string may not match. Also, if the package is not installed in editable mode, the import can fail entirely.

**File changed:** `jasper/cli/main.py`

**What changed:**

1. Added two persistence helpers:
   ```python
   _CACHE_DIR = Path.home() / ".jasper"
   _LAST_REPORT_PATH = _CACHE_DIR / "last_report.json"

   def _save_report_to_disk(report: FinalReport) -> None:
       _CACHE_DIR.mkdir(parents=True, exist_ok=True)
       _LAST_REPORT_PATH.write_text(report.model_dump_json(), encoding="utf-8")

   def _load_report_from_disk() -> Optional[FinalReport]:
       if _LAST_REPORT_PATH.exists():
           return FinalReport.model_validate_json(
               _LAST_REPORT_PATH.read_text(encoding="utf-8")
           )
       return None
   ```
   `model_dump_json()` / `model_validate_json()` are Pydantic v2's native JSON serialisers — they handle all nested models, enums, and datetimes correctly.

2. Both `ask_command()` and the interactive loop call `_save_report_to_disk(state.report)` after every successful query.

3. `export_command()` calls `_load_report_from_disk()` when `_last_report is None`:
   ```python
   if _last_report is None:
       _last_report = _load_report_from_disk()
   ```

4. `version_command()` now uses `importlib.metadata` as the authoritative source:
   ```python
   try:
       from importlib.metadata import version as pkg_version
       version = pkg_version("jasper-finance")
   except Exception:
       from .. import __version__
       version = __version__
   ```

---

### #17 — PDF report hardcodes `SUCCESS` badge and always renders tasks in green

**Root cause:** The Jinja2 template `report.html.jinja` had:
```html
<span class="ledger-entry status-passed">SUCCESS</span>
```
hardcoded unconditionally in the DATA RETRIEVAL row, so every report — including ones where all data fetches failed — displayed a green SUCCESS badge. Similarly, the audit trail rendered every task row with `class="status-passed"` regardless of `task.status`.

**Files changed:** `jasper/templates/report.html.jinja`, `jasper/styles/report_v1.css`

**What changed:**

1. DATA RETRIEVAL badge is now fully dynamic using Jinja2 conditionals:
   ```jinja
   {% set completed_count = report.audit_trail
       | selectattr('status', 'equalto', 'completed') | list | length %}
   {% set total_count = report.audit_trail | length %}
   {% if total_count == 0 %}
     <span class="ledger-entry status-failed">NO DATA</span>
   {% elif completed_count == total_count %}
     <span class="ledger-entry status-passed">SUCCESS</span>
   {% elif completed_count > 0 %}
     <span class="ledger-entry status-warning">PARTIAL ({{ completed_count }}/{{ total_count }})</span>
   {% else %}
     <span class="ledger-entry status-failed">FAILED</span>
   {% endif %}
   ```
   Four possible states: `NO DATA`, `SUCCESS`, `PARTIAL N/M`, `FAILED`.

2. Audit trail task rows now use conditional CSS:
   ```jinja
   <span class="ledger-entry
     {% if task.status == 'completed' %}status-passed{% else %}status-failed{% endif %}">
     {{ task.status | upper }}
   </span>
   ```

3. Added `.status-warning` CSS class to `report_v1.css` for the yellow PARTIAL state:
   ```css
   .status-warning {
       background-color: #fefcbf;
       color: #744210;
       border: 1pt solid #d69e2e;
   }
   ```

---

## New Feature: #23 — Public Python API

**File changed:** `jasper/__init__.py`

**What was missing:** There was no documented way to use Jasper programmatically. `JasperController.run()` existed but was not exported or documented, and returning a `Jasperstate` object required the caller to understand internal state structure.

**What was added:**

A top-level `run_research(query)` async function that wires up all components internally and returns a `FinalReport` Pydantic model:

```python
async def run_research(query: str) -> "Optional[FinalReport]":
    import os
    from .core.controller import JasperController
    from .agent.planner import Planner
    from .agent.executor import Executor
    from .agent.validator import validator as ValidatorClass
    from .agent.synthesizer import Synthesizer
    from .tools.financials import FinancialDataRouter
    from .tools.providers.alpha_vantage import AlphaVantageClient
    from .tools.providers.yfinance import YFinanceClient
    from .core.llm import get_llm

    llm = get_llm(temperature=0)
    av_client = AlphaVantageClient(api_key=os.getenv("ALPHA_VANTAGE_API_KEY", "demo"))
    yf_client = YFinanceClient()
    router = FinancialDataRouter(providers=[av_client, yf_client])

    controller = JasperController(
        planner=Planner(llm),
        executor=Executor(router),
        validator=ValidatorClass(),
        synthesizer=Synthesizer(llm),
    )

    state = await controller.run(query)
    return state.report  # Returns FinalReport or None on failure
```

The imports are lazy (inside the function body) so `import jasper` at the top level is nearly zero-cost and doesn't pull in LangChain, yfinance, or httpx unless `run_research` is actually called.

`FinalReport` is accessible from the package via a `__getattr__` hook without adding it to the module's static namespace:
```python
def __getattr__(name: str):
    if name == "FinalReport":
        from .core.state import FinalReport
        return FinalReport
    raise AttributeError(f"module 'jasper' has no attribute {name!r}")
```

**Usage:**
```python
import asyncio
from jasper import run_research, FinalReport

report: FinalReport = asyncio.run(run_research("What is Apple's revenue trend?"))
if report:
    print(report.synthesis_text)      # Full markdown analysis
    print(report.confidence_score)    # e.g. 0.87
    print(report.tickers)             # ['AAPL']
    print(report.evidence_log)        # List[EvidenceItem]
```

---

## Type Safety Fixes (Pylance Errors)

Four static type errors were resolved:

### 1. `jasper/core/state.py` — `"Reflecting"` missing from `Jasperstate.status` Literal

The controller sets `state.status = "Reflecting"` during the reflector phase, but the `Jasperstate` model only declared:
```python
status: Literal["Planning", "Executing", "Validating", "Synthesizing", "Completed", "Failed"]
```
**Fix:** Added `"Reflecting"` to the Literal union.

### 2. `jasper/__init__.py` — `FinalReport` undefined at module level

`FinalReport` was listed in `__all__` and used in the return type annotation as a bare string `"FinalReport | None"`, but the class was never imported at the top level. Pylance correctly flagged both uses as undefined.

**Fix:**
- Moved the import under a `TYPE_CHECKING` guard so it only runs during static analysis, not at runtime:
  ```python
  from typing import TYPE_CHECKING, Optional
  if TYPE_CHECKING:
      from .core.state import FinalReport
  ```
- Changed return annotation to `"Optional[FinalReport]"` (the quotes make it a forward reference, resolved only by type checkers).
- Removed `"FinalReport"` from `__all__` — it remains runtime-accessible via `__getattr__`, but `__all__` is for `import *` which doesn't apply to dynamically resolved names.

### 3. `tests/test_cli_integration.py` — importing non-existent `reflect` function

The test imported `from jasper.agent.reflector import reflect` but the refactored module exports a `Reflector` class, not a bare function.

**Fix:** Changed to `from jasper.agent.reflector import Reflector`.

### 4. `tests/test_critical_fixes.py` — variable used as type expression in `cast()`

Two `cast()` calls stored the Literal type in a variable first:
```python
TaskStatus = Literal["pending", "in_progress", "completed", "failed"]
t.status = cast(TaskStatus, status)  # Error: variable not allowed in type expression
```
Pylance requires the type argument to `cast()` to be a literal type expression, not a variable.

**Fix:** Inlined the Literal directly into both `cast()` calls:
```python
status=cast(Literal["pending", "in_progress", "completed", "failed"], status)
```
Also moved the `from typing import cast, Literal` import to above the loop (was incorrectly placed inside a `for` loop).

---

## Test Infrastructure

### New file: `pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts = -v --tb=short
```

`asyncio_mode = auto` means all `async def test_*` functions are automatically treated as asyncio coroutines without needing the `@pytest.mark.asyncio` decorator on every test.

### New file: `tests/test_critical_fixes.py`

33 unit tests across 10 test classes. All run in ~4.4 seconds. All pass.

| Class | Coverage | Tests |
|-------|----------|-------|
| `TestExceptionHierarchy` | `jasper/core/errors.py` — all 6 subclasses inherit `JasperError`, can be caught via base | 3 |
| `TestLogger` | `jasper/observability/logger.py` — `log()` does not write to stdout; `RichLogger` overrides correctly | 2 |
| `TestExecutorDispatch` | `jasper/agent/executor.py` — income/balance/alias dispatch; unknown tool sets failed; missing ticker sets failed; failed result stored in state | 6 |
| `TestFinancialDataRouter` | `jasper/tools/financials.py` — first provider wins; fallback on error; balance_sheet exists; all-fail raises; missing method skipped | 5 |
| `TestAlphaVantageClient` | `jasper/tools/providers/alpha_vantage.py` — income parses annualReports; balance parses annualReports; Note key raises; missing key raises | 4 |
| `TestYFinanceClientAsync` | `jasper/tools/providers/yfinance.py` — income uses run_in_executor; balance uses run_in_executor; deprecated attribute not referenced; returns list of dicts | 4 |
| `TestConfig` | `jasper/core/config.py` — demo key warning mentions IBM; real key no warning | 2 |
| `TestVersionCommand` | `jasper/cli/main.py` — uses importlib.metadata; fallback `__version__` exists | 2 |
| `TestExportPersistence` | `jasper/cli/main.py` — save/load roundtrip; load returns None when no cache | 2 |
| `TestPDFTemplate` | `jasper/templates/report.html.jinja` — DATA RETRIEVAL uses Jinja2 conditionals; audit trail conditional; `.status-warning` CSS exists | 3 |

---

## Dependencies Added

```toml
# pyproject.toml — [project.optional-dependencies]
dev = [
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
]
```

Install with: `pip install -e ".[dev]"`

---

## Files Changed Summary

| File | Type of Change |
|------|---------------|
| `jasper/core/errors.py` | Implemented (was empty) |
| `jasper/observability/logger.py` | Fixed stdout pollution |
| `jasper/tools/providers/yfinance.py` | Full async rewrite + deprecated API removal |
| `jasper/tools/providers/alpha_vantage.py` | Added `balance_sheet()` + `_fetch()` helper |
| `jasper/tools/financials.py` | Added `_fetch_with_fallback()`, `fetch_balance_sheet()` |
| `jasper/agent/executor.py` | Added dispatch sets, `_execute_with_retries()`, balance_sheet branch |
| `jasper/core/state.py` | Fixed `task_results` type; added `"Reflecting"` to status Literal |
| `jasper/core/config.py` | Added IBM demo key warning box |
| `jasper/cli/main.py` | Added disk persistence, version via metadata, DEMO MODE banner, LLM singleton |
| `jasper/templates/report.html.jinja` | Dynamic DATA RETRIEVAL badge + conditional task CSS |
| `jasper/styles/report_v1.css` | Added `.status-warning` class |
| `jasper/__init__.py` | Added `run_research()` public API + TYPE_CHECKING guard |
| `tests/test_cli_integration.py` | Version bumps + real agent class imports |
| `tests/test_critical_fixes.py` | New: 33-test suite |
| `pytest.ini` | New: asyncio_mode=auto config |
| `pyproject.toml` | Version bump 1.0.8→1.0.9; dev deps added |

---

## Upgrade Notes

- **`.env` required keys:** `OPENROUTER_API_KEY` (LLM), `ALPHA_VANTAGE_API_KEY` (data — optional, defaults to demo/IBM mode)
- **Model selection:** Set `OPENROUTER_MODEL` env var to override the default. Example: `OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free`
- **Session logs:** Now written to `~/.jasper/logs/session.log` (was stdout). Safe to tail in a separate terminal.
- **Cross-process export:** Last report persisted to `~/.jasper/last_report.json`. `jasper export` works from any terminal after `jasper ask`.
- **Python API:** `from jasper import run_research` — see #23 section above.
