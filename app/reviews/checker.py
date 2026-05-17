import googlemaps
from app.config import GOOGLE_MAPS_API_KEY


def get_client():
    return googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def search_places(region: str, place_type: str = "restaurant") -> list[dict]:
    gmaps = get_client()
    results = gmaps.places(query=f"{place_type} in {region}")
    places = []
    for p in results.get("results", []):
        places.append({
            "name": p.get("name", ""),
            "place_id": p.get("place_id", ""),
            "rating": p.get("rating", 0.0),
            "user_ratings_total": p.get("user_ratings_total", 0),
            "address": p.get("formatted_address", ""),
            "types": p.get("types", []),
        })
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


def recommend_places(region: str, place_type: str = "restaurant", top_n: int = 5) -> list[dict]:
    places = search_places(region, place_type)
    scored = []
    for p in places:
        score = p["rating"] * min(p["user_ratings_total"], 100) / 100
        scored.append({**p, "score": round(score, 2)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_n]
    results = []
    for t in top:
        details = get_place_details(t["place_id"])
        results.append(details)
    return results
