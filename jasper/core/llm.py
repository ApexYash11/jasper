import os
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
    model = os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash:free")
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=SecretStr(api_key),
        base_url="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "https://jasper.local"},
    )