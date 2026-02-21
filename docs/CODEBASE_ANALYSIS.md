# Jasper Finance — Codebase Analysis Report
> Generated: February 21, 2026

This document is a comprehensive audit of the Jasper codebase covering architectural observations, critical bugs, efficiency gaps, CLI/UX issues, and the next phase feature roadmap.

---

## Architecture Overview

Jasper is a terminal-native, agentic financial research tool. Given a natural-language query (e.g., "What is Apple's revenue?"), it runs a deterministic pipeline:

```
User Query
  → EntityExtractor (LLM #1)
  → Planner (LLM #2)
  → Executor (API tools: Alpha Vantage + yfinance)
  → Validator
  → Synthesizer (LLM #3)
  → FinalReport
  → CLI render (Rich) + optional PDF export (WeasyPrint/xhtml2pdf)
```

**Key source files:**
- `jasper/core/controller.py` — orchestrates all stages
- `jasper/agent/` — five agent nodes (entity_extractor, planner, executor, validator, synthesizer)
- `jasper/tools/providers/` — Alpha Vantage + yfinance adapters
- `jasper/cli/main.py` — Typer CLI with Rich Live UI
- `jasper/export/pdf.py` — PDF export
- `jasper/core/state.py` — Pydantic state models (`JasperState`, `FinalReport`)

---

## A) Critical Bugs

### [BUG] Executor crashes on `balance_sheet` / `financial_statement` tasks
- **File:** `jasper/agent/executor.py`
- **Detail:** The planner's `AVAILABLE_TOOLS` list includes `balance_sheet` and `financial_statement`, but the executor only has an `if tool == "income_statement"` branch. Any plan requesting those tools raises `ValueError: Unknown task description`.
- **Severity:** Critical

### [BUG] yfinance blocks the async event loop
- **File:** `jasper/tools/providers/yfinance.py`
- **Detail:** `yf.Ticker(ticker)` and `.quarterly_financials` are synchronous blocking I/O calls inside an `async def` function. This freezes the entire event loop during every fetch. Must be wrapped with `asyncio.get_event_loop().run_in_executor(None, ...)`.
- **Severity:** Critical

### [BUG] Alpha Vantage demo key silently returns IBM dummy data for all tickers
- **File:** `jasper/core/config.py`
- **Detail:** When no `AV_API_KEY` env var is set, the app issues a warning but continues with the `demo` key, which Alpha Vantage maps to a fixed IBM dataset regardless of ticker. Queries "succeed" with wrong company data.
- **Severity:** Critical

### [BUG] `errors.py` is completely empty
- **File:** `jasper/core/errors.py`
- **Detail:** The entire file has zero content. All errors are thrown as raw `ValueError` / `RuntimeError` / `Exception` with no domain exception hierarchy, making programmatic error handling impossible.
- **Severity:** High

### [BUG] Version test checks `1.0.7` but app is `1.0.8`
- **File:** `tests/test_cli_integration.py` (line ~14)
- **Detail:** `assert jasper.__version__ == "1.0.7"` — this test fails on the current release.
- **Severity:** High

---

## B) Agent Pipeline Issues

| Issue | File | Severity |
|---|---|---|
| `reflector.py` is a dead no-op — no retry/recovery loop | `jasper/agent/reflector.py` | High |
| Planner hard-fails on empty entity list, blocking all qualitative/macro queries | `jasper/agent/planner.py` | High |
| Validator marks ALL tasks failed if ANY single task fails — no partial-success path | `jasper/agent/validator.py` | High |
| Executor runs tasks sequentially — multi-ticker queries needlessly 2x slower | `jasper/core/controller.py` | Medium |
| `balance_sheet()` exists in yfinance provider but router never exposes it | `jasper/tools/financials.py` | High |

---

## C) LLM / AI Quality Issues

| Issue | File | Severity |
|---|---|---|
| Default model is `xiaomi/mimo-v2-flash:free` — low quality, small context, fragile JSON | `jasper/core/llm.py` | High |
| Two LLM calls before any data fetch — entity extraction + planning could be one call | `jasper/agent/planner.py` | Medium |
| No structured output / JSON-mode enforcement — fragile regex-strip JSON parsing | `jasper/agent/entity_extractor.py`, `jasper/agent/planner.py` | High |
| Synthesizer prompt repeats the same table-formatting rule 3 times — sign model ignores it | `jasper/agent/synthesizer.py` | Medium |
| No token budget / context window management — large datasets passed raw to synthesizer | `jasper/agent/synthesizer.py` | Medium |
| `agenerate()` used in some agents (deprecated LangChain v0.x API) vs `ainvoke()` elsewhere | `jasper/agent/entity_extractor.py` | Medium |

---

## D) CLI / UX Issues

| Issue | File | Severity |
|---|---|---|
| `SessionLogger.log()` prints raw JSON to stdout mid-render, breaking Rich Live UI | `jasper/observability/logger.py` | High |
| "QUERY HASH" shows truncated raw string, not a hash (PDF uses real SHA-256 — inconsistency) | `jasper/cli/interface.py` | Medium |
| `render.py` is a vestigial 5-line stub never imported anywhere | `jasper/cli/render.py` | Low |
| `export` command only works within the same process — `jasper export` as a separate command always fails | `jasper/cli/main.py` | High |
| `version` command reads `pyproject.toml` via relative path — fails after `pip install` | `jasper/cli/main.py` | Medium |
| Audit trail silently shows only last 5 tasks with no "N of M shown" indication | `jasper/cli/interface.py` | Medium |
| No streaming output — synthesis causes 10-30s blank screen | `jasper/agent/synthesizer.py` | High |
| PDF: failed tasks always rendered green (`status-passed` hardcoded in template) | `jasper/templates/report.html.jinja` | Medium |
| PDF: `DATA RETRIEVAL` status badge hardcoded `SUCCESS` regardless of actual result | `jasper/templates/report.html.jinja` | Medium |

---

## E) Data / Tools Issues

| Issue | File | Severity |
|---|---|---|
| Duplicate orphaned Alpha Vantage client with filename typo: `aplha_vantage.py` | `jasper/tools/aplha_vantage.py` | Medium |
| `FinancialClient` in `financials.py` calls `api.example.com` — permanent placeholder/dead code | `jasper/tools/financials.py` | Medium |
| yfinance uses deprecated `quarterly_financials` attribute (should be `quarterly_income_stmt`) | `jasper/tools/providers/yfinance.py` | Medium |
| yfinance field mapping uses locale-dependent column names — breaks on non-US tickers | `jasper/tools/providers/yfinance.py` | High |
| No caching of API responses — re-fetches identical data on every call | `jasper/tools/providers/` | Medium |

---

## F) Export / Output Issues

| Issue | File | Severity |
|---|---|---|
| WeasyPrint suppression `open(os.devnull)` handles are never closed — file descriptor leak on Windows | `jasper/export/pdf.py` | High |
| Evidence log values are raw dict `repr()` strings instead of clean metric/value display | `jasper/core/controller.py` | Medium |
| Jinja2 environment and CSS reloaded fresh on every render — should be module-level cached | `jasper/export/pdf.py` | Low |

---

## G) Error Handling Gaps

| Issue | File | Severity |
|---|---|---|
| `except (FinancialDataError, Exception)` double-catch swallows unexpected bugs | `jasper/agent/executor.py` | High |
| Planner JSON parse error gives useless message to user, raw LLM output not surfaced | `jasper/agent/planner.py` | Medium |
| No network timeout fallback — yfinance sync call has no `asyncio.wait_for` guard | `jasper/tools/providers/yfinance.py` | High |

---

## H) Testing Gaps

| Issue | File | Severity |
|---|---|---|
| `test_agent_modules` test has no actual imports — always passes even if agents are broken | `tests/test_cli_integration.py` | High |
| Zero unit tests for core agent logic (planner, executor, validator, synthesizer) | `tests/` | High |
| No `pytest-asyncio` in dependencies — async pipeline cannot be properly tested | `pyproject.toml` | High |
| No tests for `_fix_markdown_tables()` regex logic | `jasper/cli/interface.py` | Medium |
| No tests for PDF export validation gate with invalid inputs | `jasper/export/pdf.py` | Medium |

---

## I) Performance Concerns

| Issue | File | Severity |
|---|---|---|
| LLM recreated on every `ask` call — no singleton/session reuse | `jasper/cli/main.py` | Medium |
| `render_mission_board()` full tree rebuild on every logger event (20+ rebuilds per query) | `jasper/cli/main.py` | Low |
| `_build_final_report()` iterates `state.plan` 3 separate times — should be 1 pass | `jasper/core/controller.py` | Low |
| Jinja2 env + CSS re-loaded from disk on every PDF render | `jasper/export/pdf.py` | Low |

---

## J) Next Phase Feature Roadmap

| # | Feature | Priority |
|---|---|---|
| F1 | Wire `balance_sheet` + `cash_flow_statement` end-to-end (planner → executor → router → provider) | Critical |
| F2 | Add real-time quote tool — current price, market cap, 52-week range | High |
| F3 | Multi-ticker comparison synthesis — "Compare AAPL vs MSFT margins" | High |
| F4 | Session memory in `interactive` mode — use history for follow-up questions | High |
| F5 | LLM streaming (`astream()`) for progressive synthesis output | High |
| F6 | Watchlist / batch mode — run query across a portfolio list | Medium |
| F7 | Public Python API (`jasper/__init__.py` exports) for notebook/programmatic use | Medium |
| F8 | Structured LLM output (JSON mode) to replace fragile regex-strip parsing | High |
| F9 | Support qualitative/macro queries — remove hard-fail on empty entity list | Medium |
| F10 | Key financial metrics: P/E, P/B, debt ratios, dividend yield | High |

---

## Summary Severity Count

| Category | Critical | High | Medium | Low |
|---|---|---|---|---|
| Critical Bugs | 3 | 2 | 0 | 0 |
| Agent Pipeline | 0 | 3 | 2 | 0 |
| LLM Quality | 0 | 2 | 4 | 0 |
| CLI/UX | 0 | 3 | 5 | 1 |
| Data/Tools | 0 | 1 | 4 | 0 |
| Export/Output | 0 | 1 | 2 | 1 |
| Error Handling | 0 | 2 | 1 | 0 |
| Testing | 0 | 3 | 2 | 0 |
| Performance | 0 | 0 | 1 | 3 |

**Top 3 most dangerous:** Executor crashes on balance_sheet tasks · yfinance blocks async event loop · Alpha Vantage demo key returns wrong company data for all tickers.
