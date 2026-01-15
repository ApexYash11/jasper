from typing import List, Any, Literal
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


# --- NEW: Query Intent Model ---
# Classifies the type of financial question being asked
class QueryIntent(BaseModel):
    category: Literal["quantitative", "qualitative", "mixed"]
    reasoning: str = ""


# Combined extraction result
class ExtractionResult(BaseModel):
    entities: List[Entity]
    intent: QueryIntent


NER_PROMPT = """
Extract financial entities from the user query AND classify query intent.

Rules for entities:
- Identify companies, indices, sectors, macro indicators
- Include ticker if confidently known
- If uncertain, leave ticker null
- Do NOT guess

Rules for intent classification:
- "quantitative": Query asks for financial metrics (revenue, earnings, margins, growth rates, valuations, debt levels)
- "qualitative": Query asks for explanations (business model, strategy, competitive position, how they make money, operations)
- "mixed": Query contains both types of questions

Examples:
- "What is Apple's revenue?" → quantitative
- "Explain Uber's business model" → qualitative
- "How does Amazon make money?" → qualitative
- "Compare Tesla and Ford operating margins" → quantitative
- "What is Microsoft's strategy AND revenue growth?" → mixed

Return JSON only in this format:
{{
  "entities": [
    {{"name": "Company Name", "type": "company", "ticker": "TICKER"}}
  ],
  "intent": {{
    "category": "quantitative|qualitative|mixed",
    "reasoning": "Brief explanation of intent classification"
  }}
}}

Query:
{query}
"""


# --- Entity Extractor ---
# Handles the interpretation of user queries to identify financial entities and intent
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

    async def extract(self, query: str) -> ExtractionResult:
        """
        Extract financial entities AND classify query intent from user query.
        
        Returns:
            ExtractionResult with both entities and intent classification
        """
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

        # Extract entities
        entities = []
        for e in data.get("entities", []):
            try:
                ent = Entity(**e)
                entities.append(ent)
            except ValidationError as ve:
                # skip invalid entities but log
                self.logger.log("ENTITY_VALIDATION_ERROR", {"entity": e, "error": ve.errors()})

        # Extract intent
        intent_data = data.get("intent", {})
        try:
            intent = QueryIntent(**intent_data)
        except (ValidationError, TypeError):
            # Fallback to quantitative if intent classification fails
            self.logger.log("INTENT_EXTRACTION_ERROR", {"intent_data": intent_data})
            intent = QueryIntent(category="quantitative", reasoning="Defaulted due to extraction error")

        result = ExtractionResult(entities=entities, intent=intent)
        self.logger.log("ENTITY_EXTRACTION_COMPLETED", {"count": len(entities), "intent": intent.category})
        return result
