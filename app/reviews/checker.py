import time
import googlemaps
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import GOOGLE_MAPS_API_KEY


def get_client():
    return googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


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
        places.append({
            "name": p.get("name", ""),
            "place_id": p.get("place_id", ""),
            "rating": p.get("rating", 0.0),
            "user_ratings_total": p.get("user_ratings_total", 0),
            "address": p.get("formatted_address", p.get("vicinity", "")),
            "types": p.get("types", []),
            "price_level": p.get("price_level"),
        })

    places = _filter_by_price(places, min_price, max_price)
    return places


def get_place_details(place_id: str) -> dict:
    gmaps = get_client()
    result = gmaps.place(place_id=place_id, fields=["name", "rating", "review", "formatted_address", "price_level", "international_phone_number", "website"])
    detail = result.get("result", {})
    reviews = []
    for r in detail.get("reviews", []):
        reviews.append({
            "author": r.get("author_name", ""),
            "rating": r.get("rating", 0),
            "text": r.get("text", ""),
        })
    return {
        "name": detail.get("name", ""),
        "rating": detail.get("rating", 0.0),
        "address": detail.get("formatted_address", ""),
        "price_level": detail.get("price_level", None),
        "phone": detail.get("international_phone_number", ""),
        "website": detail.get("website", ""),
        "reviews": reviews,
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
) -> list[dict]:
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

    scored = []
    for p in all_places:
        score = _bayesian_score(p["rating"], p["user_ratings_total"])
        scored.append({**p, "score": round(score, 2)})
    scored.sort(key=lambda x: x["score"], reverse=True)

    top = scored[:top_n]

    if not include_details:
        return top

    place_ids = [t["place_id"] for t in top]
    details_map = _fetch_details_batch(place_ids)

    results = []
    for t in top:
        detail = details_map.get(t["place_id"], {})
        results.append(detail)
    return results
