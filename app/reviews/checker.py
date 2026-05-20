import time
from concurrent.futures import ThreadPoolExecutor

import click

from app.reviews import factors
from app.reviews.categories import get_category
from app.reviews.pipeline import (
    score_all as _score_all,
    fill_missing_prices_and_rescore as _fill_missing_prices_and_rescore,
)
from app.reviews.profiles import get_profile, DEFAULT_PROFILE
from app.reviews.search import (
    search_places, _deduplicate, _geocode_region, _budget_to_max_price,
    _fetch_details_batch, get_client, DEFAULT_D_HALF_KM,
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
    indoor_outdoor: str | None = None,
    vibe: str | None = None,
    estimate_missing_price: bool = False,
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

    client = get_client()
    hits_before, misses_before = client.hits, client.misses
    timings: dict[str, float] = {}
    t_total = time.perf_counter()

    t0 = time.perf_counter()
    all_places = _search_all_types(
        region, types, max_pages=max_pages, min_price=min_price,
        max_price=max_price, location=location, radius=radius,
    )
    timings["search"] = time.perf_counter() - t0

    all_places = _deduplicate(all_places)

    if indoor_outdoor:
        all_places = [
            p for p in all_places
            if factors.infer_indoor_outdoor(p.get("types")) in (indoor_outdoor, None)
        ]

    t0 = time.perf_counter()
    if location is not None:
        center = location
        d_half = DEFAULT_D_HALF_KM
    else:
        center, d_half = _geocode_region(region)
    timings["geocode"] = time.perf_counter() - t0
    weights = get_profile(profile, has_cuisine=bool(cuisine), has_audience=bool(audience))

    aspects_cache: dict[str, dict[str, float]] = {}
    if aspects:
        try:
            from app.llm.recommender import load_aspects_cache
            aspects_cache = load_aspects_cache()
        except Exception:
            aspects_cache = {}

    t0 = time.perf_counter()
    scored = _score_all(
        all_places, weights=weights, center=center, cuisine=cuisine, audience=audience,
        budget=budget, people=people, d_half=d_half, aspects=aspects,
        aspects_cache=aspects_cache, user_profile=user_profile,
    )
    timings["score"] = time.perf_counter() - t0

    k_in = max(top_n, top_n + 5) if llm_rerank else top_n
    top = scored[:k_in]

    if not include_details:
        _emit_timing(
            timings, total=time.perf_counter() - t_total,
            n_types=len(types), n_details=0,
            cache_hits=client.hits - hits_before,
            cache_misses=client.misses - misses_before,
        )
        return top[:top_n]

    place_ids = [t["place_id"] for t in top]
    t0 = time.perf_counter()
    details_map = _fetch_details_batch(place_ids)
    timings["details"] = time.perf_counter() - t0

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

    t0 = time.perf_counter()
    if estimate_missing_price and budget is not None:
        _fill_missing_prices_and_rescore(
            results, weights=weights, center=center, cuisine=cuisine,
            audience=audience, budget=budget, people=people, d_half=d_half,
            aspects=aspects, aspects_cache=aspects_cache, user_profile=user_profile,
        )

    if llm_aspects and aspects:
        from app.llm.recommender import extract_aspects
        for p in results:
            extract_aspects(p)

    if llm_rerank and len(results) > 1:
        prefs = {
            "cuisine": cuisine,
            "audience": audience,
            "people": people,
            "budget": budget,
            "aspects": aspects,
            "indoor_outdoor": indoor_outdoor,
            "vibe": vibe,
            **{k: v for k, v in parsed_prefs.items() if k != "raw"},
        }
        if llm_summarize:
            from app.llm.recommender import rerank_with_pros_cons
            results = rerank_with_pros_cons(
                results, query=query, profile=profile, prefs=prefs, k_out=top_n, lang=lang,
            )
        else:
            from app.llm.recommender import rerank_top_k
            results = rerank_top_k(
                results, query=query, profile=profile, prefs=prefs, k_out=top_n, lang=lang,
            )
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
    timings["llm"] = time.perf_counter() - t0

    _emit_timing(
        timings, total=time.perf_counter() - t_total,
        n_types=len(types), n_details=len(place_ids),
        cache_hits=client.hits - hits_before,
        cache_misses=client.misses - misses_before,
    )
    return results


def _search_all_types(
    region: str,
    types: list[str],
    *,
    max_pages: int,
    min_price: int | None,
    max_price: int | None,
    location: tuple[float, float] | None,
    radius: int | None,
) -> list[dict]:
    if len(types) == 1:
        return search_places(
            region, place_type=types[0], max_pages=max_pages,
            min_price=min_price, max_price=max_price,
            location=location, radius=radius,
        )
    workers = min(len(types), 6)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [
            ex.submit(
                search_places, region, place_type=pt, max_pages=max_pages,
                min_price=min_price, max_price=max_price,
                location=location, radius=radius,
            )
            for pt in types
        ]
        out: list[dict] = []
        for f in futures:
            out.extend(f.result())
    return out


def _emit_timing(
    timings: dict[str, float],
    *,
    total: float,
    n_types: int,
    n_details: int,
    cache_hits: int,
    cache_misses: int,
) -> None:
    parts = [
        f"geocode {timings.get('geocode', 0):.1f}s",
        f"search {timings.get('search', 0):.1f}s ({n_types}x)",
        f"details {timings.get('details', 0):.1f}s ({n_details})",
        f"score {timings.get('score', 0):.2f}s",
        f"llm {timings.get('llm', 0):.1f}s",
        f"total {total:.1f}s",
        f"cache: {cache_hits} hit / {cache_misses} miss",
    ]
    click.echo("[timing] " + " | ".join(parts), err=True)


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
