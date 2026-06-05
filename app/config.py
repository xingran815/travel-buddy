"""Central config: loads ``.env`` and exposes settings as module globals.

Importing this module triggers ``load_dotenv()`` once. The settings router can
mutate these globals at runtime (after rewriting ``.env``) so config changes
take effect without restarting the server.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def get_env(key: str, default: str = "") -> str:
    """Read an environment variable, returning ``default`` when unset."""
    return os.getenv(key, default)


LLM_PROVIDER = get_env("LLM_PROVIDER", "openai")
LLM_API_KEY = get_env("LLM_API_KEY")
LLM_BASE_URL = get_env("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = get_env("LLM_MODEL", "gpt-4o")
GOOGLE_MAPS_API_KEY = get_env("GOOGLE_MAPS_API_KEY")
APP_LANG = get_env("APP_LANG", "tr")
