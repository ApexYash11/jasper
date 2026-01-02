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
    You are a senior financial analyst. Synthesize the following research data into a concise, professional comparison.
    
    User Query: {query}
    
    Research Data:
    {data}
    
    Rules:
    - Use only the provided data.
    - If data is insufficient for a full comparison, state what is missing.
    - Focus on key operating metrics (Revenue, Net Income, etc.).
    - Do NOT hallucinate or guess numbers.
    - Maintain a neutral, professional tone.
    
    Answer:
    """)
    
    chain = prompt | self.llm
    response = await chain.ainvoke({"query": state.query, "data": data_context})
    
    self.logger.log("SYNTHESIS_COMPLETED", {"confidence": state.validation.confidence})
    return response.content
