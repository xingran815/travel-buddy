import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.llm.factory import get_provider

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"
ASPECTS_CACHE = CACHE_DIR / "aspects.json"
PROS_CONS_CACHE = CACHE_DIR / "pros_cons.json"
PRICE_LEVEL_CACHE = CACHE_DIR / "price_level.json"

ASPECT_KEYS = (
    "atmosphere", "service", "value", "cleanliness",
    "view", "romantic", "noise", "kid_friendly", "quiet",
)


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_json_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_json_cache(path: Path, data: dict) -> None:
    _ensure_cache_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _reviews_signature(reviews: list[dict]) -> str:
    blob = "|".join(f"{r.get('rating', '')}:{(r.get('text') or '')[:60]}" for r in (reviews or [])[:5])
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


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
    if not free_form or not free_form.strip():
        return {}
    system = (
        "Extract structured travel preferences from a free-form user request. "
        "Output JSON with keys: cuisine (string or null), audience ('family'/'adult'/null), "
        "aspects (list of short tags such as 'romantic','view','quiet','rooftop'), "
        "near (string or null), price_level (1-4 or null). Use null when uncertain."
    )
    user = f"Language: {lang}\nRequest: {free_form}\nReturn only JSON."
    try:
        out = _chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
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


def rerank_top_k(
    places: list[dict],
    query: str | None,
    profile: str,
    prefs: dict | None = None,
    k_out: int = 5,
    lang: str = "en",
    budget=None,
) -> list[dict]:
    if len(places) <= 1:
        return places[:k_out]
    payload = {
        "query": query or "",
        "profile": profile,
        "prefs": prefs or {},
        "places": [_place_summary(p) for p in places],
        "k_out": k_out,
    }
    system = (
        "You re-rank place recommendations. Given a JSON payload with a user query, profile, "
        "preferences, and candidate places, choose the best k_out in preferred order. Each place "
        "carries score_breakdown, up to 3 top-rated review excerpts in good_reviews, and up to 3 "
        "lowest-rated review excerpts in bad_reviews. Read BOTH sides: a high overall rating with "
        "damaging bad_reviews (e.g. 'overpriced', 'dirty', 'rude staff', 'closed early') that "
        "match the user's stated priorities should drop in your ranking. A merely-OK rating whose "
        "bad_reviews are minor or off-topic should not. The rationale must mention the deciding "
        "pro or con in 1 short sentence. Output JSON: "
        "{\"order\": [{\"place_id\": str, \"rationale\": str}, ...]}. "
        f"Reply in the user's language ({lang})."
    )
    try:
        out = _chat_json(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.2,
            budget=budget,
        )
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


_RERANK_PROS_CONS_SYSTEM = (
    "You re-rank place recommendations AND summarize each chosen place. Given a JSON payload "
    "with a user query, profile, preferences, and candidate places, choose the best k_out in "
    "preferred order. Each place carries score_breakdown, up to 3 top-rated review excerpts in "
    "good_reviews, and up to 3 lowest-rated review excerpts in bad_reviews. Read BOTH sides: "
    "a high overall rating with damaging bad_reviews (e.g. 'overpriced', 'dirty', 'rude staff', "
    "'closed early') that match the user's stated priorities should drop in your ranking. "
    "A merely-OK rating whose bad_reviews are minor or off-topic should not. "
    "For each chosen place, also produce 2 short pros and 2 short cons (≤ 12 words each), "
    "grounded in good_reviews and bad_reviews. The rationale must mention the deciding pro or "
    "con in 1 short sentence. Output JSON: "
    "{\"order\": [{\"place_id\": str, \"rationale\": str, "
    "\"pros\": [str, str], \"cons\": [str, str]}, ...]}. "
    "Reply in the user's language ({lang})."
)


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
    payload = {
        "query": query or "",
        "profile": profile,
        "prefs": prefs or {},
        "places": [_place_summary(p) for p in places],
        "k_out": k_out,
    }
    system = _RERANK_PROS_CONS_SYSTEM.replace("{lang}", lang)
    try:
        out = _chat_json(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.2,
            budget=budget,
        )
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
    cache = _load_json_cache(PROS_CONS_CACHE)
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
        key = f"{pid}:{lang}:{_reviews_signature(reviews)}"
        cache[key] = {"pros": pros, "cons": cons}
        cache_dirty = True
    if cache_dirty:
        try:
            _save_json_cache(PROS_CONS_CACHE, cache)
        except OSError:
            pass


def summarize_pros_cons(place: dict, lang: str = "en", budget=None) -> dict:
    reviews = place.get("reviews") or []
    if not reviews:
        return {"pros": [], "cons": []}
    _ensure_cache_dir()
    cache = _load_json_cache(PROS_CONS_CACHE)
    pid = place.get("place_id", "")
    sig = _reviews_signature(reviews)
    key = f"{pid}:{lang}:{sig}"
    if key in cache:
        return cache[key]
    excerpts = "\n".join(f"- ({r.get('rating', '')}/5) {(r.get('text') or '')[:240]}" for r in reviews[:5])
    system = (
        f"Summarize a place's user reviews into 2 short pros and 2 short cons. Reply in {lang}. "
        "Output JSON: {\"pros\": [str, str], \"cons\": [str, str]}. Each item ≤ 12 words."
    )
    user = f"Place: {place.get('name', '')}\nReviews:\n{excerpts}"
    try:
        out = _chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
            budget=budget,
        )
        result = {"pros": out.get("pros", [])[:3], "cons": out.get("cons", [])[:3]}
    except Exception:
        result = {"pros": [], "cons": []}
    cache[key] = result
    try:
        _save_json_cache(PROS_CONS_CACHE, cache)
    except OSError:
        pass
    return result


def estimate_price_level(place: dict, budget=None) -> int | None:
    """Estimate Google price_level (1-4) from review text when Google omits it.

    Returns None when reviews give no signal or the LLM call fails.
    """
    reviews = place.get("reviews") or []
    if not reviews:
        return None
    _ensure_cache_dir()
    cache = _load_json_cache(PRICE_LEVEL_CACHE)
    pid = place.get("place_id", "")
    sig = _reviews_signature(reviews)
    key = f"{pid}:{sig}"
    if key in cache:
        cached = cache[key]
        return cached.get("level") if isinstance(cached, dict) else None
    excerpts = "\n".join(
        f"- ({r.get('rating', '')}/5) {(r.get('text') or '')[:240]}" for r in reviews[:5]
    )
    system = (
        "Estimate Google Places price_level for a place using its user reviews. "
        "Scale: 1 = cheap, 2 = moderate, 3 = expensive, 4 = very expensive. "
        "Output JSON: {\"level\": int (1-4) or null, \"confidence\": \"low\"|\"med\"|\"high\"}. "
        "Return null level when reviews don't mention price or value."
    )
    user = f"Place: {place.get('name', '')}\nReviews:\n{excerpts}"
    try:
        out = _chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
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
    try:
        _save_json_cache(PRICE_LEVEL_CACHE, cache)
    except OSError:
        pass
    return result["level"]


def estimate_price_levels_batch(
    places: list[dict],
    budget=None,
    max_workers: int = 5,
) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    if not places:
        return out
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(estimate_price_level, p, budget): p.get("place_id", "")
            for p in places
        }
        for fut in as_completed(futures):
            out[futures[fut]] = fut.result()
    return out


def summarize_pros_cons_batch(
    places: list[dict],
    lang: str = "en",
    budget=None,
    max_workers: int = 5,
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not places:
        return out
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(summarize_pros_cons, p, lang, budget): p.get("place_id", "") for p in places}
        for fut in as_completed(futures):
            out[futures[fut]] = fut.result()
    return out


def extract_aspects(place: dict, budget=None) -> dict[str, float]:
    pid = place.get("place_id", "")
    if not pid:
        return {}
    _ensure_cache_dir()
    cache = _load_json_cache(ASPECTS_CACHE)
    cached = cache.get(pid)
    n_now = place.get("user_ratings_total") or 0
    if cached:
        n_prev = cached.get("_n", 0)
        if n_prev and abs(n_now - n_prev) / max(n_prev, 1) < 0.10:
            return {k: v for k, v in cached.items() if not k.startswith("_")}

    reviews = (place.get("reviews") or [])[:5]
    excerpts = "\n".join(f"- {(r.get('text') or '')[:200]}" for r in reviews)
    system = (
        "Tag a place with aspect scores 0..1 based on name, types, and review excerpts. "
        f"Aspects to score: {', '.join(ASPECT_KEYS)}. Output JSON: a flat object mapping aspect "
        "→ float in [0, 1]. Unknown aspects: 0.5."
    )
    user = f"Name: {place.get('name', '')}\nTypes: {place.get('types', [])}\nReviews:\n{excerpts or '(none)'}"
    try:
        out = _chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            budget=budget,
        )
        result = {k: float(out.get(k, 0.5)) for k in ASPECT_KEYS}
    except Exception:
        result = {}
    if result:
        cache[pid] = {**result, "_n": n_now}
        try:
            _save_json_cache(ASPECTS_CACHE, cache)
        except OSError:
            pass
    return result


def load_aspects_cache() -> dict[str, dict[str, float]]:
    raw = _load_json_cache(ASPECTS_CACHE)
    return {pid: {k: v for k, v in vals.items() if not k.startswith("_")} for pid, vals in raw.items()}
