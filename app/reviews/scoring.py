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
) -> dict:
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
        "distance": factors.distance_score(place_latlng, center),
        "cost": factors.cost_fit(place.get("price_level"), budget, people),
        "recency": factors.recency_score(reviews, now=now),
        "sentiment": factors.sentiment_score(reviews, fallback=f_quality),
        "audience": factors.audience_score(place_audience, audience),
        "cuisine": factors.cuisine_score(place.get("types"), place.get("name", ""), cuisine),
    }

    breakdown = {k: weights.get(k, 0.0) * raw[k] for k in FACTOR_KEYS}
    total = sum(breakdown.values())

    return {
        "total": total,
        "breakdown": breakdown,
        "raw": raw,
        "audience_tag": place_audience,
    }
