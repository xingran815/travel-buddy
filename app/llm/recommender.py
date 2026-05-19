import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.llm.factory import get_provider

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"
ASPECTS_CACHE = CACHE_DIR / "aspects.json"
PROS_CONS_CACHE = CACHE_DIR / "pros_cons.json"

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


def _place_summary(place: dict) -> dict:
    reviews = (place.get("reviews") or [])[:3]
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
        "review_excerpts": [(r.get("text") or "")[:200] for r in reviews],
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
        "preferences, and a list of candidate places (each with score_breakdown and short review "
        "excerpts), choose the best k_out in preferred order. Output JSON: "
        "{\"order\": [{\"place_id\": str, \"rationale\": str}, ...]}. Rationale must be 1 short sentence "
        f"in the user's language ({lang})."
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
        order = out.get("order") or []
        by_id = {p.get("place_id"): p for p in places}
        reranked = []
        for entry in order[:k_out]:
            pid = entry.get("place_id")
            if pid in by_id:
                p = dict(by_id[pid])
                p["llm_rationale"] = entry.get("rationale", "")
                p["llm_rank"] = len(reranked) + 1
                reranked.append(p)
        # Append any leftover places from original order that weren't selected
        seen = {p.get("place_id") for p in reranked}
        for p in places:
            if p.get("place_id") not in seen and len(reranked) < k_out:
                reranked.append(p)
        return reranked
    except Exception:
        return places[:k_out]


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
