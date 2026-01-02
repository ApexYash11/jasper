import uuid
from typing import List, Any
from langchain_core.prompts import ChatPromptTemplate
from ..core.state import Task
from .entity_extractor import EntityExtractor
import json
import re
from ..observability.logger import SessionLogger


# FIX 7: Define available tools
AVAILABLE_TOOLS = ["income_statement"]


PLANNER_PROMPT = """
You are a financial research planner.

Extracted Entities:
{entities}

Available Tools:
{available_tools}

Your job:
- Break the user's question into explicit, ordered research tasks.
- Each task must declare what data it requires.
- Use the extracted entities (tickers, names) in the task arguments.
- ONLY use tools from the available tools list.
- Do NOT assume data exists.
- Do NOT compute results.
- Do NOT answer the question.

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

    async def plan(self, query: str) -> List[Task]:
        self.logger.log("PLANNER_STARTED", {"query": query})

        # Preprocessing: Extract entities
        entities = await self.extractor.extract(query)
        
        # FIX 8: Fail fast if no entities extracted
        if not entities:
            self.logger.log("PLANNER_NO_ENTITIES", {"query": query})
            raise ValueError("Could not extract financial entities from query. Please provide company names or tickers (e.g., 'Apple' or 'AAPL')")
        
        entities_str = "\n".join([f"- {e.name} ({e.type}): {e.ticker or 'N/A'}" for e in entities])
        
        # FIX 7: Include available tools in prompt
        tools_str = ", ".join(AVAILABLE_TOOLS)
        prompt = ChatPromptTemplate.from_template(PLANNER_PROMPT)
        generate_result = await self.llm.agenerate([prompt.format_messages(query=query, entities=entities_str, available_tools=tools_str)])
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
        for t in parsed.get("tasks", []):
            if not isinstance(t, dict) or "description" not in t:
                self.logger.log("PLANNER_TASK_SCHEMA_ERROR", {"task": t})
                raise ValueError("Each task must be an object with at least a 'description' field")

            # FIX 7: Validate tool_name is known
            tool_name = t.get("tool_name", "")
            if tool_name not in AVAILABLE_TOOLS:
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

        if not tasks:
            self.logger.log("PLANNER_EMPTY_TASKS", {"response": parsed})
            raise ValueError("Planner produced empty task list")

        self.logger.log("PLANNER_COMPLETED", {"task_count": len(tasks)})
        return tasks
