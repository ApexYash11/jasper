from typing import List, Any
from pydantic import BaseModel, ValidationError
from langchain_core.prompts import ChatPromptTemplate
import json
import re
from ..observability.logger import SessionLogger


# --- Entity Model ---
# Defines the structure for extracted financial entities
class Entity(BaseModel):
    name: str
    type: str  # company, index, sector, macro
    ticker: str | None = None


NER_PROMPT = """
Extract financial entities from the user query.

Rules:
- Identify companies, indices, sectors, macro indicators
- Include ticker if confidently known
- If uncertain, leave ticker null
- Do NOT guess

Return JSON only in this format:
{{
  "entities": [
    {{"name": "Company Name", "type": "company", "ticker": "TICKER"}}
  ]
}}

Query:
{query}
"""


# --- Entity Extractor ---
# Handles the interpretation of user queries to identify financial entities
class EntityExtractor:
    def __init__(self, llm: Any, logger: SessionLogger | None = None):
        # FIX 6: Verify LLM is deterministic
        if hasattr(llm, 'temperature') and llm.temperature != 0:
            raise ValueError(f"EntityExtractor requires deterministic LLM (temperature=0), got {llm.temperature}")
        
        self.llm = llm
        self.logger = logger or SessionLogger()

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

    async def extract(self, query: str) -> List[Entity]:
        self.logger.log("ENTITY_EXTRACTION_STARTED", {"query": query})
        prompt = ChatPromptTemplate.from_template(NER_PROMPT)
        generate_result = await self.llm.agenerate([prompt.format_messages(query=query)])
        raw = generate_result.generations[0][0].text

        # Extract JSON from markdown or plain text
        json_text = self._extract_json(raw)

        try:
            data = json.loads(json_text)
        except Exception as e:
            self.logger.log("ENTITY_EXTRACTION_PARSE_ERROR", {"raw": raw, "json_text": json_text, "error": str(e)})
            raise RuntimeError("Failed to parse entity extractor output as JSON") from e

        entities = []
        for e in data.get("entities", []):
            try:
                ent = Entity(**e)
                entities.append(ent)
            except ValidationError as ve:
                # skip invalid entities but log
                self.logger.log("ENTITY_VALIDATION_ERROR", {"entity": e, "error": ve.errors()})

        self.logger.log("ENTITY_EXTRACTION_COMPLETED", {"count": len(entities)})
        return entities
