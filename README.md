# Jasper Finance

> **The terminal-native autonomous financial research agent.**  
> Deterministic planning. Tool-grounded data. Validation gating. Human-trustworthy answers.

[![PyPI](https://img.shields.io/pypi/v/jasper-finance.svg)](https://pypi.org/project/jasper-finance/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/ApexYash11/jasper.svg)](https://github.com/ApexYash11/jasper)

---

##  Why Jasper?

Financial AI is often unreliable. Most tools produce confident-sounding answers that are frequently backed by hallucinations or missing data. **Jasper takes a different approach: it treats every question as a mission.**

Instead of just "chatting," Jasper follows a rigorous 4-stage pipeline:
1.  **Plan**  Decomposes your question into structured research tasks.
2.  **Execute**  Fetches real-time data from authoritative APIs (Alpha Vantage, yfinance).
3.  **Validate**  Analyzes data completeness and financial logic.
4.  **Synthesize**  Generates a report **only if validation passes**.

**If validation fails, Jasper stops. No hallucinations. Confidence = 0.**

---

##  Key Features

-  **Autonomous Planning**: Automatically breaks down complex questions (e.g., "Compare Apple and Microsoft's R&D spend vs Revenue") into executable sub-tasks.
-  **Tool-Grounded Data**: Direct integration with [Alpha Vantage](https://www.alphavantage.co/) and [yfinance](https://github.com/ranaroussi/yfinance).
-  **Validation Gate**: A "Mission Control" that blocks synthesis if data is missing or inconsistent.
-  **Confidence Scoring**: Transparent breakdown of data coverage, data quality, and inference strength.
-  **Interactive REPL**: A professional CLI environment for iterative research.
-  **Rich Terminal UI**: Live progress boards, tree views, and structured reports.

---

##  Installation

### Using pip
`ash
pip install jasper-finance
`

### Using uv (Recommended for speed)
`ash
uv pip install jasper-finance
`

---

##  Quick Start & Setup

### 1. Get Your API Keys
To use Jasper, you need two keys:
- **OpenRouter API Key**: Used for LLM-based planning and synthesis. [Get it here](https://openrouter.ai/keys).
- **Alpha Vantage API Key**: Used for core financial statements. [Get it here (Free)](https://www.alphavantage.co/support/#api-key).

### 2. Set Environment Variables
Create a .env file or export them in your terminal:
`ash
export OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxxx"
export ALPHA_VANTAGE_API_KEY="your-key"
`

### 3. Run Your First Mission
`ash
jasper ask "What is Nvidia's revenue trend over the last 3 years?"
`

### 4. Enter Interactive Mode
For a deeper dive, use the REPL:
`ash
jasper interactive
`

---

##  Architecture: How It Works

Jasper uses a modular multi-agent system designed for transparency.

`mermaid
flowchart LR
    Q["Query"] --> P["Planner Agent"]
    P --> E["Execution Engine"]
    E --> V["Validation Gate"]
    
    V -->|Success| S["Synthesizer Agent"]
    V -->|Failure| F["Stop (Confidence=0)"]
    
    S --> R["Final Report"]
    
    subgraph Data Providers
        AV["Alpha Vantage"]
        YF["yfinance"]
    end
    
    E --> AV
    E --> YF
`

- **Planner**: Uses nthropic/claude-3-sonnet (or your configured model) to create a task list.
- **Executor**: Processes tasks sequentially, routing to the appropriate data provider.
- **Validator**: Verifies that the data returned actually answers the original intent.
- **Synthesizer**: Finalizes the report with professional financial tone.

---

##  Commands Reference

| Command | Description |
|---------|-------------|
| jasper ask "<query>" | Execute a single research mission and print the report. |
| jasper interactive | Start an interactive session for multiple queries. |
| jasper doctor | Diagnose your environment and API key configuration. |
| jasper version | Display the current installed version (v1.0.0). |
| jasper --help | View all available options and flags. |

---

##  Troubleshooting

- **"Research Failed"**: This is **intentional**. It means Jasper couldn't find enough valid data to answer you safely. Check the "Validation Issues" section in the output.
- **API Rate Limits**: If using a free Alpha Vantage key, you may hit rate limits. Use jasper doctor to verify your key.
- **Ticker Symbols**: Ensure you use the correct ticker (e.g., AAPL for Apple). For non-US stocks, use suffixes like .BSE or .NS.
- **OpenRouter Balance**: Ensure your OpenRouter account has credits or a valid credit card attached.

---

##  License & Usage

Jasper Finance is released under the **MIT License**.

### MIT License Details
- **Commercial Use**: Permitted
- **Modification**: Permitted
- **Distribution**: Permitted
- **Private Use**: Permitted
- **Liability/Warranty**: None (The software is provided "as is")

See the [LICENSE](LICENSE) file for the full legal text.

---

##  Important Links

-  **Source Code**: [GitHub Repository](https://github.com/ApexYash11/jasper)
-  **Issue Tracker**: [Report a Bug](https://github.com/ApexYash11/jasper/issues)
-  **PyPI**: [Download Package](https://pypi.org/project/jasper-finance/)
-  **Data Provider**: [Alpha Vantage](https://www.alphavantage.co/)
-  **LLM Gateway**: [OpenRouter](https://openrouter.ai/)

---

**Built by analysts, for analysts. Use Jasper to stop guessing and start researching.**
