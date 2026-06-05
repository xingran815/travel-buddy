"""Scoring profiles: the per-factor weight vectors that shape rankings.

A *profile* (``balanced``, ``foodie``, ``budget``, ``atmosphere``) is a set of
weights over ``FACTOR_KEYS`` that sums to ``1.0``. ``_BASE_PROFILES`` holds the
human-authored weights; every profile is then rebalanced by ``_with_history`` to
carve out a fixed slice for the personalisation ``history`` factor. The
module-load asserts guard the invariant that each profile covers all factors and
sums to one. ``get_profile`` applies request-time adjustments (dropping unused
cuisine/audience weight into ``quality``, boosting audience when the user states
a preference) and renormalises.
"""

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
        "quality": 0.27, "volume": 0.10, "distance": 0.05, "cost": 0.15,
        "recency": 0.10, "sentiment": 0.15, "audience": 0.10, "cuisine": 0.05, "aspects": 0.03,
    },
    "foodie": {
        "quality": 0.24, "volume": 0.10, "distance": 0.03, "cost": 0.05,
        "recency": 0.10, "sentiment": 0.15, "audience": 0.05, "cuisine": 0.25, "aspects": 0.03,
    },
    "budget": {
        "quality": 0.20, "volume": 0.10, "distance": 0.05, "cost": 0.35,
        "recency": 0.05, "sentiment": 0.12, "audience": 0.05, "cuisine": 0.05, "aspects": 0.03,
    },
    "atmosphere": {
        "quality": 0.22, "volume": 0.03, "distance": 0.05, "cost": 0.10,
        "recency": 0.05, "sentiment": 0.18, "audience": 0.10, "cuisine": 0.02, "aspects": 0.25,
    },
}

AUDIENCE_BOOST = 2.5


def _with_history(base: dict[str, float]) -> dict[str, float]:
    """Scale a base profile down by ``HISTORY_WEIGHT`` and add a history slice.

    Keeps the total at ``1.0`` while reserving a fixed share for the ``history``
    personalisation factor, which the hand-written base profiles omit."""
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
    """Return the (renormalised) weight vector for a named profile.

    When the request has no cuisine or audience preference, that factor's weight
    is folded into ``quality`` so it doesn't dilute the score with neutral 0.5s.
    When an audience *is* requested, its weight is boosted by ``AUDIENCE_BOOST``
    and the rest are shrunk proportionally, then everything is renormalised to
    sum to ``1.0``. Raises ``ValueError`` for an unknown profile name."""
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

    if has_audience and weights["audience"] > 0:
        aud = weights["audience"]
        new_aud = aud * AUDIENCE_BOOST
        diff = new_aud - aud
        other_total = sum(v for k, v in weights.items() if k != "audience")
        if other_total > 0:
            for k in list(weights.keys()):
                if k != "audience":
                    weights[k] = max(0.0, weights[k] - diff * (weights[k] / other_total))
            weights["audience"] = new_aud
            total = sum(weights.values())
            if total > 0:
                for k in weights:
                    weights[k] /= total

    return weights
