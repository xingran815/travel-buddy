import time
import googlemaps
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import GOOGLE_MAPS_API_KEY
from app.places.cache import CachedGmaps
from app.reviews import factors
from app.reviews.profiles import get_profile, DEFAULT_PROFILE
from app.reviews.scoring import composite_score


def get_client():
    return CachedGmaps(googlemaps.Client(key=GOOGLE_MAPS_API_KEY))


def _bayesian_score(rating: float, review_count: int, C: int = 25, M: float = 3.5) -> float:
    return (review_count / (review_count + C)) * rating + (C / (review_count + C)) * M


def _deduplicate(places: list[dict]) -> list[dict]:
    seen_ids = set()
    seen_names = set()
    unique = []
    for p in places:
        if p["place_id"] in seen_ids:
            continue
        norm_name = p["name"].lower().split("#")[0].strip()
        if norm_name in seen_names:
            continue
        seen_ids.add(p["place_id"])
        seen_names.add(norm_name)
        unique.append(p)
    return unique


def _filter_by_price(places: list[dict], min_price: int | None = None, max_price: int | None = None) -> list[dict]:
    filtered = []
    for p in places:
        price = p.get("price_level")
        if min_price is not None and (price is None or price < min_price):
            continue
        if max_price is not None and (price is not None and price > max_price):
            continue
        filtered.append(p)
    return filtered


def _budget_to_max_price(budget: float | None) -> int | None:
    if budget is None:
        return None
    if budget < 300:
        return 1
    if budget < 700:
        return 2
    if budget < 1500:
        return 3
    return None


DEFAULT_D_HALF_KM = 3.0


def _geocode_region(region: str) -> tuple[tuple[float, float] | None, float]:
    try:
        gmaps = get_client()
        result = gmaps.geocode(region)
        if not result:
            return None, DEFAULT_D_HALF_KM
        geom = result[0]["geometry"]
        loc = geom["location"]
        center = (float(loc["lat"]), float(loc["lng"]))
        viewport = geom.get("viewport") or {}
        ne = viewport.get("northeast") or {}
        sw = viewport.get("southwest") or {}
        if "lat" in ne and "lng" in ne and "lat" in sw and "lng" in sw:
            diag = factors.haversine(
                (float(ne["lat"]), float(ne["lng"])),
                (float(sw["lat"]), float(sw["lng"])),
            )
            d_half = max(0.5, diag / 6.0)
        else:
            d_half = DEFAULT_D_HALF_KM
        return center, d_half
    except Exception:
        return None, DEFAULT_D_HALF_KM


def search_places(
    region: str,
    place_type: str = "restaurant",
    max_pages: int = 1,
    min_price: int | None = None,
    max_price: int | None = None,
    location: tuple[float, float] | None = None,
    radius: int | None = None,
) -> list[dict]:
    gmaps = get_client()
    query = f"{place_type} in {region}"
    all_raw = []
    token = None

    for _ in range(max_pages):
        if token:
            time.sleep(2)
            results = gmaps.places(query=query, page_token=token)
        elif location and radius:
            results = gmaps.places_nearby(location=location, radius=radius, type=place_type, keyword=region)
        else:
            results = gmaps.places(query=query)
        all_raw.extend(results.get("results", []))
        token = results.get("next_page_token")
        if not token:
            break

    places = []
    for p in all_raw:
        if p.get("business_status") == "CLOSED_PERMANENTLY":
            continue
        geom = (p.get("geometry") or {}).get("location") or {}
        lat = geom.get("lat")
        lng = geom.get("lng")
        try:
            lat = float(lat) if lat is not None else None
            lng = float(lng) if lng is not None else None
        except (TypeError, ValueError):
            lat = None
            lng = None
        places.append({
            "name": p.get("name", ""),
            "place_id": p.get("place_id", ""),
            "rating": p.get("rating", 0.0),
            "user_ratings_total": p.get("user_ratings_total", 0),
            "address": p.get("formatted_address", p.get("vicinity", "")),
            "types": p.get("types", []),
            "price_level": p.get("price_level"),
            "lat": lat,
            "lng": lng,
            "business_status": p.get("business_status"),
        })

    places = _filter_by_price(places, min_price, max_price)
    return places


def get_place_details(place_id: str) -> dict:
    gmaps = get_client()
    result = gmaps.place(
        place_id=place_id,
        fields=[
            "name",
            "rating",
            "review",
            "formatted_address",
            "price_level",
            "international_phone_number",
            "website",
            "geometry/location",
            "business_status",
            "user_ratings_total",
            "type",
        ],
    )
    detail = result.get("result", {})
    reviews = []
    for r in detail.get("reviews", []):
        reviews.append({
            "author": r.get("author_name", ""),
            "rating": r.get("rating", 0),
            "text": r.get("text", ""),
            "time": r.get("time"),
            "language": r.get("language"),
        })
    geom = (detail.get("geometry") or {}).get("location") or {}
    lat = geom.get("lat")
    lng = geom.get("lng")
    try:
        lat = float(lat) if lat is not None else None
        lng = float(lng) if lng is not None else None
    except (TypeError, ValueError):
        lat = None
        lng = None
    return {
        "name": detail.get("name", ""),
        "rating": detail.get("rating", 0.0),
        "address": detail.get("formatted_address", ""),
        "price_level": detail.get("price_level", None),
        "phone": detail.get("international_phone_number", ""),
        "website": detail.get("website", ""),
        "reviews": reviews,
        "lat": lat,
        "lng": lng,
        "business_status": detail.get("business_status"),
        "user_ratings_total": detail.get("user_ratings_total"),
        "types": detail.get("types", []),
    }


def _fetch_details_batch(place_ids: list[str], max_workers: int = 5) -> dict[str, dict]:
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_place_details, pid): pid for pid in place_ids}
        for future in as_completed(futures):
            pid = futures[future]
            results[pid] = future.result()
    return results


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
