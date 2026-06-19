import os
from typing import Dict
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from .config import get_llm_api_key


def get_llm(temperature: float = 0) -> ChatOpenAI:
    """
    Get a LangChain-compatible LLM configured with Groq.
    Groq provides fast inference through an OpenAI-compatible API.

    Args:
        temperature: Controls randomness (0 = deterministic, 1 = more random)

    Returns:
        Configured ChatOpenAI instance pointing to Groq
    """
    api_key = get_llm_api_key()  # Raises ValueError if not set
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=SecretStr(api_key),
        base_url="https://api.groq.com/openai/v1",
    )


# ── Per-temperature singletons — one connection pool per temperature per process ──
_llm_singletons: "Dict[float, ChatOpenAI]" = {}


def get_llm_singleton(temperature: float = 0) -> "ChatOpenAI":
    """Return a cached LLM instance for the given temperature (one per temperature per process)."""
    global _llm_singletons
    if temperature not in _llm_singletons:
        _llm_singletons[temperature] = get_llm(temperature=temperature)
    return _llm_singletons[temperature]
