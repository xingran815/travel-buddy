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
