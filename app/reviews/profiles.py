FACTOR_KEYS = (
    "quality",
    "volume",
    "distance",
    "cost",
    "recency",
    "sentiment",
    "audience",
    "cuisine",
)

PROFILES: dict[str, dict[str, float]] = {
    "balanced": {"quality": 0.25, "volume": 0.10, "distance": 0.15, "cost": 0.15, "recency": 0.10, "sentiment": 0.10, "audience": 0.10, "cuisine": 0.05},
    "family":   {"quality": 0.20, "volume": 0.05, "distance": 0.15, "cost": 0.10, "recency": 0.05, "sentiment": 0.10, "audience": 0.30, "cuisine": 0.05},
    "adult":    {"quality": 0.20, "volume": 0.05, "distance": 0.10, "cost": 0.10, "recency": 0.10, "sentiment": 0.10, "audience": 0.30, "cuisine": 0.05},
    "foodie":   {"quality": 0.25, "volume": 0.10, "distance": 0.05, "cost": 0.05, "recency": 0.10, "sentiment": 0.15, "audience": 0.05, "cuisine": 0.25},
    "budget":   {"quality": 0.20, "volume": 0.10, "distance": 0.10, "cost": 0.35, "recency": 0.05, "sentiment": 0.10, "audience": 0.05, "cuisine": 0.05},
}

DEFAULT_PROFILE = "balanced"

for _name, _weights in PROFILES.items():
    _missing = set(FACTOR_KEYS) - set(_weights.keys())
    assert not _missing, f"Profile {_name!r} missing factors: {_missing}"
    _total = sum(_weights.values())
    assert abs(_total - 1.0) < 1e-9, f"Profile {_name!r} weights sum to {_total}, expected 1.0"


def get_profile(
    name: str | None = None,
    has_cuisine: bool = True,
    has_audience: bool = True,
) -> dict[str, float]:
    key = name or DEFAULT_PROFILE
    if key not in PROFILES:
        raise ValueError(f"Unknown profile {name!r}. Choices: {sorted(PROFILES.keys())}")
    weights = dict(PROFILES[key])

    redistribute = 0.0
    if not has_cuisine:
        redistribute += weights["cuisine"]
        weights["cuisine"] = 0.0
    if not has_audience:
        redistribute += weights["audience"]
        weights["audience"] = 0.0

    if redistribute > 0:
        weights["quality"] += redistribute

    return weights
