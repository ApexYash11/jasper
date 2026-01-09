from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from ..core.state import Task, Jasperstate, ConfidenceBreakdown
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
    ROLE: You are Jasper, a deterministic financial intelligence engine.
    TASK: Synthesize the research data into a clinical, high-density analysis.
    
    User Query: {query}
    
    Research Data:
    {data}
    
    CONSTRAINTS:
    - Use ONLY provided data.
    - NO conversational filler (e.g., "Here is the report", "Based on the data").
    - NO internal memo headers (To:, From:, Subject:, Date:).
    - NO introductory pleasantries.
    - Start immediately with the analysis headings (e.g., "1. Revenue Scale").
    - Use succinct bullet points and bolded metrics.
    - If data is partial or potentially subsidiary-only, flag it in a 'Data Qualifications' section at the end.
    
    OUTPUT STRUCTURE:
    - Findings prioritized by materiality.
    - Neutral objective tone.
    - Technical density is preferred over narrative flow.
    
    Analysis:
    """)
    
    chain = prompt | self.llm
    response = await chain.ainvoke({"query": state.query, "data": data_context})
    
    self.logger.log("SYNTHESIS_COMPLETED", {"confidence": state.validation.confidence})
    return response.content
