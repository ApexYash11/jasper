import os
from typing import Dict
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from .config import get_llm_api_key

def get_llm(temperature: float = 0) -> ChatOpenAI:
    """
    Get a LangChain-compatible LLM configured with OpenRouter.
    OpenRouter provides access to multiple models through an OpenAI-compatible API.
    
    Args:
        temperature: Controls randomness (0 = deterministic, 1 = more random)
    
    Returns:
        Configured ChatOpenAI instance pointing to OpenRouter
    """
    api_key = get_llm_api_key()  # Raises ValueError if not set
    # Default: Gemini Flash Exp (free, capable, good JSON compliance).
    # Override via OPENROUTER_MODEL env var for a different model.
    # Recommended for production: openai/gpt-4o-mini or anthropic/claude-haiku
    model = os.getenv("OPENROUTER_MODEL", "stepfun/step-3.5-flash:free")

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=SecretStr(api_key),
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://jasper.local",
            "X-Title": "Jasper Finance",
        },
    )


# ── Per-temperature singletons — one connection pool per temperature per process ──
_llm_singletons: "Dict[float, ChatOpenAI]" = {}


def get_llm_singleton(temperature: float = 0) -> "ChatOpenAI":
    """Return a cached LLM instance for the given temperature (one per temperature per process)."""
    global _llm_singletons
    if temperature not in _llm_singletons:
        _llm_singletons[temperature] = get_llm(temperature=temperature)
    return _llm_singletons[temperature]