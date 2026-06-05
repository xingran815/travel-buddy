"""Maps each place type to the preference prompts worth asking for it.

Drives the interactive recommend flow: a restaurant asks about cuisine/budget, a
museum about topic, a hotel about nights/rooms, etc. ``prompts_for_types`` merges
these when several types are selected at once.
"""

PROMPTS_BY_TYPE: dict[str, list[str]] = {
    "restaurant":         ["cuisine", "audience", "people", "budget"],
    "cafe":               ["cuisine", "audience", "people"],
    "museum":             ["topic", "audience", "people"],
    "lodging":            ["nights", "rooms", "amenities", "audience", "budget"],
    "tourist_attraction": ["audience", "indoor_outdoor", "time_required"],
    "bar":                ["audience", "vibe", "people"],
}

DEFAULT_PROMPTS: list[str] = ["audience", "people", "budget"]


def prompts_for_types(types: list[str] | None) -> list[str]:
    """Union (dedup, order-preserving) of prompts across selected types."""
    if not types:
        return list(DEFAULT_PROMPTS)
    seen: set[str] = set()
    out: list[str] = []
    for t in types:
        for p in PROMPTS_BY_TYPE.get(t, DEFAULT_PROMPTS):
            if p not in seen:
                seen.add(p)
                out.append(p)
    return out
