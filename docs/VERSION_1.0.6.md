# Version 1.0.6

Edge case fixes and robustness improvements release.

## Key Changes
- **Intent Classification**: Enhanced NER prompt with growth/prediction keywords (growth potential, expected returns, earnings growth, stock increment)
- **Safe Serialization**: Added safe_truncate() to controller for non-serializable object handling
- **Synthesizer Stability**: Added null task reference checks with orphaned result logging
- **Validator Documentation**: Clarified qualitative mode confidence calculations (data_coverage N/A, baseline inference)
- **PDF Export Flexibility**: Allow empty evidence logs for qualitative reports (BUSINESS_MODEL, GENERAL modes)
- **Test Suite**: Comprehensive edge case coverage with 6 integration tests (all passing)

## Issues Fixed
- #1: Entity extractor intent misclassification for growth queries
- #5-7: Controller crashes on non-serializable objects
- #8: Synthesizer null task reference errors
- #9: Validator confidence confusion for qualitative workflows
- #10: PDF export rejection of qualitative reports

## Testing
- All 6 edge case tests passing (100% success)
- Original failing query now routes correctly to quantitative handler
- No regressions in existing functionality