# Jasper Finance — Full Codebase Audit & Upgrade Prompt

> **Purpose:** This document is the single source of truth for all identified bugs, warnings, UI/UX issues, and upgrades across the Jasper codebase. It is structured as a numbered prompt for AI coding agents (opencode, Claude Code, Cursor, etc.) to tackle issues in priority order. Each issue has a file path, root cause, and exact fix.

---

## How to use this with opencode

Paste the following as your task prompt, then reference the numbered issues below:

```
You are working on the Jasper Finance codebase (jasper/ directory).
Read ALL files before making changes. Fix issues in the numbered order below.
For each issue: locate the file, understand the root cause, apply the fix, confirm no regressions.
Do not refactor unrelated code. Do not add new dependencies unless the issue explicitly requires one.
After each fix, note which issue number was resolved.
```

---

## Part 1 — Critical Bugs (Fix First)

---

### Issue 1 — Lambda late-binding in asyncio.gather causes wrong ticker fetches

**File:** `jasper/agent/executor.py` → `_execute_with_retries()` calls inside `execute_task()`

**Severity:** 🔴 Critical — Data correctness bug

**Root cause:**
The lambdas passed to `_execute_with_retries` close over `ticker` by reference:

```python
await self._execute_with_retries(
    state, task,
    lambda: self.financial_router.fetch_income_statement(ticker)
)
```

When `asyncio.gather` runs multiple tasks concurrently (as it does in `controller.py`), all lambdas in the closure share the same `ticker` variable from the enclosing scope. By the time the lambda executes, the loop may have advanced and `ticker` points to the last-assigned value — meaning AAPL tasks may fetch MSFT data silently.

**Fix — capture ticker as a default arg:**

```python
# income_statement
await self._execute_with_retries(
    state, task,
    lambda t=ticker: self.financial_router.fetch_income_statement(t)
)

# balance_sheet
await self._execute_with_retries(
    state, task,
    lambda t=ticker: self.financial_router.fetch_balance_sheet(t)
)

# cash_flow
await self._execute_with_retries(
    state, task,
    lambda t=ticker: self.financial_router.fetch_cash_flow(t)
)

# realtime_quote
await self._execute_with_retries(
    state, task,
    lambda t=ticker: self.financial_router.fetch_realtime_quote(t),
    skip_fiscal_validation=True,
)
```

Apply this pattern to every lambda in `execute_task()`. The `t=ticker` default-arg binding captures the value at definition time, not call time.

---

### Issue 2 — In-memory cache has no async lock — concurrent tasks can corrupt it

**File:** `jasper/tools/financials.py` → `_cache: Dict[str, tuple]`, `_cache_get()`, `_cache_set()`

**Severity:** 🔴 Critical — Race condition under concurrent task execution

**Root cause:**
The module-level `_cache` dict is read and written by multiple `asyncio.gather` tasks concurrently. The sequence `read → check TTL → write` is not atomic. Two tasks fetching the same ticker simultaneously can both miss the cache, make two API calls, and race to write — burning AV quota and potentially writing a partial result.

**Fix — add a per-key asyncio.Lock:**

```python
import asyncio

_cache: Dict[str, tuple] = {}
_cache_locks: Dict[str, asyncio.Lock] = {}

def _get_cache_lock(key: str) -> asyncio.Lock:
    if key not in _cache_locks:
        _cache_locks[key] = asyncio.Lock()
    return _cache_locks[key]

async def _cache_get_async(key: str):
    async with _get_cache_lock(key):
        entry = _cache.get(key)
        if entry is None:
            return None
        if (time.monotonic() - entry[0]) < _CACHE_TTL:
            return entry[1]
        del _cache[key]
        return None

async def _cache_set_async(key: str, data) -> None:
    async with _get_cache_lock(key):
        _cache[key] = (time.monotonic(), data)
```

Update `_fetch_with_fallback` to use `await _cache_get_async(cache_key)` and `await _cache_set_async(cache_key, result)`.

---

### Issue 3 — dist/ wheel files committed to git — bloats repo permanently

**File:** `.gitignore` + `dist/` directory

**Severity:** 🔴 Critical — Repo hygiene / clone size

**Root cause:**
Three full release wheels (`jasper_finance-1.1.1`, `1.1.4`, `1.1.6`) and their sdist tarballs (~320KB total) are tracked in git. The CI publish workflow explicitly runs `rm -rf dist/` before building, confirming these are orphaned artifacts. They permanently inflate every `git clone`.

**Fix — safe untrack (no history rewrite):**

```bash
# .gitignore — add these lines
dist/
*.whl
*.egg-info/

# Remove from index (stops tracking), but don't rewrite history
git rm -r --cached dist/
# Check actual egg-info directory name (underscore vs hyphen) first:
# ls -d jasper_finance.egg-info* jasper_finance.egg_info*
git rm -r --cached jasper_finance.egg_info/  # adjust if hyphen
git add .gitignore
git commit -m "chore: untrack dist artifacts and egg-info"
```

No `--force-push`, no history rewrite. Past wheel blobs remain in git history (they're on PyPI anyway) — that's fine. Future builds won't re-add them because `.gitignore` now covers both directories.

---

### Issue 4 — `__version__` defined in two places and out of sync

**File:** `jasper/__init__.py` (hardcoded `__version__ = "1.1.7"`) and `pyproject.toml` (also `version = "1.1.7"`)

**Severity:** 🔴 Critical — Version drift will cause bugs on PyPI installs

**Root cause:**
Version is duplicated. README still references 1.1.6 in section headers. The committed `dist/` has 1.1.6 wheels. These will diverge again the next time only one place is updated.

**Fix — single source of truth in `pyproject.toml`:**

```python
# jasper/__init__.py — replace hardcoded version with:
from importlib.metadata import version as _pkg_version, PackageNotFoundError
try:
    __version__ = _pkg_version("jasper-finance")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"  # fallback for editable installs without metadata
```

This is the same approach already used in `version_command()` — apply it consistently to `__init__.py` too.

---

### Issue 5 — `TASK_COMPLETED` log event missing `"description"` key — board shows blank task names

**File:** `jasper/core/controller.py` → `execute_with_logging()` inner function

**Severity:** 🔴 Critical — Silent UI bug, execution board never shows task names on completion

**Root cause:**
```python
self.logger.log("TASK_COMPLETED", {"task_id": task.id, "status": task.status})
```
`RichLogger.log()` reads `payload.get("description")` for the `TASK_COMPLETED` event to render the task label on the execution board. It always gets `None`. The board shows `✔ None` or blank.

**Fix — add description to the payload:**

```python
self.logger.log("TASK_COMPLETED", {
    "task_id": task.id,
    "status": task.status,
    "description": task.description,
})
```

---

## Part 2 — Streaming Issues (Fix for Perceived Performance)

---

### Issue 6 — 300-char gate creates 3–5 second silence before first visible synthesis token

**File:** `jasper/cli/main.py` → `RichLogger.on_synthesis_token()` → `_preview_update_every_chars = 300`

**Severity:** 🔴 Critical UX — Main cause of "synthesis feels frozen"

**Root cause:**
The Live board only updates after 300 characters accumulate OR a sentence ends (`., !, ?`). At ~20 tok/s × ~4 chars/tok, that's ~3.75 seconds of silence. The board shows "✍️ Compiling executive report..." frozen with no indication the model is streaming.

**Fix:**
```python
# Change these two constants in RichLogger.__init__:
self._preview_update_every_chars = 60   # was 300 — updates every ~15 tokens
self._preview_char_limit = 120           # was 160 — keeps preview snappy
```

---

### Issue 7 — Two rate limiters compounding: 200ms debounce + 2fps Live = 500ms minimum refresh

**File:** `jasper/cli/main.py` → `_min_update_interval = 0.2` and `Live(refresh_per_second=2)`

**Severity:** 🔴 Critical UX — Synthesis looks like batch processing, not streaming

**Root cause:**
There are two independent rate limiters:
1. `_min_update_interval = 0.2` — `_should_update_live()` blocks `live.update()` calls more frequent than 200ms
2. `Live(refresh_per_second=2)` — the Rich Live widget re-renders at most every 500ms

These compound in series. Effective minimum between visible terminal updates during synthesis = 500ms. With a fast model (Groq, ~100 tok/s), users still see chunky jumps instead of smooth flow.

**Fix:**
```python
# In RichLogger.__init__:
self._min_update_interval = 0.08   # was 0.2 — 80ms, ~12fps ceiling

# In execute_research():
live_context = Live(board_panel, refresh_per_second=10, console=console)
#                                                    ^ was 2
```

Rich terminals (iTerm2, Windows Terminal, VS Code) handle 10fps without flicker. This makes synthesis visually smooth.

---

### Issue 8 — Tier 2 (plain PowerShell) synthesis prints dots, not words — buffer is never flushed

**File:** `jasper/cli/main.py` → `RichLogger._handle_synthesis_print()`

**Severity:** 🔴 Critical UX for Windows users — synthesis output is invisible

**Root cause:**
`synthesis_print_buffer` accumulates tokens but is never printed. Only dots are output every 2 seconds:

```python
# Current broken behaviour:
if elapsed >= 2.0:
    self.console.print(".", end="", flush=True)
```

The buffer exists for no functional reason — it accumulates and is capped at 500 chars but never shown. Windows users on plain PowerShell see `......` instead of actual synthesis output.

**Fix — print at sentence boundaries:**
```python
def _handle_synthesis_print(self, token: str) -> None:
    self.synthesis_print_buffer += token

    # Flush at sentence boundaries or every ~80 chars
    is_sentence_end = token.rstrip().endswith((".", "!", "?", "\n"))
    is_long_enough = len(self.synthesis_print_buffer) >= 80

    if is_sentence_end or is_long_enough:
        self.console.print(self.synthesis_print_buffer, end="", flush=True)
        self.synthesis_print_buffer = ""

        # Newline after sentences for readability
        if is_sentence_end:
            self.console.print("")
```

---

### Issue 9 — astream() fallback to ainvoke() is silent — board appears frozen during fallback

**File:** `jasper/agent/synthesizer.py` → `synthesize()` → `except Exception` fallback block

**Severity:** 🟡 Warning — Bad UX for non-streaming model providers

**Root cause:**
When `astream()` fails (some OpenRouter models, e.g. certain Mistral variants, don't support streaming), the code silently falls back to `ainvoke()` — which can take 15–60 seconds with zero feedback. The board shows "✍️ Compiling..." frozen until `ainvoke` returns.

**Fix — notify the token callback before blocking call:**
```python
except Exception as e:
    self.logger.log("SYNTHESIS_STREAM_FALLBACK", {"error": str(e)})
    # Signal to UI that we're in non-streaming mode
    if token_callback:
        callback_result = token_callback(
            "[non-streaming model — generating full response, please wait...]"
        )
        if inspect.isawaitable(callback_result):
            await callback_result
    response = await chain.ainvoke({
        "query": state.query,
        "data": data_context,
        "report_mode": state.report_mode.value,
        "comparison_note": comparison_note,
    })
    full_response = response.content
```

---

### Issue 10 — Synthesis preview shows raw tail-slice, often mid-word — switch to sentence boundary

**File:** `jasper/cli/main.py` → `on_synthesis_token()` → preview construction

**Severity:** 🟡 Warning — Confusing UX, preview often shows fragment like "...nd operating mar"

**Root cause:**
```python
preview = "..." + normalized[-self._preview_char_limit:]
```
This takes the last N chars of the accumulated buffer — which is mid-word/mid-sentence. The preview should show the most recent complete sentence.

**Fix:**
```python
import re

# Replace the preview construction block:
sentences = re.split(r'(?<=[.!?])\s+', normalized)
if len(sentences) > 1 and len(sentences[-1]) > 10:
    preview = sentences[-1][:120]
elif len(sentences) > 1:
    preview = sentences[-2][:120] + " " + sentences[-1]
else:
    preview = normalized[-120:]
```

---

## Part 3 — Code Quality Warnings

---

### Issue 11 — PEP 8 naming violations on public classes

**Files:**
- `jasper/agent/validator.py` → `class validator`
- `jasper/core/state.py` → `class validationresult`

**Severity:** 🟡 Warning — Breaks Python convention, confusing alongside properly named peers

**Fix — rename to CapWords:**
```python
# validator.py
class Validator:  # was: validator

# state.py
class ValidationResult(BaseModel):  # was: validationresult
```

Update all import sites:
- `jasper/core/controller.py`: `from ..agent.validator import validator` → `from ..agent.validator import Validator`
- `jasper/__init__.py`: `from .agent.validator import validator as ValidatorClass`
- `jasper/cli/main.py`: `from ..agent.validator import validator`

---

### Issue 12 — AlphaVantageClient creates a new httpx.AsyncClient per request — no connection reuse

**File:** `jasper/tools/providers/alpha_vantage.py` → `_fetch()`

**Severity:** 🟡 Warning — Performance hit on every API call, wastes TCP handshakes

**Root cause:**
```python
async def _fetch(self, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:  # new client every call
        r = await client.get(...)
```

**Fix — share a client across requests:**
```python
class AlphaVantageClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15)
        return self._client

    async def _fetch(self, params: dict) -> dict:
        client = await self._get_client()
        r = await client.get(self.BASE_URL, params=params)
        ...

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
```

---

### Issue 13 — AlphaVantage only returns `annualReports`, discards `quarterlyReports` silently

**File:** `jasper/tools/providers/alpha_vantage.py` → `income_statement()`, `balance_sheet()`, `cash_flow()`

**Severity:** 🟡 Warning — README claims "annual + quarterly" but quarterly is silently dropped

**Root cause:**
```python
return data["annualReports"]  # quarterlyReports exists in response but is discarded
```

**Fix — return both:**
```python
async def income_statement(self, ticker: str) -> dict:
    data = await self._fetch({"function": "INCOME_STATEMENT", "symbol": ticker, "apikey": self.api_key})
    if "annualReports" not in data:
        raise DataProviderError(f"Alpha Vantage malformed income_statement response for {ticker}")
    return {
        "annual": data["annualReports"],
        "quarterly": data.get("quarterlyReports", []),
    }
```

Apply the same pattern to `balance_sheet()` and `cash_flow()`.

Note: Update `Executor._validate_financial_data()` to accept the new dict shape (check `isinstance(data, dict) and "annual" in data`).

---

### Issue 14 — Fallback `sources` hardcoded to "SEC EDGAR" — Jasper doesn't use SEC EDGAR

**Files:**
- `jasper/core/controller.py` → `_build_final_report()` → `sources = {"SEC EDGAR", "Financial Data Providers"}`
- `jasper/cli/main.py` → `execute_research()` → `sources = {"SEC EDGAR"}`

**Severity:** 🟡 Warning — Factually incorrect in generated reports and PDF audit trail

**Fix:**
```python
# In both locations, replace:
sources = {"SEC EDGAR"}
# With:
sources = {"Alpha Vantage", "yfinance"}
```

---

### Issue 15 — CI lint step has 5 brittle fallback chains — fix the env, not the command

**File:** `.github/workflows/ci.yml` → Lint step in both `test-core` and `publish` jobs

**Severity:** 🟡 Warning — Noisy CI logs, masks real PATH issues

**Root cause:**
The lint step tries `ruff`, `python -m ruff`, `python3 -m ruff` with verbose debug output — a sign the CI env had PATH problems that were worked around instead of fixed.

**Fix — simplify to one reliable call:**
```yaml
- name: Lint with ruff
  run: python -m ruff check .
```

Ruff is in `[dev]` deps and installed via `pip install -e ".[dev]"` in the prior step — `python -m ruff` is always available after that. Remove all debug echo lines and fallback chains.

---

### Issue 16 — `render_mission_board()` is dead code — never called, duplicates `build_persistent_board()`

**File:** `jasper/cli/interface.py` → `render_mission_board()` function (~80 lines)

**Severity:** 🟡 Warning — Dead code, maintenance burden

**Root cause:**
`render_mission_board()` is the old stateless renderer (rebuilds entire tree per frame). It was replaced by the persistent `build_persistent_board()` + `append_task_to_node()` architecture in v1.1.4. The old function was never removed — it's ~80 lines of unreachable code that confuses anyone reading the file.

**Fix:**
Delete `render_mission_board()` entirely from `interface.py`. Confirm with `grep -rn "render_mission_board" jasper/` that no callers exist.

---

### Issue 17 — `jasper/cli/render.py` creates its own `Console()` — conflicts with main console

**File:** `jasper/cli/render.py` → `console = Console()`

**Severity:** 🟡 Warning — Two Console instances can produce interleaved output

**Root cause:**
`render.py` creates its own `Console()` at module level (line 7). `cli/main.py` creates a separate terminal-aware `Console` with `force_terminal` / `legacy_windows` flags. If any function from `render.py` is called during a Live session, the two consoles compete and can corrupt the Live rendering.

**Fix — remove the module-level console from render.py:**
```python
# render.py: remove console = Console() at module level
# Pass console as a parameter to functions that need to print:
def render_status(msg: str, console: Console) -> None:
    console.print(f"[bold green]Jasper:[/bold green] {msg}")
```

---

## Part 4 — UI / UX Issues

---

### Issue 18 — Confidence shown as both `63%` and `(0.63)` in forensic dashboard — pick one

**File:** `jasper/cli/interface.py` → `render_forensic_report()` → confidence row

**Fix:**
```python
# Replace:
Text(f"{report.confidence_score:.0%} ({report.confidence_score:.2f})", style=conf_style)

# With:
Text(f"{report.confidence_score:.0%}", style=conf_style)

# Add separate breakdown row below:
if report.confidence_breakdown:
    bd = report.confidence_breakdown
    dash_table.add_row(
        "  └ breakdown",
        f"coverage {bd.data_coverage:.0%}  ·  quality {bd.data_quality:.0%}  ·  inference {bd.inference_strength:.0%}",
    )
```

---

### Issue 19 — Audit trail hard-capped at 5 rows regardless of query size

**File:** `jasper/cli/interface.py` → `render_forensic_report()` → `shown = report.audit_trail[-5:]`

**Root cause:**
Most queries have 3–6 tasks. Capping at 5 means a 6-task query shows "…and 1 more task (see PDF)" — which is absurd. The PDF export hint is useless unless the user has already set up the export extras.

**Fix:**
```python
MAX_CLI_AUDIT_ROWS = 10
if len(report.audit_trail) <= MAX_CLI_AUDIT_ROWS:
    shown = report.audit_trail
else:
    shown = report.audit_trail[-MAX_CLI_AUDIT_ROWS:]
    # Only show the PDF hint if there are genuinely many tasks
```

---

### Issue 20 — Evidence matrix shows raw Python dicts as "Value" — completely unreadable

**File:** `jasper/cli/interface.py` → `render_forensic_report()` → evidence table `str(item.value)`

**Root cause:**
Evidence items render as `{'fiscalDateEnding': '2024-09-28', 'totalRevenue': '391035000000'...` truncated at 100 chars. This is the primary data surface in the forensic report and it's unreadable.

**Fix — add a value formatter:**
```python
def _fmt_number(raw: str) -> str:
    """Format large numbers as $X.XB / $X.XM."""
    try:
        n = float(raw.replace(",", ""))
        if abs(n) >= 1e9:
            return f"${n/1e9:.1f}B"
        if abs(n) >= 1e6:
            return f"${n/1e6:.1f}M"
        return f"${n:,.0f}"
    except (ValueError, TypeError):
        return str(raw)

def _format_evidence_value(v) -> str:
    if isinstance(v, dict):
        date = v.get("fiscalDateEnding", "")
        rev = v.get("totalRevenue") or v.get("revenue")
        ni = v.get("netIncome")
        parts = [date] if date else []
        if rev:
            parts.append(f"Rev {_fmt_number(rev)}")
        if ni:
            parts.append(f"NI {_fmt_number(ni)}")
        return "  ·  ".join(parts) if parts else str(v)[:60]
    return str(v)[:80]

# In render_forensic_report():
evidence_table.add_row(item.id, item.metric, _format_evidence_value(item.value), item.source, item.status)
```

---

### Issue 21 — Banner gradient uses hardcoded character indices — breaks if banner changes

**File:** `jasper/cli/interface.py` → `render_banner()` → `text.stylize(..., 0, 60)`, `text.stylize(..., 60, 200)`

**Fix — line-based gradient:**
```python
def render_banner():
    lines = BANNER_ART.strip().split('\n')
    full_text = Text()
    for i, line in enumerate(lines):
        ratio = i / max(1, len(lines) - 1)
        if ratio < 0.4:
            style = "bold white"
        elif ratio < 0.75:
            style = f"bold {THEME['Accent']}"
        else:
            style = f"bold {THEME['Brand']}"
        full_text.append(line + "\n", style=style)

    subtitle = Text(" >> FINANCIAL INTELLIGENCE SYSTEM << ", style=f"bold #000000 on {THEME['Accent']}")
    return Group(Text(""), Align.center(full_text), Align.center(subtitle), Text(""))
```

---

### Issue 22 — Session history in interactive mode is lost on restart — add optional persistence

**File:** `jasper/cli/main.py` → `interactive_command()` → `history = []`

**Fix — persist to `~/.jasper/history.jsonl`:**
```python
import json

_HISTORY_PATH = _CACHE_DIR / "history.jsonl"

def _load_history(max_items: int = 20) -> list:
    if not _HISTORY_PATH.exists():
        return []
    try:
        lines = _HISTORY_PATH.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(l) for l in lines[-max_items:]]
    except Exception:
        return []

def _save_history_entry(q: str, a: str) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"q": q, "a": (a or "")[:300]}) + "\n")
    except Exception:
        pass

# In interactive_command():
history = _load_history()  # was: history = []
# After each successful query:
_save_history_entry(user_input, state.final_answer)
```

---

## Part 5 — Upgrades / Feature Work

---

### Issue 23 — Replace 3-rate-limiter streaming with a clean async refresh loop

**Files:** `jasper/cli/main.py` → `execute_research()` and `RichLogger`

**Why:** Issues 6 + 7 are symptom fixes. The real fix is architectural: decouple token arrival rate from render rate using a dedicated refresh task.

**Design:**
```python
# In execute_research(), inside the Live context:
import asyncio

stop_refresh = asyncio.Event()

async def _refresh_loop():
    while not stop_refresh.is_set():
        preview = logger.get_latest_preview()  # new method on RichLogger
        if preview:
            update_synthesis_status(synthesis_node, f"✍️  {preview}▌")
            if live:
                live.update(board_panel)
        await asyncio.sleep(0.08)  # 12.5fps

refresh_task = asyncio.create_task(_refresh_loop())
try:
    state = await controller.run(query)
finally:
    stop_refresh.set()
    await refresh_task

# Add to RichLogger:
def get_latest_preview(self) -> str:
    if not self.synthesis_buffer:
        return ""
    sentences = re.split(r'(?<=[.!?])\s+', self.synthesis_buffer.strip())
    return (sentences[-1] if sentences else self.synthesis_buffer)[-120:]
```

Remove the 300-char gate and debounce from `on_synthesis_token` — those are no longer needed. The token callback just appends to the buffer.

---

### Issue 24 — Add disk-backed persistent cache to survive process restarts

**File:** `jasper/tools/financials.py`

**Why:** AV free tier is 25 calls/day. Every `jasper ask` restart loses the in-memory cache. Users running multiple queries per day hit rate limits after ~6 queries.

**Design — aiosqlite (not shelve):**

`shelve` uses file-level locking that breaks under `asyncio.gather` concurrency. Use `aiosqlite` — truly async, safe under concurrent coroutines.

```python
import aiosqlite
import json
import os

_DISK_CACHE_DB = os.path.join(os.path.expanduser("~"), ".jasper", "cache.db")
os.makedirs(os.path.dirname(_DISK_CACHE_DB), exist_ok=True)

async def _disk_cache_get(key: str):
    try:
        async with aiosqlite.connect(_DISK_CACHE_DB) as db:
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
        async with aiosqlite.connect(_DISK_CACHE_DB) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, ts REAL, data TEXT)"
            )
            await db.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?)",
                (key, time.monotonic(), json.dumps(data, default=str))
            )
            await db.commit()
    except Exception:
        pass  # disk cache is best-effort
```

Add `aiosqlite>=0.19.0` to `pyproject.toml` dependencies.

---

### Issue 25 — Add Financial Modeling Prep (FMP) as 3rd data provider

**File:** New file `jasper/tools/providers/fmp.py` + register in `jasper/__init__.py` / `cli/main.py`

**Why:** AV free = 25 calls/day, yfinance is scrape-based and fragile. FMP free tier = 250 calls/day with a stable REST API. Adding it as a third provider in `FinancialDataRouter` costs ~50 lines and dramatically improves reliability.

**Note:** Uses the persistent-httpx-client pattern from Issue 12 — do NOT create a new `AsyncClient` per request.

```python
# jasper/tools/providers/fmp.py
import httpx
from ..exceptions import DataProviderError

class FMPClient:
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None  # reuse Issue 12 pattern

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15)
        return self._client

    async def _fetch(self, path: str, params: dict) -> list:
        client = await self._get_client()
        r = await client.get(f"{self.BASE_URL}{path}", params={"apikey": self.api_key, **params})
        if r.status_code != 200:
            raise DataProviderError(f"FMP HTTP {r.status_code} for {params}")
        data = r.json()
        if isinstance(data, dict) and "Error Message" in data:
            raise DataProviderError(f"FMP error: {data['Error Message']}")
        if not isinstance(data, list) or not data:
            raise DataProviderError(f"FMP: empty response for {path}")
        return data

    async def income_statement(self, ticker: str):
        data = await self._fetch(f"/income-statement/{ticker}", {"limit": 5})
        return [{"fiscalDateEnding": d["date"], "totalRevenue": str(d.get("revenue", 0)),
                 "netIncome": str(d.get("netIncome", 0)), "grossProfit": str(d.get("grossProfit", 0))}
                for d in data]

    async def balance_sheet(self, ticker: str):
        data = await self._fetch(f"/balance-sheet-statement/{ticker}", {"limit": 5})
        return [{"fiscalDateEnding": d["date"], "totalAssets": str(d.get("totalAssets", 0)),
                 "totalLiabilities": str(d.get("totalLiabilities", 0)),
                 "totalEquity": str(d.get("totalStockholdersEquity", 0))}
                for d in data]

    async def cash_flow(self, ticker: str):
        data = await self._fetch(f"/cash-flow-statement/{ticker}", {"limit": 5})
        return [{"fiscalDateEnding": d["date"], "operatingCashflow": str(d.get("operatingCashFlow", 0)),
                 "capitalExpenditures": str(d.get("capitalExpenditure", 0))}
                for d in data]

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
```

Add `FMPClient` as the second provider (between AV and yfinance) in `FinancialDataRouter` initialization in `cli/main.py` and `__init__.py`. Read `FMP_API_KEY` from env.

---

### Issue 26 — `run_research()` public API has no progress visibility — add event callback

**File:** `jasper/__init__.py` → `run_research()`

**Why:** The public API is used in notebooks and FastAPI routes. It returns a `FinalReport` with zero visibility into what's happening during the 10–30 second pipeline. Adding an `on_event` callback makes it usable with SSE streaming in FastAPI.

```python
from typing import Callable, Optional, Awaitable

async def run_research(
    query: str,
    on_event: Optional[Callable[[str, dict], Awaitable[None]]] = None,
) -> "Optional[FinalReport]":
    """
    on_event: async callback called with (event_type, payload) at each pipeline stage.
    Example:
        async def my_handler(event, payload):
            print(f"{event}: {payload}")
        await run_research("Apple revenue?", on_event=my_handler)
    """
    ...
```

Wire `on_event` into a custom `SessionLogger` subclass that calls it.

---

### Issue 27 — Repo hygiene: missing standard OSS files + typo in assets folder name

**Files:** Repo root

**Issues to fix:**
1. `assests/` → rename to `assets/` (typo — git mv assests assets)
2. Create `CONTRIBUTING.md` with setup instructions, dev workflow, PR guidelines
3. Create `CHANGELOG.md` with entries for v1.0.x → v1.1.7
4. Add GitHub issue templates: `.github/ISSUE_TEMPLATE/bug_report.md` and `feature_request.md`
5. Add repo description, topics, and website on GitHub (finance, agent, llm, terminal, python, langchain)
6. Rename `jasper_finance.egg-info/` → ensure it's in `.gitignore` and removed from tracking (covered in Issue 3)

---

## Execution Order for opencode

Work through issues in this sequence:

```
Phase 1 — Data Correctness (must fix before any testing)
  Issue 1  → Lambda late-binding in executor
  Issue 2  → Cache async lock
  Issue 5  → TASK_COMPLETED missing description

  After fixing Issues 1, 2, and 5, run regression tests:
  ```
  pytest tests/test_executor_lambda.py tests/test_cache_concurrency.py tests/test_logger_events.py -v
  ```

Phase 2 — Repo Hygiene (clean before streaming work)
  Issue 3  → Remove dist/ from git
  Issue 4  → Single-source __version__
  Issue 14 → Remove SEC EDGAR false attribution
  Issue 16 → Delete dead render_mission_board()
  Issue 17 → Fix render.py dual-Console

Phase 3 — Streaming (biggest perceived impact)
  PICK ONE PATH (do NOT do both):
  [Quick]  Issue 6  → (skip if doing 23)  Lower 300-char gate to 60
           Issue 7  → (skip if doing 23)  200ms debounce → 80ms, Live 2fps → 10fps
           Issue 8  → Tier 2 print synthesis words not dots
           Issue 9  → astream fallback signal
           Issue 10 → Sentence-boundary preview
  [Clean]  Issue 23 → (supersedes 6 + 7)  Async refresh loop, decouples token rate from render rate
           Issue 8  → Tier 2 print synthesis words not dots
           Issue 9  → astream fallback signal
           Issue 10 → Sentence-boundary preview

Phase 4 — Code Quality
  Issue 11 → Rename validator / validationresult
  Issue 12 → httpx persistent client
  Issue 13 → AV quarterly reports
  Issue 15 → CI lint step cleanup

Phase 5 — UI / UX
  Issue 18 → Confidence display
  Issue 19 → Audit trail cap
  Issue 20 → Evidence value formatter
  Issue 21 → Banner gradient
  Issue 22 → History persistence

Phase 6 — Upgrades (new features)
  Issue 24 → Disk cache
  Issue 25 → FMP provider
  Issue 26 → run_research() event callback
  Issue 27 → Repo hygiene
```

---

## File Map (for opencode context)

```
jasper/
├── __init__.py              → run_research() API, __version__ (Issues 4, 26)
├── __main__.py              → CLI entry point
├── agent/
│   ├── entity_extractor.py  → NER + intent classification
│   ├── executor.py          → Tool execution (Issues 1)
│   ├── planner.py           → Task decomposition
│   ├── reflector.py         → Retry/recovery loop
│   ├── synthesizer.py       → LLM synthesis + streaming (Issues 9)
│   └── validator.py         → Confidence scoring (Issue 11)
├── cli/
│   ├── interface.py         → Rich UI components (Issues 16, 18, 19, 20, 21)
│   ├── main.py              → CLI commands + RichLogger (Issues 6, 7, 8, 10, 22, 23)
│   └── render.py            → Shared console utils (Issue 17)
├── core/
│   ├── config.py            → Theme, API key loaders
│   ├── controller.py        → Pipeline orchestrator (Issue 5)
│   ├── errors.py            → Exception hierarchy
│   ├── llm.py               → OpenRouter LLM singleton
│   └── state.py             → Pydantic models (Issue 11)
├── export/
│   └── pdf.py               → WeasyPrint PDF export
├── observability/
│   └── logger.py            → SessionLogger → ~/.jasper/logs/
└── tools/
    ├── exceptions.py
    ├── financials.py         → Cache + FinancialDataRouter (Issues 2, 14, 24)
    └── providers/
        ├── alpha_vantage.py  → AV REST client (Issues 12, 13)
        ├── yfinance.py       → yfinance async wrapper
        └── fmp.py            → (new) FMP provider (Issue 25)
```

---

*Generated from full static analysis of jasper/ — 29 Python files, ~3,600 lines across agent, cli, core, export, observability, and tools modules.*