# Jasper Finance

> **The terminal-native autonomous financial research agent.**  
> Deterministic planning. Tool-grounded data. Validation gating. Human-trustworthy answers.

[![PyPI](https://img.shields.io/pypi/v/jasper-finance.svg)](https://pypi.org/project/jasper-finance/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/ApexYash11/jasper.svg)](https://github.com/ApexYash11/jasper)

---

![Hero Img](https://github.com/CyberBoyAyush/jasper/blob/main/assests/Screenshot%202026-01-10%20125137.png)

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

* 🧠 **Autonomous Planning**: Automatically breaks down complex questions (e.g., "Compare Apple and Microsoft's R&D spend vs Revenue") into executable sub-tasks.
* ⚙️ **Tool-Grounded Data**: Direct integration with [Alpha Vantage](https://www.alphavantage.co/) and [yfinance](https://github.com/ranaroussi/yfinance).
* ✅ **Validation Gate**: A "Mission Control" that blocks synthesis if data is missing or inconsistent.
* 📊 **Confidence Scoring**: Transparent breakdown of data coverage, data quality, and inference strength.
* 💬 **Interactive REPL**: A professional CLI environment for iterative research.
* 🎨 **Rich Terminal UI**: Live progress boards, tree views, and structured reports.
* 📄 **PDF Export**: Generate professional financial research reports and export as PDFs.

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
docker build -t jasper-finance:1.0.5 .
docker run -it jasper-finance:1.0.5 interactive
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

### Interactive Mode (Multiple Queries)

```bash
jasper interactive
```

### Export to PDF

```bash
jasper export "Analyze Tesla's operating margins"
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

---

## 🔧 All Commands

| Command | What It Does |
| --- | --- |
| `jasper ask "question"` | Execute a single research mission |
| `jasper interactive` | Enter multi-query mode |
| `jasper export <query>` | Generate research and export as PDF report |
| `jasper doctor` | Verify API keys and setup |
| `jasper version` | Show installed version |
| `jasper --help` | View all commands |

---

## ❓ Troubleshooting

| Problem | Solution |
| --- | --- |
| `Research Failed` | By design. Check validation issues. Usually means incomplete data or invalid ticker. |
| `API Rate Limit Hit` | Free Alpha Vantage: ~5 calls/min. Wait or upgrade key. |
| `API KEY not set` | Run `jasper doctor` and export missing keys. |
| `Ticker not found` | Use symbol (AAPL), not name (Apple). International: add suffix (.NS, .BSE). |
| `pycairo build fails` | Install Cairo: `brew install cairo` (macOS) or `sudo apt install libcairo2-dev` (Linux). |

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

**Built by analysts, for analysts. Stop guessing. Start researching. Jasper Finance v1.0.5**
