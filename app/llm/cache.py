"""Tiny JSON-file cache used by the LLM recommendation helpers, plus the review
helpers that build cache keys and prompt excerpts. All functions are pure and
take an explicit path, so callers own where each cache lives."""

import hashlib
import json
from pathlib import Path


def load_json_cache(path: Path) -> dict:
    """Read a JSON cache file, returning ``{}`` if it is missing or corrupt."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_json_cache(path: Path, data: dict) -> None:
    """Write ``data`` as pretty JSON, creating the parent directory as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_json_cache_safe(path: Path, data: dict) -> None:
    """Write the cache but swallow filesystem errors — caching is best-effort."""
    try:
        save_json_cache(path, data)
    except OSError:
        pass


def reviews_signature(reviews: list[dict]) -> str:
    """Fingerprint the first 5 reviews (rating + 60 chars each) for cache keys.

    Truncating keeps the key stable against minor review edits while still
    invalidating when the leading reviews change materially."""
    blob = "|".join(f"{r.get('rating', '')}:{(r.get('text') or '')[:60]}" for r in (reviews or [])[:5])
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def format_review_excerpts(
    reviews: list[dict], limit: int = 5, maxlen: int = 240, with_rating: bool = True,
) -> str:
    """Render up to ``limit`` reviews as bullet lines for an LLM prompt."""
    lines = []
    for r in (reviews or [])[:limit]:
        text = (r.get("text") or "")[:maxlen]
        lines.append(f"- ({r.get('rating', '')}/5) {text}" if with_rating else f"- {text}")
    return "\n".join(lines)
