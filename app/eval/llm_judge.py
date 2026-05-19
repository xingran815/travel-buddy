import json

from app.llm.factory import get_provider


def _place_brief(p: dict) -> dict:
    reviews = (p.get("reviews") or [])[:2]
    return {
        "name": p.get("name", ""),
        "types": p.get("types", []),
        "rating": p.get("rating"),
        "n_reviews": p.get("user_ratings_total"),
        "price_level": p.get("price_level"),
        "distance_km": p.get("distance_km"),
        "audience_tag": p.get("audience_tag"),
        "review_excerpts": [(r.get("text") or "")[:160] for r in reviews],
    }


def judge(query: dict, results: list[dict], lang: str = "en", budget=None) -> dict:
    payload = {
        "query": query,
        "n_results": len(results),
        "results": [_place_brief(p) for p in results],
    }
    system = (
        "You are an evaluator for a place-recommendation system. Score the result list on four "
        "axes (1-10 integers): relevance to query/profile, diversity, coverage of options, "
        "freshness (newer reviews and currently-operating places). Then compute an overall "
        "(float average). Output JSON: "
        "{\"relevance\": int, \"diversity\": int, \"coverage\": int, \"freshness\": int, "
        "\"overall\": float, \"rationale\": short_string}. "
        f"Write rationale in {lang}."
    )
    user = json.dumps(payload, ensure_ascii=False)
    try:
        result = get_provider().chat_json(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
        )
        if budget is not None and result.usage is not None:
            budget.add_usage(result.usage)
        return _coerce_verdict(json.loads(result.text.strip()))
    except Exception as e:
        return {
            "relevance": 0, "diversity": 0, "coverage": 0,
            "freshness": 0, "overall": 0.0, "rationale": f"error: {e}",
        }


def _coerce_verdict(raw: dict) -> dict:
    def _int(v, default=5):
        try:
            return max(0, min(10, int(round(float(v)))))
        except (TypeError, ValueError):
            return default

    def _float(v, default=5.0):
        try:
            return max(0.0, min(10.0, float(v)))
        except (TypeError, ValueError):
            return default

    relevance = _int(raw.get("relevance"))
    diversity = _int(raw.get("diversity"))
    coverage = _int(raw.get("coverage"))
    freshness = _int(raw.get("freshness"))
    overall = raw.get("overall")
    if overall is None:
        overall = (relevance + diversity + coverage + freshness) / 4.0
    return {
        "relevance": relevance,
        "diversity": diversity,
        "coverage": coverage,
        "freshness": freshness,
        "overall": round(_float(overall, default=(relevance + diversity + coverage + freshness) / 4.0), 2),
        "rationale": (raw.get("rationale") or "")[:500],
    }
