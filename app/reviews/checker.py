"""Orchestrates the place-recommendation pipeline:
parse query → locate → search → score → fetch details → LLM rerank/summarize."""

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
    _fetch_details_batch, get_client, DEFAULT_D_HALF_KM, _make_search_grid,
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
    """Return the top-N recommended places for a region.

    Runs the full pipeline: optionally LLM-parse the free-form ``query``, geocode
    the region into search points, search each place type, score and rank the
    candidates, fetch details, and optionally LLM-rerank/summarize the result.
    """
    parsed_prefs: dict = {}
    if llm_parse and query:
        cuisine, audience, aspects, parsed_prefs = _merge_parsed_prefs(
            query, lang, cuisine, audience, aspects,
        )

    search_types = place_types or [place_type]
    if budget is not None and max_price is None:
        max_price = _budget_to_max_price(budget)

    client = get_client()
    hits_before, misses_before = client.hits, client.misses
    timings: dict[str, float] = {}
    t_total = time.perf_counter()

    t0 = time.perf_counter()
    center, d_half, search_points = _resolve_search_points(region, location, radius)
    timings["geocode"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    all_places = _search_all_types(
        region, search_types, max_pages=max_pages, min_price=min_price,
        max_price=max_price, search_points=search_points,
    )
    timings["search"] = time.perf_counter() - t0

    all_places = _deduplicate(all_places)
    if indoor_outdoor:
        all_places = [
            p for p in all_places
            if factors.infer_indoor_outdoor(p.get("types")) in (indoor_outdoor, None)
        ]
    weights = get_profile(profile, has_cuisine=bool(cuisine), has_audience=bool(audience))
    aspects_cache = _load_aspects_cache(aspects)

    t0 = time.perf_counter()
    scored = _score_all(
        all_places, weights=weights, center=center, cuisine=cuisine, audience=audience,
        budget=budget, people=people, d_half=d_half, aspects=aspects,
        aspects_cache=aspects_cache, user_profile=user_profile,
    )
    timings["score"] = time.perf_counter() - t0

    k_in = max(top_n, top_n + 5) if llm_rerank else top_n
    top = scored[:k_in]

    def emit(n_details):
        _emit_timing(
            timings, total=time.perf_counter() - t_total, n_types=len(search_types),
            n_details=n_details, cache_hits=client.hits - hits_before,
            cache_misses=client.misses - misses_before,
        )

    if not include_details:
        emit(0)
        return top[:top_n]

    place_ids = [t["place_id"] for t in top]
    t0 = time.perf_counter()
    details_map = _fetch_details_batch(place_ids)
    timings["details"] = time.perf_counter() - t0
    results = _merge_details(top, details_map)

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
    results = _apply_llm_rerank_and_summary(
        results, query=query, profile=profile, cuisine=cuisine, audience=audience,
        people=people, budget=budget, aspects=aspects, indoor_outdoor=indoor_outdoor,
        vibe=vibe, parsed_prefs=parsed_prefs, llm_rerank=llm_rerank,
        llm_summarize=llm_summarize, top_n=top_n, lang=lang,
    )
    timings["llm"] = time.perf_counter() - t0

    emit(len(place_ids))
    return results


def _merge_parsed_prefs(query, lang, cuisine, audience, aspects):
    """LLM-parse the query and backfill blank cuisine/audience/aspects.

    Returns ``(cuisine, audience, aspects, parsed_prefs)``."""
    from app.llm.recommender import parse_query
    parsed_prefs = parse_query(query, lang=lang) or {}
    if not cuisine and parsed_prefs.get("cuisine"):
        cuisine = parsed_prefs["cuisine"]
    if not audience and parsed_prefs.get("audience"):
        audience = parsed_prefs["audience"]
    if not aspects and parsed_prefs.get("aspects"):
        aspects = parsed_prefs["aspects"]
    return cuisine, audience, aspects, parsed_prefs


def _resolve_search_points(region, location, radius):
    """Resolve where to search, returning ``(center, d_half, search_points)``.

    Uses an explicit ``location`` if given, otherwise geocodes ``region`` into a
    grid of ``(point, radius)`` probes for geographic diversity."""
    if location is not None:
        search_points = [(location, radius)] if radius else []
        return location, DEFAULT_D_HALF_KM, search_points
    center, d_half, search_radius_m = _geocode_region(region)
    if center is not None and search_radius_m is not None:
        return center, d_half, _make_search_grid(center, search_radius_m)
    return center, d_half, []


def _load_aspects_cache(aspects):
    """Load the cached aspect scores when aspects are requested, else ``{}``."""
    if not aspects:
        return {}
    try:
        from app.llm.recommender import load_aspects_cache
        return load_aspects_cache()
    except Exception:
        return {}


def _merge_details(top, details_map):
    """Overlay fetched detail fields onto each scored place, keeping score metadata."""
    score_keys = ("score", "score_breakdown", "score_raw", "audience_tag", "distance_km", "d_half_km")
    results = []
    for t in top:
        detail = details_map.get(t["place_id"], {}) or {}
        merged = {**t, **{k: v for k, v in detail.items() if v not in (None, "", [], {})}}
        for key in score_keys:
            merged[key] = t[key]
        results.append(merged)
    return results


def _apply_llm_rerank_and_summary(
    results, *, query, profile, cuisine, audience, people, budget, aspects,
    indoor_outdoor, vibe, parsed_prefs, llm_rerank, llm_summarize, top_n, lang,
):
    """Apply LLM reranking and/or pros/cons summaries, returning the final list."""
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
            return rerank_with_pros_cons(
                results, query=query, profile=profile, prefs=prefs, k_out=top_n, lang=lang,
            )
        from app.llm.recommender import rerank_top_k
        return rerank_top_k(
            results, query=query, profile=profile, prefs=prefs, k_out=top_n, lang=lang,
        )

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


def _search_all_types(
    region: str,
    types: list[str],
    *,
    max_pages: int,
    min_price: int | None,
    max_price: int | None,
    search_points: list[tuple[tuple[float, float], int]],
) -> list[dict]:
    """Search every (place type × search point) combination and concatenate.

    Builds one search task per type and grid point (or one text search per type
    when there are no points), running them concurrently — up to 10 at a time —
    since each is an independent Places API call. Results are returned unmerged;
    ``_deduplicate`` collapses the overlap from neighbouring grid points."""
    tasks = []
    if search_points:
        for pt in types:
            for loc, rad in search_points:
                tasks.append((pt, loc, rad))
    else:
        for pt in types:
            tasks.append((pt, None, None))

    if len(tasks) == 1:
        pt, loc, rad = tasks[0]
        return search_places(
            region, place_type=pt, max_pages=max_pages,
            min_price=min_price, max_price=max_price,
            location=loc, radius=rad,
        )
    workers = min(len(tasks), 10)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [
            ex.submit(
                search_places, region, place_type=pt, max_pages=max_pages,
                min_price=min_price, max_price=max_price,
                location=loc, radius=rad,
            )
            for pt, loc, rad in tasks
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
    """Print a one-line per-stage timing + cache-hit breakdown to stderr."""
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
    """Recommend places for each category id, returning ``{category_id: [places]}``.

    ``category_ids`` drives type selection, so ``place_type``/``place_types``/``top_n``
    may not be passed through ``shared_kwargs``."""
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
