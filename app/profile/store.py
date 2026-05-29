"""User profile: persisted preferences and the feedback history behind scoring.

The profile is a single JSON file under ``$XDG_CONFIG_HOME`` holding stated
preferences (cuisines, budget, language, dislikes) and a log of feedback events.
``factors.history_score`` reads this log via ``UserProfile.summary_for`` to
personalise rankings. To keep the file bounded, events beyond
``DEFAULT_KEEP_RECENT`` are *compacted* into per-place tallies rather than
discarded, so old signal still counts.
"""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.profile.history import (
    ACTIONS,
    CompactedEntry,
    HistoryEvent,
    PlaceSummary,
)

DEFAULT_KEEP_RECENT = 1000


def default_profile_path() -> Path:
    """Return the profile path under ``$XDG_CONFIG_HOME`` (``~/.config`` fallback)."""
    xdg = os.getenv("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg) / "youtube_summary" / "profile.json"


@dataclass
class UserProfile:
    """Stated preferences plus the feedback history used for personalisation."""

    cuisine_prefs: list[str] = field(default_factory=list)
    default_budget: float | None = None
    default_language: str = "en"
    disliked_keywords: list[str] = field(default_factory=list)
    history: list[HistoryEvent] = field(default_factory=list)
    compacted: dict[str, CompactedEntry] = field(default_factory=dict)

    def summary_for(self, place_id: str) -> PlaceSummary | None:
        """Aggregate live events and compacted tallies for one place.

        Returns a ``PlaceSummary`` combining recent ``(action, ts, rating)``
        events with any compacted counts, or ``None`` when the user has no
        record for ``place_id``."""
        if not place_id:
            return None
        events = [
            (e.action, e.ts, e.rating) for e in self.history if e.place_id == place_id
        ]
        comp = self.compacted.get(place_id)
        if not events and comp is None:
            return None
        visited = any(a == "visited" for a, _, _ in events)
        if comp is not None and comp.visited_count > 0:
            visited = True
        return PlaceSummary(
            events=events,
            compacted_liked=comp.liked_count if comp else 0,
            compacted_disliked=comp.disliked_count if comp else 0,
            visited=visited,
        )

    def record(
        self,
        place_id: str,
        action: str,
        rating: int | None = None,
        now: float | None = None,
        keep_recent: int = DEFAULT_KEEP_RECENT,
    ) -> None:
        """Append a feedback event, compacting old history if it grew too large.

        Raises ``ValueError`` for an action outside ``ACTIONS``."""
        if action not in ACTIONS:
            raise ValueError(f"Unknown action {action!r}; must be one of {ACTIONS}")
        ts = now if now is not None else time.time()
        self.history.append(HistoryEvent(place_id=place_id, action=action, ts=ts, rating=rating))
        self._compact_if_needed(keep_recent=keep_recent)

    def _compact_if_needed(self, keep_recent: int = DEFAULT_KEEP_RECENT) -> None:
        """Fold the oldest events past ``keep_recent`` into per-place tallies."""
        if len(self.history) <= keep_recent:
            return
        excess = len(self.history) - keep_recent
        to_compact = self.history[:excess]
        self.history = self.history[excess:]
        for ev in to_compact:
            entry = self.compacted.setdefault(ev.place_id, CompactedEntry())
            if ev.action == "liked":
                entry.liked_count += 1
            elif ev.action == "disliked":
                entry.disliked_count += 1
            elif ev.action == "visited":
                entry.visited_count += 1
            entry.last_seen_ts = max(entry.last_seen_ts, ev.ts)


def load_profile(path: str | Path | None = None) -> UserProfile:
    """Load the profile JSON, returning a fresh empty profile if absent or corrupt."""
    p = Path(path) if path is not None else default_profile_path()
    if not p.exists():
        return UserProfile()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return UserProfile()
    history = [HistoryEvent(**e) for e in raw.get("history", []) if isinstance(e, dict)]
    compacted_raw = raw.get("compacted", {}) or {}
    compacted = {
        pid: CompactedEntry(**vals)
        for pid, vals in compacted_raw.items()
        if isinstance(vals, dict)
    }
    return UserProfile(
        cuisine_prefs=list(raw.get("cuisine_prefs", []) or []),
        default_budget=raw.get("default_budget"),
        default_language=raw.get("default_language", "en") or "en",
        disliked_keywords=list(raw.get("disliked_keywords", []) or []),
        history=history,
        compacted=compacted,
    )


def save_profile(profile: UserProfile, path: str | Path | None = None) -> Path:
    """Atomically write the profile to JSON (temp file + replace); return the path."""
    p = Path(path) if path is not None else default_profile_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cuisine_prefs": profile.cuisine_prefs,
        "default_budget": profile.default_budget,
        "default_language": profile.default_language,
        "disliked_keywords": profile.disliked_keywords,
        "history": [asdict(e) for e in profile.history],
        "compacted": {pid: asdict(c) for pid, c in profile.compacted.items()},
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return p
