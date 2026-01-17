# Version 1.0.8

Patch release: PyPI metadata hygiene fix (1.0.7 was already published).

## Key Changes
- **Build Metadata Fix**: Regenerated egg-info to ensure correct PyPI distribution
- **Version Consistency**: All version strings synchronized across pyproject.toml, __init__.py, CLI, and tests
- **Tag Alignment**: Repository tag v1.0.8 includes full metadata corrections

## Technical Details
- Resolved stale `jasper_finance.egg-info` from previous builds
- Confirmed all source version strings in sync (1.0.8)
- Validated package name normalization for PyPI upload

## Deployment
- No code changes from v1.0.7
- Safe for production upgrade
- Supersedes v1.0.7 due to metadata fix

## Testing
- All existing tests passing
- Version check: `jasper version` correctly reports 1.0.8
- Package import: `import jasper; print(jasper.__version__)` returns "1.0.8"
