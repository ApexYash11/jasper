from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from ..core.state import Jasperstate
from ..observability.logger import SessionLogger

# Safe context window: truncate raw data to ~12 000 chars so it fits within
# small free-tier context windows (4K–8K tokens) while preserving structure.
_MAX_CONTEXT_CHARS = 12_000


class Synthesizer:
    def __init__(self, llm: Any, logger: SessionLogger | None = None):
        self.llm = llm
        self.logger = logger or SessionLogger()

    @staticmethod
    def _truncate_context(data_context: str, max_chars: int = _MAX_CONTEXT_CHARS) -> str:
        """
        Trim the data_context string to max_chars characters.
        Tries to cut at a natural boundary (double newline) and appends a note.
        """
        if len(data_context) <= max_chars:
            return data_context
        cut = data_context[:max_chars].rfind("\n\n")
        if cut == -1:
            cut = max_chars
        return data_context[:cut] + "\n\n[... data truncated for context window ...]\n"

    async def synthesize(self, state: Jasperstate) -> str:
        self.logger.log("SYNTHESIS_STARTED", {"plan_length": len(state.plan)})

        if not state.validation or not state.validation.is_valid:
            raise ValueError("Cannot synthesize without passing validation")

        # Build data context from task results
        data_context = ""
        for task_id, result in state.task_results.items():
            task = next((t for t in state.plan if t.id == task_id), None)
            if not task:
                self.logger.log("SYNTHESIZER_ORPHANED_RESULT", {"task_id": task_id})
                desc = "Unknown Task (orphaned result)"
            else:
                desc = task.description
            data_context += f"Task: {desc}\nData: {result}\n\n"

        # Guard against overflowing small context windows
        data_context = self._truncate_context(data_context)

        # Detect multi-ticker comparison mode
        tickers = []
        for task in state.plan:
            if task.tool_args:
                t = task.tool_args.get("ticker") or task.tool_args.get("symbol")
                if t and t.upper() not in tickers:
                    tickers.append(t.upper())
        is_comparison = len(tickers) >= 2

        comparison_note = ""
        if is_comparison:
            comparison_note = (
                "\n\nCOMPARATIVE ANALYSIS MODE: The data covers multiple tickers: "
                + ", ".join(tickers)
                + ". Explicitly cross-analyse their metrics: margins, growth rates, "
                "valuations, and debt ratios side-by-side. Include a COMPARISON TABLE."
            )

        prompt = ChatPromptTemplate.from_template("""
    ROLE: You are Jasper, a deterministic financial intelligence engine for institutional analysts.
    ACTIVE REPORT MODE: {report_mode}
    TASK: Synthesize research data into a professional analyst memo.{comparison_note}

    User Query: {query}

    Research Data:
    {data}

    REPORT SCOPE CONSTRAINTS:
    - BUSINESS_MODEL: Focus strictly on business quality, strategy, and moats.
    - RISK_ANALYSIS: Focus strictly on exposures, concentration, and threats.
    - FINANCIAL_EVIDENCE: Focus strictly on presenting verified financial metrics.
    - GENERAL: Provide a balanced overview.

    REPORT STRUCTURE (MANDATORY):

    1. EXECUTIVE SIGNAL BOX
       **COMPANY**: [Name]
       **CORE ENGINE**: [One-sentence business model logic]
       **THESIS**: [One-sentence research conclusion]

    2. EXECUTIVE SUMMARY
       - SKIMMABLE KEY FINDINGS: 3-4 bullet points.
       - SCOPE OF EVIDENCE: What is proven vs. what is inferred.

    3. BUSINESS MODEL MECHANICS
       - Qualitative narrative of revenue/margin logic.
       - Use *Assumptions* block (italicized) for inferred logic.
       - End with: **What This Means:** [interpretation paragraph]

    4. FINANCIAL EVIDENCE
       Tables MUST follow this exact format — each row on its own line:

       | Metric | Value |
       |:---|:---|
       | Item 1 | Data 1 |
       | Item 2 | Data 2 |

       Rules:
       - Separator row (|:---|:---|) on its OWN line immediately after header.
       - NEVER put multiple rows on one line.
       - Use currency shorthand: $130.5B, $45M, 12.3%.
       - Bold all column headers.
       - After each table: **What This Means:** [interpretation]
       - Missing data: use "N/A".

    5. LIMITATIONS & DATA GAPS
       Use: ### ⚠️ WARNING: [Issue Name]
       DO NOT use blockquotes (>), colored text, or diff syntax blocks.

    FORMATTING CONSTRAINTS:
    - Neutral, institutional tone. No conversational filler.
    - Bold (**text**) for emphasis. ## for sections, ### for subsections.
    - Numbers: always B/M/K shorthand in tables.

    Analysis:
    """)

        chain = prompt | self.llm
        response = await chain.ainvoke({
            "query": state.query,
            "data": data_context,
            "report_mode": state.report_mode.value,
            "comparison_note": comparison_note,
        })

        self.logger.log("SYNTHESIS_COMPLETED", {"confidence": state.validation.confidence})
        return response.content
