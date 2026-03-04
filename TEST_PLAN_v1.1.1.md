# Jasper v1.1.1 Feature Test Plan

## Overview
This test plan covers 3 comprehensive queries that showcase all major features released in v1.1.1.

---

## Query 1: Basic Financial Analysis (Single Company)
**Purpose**: Test core data fetching, balance sheet support, and basic synthesis

**Query**: 
```
What is Apple's current financial position? Show me revenue and assets.
```

**Features Tested**:
- ✓ Income statement fetching (AlphaVantageClient.income_statement)
- ✓ Balance sheet fetching (AlphaVantageClient.balance_sheet)
- ✓ FinancialDataRouter provider fallback (AV → YFinance)
- ✓ Executor dispatches income_statement AND balance_sheet
- ✓ Synthesizer generates report
- ✓ Validation logic (partial success support)
- ✓ Live rendering without artifact lines
- ✓ Logger does NOT print to stdout
- ✓ In-memory caching (second AAPL query uses cache)

**Expected Output**:
- Clean interactive UI with PLANNING → EXECUTION → SYNTHESIS phases
- No green horizontal line artifacts
- PDF/HTML export capability
- Confidence score and validation status

---

## Query 2: Comparative Analysis (Multiple Companies)
**Purpose**: Test multi-company research, data aggregation, and complex synthesis

**Query**: 
```
Compare the business model of Microsoft and Google. What are their key revenue sources and profit margins?
```

**Features Tested**:
- ✓ Multiple ticker handling (MSFT vs GOOGL)
- ✓ Entity extraction and mode inference (COMPARATIVE mode)
- ✓ Parallel task execution (fetch income statements for both)
- ✓ Balance sheet data for comparison
- ✓ Synthesizer context truncation (#22)
- ✓ Confidence scoring with partial data
- ✓ Report persistence to disk (cross-process support)
- ✓ Event logging with debounced Live updates

**Expected Output**:
- Comparative analysis with metrics side-by-side
- Synthesis highlighting differences
- Report cache available for export

---

## Query 3: Edge Case Testing (Real-world Scenario)
**Purpose**: Test error recovery, fallbacks, and robust validation

**Query**: 
```
What is the revenue trend for Tesla and Amazon over the last quarters?
```

**Features Tested**:
- ✓ Historical data fetching
- ✓ Reflector retry/recovery loop (#10) - if data fetch fails
- ✓ Validator partial-success path (#21) - proceeds even if 1 company fails
- ✓ Fallback to YFinance if Alpha Vantage rate-limited
- ✓ New executor dispatches (realtime_quote, cash_flow if available)
- ✓ Demo key warning (if no real Alpha Vantage key set)
- ✓ Version command (verify importlib.metadata usage)
- ✓ Exception hierarchy handling

**Expected Output**:
- Graceful degradation if data partially available
- Recovery attempts visible in live UI
- Confidence score reflects data availability
- Exportable report with warnings if applicable

---

## Testing Sequence

### Step 1: Check Version
```bash
python -m jasper version
```
Verifies: Version command uses importlib.metadata ✓

### Step 2: Run Interactive Session
```bash
python -m jasper interactive
```

**Test Sequence**:
1. Run Query 1 (Apple)
2. Run Query 1 again (tests caching)
3. Run Query 2 (Microsoft vs Google)
4. Export PDF: `/export`
5. Export HTML: `/html`
6. Run Query 3 (Tesla & Amazon)
7. Type `exit`

### Step 3: Run Direct Queries (Non-interactive)
```bash
python -m jasper ask "What is Apple's revenue and total assets?"
python -m jasper ask "Compare Microsoft and Google business models"
python -m jasper ask "What are the revenue trends for Tesla?"
```

---

## Features Mapped to Queries

| Feature | Query 1 | Query 2 | Query 3 |
|---------|---------|---------|---------|
| Income Statement | ✓ | ✓ | ✓ |
| Balance Sheet | ✓ | ✓ | ✓ |
| Multiple Tickers | - | ✓ | ✓ |
| Caching | ✓* | - | - |
| Error Recovery | - | - | ✓ |
| Export (PDF/HTML) | ✓ | ✓ | ✓ |
| Live Rendering | ✓ | ✓ | ✓ |
| No Stdout Prints | ✓ | ✓ | ✓ |
| Confidence Scoring | ✓ | ✓ | ✓ |
| Demo Key Warning | ✓ | ✓ | ✓ |
| Report Persistence | ✓ | ✓ | ✓ |

*2nd run of Query 1

---

## Validation Checklist

- [ ] Interactive mode launches without errors
- [ ] No green horizontal line artifacts appear
- [ ] Queries complete with synthesis text
- [ ] PDF export works correctly
- [ ] HTML export works correctly
- [ ] Type `exit` cleanly exits
- [ ] Version command shows v1.1.1
- [ ] All logger output goes to Live panel, not stdout
- [ ] Confidence scores display correctly
- [ ] Multi-ticker queries show both results
- [ ] Cached queries retrieve instantly

---

## Notes

- If using demo API key: Yellow warning appears about "IBM dummy data"
- Real API key: No warning, real financial data returned
- Cache clears between CLI invocations (not within interactive session)
- First query takes ~5-10s, subsequent queries ~3-5s

