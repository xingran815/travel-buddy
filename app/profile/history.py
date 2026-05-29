from dataclasses import dataclass, field

ACTIONS = ("liked", "disliked", "visited", "summarized", "searched")


@dataclass
class HistoryEvent:
    place_id: str
    action: str
    ts: float
    rating: int | None = None


@dataclass
class CompactedEntry:
    liked_count: int = 0
    disliked_count: int = 0
    visited_count: int = 0
    last_seen_ts: float = 0.0


@dataclass
class PlaceSummary:
    events: list[tuple[str, float, int | None]] = field(default_factory=list)
    compacted_liked: int = 0
    compacted_disliked: int = 0
    visited: bool = False
