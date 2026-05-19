FACTOR_KEYS = (
    "quality",
    "volume",
    "distance",
    "cost",
    "recency",
    "sentiment",
    "audience",
    "cuisine",
    "aspects",
    "history",
)

HISTORY_WEIGHT = 0.06

_BASE_PROFILES: dict[str, dict[str, float]] = {
    "balanced": {
        "quality": 0.22, "volume": 0.10, "distance": 0.15, "cost": 0.15,
        "recency": 0.10, "sentiment": 0.10, "audience": 0.10, "cuisine": 0.05, "aspects": 0.03,
    },
    "family": {
        "quality": 0.17, "volume": 0.05, "distance": 0.15, "cost": 0.10,
        "recency": 0.05, "sentiment": 0.10, "audience": 0.30, "cuisine": 0.05, "aspects": 0.03,
    },
    "adult": {
        "quality": 0.17, "volume": 0.05, "distance": 0.10, "cost": 0.10,
        "recency": 0.10, "sentiment": 0.10, "audience": 0.30, "cuisine": 0.05, "aspects": 0.03,
    },
    "foodie": {
        "quality": 0.22, "volume": 0.10, "distance": 0.05, "cost": 0.05,
        "recency": 0.10, "sentiment": 0.15, "audience": 0.05, "cuisine": 0.25, "aspects": 0.03,
    },
    "budget": {
        "quality": 0.17, "volume": 0.10, "distance": 0.10, "cost": 0.35,
        "recency": 0.05, "sentiment": 0.10, "audience": 0.05, "cuisine": 0.05, "aspects": 0.03,
    },
    "aspect-heavy": {
        "quality": 0.20, "volume": 0.03, "distance": 0.10, "cost": 0.10,
        "recency": 0.05, "sentiment": 0.15, "audience": 0.10, "cuisine": 0.02, "aspects": 0.25,
    },
}


def _with_history(base: dict[str, float]) -> dict[str, float]:
    factor = 1.0 - HISTORY_WEIGHT
    weights = {k: v * factor for k, v in base.items()}
    weights["history"] = HISTORY_WEIGHT
    return weights


PROFILES: dict[str, dict[str, float]] = {name: _with_history(w) for name, w in _BASE_PROFILES.items()}

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
