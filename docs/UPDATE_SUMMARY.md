# Jasper Finance — Update Summary

Consolidated changelog from initial release through v1.0.9.

---

## v1.0.9 — Code-Quality & Reliability (Feb 2026)

**15 targeted fixes from structured code review.**

### Security / Privacy
- `entity_extractor.py` — FATAL parse log no longer records full LLM response; logs `raw_hash`, `raw_len`, and a 200-char preview instead.

### Correctness
- `validator.py` — `hard_failures` (task errors) now included in the `is_valid` check when all tasks complete; previously task errors were silently ignored.
- `reflector.py` — `recovered` / `still_failed` metrics now count only tasks that were actually retried, not all completed/incomplete tasks in the plan.
- `reflector.py` — retry loop now honours `self.max_retries` per task; previously looped exactly once regardless.
- `executor.py` — quote tools (`realtime_quote`, `key_metrics`) pass `skip_fiscal_validation=True` to bypass the `fiscalDateEnding` list check that doesn't apply to flat quote dicts.
- `executor.py` — unknown-tool error message now lists all registered aliases from all dispatch sets.
- `llm.py` — replaced scalar `_llm_singleton` with `Dict[float, ChatOpenAI]` keyed by temperature; previous singleton silently ignored the `temperature` argument on second call.
- `yfinance.py` — `_get()` helper in `realtime_quote()` now delegates to `_safe_str()` which handles `numpy.nan`; previously returned the string `"nan"`.
- `__init__.py` — docstring no longer references `state.error` (internal field not exposed to callers).

### Robustness
- `reflector.py` — `executor.execute_task()` wrapped in `try/except`; unhandled exceptions now set `task.status="failed"` and log `REFLECTOR_RETRY_FAILED` instead of crashing the pipeline.
- `controller.py` — `reflector.reflect()` wrapped in `try/except`; a reflector crash now logs `REFLECTION_FAILED` and continues to validation with whatever data was collected.
- `entity_extractor.py` — `JSONDecodeError` is raised immediately (deterministic at `temperature=0`) instead of being retried; separate `except Exception` branch handles transient network errors.
- `planner.py` — same deterministic-parse-error fast-fail applied; transient API errors retry up to 3 times.

### Performance
- `financials.py` — stale cache entries are evicted on read (`del _cache[key]`) preventing unbounded memory growth.
- `financials.py` — `realtime_quote` bypasses the TTL cache entirely so live prices are never served stale.

### UX
- `cli/main.py` — context-history ellipsis (`...`) is now only appended when the prior answer exceeds 300 characters.

---

## v1.0.8 — Enhancements Wave 2 (Feb 2026)

- **LLM Streaming** — `Synthesizer.synthesize()` uses `chain.astream()` with a Rich `Live` panel; tokens display as they arrive.
- **Session Memory** — `interactive` mode prepends last 3 Q&A pairs as structured context into each new query.
- **LLM Singleton** — `get_llm_singleton()` replaces per-call `get_llm()` in CLI, reusing the HTTP connection pool across queries.
- **Qualitative Query Support** — Empty entity list no longer hard-fails; qualitative intent routes directly to LLM synthesis from domain knowledge.
- **Confidence Breakdown** — `ConfidenceBreakdown` model added with `data_coverage`, `data_quality`, `inference_strength`, `overall` fields.
- **Forensic Audit Trail** — `FinalReport` extended with `evidence_log`, `inference_map`, `logic_constraints`, `audit_trail`.
- **Public Python API** — `jasper/__init__.py` exports `run_research()` async function and `FinalReport` (lazy import via `__getattr__`).

---

## v1.0.7 — Enhancements Wave 1 (Feb 2026)

- **Real-time Quote Tool** — `fetch_realtime_quote()` added to `FinancialDataRouter` and both providers; executor dispatches `realtime_quote` and `key_metrics`.
- **Balance Sheet Tool** — `fetch_balance_sheet()` fully wired through router, both providers, and executor.
- **Cash Flow Tool** — `fetch_cash_flow()` wired end-to-end.
- **TTL Response Cache** — In-memory cache with 15-min default TTL (`JASPER_CACHE_TTL_SECS`) added to `financials.py`.
- **Partial-Success Validation** — Validator proceeds with synthesis if ≥ 50 % of tasks complete, with confidence penalty.
- **Reflector Agent** — `reflector.py` fully implemented: transient-error retry loop, permanent-error graceful skip, integrated into controller pipeline between Execution and Validation.
- **Dead Code Removed** — `jasper/tools/aplha_vantage.py`, `jasper/cli/render.py`, `jasper/main.py`, and `FinancialClient` placeholder removed.
- **Default LLM upgraded** — Changed from `xiaomi/mimo-v2-flash:free` to `google/gemini-2.0-flash-exp:free`; `OPENROUTER_MODEL` env override documented.
- **Context Window Guard** — Synthesizer truncates task data to a token budget before building the synthesis prompt.
- **PDF Unique Filenames** — Exports now use `jasper_report_YYYYMMDD_HHMMSS.pdf` format.
- **Report Persistence** — Reports saved as JSON to `exports/` for cross-session recall.

---

## v1.0.6 → v1.0.3 — Incremental Fixes (Jan–Feb 2026)

See [VERSION_1.0.6.md](VERSION_1.0.6.md), [VERSION_1.0.5.md](VERSION_1.0.5.md), [VERSION_1.0.4.md](VERSION_1.0.4.md), [VERSION_1.0.3.md](VERSION_1.0.3.md) for individual release notes.

---

## v1.0.0 — Critical Bug Fixes (Jan 2026)

Eight critical bugs fixed:
1. Alpha Vantage response parsing (key mismatch `annualReports` → `annualReports`)
2. yfinance deprecated `quarterly_financials` replaced with `quarterly_income_stmt`
3. Executor dispatch table missing `financial_statement` alias and `cash_flow` / `realtime_quote` branches
4. Reflector stub (`return state`) replaced with full implementation
5. Validator partial-success path added
6. `config.py` ALPHA_VANTAGE_API_KEY `"demo"` warning logic corrected
7. `version` CLI command fixed to use `importlib.metadata`
8. PDF export filename uniqueness

See [TEST_REPORT_v1.0.0.md](TEST_REPORT_v1.0.0.md) for the full 33-test validation report.

---

## v0.2.0 — Architecture Overhaul (Jan 2026)

See [VERSION_0.2.0.md](VERSION_0.2.0.md).

---

## v0.1.0 — Initial Release (Jan 2026)

See [RELEASE_v0.1.0.md](RELEASE_v0.1.0.md).
