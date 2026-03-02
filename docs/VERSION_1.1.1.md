# Jasper v1.1.1 — Release Notes

**Release date:** March 2, 2026  
**Status:** Stable  
**Test coverage:** 77/77 tests passing (100%)

---

## Summary

v1.1.1 is a patch release that fixes PyPI metadata consistency issues. It updates all version strings in package documentation to correctly reflect v1.1.1, ensuring successful package publication on PyPI.

**No code or dependency changes.** Pure documentation and metadata updates.

---

## What's Fixed

### PyPI & Package Metadata
- ✅ **README.md** — Updated footer from v1.1.0 → v1.1.1
- ✅ **README.md** — Updated Docker image tags from jasper-finance:1.0.9 → jasper-finance:1.1.1
- ✅ **pyproject.toml** — Version field already set to 1.1.1 (no changes needed)
- ✅ **GitHub Release Documentation** — Created VERSION_1.1.1.md

### Test Results
- ✅ **77/77 tests passing** (unchanged from v1.1.0)
- ✅ All platform integrations verified
- ✅ Package build validation passed

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
git checkout v1.1.1
pip install -e .
```

---

## Compatibility

| Component | Requirement | Tested |
| --- | --- | --- |
| Python | 3.9–3.12 | ✅ 3.12.4 |
| Typer | 0.9.0 | ✅ |
| Click | 8.0.4–8.0.x | ✅ |
| Pydantic | ≥2.0.0 | ✅ |
| LangChain | ≥0.1.0 | ✅ |

---

## Migration Notes

**No breaking changes.** Existing code and CLI usage remain unchanged. This release is purely a metadata sync update.

---

## Files Changed

- `README.md` — Updated v1.1.0 → v1.1.1 (footer and Docker tags)
- `docs/VERSION_1.1.1.md` — This file

---

## Known Issues

None. Version 1.1.1 is stable and production-ready.

---

**Built by analysts, for analysts. Stop guessing. Start researching. Jasper Finance v1.1.1**
