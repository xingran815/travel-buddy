import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "cache" / "places.sqlite"

GEOCODE_TTL = 7 * 86400
SEARCH_TTL = 86400
DETAILS_TTL = 86400


class PlacesCache:
    def __init__(self, path: str | Path = DEFAULT_CACHE_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS places_cache ("
            "key TEXT PRIMARY KEY, "
            "response TEXT NOT NULL, "
            "fetched_at REAL NOT NULL, "
            "ttl REAL NOT NULL)"
        )

    @staticmethod
    def make_key(method: str, args: tuple, kwargs: dict) -> str:
        payload = json.dumps(
            {"m": method, "a": list(args), "k": kwargs},
            sort_keys=True,
            default=str,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, key: str, now: float | None = None) -> Any | None:
        ts = now if now is not None else time.time()
        row = self._conn.execute(
            "SELECT response, fetched_at, ttl FROM places_cache WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        response, fetched_at, ttl = row
        if (ts - fetched_at) > ttl:
            return None
        return json.loads(response)

    def set(self, key: str, response: Any, ttl: float, now: float | None = None) -> None:
        ts = now if now is not None else time.time()
        self._conn.execute(
            "INSERT OR REPLACE INTO places_cache (key, response, fetched_at, ttl) VALUES (?, ?, ?, ?)",
            (key, json.dumps(response, ensure_ascii=False), ts, ttl),
        )

    def clear(self) -> None:
        self._conn.execute("DELETE FROM places_cache")

    def close(self) -> None:
        self._conn.close()


def _cache_enabled_default() -> bool:
    return os.getenv("PLACES_CACHE", "on").lower() not in {"off", "0", "false", "no"}


class CachedGmaps:
    """Thin proxy around a googlemaps.Client that caches geocode / places /
    places_nearby / place responses to a local SQLite store. Non-cached methods
    pass through unchanged."""

    def __init__(self, client, cache: PlacesCache | None = None, enabled: bool | None = None) -> None:
        self._client = client
        self._cache = cache if cache is not None else PlacesCache()
        self.enabled = _cache_enabled_default() if enabled is None else enabled
        self.hits = 0
        self.misses = 0

    def geocode(self, *args, **kwargs):
        return self._call("geocode", args, kwargs, ttl=GEOCODE_TTL)

    def places(self, *args, **kwargs):
        return self._call("places", args, kwargs, ttl=SEARCH_TTL)

    def places_nearby(self, *args, **kwargs):
        return self._call("places_nearby", args, kwargs, ttl=SEARCH_TTL)

    def place(self, *args, **kwargs):
        return self._call("place", args, kwargs, ttl=DETAILS_TTL)

    def __getattr__(self, name):
        return getattr(self._client, name)

    def _call(self, method: str, args: tuple, kwargs: dict, ttl: float):
        impl = getattr(self._client, method)
        if not self.enabled:
            return impl(*args, **kwargs)
        key = self._cache.make_key(method, args, kwargs)
        cached = self._cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        response = impl(*args, **kwargs)
        self._cache.set(key, response, ttl)
        self.misses += 1
        return response
