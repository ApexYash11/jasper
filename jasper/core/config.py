from dotenv import load_dotenv
import os

load_dotenv()

def get_llm_api_key() -> str:
    """Get LLM API key from environment."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise ValueError(
            "OPENROUTER_API_KEY not set. "
            "Get one at https://openrouter.ai/keys, then add to .env or export as env var."
        )
    return key

def get_financial_api_key() -> str:
    """Get financial data provider API key from environment."""
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
    if key == "demo":
        import warnings
        warnings.warn(
            "\n"
            "╔══ ALPHA VANTAGE DEMO KEY ACTIVE ══════════════════════════════╗\n"
            "║  WARNING: No ALPHA_VANTAGE_API_KEY set in .env               ║\n"
            "║  The 'demo' key ALWAYS returns IBM (ticker: IBM) data,        ║\n"
            "║  regardless of the ticker you query.                          ║\n"
            "║  Data shown will NOT correspond to your queried company.      ║\n"
            "║  → Get a free key at https://www.alphavantage.co/support/     ║\n"
            "║    and add  ALPHA_VANTAGE_API_KEY=<key>  to your .env         ║\n"
            "╚═══════════════════════════════════════════════════════════════╝",
            UserWarning,
            stacklevel=2,
        )
    return key

def get_config():
    return {
        "LLM_API_KEY": get_llm_api_key(),
        "FINANCIAL_API_KEY": get_financial_api_key(),
        "ENV": os.getenv("ENV", "dev"),
    }

# --- JASPER UI CONFIGURATION ---

THEME = {
    "Background": "#000000",
    "Primary Text": "#E0E0E0",
    "Accent": "#00EA78",  # Phosphor Green
    "Brand": "#00EA78",   # Phosphor Green
    "Success": "#00EA78", # Phosphor Green
    "Warning": "#FFB302",
    "Error": "#FF007F",
}

BANNER_ART = """
      ██╗   ██████╗  ███████╗ ██████╗  ███████╗ ██████╗ 
      ██║  ██╔═══██╗ ██╔════╝ ██╔══██╗ ██╔════╝ ██╔══██╗
      ██║  ████████║ ███████╗ ██████╔╝ █████╗   ██████╔╝
 ██   ██║  ██╔═══██║ ╚════██║ ██╔═══╝  ██╔══╝   ██╔══██╗
 ╚█████╔╝  ██║   ██║ ███████║ ██║      ███████╗ ██║  ██║
  ╚════╝   ╚═╝   ╚═╝ ╚══════╝ ╚═╝      ╚══════╝ ╚═╝  ╚═╝
"""
