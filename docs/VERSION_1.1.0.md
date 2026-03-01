# Jasper v1.1.0 — Release Notes

**Release date:** March 1, 2026  
**Status:** Stable  
**Test coverage:** 77/77 tests passing (100%)

---

## Summary

v1.1.0 is a critical dependency fix release. It resolves a Click 8.3.1 incompatibility with Typer 0.9.0 that was causing CLI help rendering to crash with `TypeError: Parameter.make_metavar() missing 1 required positional argument: 'ctx'`.

**No code changes to core logic.** Pure dependency version pinning.

---

## What's Fixed

### Dependencies
- **Click** pinned to `<8.1.0` (was `<9.0.0`)
  - Click 8.3.1+ breaks Typer 0.9.0's help rendering
  - Click 8.0.4 is fully compatible with current Typer
  
### Test Results
- ✅ **77/77 tests passing** (was 76/77)
- ✅ `test_cli_help` now works without crash
- ✅ All other tests remain passing
- ℹ️ 69 deprecation warnings (pre-existing, non-fatal)

### CLI Impact
```bash
jasper --help          # ✅ Now works (was crashing)
jasper ask "query"     # ✅ Still works
jasper interactive     # ✅ Still works
jasper export          # ✅ Still works
jasper doctor          # ✅ Still works
jasper version         # ✅ Still works
```

---

## Files Changed

- `pyproject.toml` — Updated Click constraint
- `docs/UPDATE_SUMMARY.md` — Added v1.1.0 changelog entry
- `README.md` — Updated footer from v1.0.9 → v1.1.0
- `tests/test_cli_integration.py` — Updated version strings

---

## Installation & Upgrade

### From PyPI
```bash
pip install --upgrade jasper-finance
```

### From source
```bash
git clone https://github.com/ApexYash11/jasper.git
cd jasper
git checkout v1.1.0
pip install -e .
```

---

## Compatibility

| Component | Requirement | Tested |
| --- | --- | --- |
| Python | 3.9–3.12 | ✅ 3.12.4 |
| Typer | 0.9.0 | ✅ |
| Click | 8.0.4 | ✅ |
| Pydantic | ≥2.0.0 | ✅ |
| LangChain | ≥0.1.0 | ✅ |

---

## Migration Notes

**No breaking changes.** Existing code and CLI usage remain unchanged. This is a pure dependency fix.

---

## Known Issues

None. Version 1.1.0 is stable and production-ready.

---

**Built by analysts, for analysts. Stop guessing. Start researching. Jasper Finance v1.1.0**
