# Jasper Finance

> **The terminal-native autonomous financial research agent.**  
> Deterministic planning. Tool-grounded data. Validation gating. Human-trustworthy answers.

[![PyPI](https://img.shields.io/pypi/v/jasper-finance.svg)](https://pypi.org/project/jasper-finance/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/ApexYash11/jasper.svg)](https://github.com/ApexYash11/jasper)

---

## 🎯 Why Jasper?

Financial AI is often unreliable. Most tools produce confident-sounding answers that are frequently backed by hallucinations or missing data. **Jasper takes a different approach: it treats every question as a mission.**

Instead of just "chatting," Jasper follows a rigorous 4-stage pipeline:
1. **Plan** → Decomposes your question into structured research tasks.
2. **Execute** → Fetches real-time data from authoritative APIs (Alpha Vantage, yfinance).
3. **Validate** → Analyzes data completeness and financial logic.
4. **Synthesize** → Generates a report **only if validation passes**.

**If validation fails, Jasper stops. No hallucinations. Confidence = 0.**

---

## ✨ Key Features

- 🧠 **Autonomous Planning**: Automatically breaks down complex questions (e.g., "Compare Apple and Microsoft's R&D spend vs Revenue") into executable sub-tasks.
- ⚙️ **Tool-Grounded Data**: Direct integration with [Alpha Vantage](https://www.alphavantage.co/) and [yfinance](https://github.com/ranaroussi/yfinance).
- ✅ **Validation Gate**: A "Mission Control" that blocks synthesis if data is missing or inconsistent.
- 📊 **Confidence Scoring**: Transparent breakdown of data coverage, data quality, and inference strength.
- 💬 **Interactive REPL**: A professional CLI environment for iterative research.
- 🎨 **Rich Terminal UI**: Live progress boards, tree views, and structured reports.
- 📄 **PDF Export**: Generate professional financial research reports and export as PDFs.

---

## 🚀 Installation

### Using pip
```bash
pip install jasper-finance
```

### From Source (Development)
```bash
git clone https://github.com/ApexYash11/jasper.git
cd jasper
pip install -e .
```

---

## 🛠️ Setup (2 Minutes)

### Step 1: Get API Keys
You need **two free API keys**:

| API | Purpose | Get Key |
|-----|---------|---------|
| **OpenRouter** | LLM synthesis & planning | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Alpha Vantage** | Financial data (statements) | [alphavantage.co/support](https://www.alphavantage.co/support/#api-key) *(free)* |

### Step 2: Configure Environment
Create a `.env` file in your working directory:

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
```

**Or** export in your terminal:
```bash
# macOS/Linux
export OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxxx"
export ALPHA_VANTAGE_API_KEY="your-key"

# Windows PowerShell
$env:OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxxx"
$env:ALPHA_VANTAGE_API_KEY="your-key"
```

### Step 3: Verify Setup
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

Output:
```
MISSION CONTROL
[PLANNING] Breaking down your question...
[EXECUTING] Fetching financial data...
[VALIDATING] Checking data integrity...
[SYNTHESIZING] Generating report...

INTELLIGENCE MEMO
Nvidia Revenue Analysis 2022-2024
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Report content...]
```

### Interactive Mode (Multiple Queries)
```bash
jasper interactive
```

You'll see:
```
Interactive Mode. Type 'exit' to quit.

? Enter Financial Query: Analyze Tesla's operating margins.
[Jasper processes your query...]

? Enter Financial Query: Compare Ford vs GM revenue growth.
[Next query...]
```

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
        │  Breaks down question   │
        │  into research tasks    │
        └────────────┬────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ 2️⃣ EXECUTION ENGINE    │
        │  Fetches real data      │
        │  - Alpha Vantage        │
        │  - yfinance             │
        └────────────┬────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ 3️⃣ VALIDATION GATE     │
        │  Checks data quality    │
        │  & completeness         │
        └────┬───────────┬────────┘
             │           │
          ✅ PASS    ❌ FAIL
             │           │
             ▼           ▼
      ┌─────────────┐  Research Failed
      │ 4️⃣ SYNTHESIZE│  (Confidence = 0)
      │   Report    │
      └──────┬──────┘
             │
             ▼
    ┌─────────────────────┐
    │   FINAL REPORT      │
    │  + Confidence Score │
    └─────────────────────┘
```

**Key Agents:**
- **Planner**: Decomposes questions → creates task list
- **Executor**: Runs tasks → fetches from APIs
- **Validator**: Verifies completeness → blocks bad synthesis
- **Synthesizer**: Writes professional report

---

## 💡 Real Examples

### Example 1: Single Query
```bash
$ jasper ask "What is Apple's revenue trend over the last 3 years?"

MISSION CONTROL
[EXECUTING] Fetching live market data...
└── RESEARCH PLAN
    ├── ✔ Fetch income statement for AAPL
    ├── ✔ Calculate YoY growth percentages
    └── ✔ Validate data consistency

INTELLIGENCE MEMO
Apple Inc. Revenue Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━
- 2022: $394.3B
- 2023: $383.3B (-2.8%)
- 2024: $391.0B (+1.9%)

Overall Confidence: 95%
Data Coverage: 100%
```

### Example 2: Failed Research (By Design)
```bash
$ jasper ask "What is the revenue of a private company with no SEC filings?"

MISSION CONTROL
[VALIDATING] Verifying data integrity...

Research Failed

Validation Issues:
  - No financial data available for private companies
  - SEC filings required (Alpha Vantage provides only public data)

Overall Confidence: 0%
```
This is **intentional**. No hallucinations.

---

## 🔧 All Commands

| Command | What It Does |
|---------|------------|
| `jasper ask "question"` | Execute a single research mission |
| `jasper interactive` | Enter multi-query mode |
| `jasper export <query>` | Generate research and export as PDF report |
| `jasper doctor` | Verify API keys and setup |
| `jasper version` | Show installed version |
| `jasper --help` | View all commands |

---

## ❓ Troubleshooting

**Problem**: `"Research Failed"`  
**Solution**: This is by design. Check the validation issues output. Usually means data is incomplete or ticker doesn't exist.

**Problem**: `API Rate Limit Hit`  
**Solution**: Using free Alpha Vantage key? Limit is ~5 calls/min. Wait a moment or upgrade your key.

**Problem**: `OPENROUTER_API_KEY not set`  
**Solution**: 
```bash
echo $OPENROUTER_API_KEY  # Check if set
export OPENROUTER_API_KEY="sk-or-v1-xxxxx"  # Set it
jasper doctor  # Verify
```

**Problem**: `Ticker not found`  
**Solution**: Verify the ticker symbol is correct (AAPL, not APPLE). For international stocks, use `.NS` or `.BSE` suffix.

---

## ⚖️ License

Jasper Finance is released under the **MIT License** (2026, ApexYash).

### What MIT Means
- ✅ **Commercial Use**: Yes, you can use this commercially.
- ✅ **Modification**: Yes, you can modify the code.
- ✅ **Distribution**: Yes, you can redistribute.
- ✅ **Private Use**: Yes, use for private projects.
- ⚠️ **Warranty**: None. No liability for damages.

See [LICENSE](LICENSE) for full legal text.

---

## 🔗 Links

| What | Link |
|------|------|
| 📦 **PyPI Package** | [pypi.org/project/jasper-finance/](https://pypi.org/project/jasper-finance/) |
| 💻 **GitHub Source** | [github.com/ApexYash11/jasper](https://github.com/ApexYash11/jasper) |
| 🐛 **Report Issues** | [github.com/ApexYash11/jasper/issues](https://github.com/ApexYash11/jasper/issues) |
| 📊 **Data: Alpha Vantage** | [alphavantage.co](https://www.alphavantage.co/) |
| 📈 **Data: yfinance** | [github.com/ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) |
| 🤖 **LLM: OpenRouter** | [openrouter.ai](https://openrouter.ai/) |

---

**Built by analysts, for analysts. Stop guessing. Start researching. Jasper Finance v1.0.0**
