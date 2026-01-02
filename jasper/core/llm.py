import os
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_llm(temperature: float = 0) -> ChatOpenAI:
    """
    Get a LangChain-compatible LLM configured with OpenRouter.
    OpenRouter provides access to multiple models through an OpenAI-compatible API.
    
    Args:
        temperature: Controls randomness (0 = deterministic, 1 = more random)
    
    Returns:
        Configured ChatOpenAI instance pointing to OpenRouter
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash:free")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=SecretStr(api_key),
        base_url="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "https://jasper.local"},
    )