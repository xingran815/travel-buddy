import os
from dotenv import load_dotenv

load_dotenv()


def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


LLM_API_KEY = get_env("LLM_API_KEY")
LLM_BASE_URL = get_env("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = get_env("LLM_MODEL", "gpt-4o")
GOOGLE_MAPS_API_KEY = get_env("GOOGLE_MAPS_API_KEY")
APP_LANG = get_env("APP_LANG", "tr")
