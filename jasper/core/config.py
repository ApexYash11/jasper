from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

def get_config():
    return {
        "API_KEY": os.getenv("API_KEY", ""),
        "ENV": os.getenv("ENV", "dev"),
    }
