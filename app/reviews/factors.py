"""Per-factor scoring functions for the recommendation engine.

Each ``*_score`` / ``*_fit`` function maps one signal about a place (rating,
review volume, distance, price, recency, sentiment, audience, cuisine, aspects,
or user history) onto a normalised ``0.0–1.0`` score, where higher is better.
``app/reviews/pipeline.py`` multiplies these by the profile weights from
``app/reviews/profiles.py`` to produce the composite score.

Two conventions run through the module:

* **Neutral default of ``0.5``** — when a factor cannot be evaluated (missing
  price, no location, no stated preference, unknown history) the function
  returns ``0.5`` so the factor neither helps nor hurts the place's ranking.
  ``history_score`` uses ``0.55`` for "no signal yet" to give never-seen places
  a hair's edge over places the user has explicitly rated as neutral.
* **Module-level keyword/type sets** (``ADULT_TYPES``, ``CUISINE_KEYWORDS``,
  ``INDOOR_TYPES`` …) drive the categorical inference used by
  ``infer_audience``, ``infer_indoor_outdoor`` and ``cuisine_score``.
"""

import math
import time

ADULT_TYPES = {"bar", "night_club", "liquor_store", "casino"}
FAMILY_TYPES = {"amusement_park", "aquarium", "zoo", "park", "museum", "tourist_attraction"}
ADULT_KEYS = {"bar", "pub", "lounge", "club", "cocktail"}
FAMILY_KEYS = {"family", "kids", "children", "playground"}

INDOOR_TYPES = {
    "museum", "art_gallery", "aquarium", "shopping_mall",
    "movie_theater", "bowling_alley", "spa", "gym", "library", "casino",
}
OUTDOOR_TYPES = {
    "park", "zoo", "amusement_park", "natural_feature",
    "campground", "stadium",
}

CUISINE_KEYWORDS: dict[str, set[str]] = {
    "turkish": {"turkish", "kebap", "kebab", "köfte", "lahmacun", "pide", "meze", "ocakbaşı"},
    "italian": {"italian", "pizza", "pasta", "trattoria", "osteria", "ristorante"},
    "japanese": {"japanese", "sushi", "ramen", "izakaya", "yakitori"},
    "chinese": {"chinese", "dim sum", "wok", "dumpling"},
    "indian": {"indian", "curry", "tandoor", "biryani"},
    "mexican": {"mexican", "taco", "burrito", "taqueria"},
    "french": {"french", "bistro", "brasserie", "patisserie"},
    "mediterranean": {"mediterranean", "greek", "lebanese", "falafel", "hummus", "shawarma"},
    "seafood": {"seafood", "fish", "oyster", "balık"},
    "vegetarian": {"vegetarian", "vegan", "plant-based"},
    "steakhouse": {"steakhouse", "steak", "grill"},
    "cafe": {"cafe", "café", "coffee", "kafe"},
    "dessert": {"dessert", "patisserie", "bakery", "pastane"},
}

NEUTRAL_PLACE_TYPES = {"restaurant", "food", "cafe", "meal_takeaway", "meal_delivery"}


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in kilometres between two ``(lat, lng)`` points."""
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _bayesian(rating: float, count: int, c_prior: int = 25, m_prior: float = 3.5) -> float:
    """Bayesian-adjusted rating that shrinks toward the prior mean ``m_prior``.

    Blends the observed ``rating`` with a prior of ``m_prior`` (3.5 stars)
    weighted as if it were ``c_prior`` (25) reviews. A place with few reviews is
    pulled toward 3.5; one with thousands is barely moved, so cold-start places
    with a lone 5-star review can't outrank well-reviewed favourites."""
    return (count / (count + c_prior)) * rating + (c_prior / (count + c_prior)) * m_prior


def quality_score(rating: float, review_count: int) -> float:
    """Bayesian rating normalised to ``0–1`` (the raw 0–5 average / 5)."""
    raw = _bayesian(rating or 0.0, review_count or 0)
    return max(0.0, min(1.0, raw / 5.0))


def volume_score(review_count: int) -> float:
    """Review-count confidence on a log scale, saturating near 5000 reviews."""
    if not review_count or review_count <= 0:
        return 0.0
    return min(1.0, math.log10(review_count + 1) / math.log10(5001))


def distance_score(
    place_latlng: tuple[float, float] | None,
    center: tuple[float, float] | None,
    d_half: float = 3.0,
) -> float:
    """Exponential proximity decay: ``exp(-distance_km / d_half)``.

    ``d_half`` is the half-life distance (km) at which the score falls to
    ``e^-1 ≈ 0.37``; the caller derives it from the geocoded region's viewport
    so the decay scales with how large the searched area is. Returns the neutral
    ``0.5`` when either point is unknown."""
    if place_latlng is None or center is None:
        return 0.5
    d_km = haversine(center, place_latlng)
    return math.exp(-d_km / d_half)


def cost_fit(price_level: int | None, budget: float | None, people: int = 2) -> float:
    """Score how well a place's price level fits the per-person budget.

    Places at or below the target price level (see ``_budget_to_target_price``)
    score ``1.0``; each level over budget costs ``0.4``. Returns ``0.5`` when the
    price level or budget is unknown."""
    if price_level is None:
        return 0.5
    target = _budget_to_target_price(budget, people)
    if target is None:
        return 0.5
    over = max(0, price_level - target)
    return max(0.0, 1.0 - 0.4 * over)


def _budget_to_target_price(budget: float | None, people: int = 2) -> int | None:
    """Soft scoring target: per-person spend → ideal Google price_level for
    cost_fit. Finer-grained than checker._budget_to_max_price (the hard
    pre-fetch cap)."""
    if budget is None or people <= 0:
        return None
    per_person = budget / people
    if per_person < 25:
        return 1
    if per_person < 60:
        return 2
    if per_person < 120:
        return 3
    return 4


def recency_score(reviews: list[dict], now: float | None = None) -> float:
    """Mean freshness of the supplied reviews, decaying over ~1 year.

    Each review contributes ``exp(-age_days / 365)``; the result is their
    average. Returns ``0.5`` when no reviews carry a timestamp."""
    if not reviews:
        return 0.5
    now_ts = now if now is not None else time.time()
    weights = []
    for rev in reviews:
        t = rev.get("time")
        if t is None:
            continue
        age_days = max(0.0, (now_ts - t) / 86400.0)
        weights.append(math.exp(-age_days / 365.0))
    if not weights:
        return 0.5
    return sum(weights) / len(weights)


def sentiment_score(reviews: list[dict], fallback: float = 0.5) -> float:
    """Average review rating rescaled to ``0–1`` (``(rating - 1) / 4``).

    A lightweight stand-in for true text sentiment based on the per-review star
    ratings. Returns ``fallback`` (usually the quality score) when no review
    carries a rating."""
    if not reviews:
        return fallback
    vals = []
    for rev in reviews:
        r = rev.get("rating")
        if r is None:
            continue
        vals.append(max(0.0, min(1.0, (r - 1) / 4.0)))
    if not vals:
        return fallback
    return sum(vals) / len(vals)


def infer_audience(types: list[str] | None, name: str = "") -> str:
    """Classify a place as ``"adult"``, ``"family"`` or ``"neutral"``.

    Matches the place's types and name against ``ADULT_TYPES``/``ADULT_KEYS``
    and ``FAMILY_TYPES``/``FAMILY_KEYS``; "adult" wins ties (a bar tagged as a
    tourist attraction is still adult)."""
    types_set = {str(t).lower() for t in (types or [])}
    name_lower = (name or "").lower()
    adult_hit = bool(types_set & ADULT_TYPES) or any(k in name_lower for k in ADULT_KEYS)
    family_hit = bool(types_set & FAMILY_TYPES) or any(k in name_lower for k in FAMILY_KEYS)
    if adult_hit:
        return "adult"
    if family_hit:
        return "family"
    return "neutral"


def infer_indoor_outdoor(types: list[str] | None) -> str | None:
    """Return ``"indoor"``/``"outdoor"`` from the place types, or ``None``."""
    types_set = {str(t).lower() for t in (types or [])}
    if types_set & INDOOR_TYPES:
        return "indoor"
    if types_set & OUTDOOR_TYPES:
        return "outdoor"
    return None


def audience_score(place_audience: str, preference: str | None) -> float:
    """Match an inferred audience against the user's preference.

    ``1.0`` on an exact match, ``0.5`` when the place is ``"neutral"`` or no
    preference was given, ``0.0`` on a mismatch."""
    if preference is None:
        return 0.5
    if place_audience == preference:
        return 1.0
    if place_audience == "neutral":
        return 0.5
    return 0.0


def aspects_score(place_aspects: dict[str, float] | None, requested: list[str] | None) -> float:
    """Average the LLM-extracted aspect scores for the requested aspects.

    ``place_aspects`` maps aspect name → ``0–1`` score (produced by
    ``app/llm/recommender.extract_aspects``). Returns the mean over the
    ``requested`` aspects that the place has scores for, or ``0.5`` when nothing
    was requested or no matching aspect scores exist."""
    if not requested:
        return 0.5
    if not place_aspects:
        return 0.5
    vals = []
    for asp in requested:
        v = place_aspects.get(asp.strip().lower())
        if v is None:
            continue
        vals.append(max(0.0, min(1.0, float(v))))
    if not vals:
        return 0.5
    return sum(vals) / len(vals)


def history_score(
    place_id: str,
    user_profile,
    now: float | None = None,
    decay_days: float = 180.0,
    saturation_k: float = 0.4,
) -> float:
    """Personalisation score from the user's past feedback on this place.

    Sums time-decayed ``liked`` (weighted by any 1–5 rating) and ``disliked``
    events — both live events and pre-compacted tallies — then squashes the net
    through a saturating curve into ``0–1`` around a neutral ``0.5``. Events
    decay with a ``decay_days`` (180-day) half-life so stale opinions fade.
    Returns ``0.55`` when the user has no history for the place (a slight edge
    over places they rated as a wash), and ``0.5`` when signals cancel out."""
    if user_profile is None or not place_id:
        return 0.55
    summary = user_profile.summary_for(place_id)
    if summary is None:
        return 0.55

    now_ts = now if now is not None else time.time()
    liked_weight = 0.0
    disliked_weight = 0.0
    for action, ts, rating in summary.events:
        age_days = max(0.0, (now_ts - ts) / 86400.0)
        decay = math.exp(-age_days / decay_days)
        if action == "liked":
            liked_weight += decay * ((rating / 5.0) if rating else 1.0)
        elif action == "disliked":
            disliked_weight += decay

    liked_weight += 0.5 * summary.compacted_liked
    disliked_weight += 0.5 * summary.compacted_disliked

    net = liked_weight - disliked_weight
    if abs(net) < 1e-9:
        if (liked_weight + disliked_weight) > 0 or summary.visited:
            return 0.5
        return 0.55
    if net > 0:
        return min(1.0, 0.5 + 0.5 * (1.0 - math.exp(-saturation_k * net)))
    return max(0.0, 0.5 - 0.5 * (1.0 - math.exp(-saturation_k * (-net))))


def cuisine_score(types: list[str] | None, name: str, preference: str | None) -> float:
    """Match a place against a preferred cuisine via keyword lookup.

    Expands ``preference`` through ``CUISINE_KEYWORDS`` (e.g. ``"italian"`` →
    pizza/pasta/trattoria…) and looks for any keyword in the name or types:
    ``1.0`` on a hit, ``0.5`` for a generic eatery (``NEUTRAL_PLACE_TYPES``) that
    might still fit, ``0.0`` otherwise. Returns ``0.5`` when no cuisine was
    requested."""
    if not preference:
        return 0.5
    pref = preference.lower().strip()
    types_set = {str(t).lower() for t in (types or [])}
    name_lower = (name or "").lower()

    keywords = CUISINE_KEYWORDS.get(pref, {pref})

    if any(k in name_lower for k in keywords):
        return 1.0
    if any(k in t for t in types_set for k in keywords):
        return 1.0
    if types_set & NEUTRAL_PLACE_TYPES:
        return 0.5
    return 0.0
