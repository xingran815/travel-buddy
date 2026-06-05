"""Combine the individual factor scores into one weighted composite score.

This is the single place that knows the full factor vector. ``composite_score``
calls every ``app/reviews/factors.py`` scorer for one place, multiplies each by
its profile weight, and returns the weighted total plus the per-factor
``breakdown`` (weight × raw) and the unweighted ``raw`` values. The batch driver
that scales these to the 0–5 range and sorts lives in ``app/reviews/pipeline.py``.
"""

from app.reviews import factors
from app.reviews.profiles import FACTOR_KEYS


def composite_score(
    place: dict,
    weights: dict[str, float],
    center: tuple[float, float] | None = None,
    cuisine: str | None = None,
    audience: str | None = None,
    budget: float | None = None,
    people: int = 2,
    now: float | None = None,
    d_half: float = 3.0,
    aspects: list[str] | None = None,
    place_aspects: dict[str, float] | None = None,
    user_profile=None,
) -> dict:
    """Score one place and return ``{total, breakdown, raw, audience_tag}``.

    ``total`` is the weighted sum of all ten factors (still on the ``0–1``
    scale); ``breakdown`` maps each factor to its weighted contribution and
    ``raw`` to its unweighted score. Only factors present in ``FACTOR_KEYS``
    contribute, so a weight dict missing a key simply drops that factor."""
    place_latlng = None
    lat = place.get("lat")
    lng = place.get("lng")
    if lat is not None and lng is not None:
        place_latlng = (lat, lng)

    place_audience = factors.infer_audience(place.get("types"), place.get("name", ""))
    reviews = place.get("reviews", []) or []

    f_quality = factors.quality_score(place.get("rating", 0.0), place.get("user_ratings_total", 0))
    raw = {
        "quality": f_quality,
        "volume": factors.volume_score(place.get("user_ratings_total", 0)),
        "distance": factors.distance_score(place_latlng, center, d_half=d_half),
        "cost": factors.cost_fit(place.get("price_level"), budget, people),
        "recency": factors.recency_score(reviews, now=now),
        "sentiment": factors.sentiment_score(reviews, fallback=f_quality),
        "audience": factors.audience_score(place_audience, audience),
        "cuisine": factors.cuisine_score(place.get("types"), place.get("name", ""), cuisine),
        "aspects": factors.aspects_score(place_aspects, aspects),
        "history": factors.history_score(place.get("place_id", ""), user_profile, now=now),
    }

    breakdown = {k: weights.get(k, 0.0) * raw[k] for k in FACTOR_KEYS}
    total = sum(breakdown.values())

    return {
        "total": total,
        "breakdown": breakdown,
        "raw": raw,
        "audience_tag": place_audience,
    }
