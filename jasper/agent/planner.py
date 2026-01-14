import uuid
from typing import List, Any, Tuple
from langchain_core.prompts import ChatPromptTemplate
from ..core.state import Task, ReportMode
from .entity_extractor import EntityExtractor
import json
import re
from ..observability.logger import SessionLogger


# FIX 7: Define available tools
AVAILABLE_TOOLS = ["income_statement"]


PLANNER_PROMPT = """
You are a financial research planner.
ACTIVE REPORT MODE: {report_mode}

Query Intent: {intent}
Extracted Entities:
{entities}

Available Tools:
{available_tools}

Your job:
- Strictly adhere to the ACTIVE REPORT MODE. Do NOT generate tasks outside this scope.
- BUSINESS_MODEL Mode: Prioritize narrative tasks concerning business quality, segments, and moat.
- RISK_ANALYSIS Mode: Prioritize tasks investigating debt, concentration, and competitive threats.
- FINANCIAL_EVIDENCE Mode: Create ONLY tasks that fetch raw financial statement data.

- If intent is QUALITATIVE: Return empty task list (no data fetching needed). Synthesis will use domain knowledge only.
- If intent is QUANTITATIVE: Break the query into explicit, ordered research tasks for data fetching.
- If intent is MIXED: Create both qualitative synthesis tasks AND quantitative data-fetching tasks.

For QUANTITATIVE tasks:
- Each task must declare what data it requires
- Use extracted entities (tickers, names) in task arguments
- ONLY use tools from the available tools list
- Do NOT assume data exists
- Do NOT compute results
- Do NOT answer the question

Output JSON ONLY in this format:
{{
  "tasks": [
    {{
      "description": "Fetch income statement for AAPL",
      "tool_name": "income_statement",
      "tool_args": {{"ticker": "AAPL"}},
      "status": "pending"
    }}
  ]
}}

For QUALITATIVE or MIXED queries with no quantitative component:
- Return: {{"tasks": []}}

User question:
{query}
"""


# --- Planner ---
# Orchestrates the research process by breaking down queries into tasks
class Planner:
    def __init__(self, llm: Any, logger: SessionLogger | None = None):
        # FIX 6: Verify LLM is deterministic
        if hasattr(llm, 'temperature') and llm.temperature != 0:
            raise ValueError(f"Planner requires deterministic LLM (temperature=0), got {llm.temperature}")
        
        self.llm = llm
        self.logger = logger or SessionLogger()
        self.extractor = EntityExtractor(llm, logger=self.logger)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text, handling markdown code blocks."""
        # Remove markdown code block markers
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        text = text.strip()
        
        # Find the first { and match it with the last }
        start_idx = text.find('{')
        if start_idx == -1:
            return text
        
        # Find matching closing brace by counting
        brace_count = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_idx:i+1]
        
        return text[start_idx:]

    def _infer_mode(self, query: str, intent_category: str) -> ReportMode:
        """Determines report mode based on query keywords and intent."""
        query_lower = query.lower()
        
        # Risk Priority
        if any(w in query_lower for w in ["risk", "exposure", "concentration", "threat", "weakness"]):
            return ReportMode.RISK_ANALYSIS
            
        # Financial Evidence Priority
        if intent_category == "quantitative" or any(w in query_lower for w in ["revenue", "margin", "earnings", "profit", "debt", "balance sheet"]):
            return ReportMode.FINANCIAL_EVIDENCE
            
        # Business Model Priority (Qualitative focus)
        if intent_category == "qualitative" or any(w in query_lower for w in ["business model", "strategy", "how they make money", "operations", "competitive", "advantage"]):
            return ReportMode.BUSINESS_MODEL
            
        return ReportMode.GENERAL

    async def plan(self, query: str) -> Tuple[List[Task], ReportMode]:
        self.logger.log("PLANNER_STARTED", {"query": query})

        # Preprocessing: Extract entities AND intent
        extraction_result = await self.extractor.extract(query)
        entities = extraction_result.entities
        intent = extraction_result.intent
        
        # Infer mode
        report_mode = self._infer_mode(query, intent.category)
        self.logger.log("MODE_INFERRED", {"mode": report_mode.value})
        
        # FIX 8: Fail fast if no entities extracted
        if not entities:
            self.logger.log("PLANNER_NO_ENTITIES", {"query": query})
            raise ValueError("Could not extract financial entities from query. Please provide company names or tickers (e.g., 'Apple' or 'AAPL')")
        
        entities_str = "\n".join([f"- {e.name} ({e.type}): {e.ticker or 'N/A'}" for e in entities])
        
        # FIX 7: Include available tools and intent in prompt
        tools_str = ", ".join(AVAILABLE_TOOLS)
        prompt = ChatPromptTemplate.from_template(PLANNER_PROMPT)
        generate_result = await self.llm.agenerate([prompt.format_messages(
            query=query, 
            entities=entities_str, 
            available_tools=tools_str,
            intent=intent.category,
            report_mode=report_mode.value
        )])
        response = generate_result.generations[0][0].text

        # Extract JSON from markdown or plain text
        json_text = self._extract_json(response)

        try:
            parsed = json.loads(json_text)
        except Exception as e:
            self.logger.log("PLANNER_PARSE_ERROR", {"raw": response, "json_text": json_text, "error": str(e)})
            raise RuntimeError("Planner output is not valid JSON") from e

        if not isinstance(parsed, dict) or "tasks" not in parsed or not isinstance(parsed["tasks"], list):
            self.logger.log("PLANNER_SCHEMA_ERROR", {"parsed": parsed})
            raise ValueError("Planner output must be a JSON object with a 'tasks' list")

        tasks: List[Task] = []
        
        # FIX: For qualitative queries, empty task list is valid
        if intent.category == "qualitative" and len(parsed.get("tasks", [])) == 0:
            self.logger.log("PLANNER_QUALITATIVE_NO_TASKS", {
                "intent": intent.category,
                "reasoning": intent.reasoning
            })
            return tasks, report_mode  # Return empty task list for qualitative queries
        
        for t in parsed.get("tasks", []):
            if not isinstance(t, dict) or "description" not in t:
                self.logger.log("PLANNER_TASK_SCHEMA_ERROR", {"task": t})
                raise ValueError("Each task must be an object with at least a 'description' field")

            # FIX 7: Validate tool_name is known
            tool_name = t.get("tool_name", "")
            if tool_name and tool_name not in AVAILABLE_TOOLS:
                raise ValueError(f"Unknown tool: {tool_name}. Available: {AVAILABLE_TOOLS}")

            tasks.append(
                Task(
                    id=str(uuid.uuid4()),
                    description=t["description"],
                    tool_name=tool_name,
                    tool_args=t.get("tool_args", {}),
                    status=t.get("status", "pending"),
                    error=t.get("error", None),
                )
            )

        # For qualitative queries, empty task list is allowed
        if intent.category != "qualitative" and not tasks:
            self.logger.log("PLANNER_EMPTY_TASKS", {"response": parsed, "intent": intent.category})
            raise ValueError("Planner produced empty task list for non-qualitative query")

        self.logger.log("PLANNER_COMPLETED", {"task_count": len(tasks), "intent": intent.category})
        return tasks, report_mode
