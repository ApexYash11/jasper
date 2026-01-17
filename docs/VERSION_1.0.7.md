# Version 1.0.7

Maintenance release: corrected PyPI release metadata and build system configuration.

## Key Changes
- **Build Metadata Fix**: Regenerated egg-info to resolve version mismatch in PyPI distribution
- **Package Normalization**: Verified jasper-finance package name normalization for PyPI compliance
- **Version Consistency**: All version strings synchronized across pyproject.toml, __init__.py, CLI, and tests

## Technical Details
- Fixed stale `jasper_finance.egg-info` containing outdated v1.0.2 metadata
- Confirmed all source version strings in sync (1.0.7)
- Validated package name normalization: `jasper-finance` (PyPI) → `jasper_finance` (egg-info)

## Deployment
- No code changes from v1.0.6
- Safe for production upgrade
- Recommended for users on v1.0.6 to ensure proper dependency resolution

## Testing
- All existing tests passing
- Version check: `jasper version` correctly reports 1.0.7
- Package import: `import jasper; print(jasper.__version__)` returns "1.0.7"
