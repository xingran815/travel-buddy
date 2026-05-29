"""Settings and cache-management endpoints (health, settings, cache stats/clear).

Settings updates are persisted to the project ``.env`` and the in-memory
``app.config`` values are refreshed so they take effect without a restart.
"""

import json
import sqlite3
from pathlib import Path

from dotenv import load_dotenv, set_key
from fastapi import APIRouter

import app.config as config
from app.server.schemas import (
    CacheClearRequest,
    CacheStatsResponse,
    HealthResponse,
    SettingsResponse,
    SettingsUpdate,
)

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = PROJECT_ROOT / ".env"


@router.get("/health")
def health() -> HealthResponse:
    """Liveness probe returning the static status/version payload."""
    return HealthResponse()


@router.get("/settings")
def get_settings() -> SettingsResponse:
    """Return current settings; API keys are reported only as set/unset booleans."""
    return SettingsResponse(
        llm_provider=config.LLM_PROVIDER,
        llm_model=config.LLM_MODEL,
        llm_base_url=config.LLM_BASE_URL,
        llm_api_key_set=bool(config.LLM_API_KEY),
        google_maps_api_key_set=bool(config.GOOGLE_MAPS_API_KEY),
        app_lang=config.APP_LANG,
    )


@router.put("/settings")
def update_settings(req: SettingsUpdate) -> SettingsResponse:
    """Persist the provided settings to ``.env`` and refresh ``app.config`` live."""
    env_map = {
        "llm_provider": "LLM_PROVIDER",
        "llm_api_key": "LLM_API_KEY",
        "llm_model": "LLM_MODEL",
        "llm_base_url": "LLM_BASE_URL",
        "google_maps_api_key": "GOOGLE_MAPS_API_KEY",
        "app_lang": "APP_LANG",
    }
    updates = req.model_dump(exclude_none=True)
    if not updates:
        return get_settings()

    ENV_PATH.touch(exist_ok=True)
    for field, env_key in env_map.items():
        if field in updates:
            set_key(str(ENV_PATH), env_key, str(updates[field]))

    load_dotenv(ENV_PATH, override=True)
    config.LLM_PROVIDER = config.get_env("LLM_PROVIDER", "openai")
    config.LLM_API_KEY = config.get_env("LLM_API_KEY")
    config.LLM_BASE_URL = config.get_env("LLM_BASE_URL", "https://api.openai.com/v1")
    config.LLM_MODEL = config.get_env("LLM_MODEL", "gpt-4o")
    config.GOOGLE_MAPS_API_KEY = config.get_env("GOOGLE_MAPS_API_KEY")
    config.APP_LANG = config.get_env("APP_LANG", "tr")

    return get_settings()


@router.get("/cache/stats")
def cache_stats() -> CacheStatsResponse:
    """Report on-disk sizes/entry counts for the places, pros-cons, and aspects caches."""
    stats = CacheStatsResponse()

    db_path = PROJECT_ROOT / "cache" / "places.sqlite"
    if db_path.exists():
        stats.places_size_bytes = db_path.stat().st_size
        try:
            conn = sqlite3.connect(str(db_path))
            row = conn.execute("SELECT COUNT(*) FROM places_cache").fetchone()
            stats.places_entries = row[0] if row else 0
            conn.close()
        except Exception:
            pass

    pc_path = PROJECT_ROOT / "cache" / "pros_cons.json"
    if pc_path.exists():
        try:
            data = json.loads(pc_path.read_text())
            stats.pros_cons_entries = len(data)
        except Exception:
            pass

    asp_path = PROJECT_ROOT / "cache" / "aspects.json"
    if asp_path.exists():
        try:
            data = json.loads(asp_path.read_text())
            stats.aspects_entries = len(data)
        except Exception:
            pass

    return stats


@router.post("/cache/clear")
def clear_cache(req: CacheClearRequest) -> dict:
    """Clear the places cache, the LLM JSON caches, or both per ``req.target``.

    Returns the list of cache targets that were actually cleared."""
    cleared: list[str] = []

    if req.target in ("places", "all"):
        db_path = PROJECT_ROOT / "cache" / "places.sqlite"
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                conn.execute("DELETE FROM places_cache")
                conn.commit()
                conn.close()
                cleared.append("places")
            except Exception:
                pass

    if req.target in ("llm", "all"):
        for name in ("pros_cons.json", "aspects.json"):
            p = PROJECT_ROOT / "cache" / name
            if p.exists():
                p.write_text("{}")
                cleared.append(name)

    return {"cleared": cleared}
