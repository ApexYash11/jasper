# Jasper Finance

Autonomous financial research agent for analysts who demand transparency.

**Deterministic workflow:** Planning → Execution → Validation → Synthesis. Fetches real financial data (Alpha Vantage, yfinance). Blocks answers when validation fails. No hallucinations.

## Features

- **Task Planning** — Decomposes questions into research tasks
- **Tool-Grounded Data** — Fetches from real financial APIs
- **Validation Gate** — Blocks synthesis if data is missing/incomplete
- **Confidence Scoring** — Reports data coverage, quality, inference strength
- **Interactive REPL** — Iterative research with full validation on each query
- **Professional CLI** — Progress board + final report with metrics

## Install

```bash
pip install jasper-finance
```

## Usage

Single query:
```bash
jasper ask "What is Apple's revenue trend?"
```

Interactive mode:
```bash
jasper interactive
```

Setup:
```bash
export OPENROUTER_API_KEY="your-key"
export ALPHA_VANTAGE_API_KEY="your-key"  # optional
jasper doctor  # validate setup
```

## Principles

✓ Tool-grounded answers (no invention)  
✓ Validation blocks synthesis (fail-safe)  
✓ Deterministic LLM (temperature = 0)  
✓ Human review always required  
✗ No investment advice  
✗ No trading API integration

**GitHub:** https://github.com/ApexYash11/jasper

**License:** MIT

