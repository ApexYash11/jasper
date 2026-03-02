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

    async def synthesize(self, state: Jasperstate, token_callback=None) -> str:
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
                + ". Use compact comparison tables and never exceed 3 columns per table "
                "(Metric + up to 2 tickers). If there are more than 2 tickers, split into multiple tables. "
                "Include a comparison table using this pattern:\n"
                "| Metric | Ticker A | Ticker B |\n"
                "|:---|:---|:---|\n"
                "| Revenue | $X.XB | $Y.YB |"
            )

        prompt = ChatPromptTemplate.from_template("""
    ROLE: You are Jasper, a deterministic financial intelligence engine.
    ACTIVE REPORT MODE: {report_mode}
    TASK: Synthesize research data into a professional analyst memo.{comparison_note}

    User Query: {query}

    Research Data:
    {data}

    CRITICAL TABLE FORMATTING RULE — NEVER VIOLATE THIS:
    Every table row MUST be on its own separate line. Never put two rows on one line.
    Every row MUST start with | and end with |.
    Never emit placeholder rows like |  |  |.
    Keep tables compact: max 3 columns (prefer multiple small tables over one wide table).
    Keep headers short (1-3 words) and use compact numbers (B/M/K, percentages).
    If content is non-comparative, prefer bullets over tables.

    CORRECT (each row on its own line):
    | Metric | Value |
    |:---|:---|
    | Revenue | $130.5B |
    | Net Income | $29.9B |

    WRONG (never do this — will break rendering):
    | Revenue | $130.5B | | Net Income | $29.9B |

    WRONG (never do this — empty filler row):
    |  |  |

    REPORT STRUCTURE:
    1. EXECUTIVE SIGNAL BOX — Company, Core Engine, Thesis (one sentence each)
    2. EXECUTIVE SUMMARY — 3-4 bullet key findings
    3. BUSINESS MODEL MECHANICS — qualitative narrative
    4. FINANCIAL EVIDENCE — compact tables using the CORRECT format above, each followed by What This Means:
    5. LIMITATIONS & DATA GAPS — use ### ⚠️ WARNING: [Issue Name] format

    FORMATTING: Neutral institutional tone. Bold for emphasis. ## sections, ### subsections.
    Numbers: always B/M/K shorthand in tables. Missing data: use N/A.

    Analysis:
    """)

        chain = prompt | self.llm

        # Stream tokens to callback if provided, otherwise collect silently
        full_response = ""
        try:
            async for chunk in chain.astream({
                "query": state.query,
                "data": data_context,
                "report_mode": state.report_mode.value,
                "comparison_note": comparison_note,
            }):
                token = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response += token
                if token_callback:
                    token_callback(token)
        except Exception as e:
            # If streaming fails (some models don't support it), fall back to ainvoke
            self.logger.log("SYNTHESIS_STREAM_FALLBACK", {"error": str(e)})
            response = await chain.ainvoke({
                "query": state.query,
                "data": data_context,
                "report_mode": state.report_mode.value,
                "comparison_note": comparison_note,
            })
            full_response = response.content

        self.logger.log("SYNTHESIS_COMPLETED", {"confidence": state.validation.confidence})
        return full_response
