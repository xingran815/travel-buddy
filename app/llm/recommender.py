"""LLM recommendation helpers: query parsing, reranking, pros/cons and price-level
estimation, and aspect tagging. Prompts live in :mod:`app.llm.prompts`; the JSON
cache and review helpers in :mod:`app.llm.cache`."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.llm.cache import (
    format_review_excerpts,
    load_json_cache,
    reviews_signature,
    save_json_cache_safe,
)
from app.llm.factory import get_provider
from app.llm.prompts import (
    ASPECT_KEYS,
    EXTRACT_ASPECTS_SYSTEM,
    PARSE_QUERY_SYSTEM,
    PRICE_LEVEL_SYSTEM,
    RERANK_PROS_CONS_SYSTEM,
    RERANK_SYSTEM,
    SUMMARIZE_SYSTEM,
)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"
ASPECTS_CACHE = CACHE_DIR / "aspects.json"
PROS_CONS_CACHE = CACHE_DIR / "pros_cons.json"
PRICE_LEVEL_CACHE = CACHE_DIR / "price_level.json"


def _chat_json(messages: list[dict], temperature: float = 0.1, budget=None) -> dict:
    result = get_provider().chat_json(messages, temperature=temperature)
    if budget is not None and result.usage is not None:
        budget.add_usage(result.usage)
    text = (result.text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Strip Markdown fences if a provider returned them despite json mode
        cleaned = text.strip("`").lstrip("json").strip()
        return json.loads(cleaned)


def parse_query(free_form: str, lang: str = "en", budget=None) -> dict:
    """Parse a free-form request into structured prefs; ``{"raw": ...}`` on failure."""
    if not free_form or not free_form.strip():
        return {}
    user = f"Language: {lang}\nRequest: {free_form}\nReturn only JSON."
    try:
        out = _chat_json(
            [{"role": "system", "content": PARSE_QUERY_SYSTEM}, {"role": "user", "content": user}],
            temperature=0.1,
            budget=budget,
        )
    except Exception:
        return {"raw": free_form}
    out["raw"] = free_form
    return out


def _split_reviews_by_rating(
    reviews: list[dict], n_top: int = 3, n_bot: int = 3,
) -> tuple[list[dict], list[dict]]:
    with_text = [r for r in (reviews or []) if (r.get("text") or "").strip()]
    n = len(with_text)
    if n == 0:
        return [], []
    by_rating_desc = sorted(with_text, key=lambda r: r.get("rating") or 0, reverse=True)
    top_cap = n_top if n <= 1 else min(n_top, max(1, n - 1))
    top = by_rating_desc[:top_cap]
    top_ids = {id(r) for r in top}
    remaining = [r for r in with_text if id(r) not in top_ids]
    return top, sorted(remaining, key=lambda r: r.get("rating") or 0)[:n_bot]


def _excerpt(r: dict) -> dict:
    return {"rating": r.get("rating"), "text": (r.get("text") or "")[:240]}


def _place_summary(place: dict) -> dict:
    good, bad = _split_reviews_by_rating(place.get("reviews") or [])
    return {
        "place_id": place.get("place_id", ""),
        "name": place.get("name", ""),
        "types": place.get("types", []),
        "rating": place.get("rating"),
        "n_reviews": place.get("user_ratings_total"),
        "price_level": place.get("price_level"),
        "distance_km": place.get("distance_km"),
        "audience_tag": place.get("audience_tag"),
        "score_breakdown": place.get("score_breakdown"),
        "good_reviews": [_excerpt(r) for r in good],
        "bad_reviews": [_excerpt(r) for r in bad],
    }


def _rerank_payload(places, query, profile, prefs, k_out) -> dict:
    return {
        "query": query or "",
        "profile": profile,
        "prefs": prefs or {},
        "places": [_place_summary(p) for p in places],
        "k_out": k_out,
    }


def _rerank_chat(system: str, payload: dict, budget) -> dict:
    return _chat_json(
        [{"role": "system", "content": system},
         {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        temperature=0.2,
        budget=budget,
    )


def rerank_top_k(
    places: list[dict],
    query: str | None,
    profile: str,
    prefs: dict | None = None,
    k_out: int = 5,
    lang: str = "en",
    budget=None,
) -> list[dict]:
    """Reorder candidates by LLM judgment, returning the best ``k_out`` places."""
    if len(places) <= 1:
        return places[:k_out]
    payload = _rerank_payload(places, query, profile, prefs, k_out)
    try:
        out = _rerank_chat(RERANK_SYSTEM.replace("{lang}", lang), payload, budget)
    except Exception:
        return places[:k_out]
    return _apply_rerank_order(out.get("order") or [], places, k_out)


def _apply_rerank_order(order: list[dict], places: list[dict], k_out: int) -> list[dict]:
    by_id = {p.get("place_id"): p for p in places}
    reranked = []
    for entry in order[:k_out]:
        pid = entry.get("place_id")
        if pid in by_id:
            p = dict(by_id[pid])
            p["llm_rationale"] = entry.get("rationale", "")
            p["llm_rank"] = len(reranked) + 1
            reranked.append(p)
    seen = {p.get("place_id") for p in reranked}
    for p in places:
        if p.get("place_id") not in seen and len(reranked) < k_out:
            reranked.append(p)
    return reranked


def rerank_with_pros_cons(
    places: list[dict],
    query: str | None,
    profile: str,
    prefs: dict | None = None,
    k_out: int = 5,
    lang: str = "en",
    budget=None,
) -> list[dict]:
    """Rerank candidates and emit pros/cons in a single LLM call."""
    if len(places) <= 1:
        return places[:k_out]
    payload = _rerank_payload(places, query, profile, prefs, k_out)
    try:
        out = _rerank_chat(RERANK_PROS_CONS_SYSTEM.replace("{lang}", lang), payload, budget)
    except Exception:
        return rerank_top_k(places, query, profile, prefs, k_out, lang, budget)
    order = out.get("order") or []
    reranked = _apply_rerank_order(order, places, k_out)
    _attach_and_cache_pros_cons(reranked, order, places, lang)
    missing = [p for p in reranked if not p.get("pros") and not p.get("cons")]
    if missing:
        backfill = summarize_pros_cons_batch(missing, lang=lang, budget=budget)
        for p in missing:
            s = backfill.get(p.get("place_id", ""))
            if s:
                p["pros"] = s.get("pros", [])
                p["cons"] = s.get("cons", [])
    return reranked


def _attach_and_cache_pros_cons(
    reranked: list[dict], order: list[dict], original_places: list[dict], lang: str,
) -> None:
    entries_by_id = {e.get("place_id"): e for e in order if isinstance(e, dict)}
    reviews_by_id = {p.get("place_id"): (p.get("reviews") or []) for p in original_places}
    cache = load_json_cache(PROS_CONS_CACHE)
    cache_dirty = False
    for place in reranked:
        pid = place.get("place_id")
        entry = entries_by_id.get(pid)
        if not entry:
            continue
        pros = [str(x) for x in (entry.get("pros") or [])[:3]]
        cons = [str(x) for x in (entry.get("cons") or [])[:3]]
        place["pros"] = pros
        place["cons"] = cons
        reviews = reviews_by_id.get(pid) or []
        if not reviews:
            continue
        key = f"{pid}:{lang}:{reviews_signature(reviews)}"
        cache[key] = {"pros": pros, "cons": cons}
        cache_dirty = True
    if cache_dirty:
        save_json_cache_safe(PROS_CONS_CACHE, cache)


def summarize_pros_cons(place: dict, lang: str = "en", budget=None) -> dict:
    """Return ``{"pros": [...], "cons": [...]}`` for a place, cached by review fingerprint."""
    reviews = place.get("reviews") or []
    if not reviews:
        return {"pros": [], "cons": []}
    cache = load_json_cache(PROS_CONS_CACHE)
    pid = place.get("place_id", "")
    key = f"{pid}:{lang}:{reviews_signature(reviews)}"
    if key in cache:
        return cache[key]
    user = f"Place: {place.get('name', '')}\nReviews:\n{format_review_excerpts(reviews)}"
    try:
        out = _chat_json(
            [{"role": "system", "content": SUMMARIZE_SYSTEM.replace("{lang}", lang)},
             {"role": "user", "content": user}],
            temperature=0.2,
            budget=budget,
        )
        result = {"pros": out.get("pros", [])[:3], "cons": out.get("cons", [])[:3]}
    except Exception:
        result = {"pros": [], "cons": []}
    cache[key] = result
    save_json_cache_safe(PROS_CONS_CACHE, cache)
    return result


def estimate_price_level(place: dict, budget=None) -> int | None:
    """Estimate Google price_level (1-4) from review text when Google omits it.

    Returns None when reviews give no signal or the LLM call fails.
    """
    reviews = place.get("reviews") or []
    if not reviews:
        return None
    cache = load_json_cache(PRICE_LEVEL_CACHE)
    pid = place.get("place_id", "")
    key = f"{pid}:{reviews_signature(reviews)}"
    if key in cache:
        cached = cache[key]
        return cached.get("level") if isinstance(cached, dict) else None
    user = f"Place: {place.get('name', '')}\nReviews:\n{format_review_excerpts(reviews)}"
    try:
        out = _chat_json(
            [{"role": "system", "content": PRICE_LEVEL_SYSTEM}, {"role": "user", "content": user}],
            temperature=0.1,
            budget=budget,
        )
    except Exception:
        return None
    level = out.get("level")
    if isinstance(level, int) and 1 <= level <= 4:
        result = {"level": level, "confidence": out.get("confidence", "low")}
    else:
        result = {"level": None, "confidence": "low"}
    cache[key] = result
    save_json_cache_safe(PRICE_LEVEL_CACHE, cache)
    return result["level"]


def _run_per_place(places: list[dict], task, max_workers: int = 5) -> dict:
    """Run ``task(place)`` over places concurrently, keyed by place_id."""
    out: dict = {}
    if not places:
        return out
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(task, p): p.get("place_id", "") for p in places}
        for fut in as_completed(futures):
            out[futures[fut]] = fut.result()
    return out


def estimate_price_levels_batch(places, budget=None, max_workers: int = 5) -> dict[str, int | None]:
    """Estimate price levels for many places concurrently, keyed by place_id."""
    return _run_per_place(places, lambda p: estimate_price_level(p, budget), max_workers)


def summarize_pros_cons_batch(places, lang: str = "en", budget=None, max_workers: int = 5) -> dict[str, dict]:
    """Summarize pros/cons for many places concurrently, keyed by place_id."""
    return _run_per_place(places, lambda p: summarize_pros_cons(p, lang, budget), max_workers)


def extract_aspects(place: dict, budget=None) -> dict[str, float]:
    """Score a place across ASPECT_KEYS (0..1), cached until its review count drifts >10%."""
    pid = place.get("place_id", "")
    if not pid:
        return {}
    cache = load_json_cache(ASPECTS_CACHE)
    cached = cache.get(pid)
    n_now = place.get("user_ratings_total") or 0
    if cached:
        # Reuse the cached scores unless the review count moved by >10%.
        n_prev = cached.get("_n", 0)
        if n_prev and abs(n_now - n_prev) / max(n_prev, 1) < 0.10:
            return {k: v for k, v in cached.items() if not k.startswith("_")}

    excerpts = format_review_excerpts(place.get("reviews") or [], maxlen=200, with_rating=False)
    user = f"Name: {place.get('name', '')}\nTypes: {place.get('types', [])}\nReviews:\n{excerpts or '(none)'}"
    try:
        out = _chat_json(
            [{"role": "system", "content": EXTRACT_ASPECTS_SYSTEM}, {"role": "user", "content": user}],
            temperature=0.1,
            budget=budget,
        )
        result = {k: float(out.get(k, 0.5)) for k in ASPECT_KEYS}
    except Exception:
        result = {}
    if result:
        cache[pid] = {**result, "_n": n_now}
        save_json_cache_safe(ASPECTS_CACHE, cache)
    return result


def load_aspects_cache() -> dict[str, dict[str, float]]:
    """Load all cached aspect scores, stripping bookkeeping keys (``_n``)."""
    raw = load_json_cache(ASPECTS_CACHE)
    return {pid: {k: v for k, v in vals.items() if not k.startswith("_")} for pid, vals in raw.items()}
