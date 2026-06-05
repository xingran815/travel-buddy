"""Batch scoring driver: score, scale, sort, and patch missing prices.

Wraps ``app/reviews/scoring.composite_score`` over a list of candidate places.
Scores and breakdowns are scaled from the internal ``0–1`` range to the
user-facing ``0–5`` range here, results are sorted best-first, and
``fill_missing_prices_and_rescore`` does a second LLM-assisted pass to recover
``price_level`` for places Google left blank.
"""

from app.reviews import factors
from app.reviews.scoring import composite_score


def score_all(
    all_places: list[dict],
    *,
    weights: dict[str, float],
    center,
    cuisine,
    audience,
    budget,
    people: int,
    d_half: float,
    aspects,
    aspects_cache: dict[str, dict[str, float]],
    user_profile,
) -> list[dict]:
    """Score every candidate, attach scaled fields, and sort best-first.

    Each returned place is the original dict plus ``score`` (0–5),
    ``score_breakdown`` and ``score_raw`` (scaled per-factor values),
    ``audience_tag``, ``distance_km`` from ``center``, and the ``d_half_km`` used
    for distance decay. ``aspects_cache`` supplies per-place LLM aspect scores
    keyed by ``place_id``."""
    scored = []
    for p in all_places:
        result = composite_score(
            p, weights=weights, center=center, cuisine=cuisine, audience=audience,
            budget=budget, people=people, d_half=d_half, aspects=aspects,
            place_aspects=aspects_cache.get(p.get("place_id", "")),
            user_profile=user_profile,
        )
        distance_km = None
        if center and p.get("lat") is not None and p.get("lng") is not None:
            distance_km = round(factors.haversine(center, (p["lat"], p["lng"])), 2)
        scored.append({
            **p,
            "score": round(result["total"] * 5.0, 2),
            "score_breakdown": {k: round(v * 5.0, 3) for k, v in result["breakdown"].items()},
            "score_raw": {k: round(v, 3) for k, v in result["raw"].items()},
            "audience_tag": result["audience_tag"],
            "distance_km": distance_km,
            "d_half_km": round(d_half, 2),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def fill_missing_prices_and_rescore(
    results: list[dict],
    *,
    weights: dict[str, float],
    center,
    cuisine,
    audience,
    budget,
    people: int,
    d_half: float,
    aspects,
    aspects_cache: dict[str, dict[str, float]],
    user_profile,
) -> None:
    """Estimate missing price levels via the LLM, then rescore in place.

    Finds results that have reviews but no Google ``price_level``, asks
    ``estimate_price_levels_batch`` to infer one (1–4) from the review text,
    marks them ``price_level_source="llm"``, and recomputes ``score`` /
    breakdowns for just those places before re-sorting. Mutates ``results``;
    no-op when nothing is missing a price."""
    needing = [p for p in results if p.get("price_level") is None and p.get("reviews")]
    if not needing:
        return
    from app.llm.recommender import estimate_price_levels_batch
    estimates = estimate_price_levels_batch(needing)
    updated_ids = set()
    for p in results:
        pid = p.get("place_id", "")
        est = estimates.get(pid)
        if est is not None and p.get("price_level") is None:
            p["price_level"] = est
            p["price_level_source"] = "llm"
            updated_ids.add(pid)
    if not updated_ids:
        return
    for p in results:
        if p.get("place_id") not in updated_ids:
            continue
        rescored = composite_score(
            p, weights=weights, center=center, cuisine=cuisine, audience=audience,
            budget=budget, people=people, d_half=d_half, aspects=aspects,
            place_aspects=aspects_cache.get(p.get("place_id", "")),
            user_profile=user_profile,
        )
        p["score"] = round(rescored["total"] * 5.0, 2)
        p["score_breakdown"] = {k: round(v * 5.0, 3) for k, v in rescored["breakdown"].items()}
        p["score_raw"] = {k: round(v, 3) for k, v in rescored["raw"].items()}
        p["audience_tag"] = rescored["audience_tag"]
    results.sort(key=lambda x: x["score"], reverse=True)
