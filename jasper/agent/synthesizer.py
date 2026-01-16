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
        desc = task.description if task else "Unknown Task"
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
       > **COMPANY**: [Name]
       > **CORE ENGINE**: [One-sentence business model logic]
       > **THESIS**: [One-sentence research conclusion]
    
    2. EXECUTIVE SUMMARY
       - SKIMMABLE KEY FINDINGS: 3-4 bullet points.
       - SCOPE OF EVIDENCE: What is proven vs. what is inferred.
    
    3. BUSINESS MODEL MECHANICS
       - Qualitative narrative of revenue/margin logic.
       - Use *Assumptions* block (italicized) for any inferred logic.
       - Add a "> **What This Means**" callout after this section.
    
    4. FINANCIAL EVIDENCE
       - Tabular data support.
       - MANDATORY TABLE FORMAT:
         - Each row MUST be on a new line.
         - The separator row (|---|) MUST follow the header row immediately.
         - Do NOT combine multiple rows into a single string or line.
         - Use clean, standard Markdown table syntax.
       - Use clean Markdown tables with a blank line before and after.
       - Bold all table headers.
       - Add a "> **What This Means**" callout after each major table.
       - Note: If data is missing for a metric, use "N/A" or "---".
    
    5. LIMITATIONS & DATA GAPS
       - Explicit warning block for missing or low-confidence data.
       - Format as: "### ⚠️ WARNING: [Issue Name]" followed by description.
    
    CONSTRAINTS:
    - Neutral, institutional tone. No conversational filler.
    - VISUAL SEPARATION: 
      - Facts: Plain text.
      - Interpretation: Use Markdown blockquotes (>).
      - Assumptions: Use italics (*text*).
      - Limitations: Use bold warning headers.
    - Visual hierarchy: Use ## for sections, ### for subsections.
    
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
