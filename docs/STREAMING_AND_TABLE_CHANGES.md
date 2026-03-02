# Jasper CLI Updates: Streaming, Tables, and Layout

## Summary
This document captures the recent implementation changes made to improve:
- synthesis streaming behavior,
- terminal table readability,
- comparison-query reliability (ticker resolution), and
- CLI layout quality.

---

## 1) Streaming output changes

### What changed
- Bounded synthesis preview in live mission board (no near-full token echo).
- Token updates now render short, sanitized rolling text only.
- Added duplicate-preview suppression to reduce noisy rerenders.
- Kept full synthesis content for final report output.

### Files
- `jasper/cli/main.py`

### Impact
- Live output is readable and less distracting.
- Sensitive/verbose in-flight raw output is no longer dumped to terminal.

---

## 2) Table rendering changes (Dexter-inspired)

### What changed
- Added markdown-table parsing + unicode box-table rendering pipeline for CLI.
- Existing markdown table repair remains in place, then box transformation is applied.
- Final CLI report paths now use formatted output pipeline.
- Box tables are wrapped in fenced text blocks to preserve line structure in Rich Markdown.

### Files
- `jasper/cli/interface.py`

### Impact
- Financial evidence tables render as readable boxed tables instead of broken pipe lines.
- Compressed/LLM-mangled rows are significantly more recoverable in terminal view.

---

## 3) Synthesis prompt constraints (table quality at source)

### What changed
- Tightened table instructions in synthesizer prompt:
  - max 3 columns per table,
  - strict row boundaries,
  - no empty filler rows,
  - compact headers/numbers,
  - prefer bullets for non-comparative content.
- Multi-ticker guidance now explicitly asks to split into multiple compact tables when needed.

### Files
- `jasper/agent/synthesizer.py`

### Impact
- Lower chance of malformed, overly wide, or noisy tables being generated.

---

## 4) Ticker robustness fixes (query execution reliability)

### What changed
- Added ticker candidate fallback strategy in financial router:
  - alias map for common Indian symbols,
  - `.NS` candidate fallback for likely NSE tickers.
- Router now tries multiple symbol candidates before failing.
- Error message now includes tried symbols for debugging.

### Files
- `jasper/tools/financials.py`

### Impact
- Queries like ICICI/HDFC no longer fail due to raw symbol normalization issues.

---

## 5) Quote-path hardening for fallback

### What changed
- `realtime_quote` now treats quote payloads with no actionable fields as provider failure.
- This enables router fallback to alternate symbols (for example, NSE forms) instead of accepting empty N/A payloads.

### Files
- `jasper/tools/providers/yfinance.py`

### Impact
- Prevents false-success quote fetches on invalid symbols.

---

## 6) Layout cleanup changes

### What changed
- Added compact layout normalization for CLI synthesis markdown:
  - normalizes warning headers,
  - removes obvious visual noise lines,
  - collapses excessive blank lines (outside fenced blocks).

### Files
- `jasper/cli/interface.py`

### Impact
- Cleaner terminal output in warning-heavy sections.

---

## 7) Streaming/progress UX upgrades (Dexter-style direction)

### What changed
- Added execution task timing capture and completion duration display.
- Improved mission-board status text on task completion/failure with concise updates.

### Files
- `jasper/cli/main.py`

### Impact
- Better operator feedback during long runs.
- Progress feels more structured and less opaque.

---

## 8) Tests added/updated

### Added coverage
- Bounded/sanitized synthesis preview assertions.
- CLI box-table rendering assertions.
- Compressed comparison table rendering regression.
- Indian ticker alias fallback regression.

### Files
- `tests/test_integration_fixes.py`
- `tests/test_table_parsing.py`
- `tests/test_critical_fixes.py`

---

## 9) Validation status

Focused regression suites were run after changes and passed:
- integration + table parsing suites,
- critical fixes suite,
- repeated interactive smoke tests with ICICI/HDFC comparison prompts.

---

## 10) Notes

- Some data-source limitations (for example missing NPA/CET1 fields from upstream payloads) still surface as warnings in synthesis; these are content/data constraints, not rendering regressions.
- Current improvements prioritize terminal UX and robust symbol handling without changing the broader architecture.
