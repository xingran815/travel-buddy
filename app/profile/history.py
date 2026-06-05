"""Data types for the user's feedback history (see ``app/profile/store.py``)."""

from dataclasses import dataclass, field

ACTIONS = ("liked", "disliked", "visited", "summarized", "searched")


@dataclass
class HistoryEvent:
    """A single timestamped feedback event for one place."""

    place_id: str
    action: str
    ts: float
    rating: int | None = None


@dataclass
class CompactedEntry:
    """Aggregated counts for a place whose individual events have been pruned."""

    liked_count: int = 0
    disliked_count: int = 0
    visited_count: int = 0
    last_seen_ts: float = 0.0


@dataclass
class PlaceSummary:
    """Combined live events + compacted tallies for one place, fed to scoring."""

    events: list[tuple[str, float, int | None]] = field(default_factory=list)
    compacted_liked: int = 0
    compacted_disliked: int = 0
    visited: bool = False
