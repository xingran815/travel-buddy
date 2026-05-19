from app.reviews import factors
from app.reviews.categories import get_category
from app.reviews.profiles import get_profile, DEFAULT_PROFILE
from app.reviews.scoring import composite_score
from app.reviews.search import (
    search_places, _deduplicate, _geocode_region, _budget_to_max_price,
    _fetch_details_batch, DEFAULT_D_HALF_KM,
)




def recommend_places(
    region: str,
    place_type: str = "restaurant",
    place_types: list[str] | None = None,
    top_n: int = 5,
    max_pages: int = 1,
    min_price: int | None = None,
    max_price: int | None = None,
    budget: float | None = None,
    location: tuple[float, float] | None = None,
    radius: int | None = None,
    include_details: bool = True,
    profile: str = DEFAULT_PROFILE,
    cuisine: str | None = None,
    audience: str | None = None,
    people: int = 2,
    query: str | None = None,
    aspects: list[str] | None = None,
    llm_parse: bool = False,
    llm_rerank: bool = False,
    llm_summarize: bool = False,
    llm_aspects: bool = False,
    lang: str = "en",
    user_profile=None,
) -> list[dict]:
    parsed_prefs: dict = {}
    if llm_parse and query:
        from app.llm.recommender import parse_query
        parsed_prefs = parse_query(query, lang=lang) or {}
        if not cuisine and parsed_prefs.get("cuisine"):
            cuisine = parsed_prefs["cuisine"]
        if not audience and parsed_prefs.get("audience"):
            audience = parsed_prefs["audience"]
        if not aspects and parsed_prefs.get("aspects"):
            aspects = parsed_prefs["aspects"]

    types = place_types or [place_type]
    if budget is not None and max_price is None:
        max_price = _budget_to_max_price(budget)

    all_places = []
    for pt in types:
        places = search_places(
            region,
            place_type=pt,
            max_pages=max_pages,
            min_price=min_price,
            max_price=max_price,
            location=location,
            radius=radius,
        )
        all_places.extend(places)

    all_places = _deduplicate(all_places)

    if location is not None:
        center = location
        d_half = DEFAULT_D_HALF_KM
    else:
        center, d_half = _geocode_region(region)
    weights = get_profile(profile, has_cuisine=bool(cuisine), has_audience=bool(audience))

    aspects_cache: dict[str, dict[str, float]] = {}
    if aspects:
        try:
            from app.llm.recommender import load_aspects_cache
            aspects_cache = load_aspects_cache()
        except Exception:
            aspects_cache = {}

    scored = []
    for p in all_places:
        result = composite_score(
            p,
            weights=weights,
            center=center,
            cuisine=cuisine,
            audience=audience,
            budget=budget,
            people=people,
            d_half=d_half,
            aspects=aspects,
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

    k_in = max(top_n, top_n + 5) if llm_rerank else top_n
    top = scored[:k_in]

    if not include_details:
        return top[:top_n]

    place_ids = [t["place_id"] for t in top]
    details_map = _fetch_details_batch(place_ids)

    results = []
    for t in top:
        detail = details_map.get(t["place_id"], {}) or {}
        merged = {**t, **{k: v for k, v in detail.items() if v not in (None, "", [], {})}}
        merged["score"] = t["score"]
        merged["score_breakdown"] = t["score_breakdown"]
        merged["score_raw"] = t["score_raw"]
        merged["audience_tag"] = t["audience_tag"]
        merged["distance_km"] = t["distance_km"]
        merged["d_half_km"] = t["d_half_km"]
        results.append(merged)

    if llm_aspects and aspects:
        from app.llm.recommender import extract_aspects
        for p in results:
            extract_aspects(p)

    if llm_rerank and len(results) > 1:
        from app.llm.recommender import rerank_top_k
        prefs = {
            "cuisine": cuisine,
            "audience": audience,
            "people": people,
            "budget": budget,
            "aspects": aspects,
            **{k: v for k, v in parsed_prefs.items() if k != "raw"},
        }
        results = rerank_top_k(results, query=query, profile=profile, prefs=prefs, k_out=top_n, lang=lang)
    else:
        results = results[:top_n]

    if llm_summarize and results:
        from app.llm.recommender import summarize_pros_cons_batch
        summaries = summarize_pros_cons_batch(results, lang=lang)
        for p in results:
            s = summaries.get(p.get("place_id", ""))
            if s:
                p["pros"] = s.get("pros", [])
                p["cons"] = s.get("cons", [])

    return results


def recommend_by_categories(
    region: str,
    category_ids: list[str],
    top_n_per: int = 5,
    **shared_kwargs,
) -> dict[str, list[dict]]:
    if not category_ids:
        return {}
    # Disallow conflicting per-category args
    for blocked in ("place_type", "place_types", "top_n"):
        if blocked in shared_kwargs:
            raise TypeError(f"recommend_by_categories does not accept {blocked!r}; category_ids drives type selection")
    out: dict[str, list[dict]] = {}
    for cat_id in category_ids:
        category = get_category(cat_id)
        out[cat_id] = recommend_places(
            region,
            place_type=category.google_types[0],
            place_types=list(category.google_types),
            top_n=top_n_per,
            **shared_kwargs,
        )
    return out
