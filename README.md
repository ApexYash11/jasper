# Jasper 🤖

Jasper is an autonomous research agent focused on structured, reproducible financial research workflows. It uses task planning, modular agents, and pluggable data providers to perform stepwise analysis from raw data to concise conclusions.

![screenshot](assets/screenshot.png)

## Overview

Jasper turns complex financial questions into clear research plans, executes those plans using available tools and data providers, validates results, and synthesizes final answers for users via a CLI.

**Key Capabilities:**
- **Task Planning:** Decomposes questions into sequenced research tasks.
- **Autonomous Execution:** Orchestrates agents and tools to fetch and compute financial data.
- **Self-Validation:** Re-checks results and re-runs steps when needed.
- **Provider Integration:** Includes provider adapters (e.g., Alpha Vantage) for financial statements and time-series.
- **CLI-first UX:** Lightweight terminal interface for interactive sessions and development.

## Quickstart

### Prerequisites
- Python 3.10 or newer
- An OpenAI-compatible API key (if using LLM features)

Create and activate a virtual environment, then install the package in editable mode:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -e .
```

### Run the CLI

Start the interactive CLI:

```bash
python -m jasper
```

Or run the main module directly: see [jasper/cli/main.py](jasper/cli/main.py)

### Example Prompts
- "Compare revenue growth for AAPL vs MSFT over the last 4 quarters"
- "Summarize Tesla's cash flow trends and material risks"
- "Compute debt-to-equity for Amazon using latest financials"

## Architecture

Jasper uses a modular, agent-based structure:
- **Planner** — Converts user questions into ordered tasks. See [jasper/agent/planner.py](jasper/agent/planner.py)
- **Executor** — Runs tasks against tools and providers. See [jasper/agent/executor.py](jasper/agent/executor.py)
- **Validator** — Verifies outputs and requests re-runs when needed. See [jasper/agent/validator.py](jasper/agent/validator.py)
- **Providers** — Adapters for data sources in [jasper/tools/providers](jasper/tools/providers)

## Tech Stack
- **Language:** Python
- **Package:** pyproject.toml (PEP 621 / Poetry-style metadata)
- **LLM:** Pluggable LLM integrations (configurable in `jasper/core/llm.py`)
- **Data Providers:** Alpha Vantage adapter included under `jasper/tools/providers`

## Contributing
1. Fork the repo
2. Create a feature branch
3. Run tests and linters
4. Open a pull request with a clear description

Please keep PRs small and focused.

## License
This project is provided under the MIT License.
