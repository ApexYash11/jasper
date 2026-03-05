# Jasper Finance

> **The terminal-native autonomous financial research agent.**  
> Deterministic planning. Tool-grounded data. Reflection-driven recovery. Human-trustworthy answers.

[![PyPI](https://img.shields.io/pypi/v/jasper-finance.svg)](https://pypi.org/project/jasper-finance/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/ApexYash11/jasper.svg)](https://github.com/ApexYash11/jasper)

---

![Hero Img](https://github.com/CyberBoyAyush/jasper/blob/main/assests/Screenshot%202026-01-10%20125137.png)

## 🎯 Why Jasper?

Financial AI is often unreliable. Most tools produce confident-sounding answers that are frequently backed by hallucinations or missing data. **Jasper takes a different approach: it treats every question as a mission.**

Instead of just "chatting," Jasper follows a rigorous 5-stage pipeline:

1. **Plan** → Decomposes your question into structured research tasks with intent classification.
2. **Execute** → Fetches real-time data from authoritative APIs (Alpha Vantage, yfinance).
3. **Reflect** → Retries transient failures, degrades gracefully on permanent ones.
4. **Validate** → Analyzes data completeness and financial logic with partial-success support.
5. **Synthesize** → Generates a report with a confidence score and full audit trail.

**Partial data? Jasper continues with caveats and a penalised confidence score — no silent hallucinations.**

---

## 📝 What's New in v1.1.3

### 🐛 Bug Fixes & Stability

- **Exception Hierarchy**: Introduced a cohesive exception model with `JasperError` base class for all custom exceptions (EntityExtractionError, PlannerError, DataFetchError, ValidationError, ConfigurationError, SynthesisError). Enables precise error handling and recovery strategies.
- **Logger Output Control**: Fixed logger to never print to stdout. All session events are now captured cleanly without terminal pollution. RichLogger correctly updates the Live panel instead.
- **Version Command**: Now uses `importlib.metadata` instead of parsing `pyproject.toml` directly. Guarantees version consistency across all deployment methods (pip, Docker, executables).

### ✨ New Features & Enhancements

- **Balance Sheet Data**: New `balance_sheet` tool now dispatched by executor. Fetch total assets, liabilities, equity, debt ratios alongside income statements for complete financial picture.
- **Cash Flow Statements**: New `cash_flow` tool provides operating, investing, and financing cash flows. Critical for understanding liquidity and capital allocation.
- **Real-time Quotes**: New `realtime_quote` tool fetches live price, market cap, P/E ratio, 52-week range, and trading volume. Always bypasses cache for latest data.
- **Async Provider Execution**: Both `YFinanceClient` and `AlphaVantageClient` now properly use `asyncio.run_in_executor()` to prevent blocking the event loop. Non-blocking concurrent data fetches.
- **Smart Fallback Routing**: `FinancialDataRouter` tries Alpha Vantage first, then seamlessly falls back to yfinance. Automatic `.NS` suffix retry for Indian stocks (e.g., plain `RELIANCE` → `RELIANCE.NS`).
- **In-Memory Response Caching**: API responses cached in-memory with TTL (default 15 minutes, configurable via `JASPER_CACHE_TTL_SECS`). Saves quota on repeated queries. Real-time quotes always bypass cache.

### 🎯 Reliability & Recovery

- **Reflector Retry Loop**: Post-execution reflector now intelligently retries transient failures (timeouts, rate limits, service unavailable) up to configurable `max_retries` times per task before gracefully skipping.
- **Partial-Success Validation**: Validation gate now explicitly accepts ≥50% task completion rate. Synthesis proceeds with a confidence penalty and visible data-gap caveats. No more hard failures on partial data.
- **Validator Confidence Breakdown**: Calculates transparency score as: `data_coverage × data_quality × inference_strength`. Penalises missing data automatically.
- **Task Error Tracking**: All task failures now logged with detailed error messages. Audit trail clearly shows which data sources succeeded/failed.

### 🎨 UI & Export Improvements

- **Conditional PDF Status Badges**: PDF report now uses Jinja2 conditionals to dynamically render status badges based on actual data retrieval results. No more hardcoded "SUCCESS" labels when data is missing.
- **PDF Context Truncation**: Long synthesis contexts (>10K chars) automatically truncated with a truncation note appended. Prevents LLM context overflow and keeps reports concise.
- **Cross-Process Report Persistence**: Research reports now automatically persisted to disk as JSON cache. `_load_report_from_disk()` enables session continuity and easy re-export.
- **Live Streaming Synthesis**: Real-time Rich Live panel updates during synthesis. No blank screens while LLM generates responses.

### 🐍 Developer Experience

- **Public Python API**: New `run_research()` async function and `FinalReport` Pydantic model exported from `jasper` package. Use Jasper programmatically in notebooks, FastAPI routes, or CI pipelines.
- **Detailed Docstrings**: All agent classes (Planner, Executor, Reflector, Synthesizer, Validator) now have comprehensive docstrings explaining intent, parameters, and return values.
- **Demo Mode Warning**: When using demo Alpha Vantage key, explicit warning message mentions "IBM" to alert users that demo responses are dummy data, not real market information.

### 🔧 Internal Improvements

- **Entity Extractor**: Improved ticker/company name extraction from complex queries. Better handling of multi-company comparisons.
- **Context Window Management**: Synthesizer now actively manages context window size to avoid exceeding LLM limits. Graceful truncation with notes.
- **Executor Task Dispatching**: Unified task dispatch logic. Supports income_statement, balance_sheet, cash_flow, realtime_quote, financial_statement (alias), and key_metrics tools.

### 📊 Data Provider Enhancements

- **Alpha Vantage**: Now properly parses and surfaces both annual and quarterly reports. Better error messages for rate-limited responses and missing data.
- **yfinance**: Eliminated use of deprecated `quarterly_financials` attribute. Uses modern `quarterly_income_stmt` API exclusively.
- **Provider Abstraction**: Providers without requested method (e.g., missing balance_sheet) silently skipped instead of erroring out.

### 🧪 Testing

- 16 new comprehensive test suites covering all critical fixes.
- Full round-trip testing for report save/load persistence.
- Async provider mocking with proper executor simulation.
- Conditional template rendering validation via CSS class detection.

---

## ✨ Key Features

* 🧠 **Autonomous Planning**: Automatically breaks down complex questions into executable sub-tasks with query-intent classification (`quantitative` / `qualitative` / `mixed`).
* ⚙️ **Tool-Grounded Data**: Income statements, balance sheets, cash flow, and real-time quotes via [Alpha Vantage](https://www.alphavantage.co/) and [yfinance](https://github.com/ranaroussi/yfinance). Supports US and Indian (NSE `.NS`) stocks.
* 🔄 **Reflector Agent**: Post-execution recovery loop that retries transient network/rate-limit failures up to `max_retries` times per task before gracefully skipping.
* ✅ **Partial-Success Validation**: If ≥ 50 % of tasks complete, synthesis proceeds with a confidence penalty and a visible data-gap caveat instead of hard-failing.
* 📊 **Confidence Breakdown**: Transparent `data_coverage × data_quality × inference_strength` scoring per report.
* ⚡ **LLM Streaming**: Synthesis tokens stream to the terminal in real-time via a Rich `Live` panel — no more blank screens.
* 💬 **Session Memory**: Interactive mode carries the last 3 Q&A pairs as context so follow-up questions work naturally.
* 🌐 **Qualitative Queries**: Questions without a ticker (e.g. "Explain yield curve inversion") are answered directly from LLM domain knowledge.
* 🗄️ **TTL Response Cache**: API responses are cached in-memory for 15 minutes (configurable via `JASPER_CACHE_TTL_SECS`) to save Alpha Vantage quota. Real-time quotes always bypass the cache.
* 🐍 **Public Python API**: Use Jasper programmatically in notebooks, web APIs, or CI pipelines via `from jasper import run_research`.
* 📄 **PDF & HTML Export**: Professional research reports with timestamped unique filenames and persistent JSON cache across sessions.
* 🎨 **Rich Terminal UI**: Live progress boards, tree views, and structured reports.

---

## 🚀 Installation

### Option 1: Python pip (All Platforms)

```bash
pip install jasper-finance
jasper interactive
```

### Option 2: Pre-Built Executable

**No Python needed. Everything bundled including PDF renderer.**

**Windows:**
```bash
git clone https://github.com/ApexYash11/jasper.git
cd jasper
.\scripts\build.ps1
.\dist\jasper\jasper.exe interactive
```

**Linux/macOS:**
```bash
git clone https://github.com/ApexYash11/jasper.git
cd jasper
chmod +x scripts/build.sh && ./scripts/build.sh
./dist/jasper/jasper interactive
```

### Option 3: Docker (Production)

```bash
docker build -t jasper-finance:1.1.3 .
docker run -it jasper-finance:1.1.3 interactive
```

---

## 🖥️ Platform-Specific Setup with Conda

Using Conda ensures isolated environments and avoids dependency conflicts.

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install system dependencies
brew install miniforge pkg-config cairo

# Initialize Conda
conda init zsh
source ~/.zshrc

# Create and activate environment
conda create -n jasper python=3.11 -y
conda activate jasper

# Install Jasper
pip install jasper-finance
```

### Linux (Ubuntu/Debian)

```bash
# Install system dependencies
sudo apt update
sudo apt install -y pkg-config libcairo2-dev

# Install Miniforge
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b
~/miniforge3/bin/conda init bash
source ~/.bashrc

# Create and activate environment
conda create -n jasper python=3.11 -y
conda activate jasper

# Install Jasper
pip install jasper-finance
```

### Windows

```powershell
# Install Miniforge from: https://github.com/conda-forge/miniforge/releases
# Run the installer, then open Miniforge Prompt

# Create and activate environment
conda create -n jasper python=3.11 -y
conda activate jasper

# Install Jasper
pip install jasper-finance
```

### Daily Usage (All Platforms)

```bash
# Activate environment
conda activate jasper

# Run Jasper
jasper interactive

# Deactivate when done
conda deactivate
```

---

## 🛠️ Setup (2 Minutes)

### Step 1: Get API Keys

You need **two free API keys**:

| API | Purpose | Get Key |
| --- | --- | --- |
| **OpenRouter** | LLM synthesis & planning | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Alpha Vantage** | Financial data (statements) | [alphavantage.co/support](https://www.alphavantage.co/support/#api-key) *(free)* |

### Step 2: Configure Environment

**macOS/Linux:**
```bash
export OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxxx"
export ALPHA_VANTAGE_API_KEY="your-alpha-vantage-key"
```

To make permanent, add to `~/.zshrc` (macOS) or `~/.bashrc` (Linux).

**Windows PowerShell:**
```powershell
$env:OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxxx"
$env:ALPHA_VANTAGE_API_KEY="your-key"
```

**Or use a `.env` file** in your working directory:
```
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
```

### Step 3: (Optional) Choose a Model

Jasper defaults to `stepfun/step-3.5-flash:free` via OpenRouter. Override with:
```bash
export OPENROUTER_MODEL="openai/gpt-4o-mini"   # recommended for production
export OPENROUTER_MODEL="anthropic/claude-haiku-20240307"
```

### Step 4: Verify Setup

```bash
jasper doctor
```

Expected output:
```
✅ OPENROUTER_API_KEY is set
✅ ALPHA_VANTAGE_API_KEY is set
✅ Python 3.9+ installed
✅ All dependencies available
```

---

## 📖 Quick Start

### Single Query (One-off Research)

```bash
jasper ask "What is Nvidia's revenue trend over the last 3 years?"
```

### Interactive Mode (Multiple Queries with Session Memory)

```bash
jasper interactive
```

Session memory is automatic — follow-up questions like *"and what about their cash flow?"* retain context from the previous 3 exchanges.

### Qualitative / Macro Queries (No Ticker Required)

```bash
jasper ask "Explain yield curve inversion and its impact on equities"
jasper ask "What is quantitative tightening?"
```

### Indian & International Stocks

```bash
jasper ask "What is Reliance Industries revenue trend?"   # auto-resolves RELIANCE.NS
jasper ask "Analyze Infosys operating margins"            # INFY.NS
jasper ask "Compare HDFC Bank and ICICI Bank"             # HDFCBANK.NS, ICICIBANK.NS
```

### Export to PDF

```bash
jasper export "Analyze Tesla's operating margins"
# Saves as: exports/jasper_report_20260222_143012.pdf  (unique per run)
```

---

## 🐍 Python API

Use Jasper programmatically in notebooks, FastAPI routes, or CI pipelines:

```python
import asyncio
from jasper import run_research, FinalReport

report: FinalReport | None = asyncio.run(
    run_research("What is Apple's revenue trend over the last 3 years?")
)

if report:
    print(report.synthesis_text)
    print(f"Confidence: {report.confidence_score:.0%}")
    print(f"Tickers analysed: {report.tickers}")
    print(f"Data sources: {report.data_sources}")
```

`run_research()` returns a fully populated `FinalReport` Pydantic model or `None` if the pipeline failed.

---

## 🏗️ How It Works (Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR QUESTION                         │
│          "What is Apple's revenue trend?"                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   1️⃣ PLANNER AGENT     │
        │ Intent classification   │
        │ (quant / qual / mixed)  │
        │ Task decomposition      │
        └────────────┬────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ 2️⃣ EXECUTION ENGINE    │
        │  Income statement       │
        │  Balance sheet          │
        │  Cash flow              │
        │  Real-time quote        │
        │  (Alpha Vantage + yf)   │
        └────────────┬────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   3️⃣ REFLECTOR         │
        │ Retry transient errors  │
        │ Degrade on permanent    │
        │  ones gracefully        │
        └────────────┬────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ 4️⃣ VALIDATION GATE     │
        │ ≥50% tasks → partial ✅ │
        │ <50% tasks → fail ❌    │
        │ Confidence breakdown    │
        └────┬───────────┬────────┘
             │           │
          ✅ PASS    ❌ FAIL
             │           │
             ▼           ▼
      ┌─────────────┐  Research Failed
      │ 5️⃣ SYNTHESIZE│  (partial data
      │  (streaming) │   reported)
      └──────┬──────┘
             │
             ▼
    ┌─────────────────────┐
    │   FINAL REPORT      │
    │  + Confidence Score │
    │  + Audit Trail      │
    └─────────────────────┘
```

---

## 🔧 All Commands

| Command | What It Does |
| --- | --- |
| `jasper ask "question"` | Execute a single research mission |
| `jasper interactive` | Enter multi-query mode with session memory |
| `jasper export <query>` | Generate research and export as PDF report |
| `jasper doctor` | Verify API keys and setup |
| `jasper version` | Show installed version |
| `jasper --help` | View all commands |

---

## 📊 Available Data Tools

| Tool | Description | Providers |
| --- | --- | --- |
| `income_statement` | Annual + quarterly P&L (revenue, EBIT, net income) | Alpha Vantage, yfinance |
| `balance_sheet` | Assets, liabilities, equity, debt ratios | Alpha Vantage, yfinance |
| `cash_flow` | Operating / investing / financing cash flows | Alpha Vantage, yfinance |
| `realtime_quote` | Live price, market cap, P/E, 52-week range, volume | yfinance (always fresh) |
| `key_metrics` | EV/EBITDA, ROE, ROA, margins, growth rates | yfinance |

> Alpha Vantage is tried first; yfinance is the automatic fallback. Both providers support US and Indian NSE stocks (`.NS` suffix).

---

## ⚙️ Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | *(required)* | Your OpenRouter API key |
| `ALPHA_VANTAGE_API_KEY` | `demo` | Alpha Vantage key (demo = IBM only) |
| `OPENROUTER_MODEL` | `google/gemini-2.0-flash-exp:free` | LLM model override |
| `JASPER_CACHE_TTL_SECS` | `900` | API response cache TTL in seconds |

---

## ❓ Troubleshooting

| Problem | Solution |
| --- | --- |
| `Research Failed` | By design. Check validation issues. Usually incomplete data or invalid ticker. |
| `Partial data — confidence penalised` | Normal for rate-limited sessions. Report still generated with caveats. |
| `API Rate Limit Hit` | Free Alpha Vantage: ~25 calls/day. Jasper's TTL cache reduces redundant calls. |
| `API KEY not set` | Run `jasper doctor` and export missing keys. |
| `Ticker not found` | Use symbol (AAPL), not name (Apple). Indian: add `.NS` suffix (RELIANCE.NS). |
| `pycairo build fails` | Install Cairo: `brew install cairo` (macOS) or `sudo apt install libcairo2-dev` (Linux). |
| `nan in report output` | Fixed in v1.0.9 — upgrade with `pip install --upgrade jasper-finance`. |

---

## ⚖️ License

Jasper Finance is released under the **MIT License** (2026, ApexYash).

* ✅ Commercial Use
* ✅ Modification
* ✅ Distribution
* ✅ Private Use
* ⚠️ No Warranty

See [LICENSE](LICENSE) for full legal text.

---

## 🔗 Links

| Resource | Link |
| --- | --- |
| 📦 PyPI Package | [pypi.org/project/jasper-finance/](https://pypi.org/project/jasper-finance/) |
| 💻 GitHub Source | [github.com/ApexYash11/jasper](https://github.com/ApexYash11/jasper) |
| 🐛 Report Issues | [github.com/ApexYash11/jasper/issues](https://github.com/ApexYash11/jasper/issues) |
| 📊 Data: Alpha Vantage | [alphavantage.co](https://www.alphavantage.co/) |
| 📈 Data: yfinance | [github.com/ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) |
| 🤖 LLM: OpenRouter | [openrouter.ai](https://openrouter.ai/) |

---

**Built by analysts, for analysts. Stop guessing. Start researching. Jasper Finance v1.1.3**
