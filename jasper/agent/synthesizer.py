from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from ..core.state import Jasperstate
from ..observability.logger import SessionLogger


# --- Synthesizer ---
# Combines task results into a final answer with confidence breakdown
class Synthesizer:
  def __init__(self, llm: Any, logger: SessionLogger | None = None):
    self.llm = llm
    self.logger = logger or SessionLogger()

  async def synthesize(self, state: Jasperstate) -> str:
    self.logger.log("SYNTHESIS_STARTED", {"plan_length": len(state.plan)})
    
    # Ensure validation passed
    if not state.validation or not state.validation.is_valid:
        raise ValueError("Cannot synthesize without passing validation")
    
    data_context = ""
    for task_id, result in state.task_results.items():
        task = next((t for t in state.plan if t.id == task_id), None)
        # FIX #8: Handle null task reference gracefully
        if not task:
            self.logger.log("SYNTHESIZER_ORPHANED_RESULT", {"task_id": task_id})
            desc = "Unknown Task (orphaned result)"
        else:
            desc = task.description
        data_context += f"Task: {desc}\nData: {result}\n\n"

    prompt = ChatPromptTemplate.from_template("""
    ROLE: You are Jasper, a deterministic financial intelligence engine for institutional analysts.
    ACTIVE REPORT MODE: {report_mode}
    TASK: Synthesize research data into a professional analyst memo matching the ACTIVE REPORT MODE.
    
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
       - Use *Assumptions* block (italicized) for any inferred logic.
       - End this section with: **What This Means:** [interpretation paragraph]
    
    4. FINANCIAL EVIDENCE
       - Tabular data support with PROPER FORMATTING.
       - CRITICAL TABLE FORMATTING RULES (MANDATORY):
         * EVERY ROW MUST START ON A NEW LINE. Use actual line breaks, not pipes.
         * Correct format:
           | Metric | Value |
           |:---|:---|
           | Item 1 | Data 1 |
           | Item 2 | Data 2 |
           | Item 3 | Data 3 |
         * WRONG format (NEVER DO THIS):
           | Metric | Value | |:---|:---| | Item 1 | Data 1 | | Item 2 | Data 2 |
         * Each data row MUST be on its own line with a line break before it.
         * The separator row (|:---|:---|) MUST be on its own line immediately after header.
         * Use currency shorthand: $130.5B instead of $130,497,000,000
         * Format large numbers: use B for billions, M for millions, K for thousands
       - Example of CORRECT table:
         | Fiscal Year | Revenue | Net Income |
         |:---|:---|:---|
         | 2025 | $416.2B | $112.0B |
         | 2024 | $391.0B | $93.7B |
         | 2023 | $383.3B | $97.0B |
       - Use clean Markdown tables with a blank line before and after.
       - Bold all table headers: **Metric** instead of metric.
       - After each table, add: **What This Means:** [interpretation]
       - Note: If data is missing for a metric, use "N/A" or "---".
    
    5. LIMITATIONS & DATA GAPS
       - Format each limitation with a Level 3 header.
       - Use: ### ⚠️ WARNING: [Issue Name]
       - Follow with clear description of the constraint.
       - DO NOT use colored text, blockquotes (>), or diff syntax blocks.
    
    FORMATTING CONSTRAINTS:
    - Neutral, institutional tone. No conversational filler.
    - DO NOT USE: Blockquotes (>), colored text, code blocks for styling, markdown syntax highlighting.
    - DO USE: Bold text (**text**) for emphasis and callouts.
    - Visual hierarchy: Use ## for major sections, ### for subsections and warnings.
    - Interpretation blocks: Always use **What This Means:** on its own paragraph after tables/sections.
    - NUMBERS: Always use shorthand (B/M/K) in tables. Format: $X.XB or XX% for percentages.
    
    TABLE OUTPUT RULES (CRITICAL - MOST IMPORTANT):
    - NEVER write a table on a single line.
    - ALWAYS use actual newline characters between table elements.
    - If you are tempted to write: | Header | | --- | | Data |
    - STOP. This is WRONG. Write it as:
      | Header |
      | --- |
      | Data |
    - Each pipe-delimited row must be on its own line. Use Python's implicit line joining or explicit newlines.
    - Test: If your output has a pipe (|) character followed immediately by another pipe on the same line with data between them on a single line, you have failed. REFORMAT.
    
    Analysis:
    """)
    
    chain = prompt | self.llm
    response = await chain.ainvoke({
        "query": state.query, 
        "data": data_context,
        "report_mode": state.report_mode.value
    })
    
    self.logger.log("SYNTHESIS_COMPLETED", {"confidence": state.validation.confidence})
    return response.content
