import math
import time

ADULT_TYPES = {"bar", "night_club", "liquor_store", "casino"}
FAMILY_TYPES = {"amusement_park", "aquarium", "zoo", "park", "museum", "tourist_attraction"}
ADULT_KEYS = {"bar", "pub", "lounge", "club", "cocktail"}
FAMILY_KEYS = {"family", "kids", "children", "playground"}

CUISINE_KEYWORDS: dict[str, set[str]] = {
    "turkish": {"turkish", "kebap", "kebab", "köfte", "lahmacun", "pide", "meze", "ocakbaşı"},
    "italian": {"italian", "pizza", "pasta", "trattoria", "osteria", "ristorante"},
    "japanese": {"japanese", "sushi", "ramen", "izakaya", "yakitori"},
    "chinese": {"chinese", "dim sum", "wok", "dumpling"},
    "indian": {"indian", "curry", "tandoor", "biryani"},
    "mexican": {"mexican", "taco", "burrito", "taqueria"},
    "french": {"french", "bistro", "brasserie", "patisserie"},
    "mediterranean": {"mediterranean", "greek", "lebanese", "falafel", "hummus", "shawarma"},
    "seafood": {"seafood", "fish", "oyster", "balık"},
    "vegetarian": {"vegetarian", "vegan", "plant-based"},
    "steakhouse": {"steakhouse", "steak", "grill"},
    "cafe": {"cafe", "café", "coffee", "kafe"},
    "dessert": {"dessert", "patisserie", "bakery", "pastane"},
}

NEUTRAL_PLACE_TYPES = {"restaurant", "food", "cafe", "meal_takeaway", "meal_delivery"}


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _bayesian(rating: float, count: int, C: int = 25, M: float = 3.5) -> float:
    return (count / (count + C)) * rating + (C / (count + C)) * M


def quality_score(rating: float, review_count: int) -> float:
    raw = _bayesian(rating or 0.0, review_count or 0)
    return max(0.0, min(1.0, raw / 5.0))


def volume_score(review_count: int) -> float:
    if not review_count or review_count <= 0:
        return 0.0
    return min(1.0, math.log10(review_count + 1) / math.log10(5001))


def distance_score(place_latlng: tuple[float, float] | None, center: tuple[float, float] | None, d_half: float = 3.0) -> float:
    if place_latlng is None or center is None:
        return 0.5
    d_km = haversine(center, place_latlng)
    return math.exp(-d_km / d_half)


def cost_fit(price_level: int | None, budget: float | None, people: int = 2) -> float:
    if price_level is None:
        return 0.5
    target = _budget_to_target_price(budget, people)
    if target is None:
        return 0.5
    over = max(0, price_level - target)
    return max(0.0, 1.0 - 0.4 * over)


def _budget_to_target_price(budget: float | None, people: int = 2) -> int | None:
    if budget is None or people <= 0:
        return None
    per_person = budget / people
    if per_person < 25:
        return 1
    if per_person < 60:
        return 2
    if per_person < 120:
        return 3
    return 4


def recency_score(reviews: list[dict], now: float | None = None) -> float:
    if not reviews:
        return 0.5
    now_ts = now if now is not None else time.time()
    weights = []
    for rev in reviews:
        t = rev.get("time")
        if t is None:
            continue
        age_days = max(0.0, (now_ts - t) / 86400.0)
        weights.append(math.exp(-age_days / 365.0))
    if not weights:
        return 0.5
    return sum(weights) / len(weights)


def sentiment_score(reviews: list[dict], fallback: float = 0.5) -> float:
    if not reviews:
        return fallback
    vals = []
    for rev in reviews:
        r = rev.get("rating")
        if r is None:
            continue
        vals.append(max(0.0, min(1.0, (r - 1) / 4.0)))
    if not vals:
        return fallback
    return sum(vals) / len(vals)


def infer_audience(types: list[str] | None, name: str = "") -> str:
    types_set = {str(t).lower() for t in (types or [])}
    name_lower = (name or "").lower()
    adult_hit = bool(types_set & ADULT_TYPES) or any(k in name_lower for k in ADULT_KEYS)
    family_hit = bool(types_set & FAMILY_TYPES) or any(k in name_lower for k in FAMILY_KEYS)
    if adult_hit:
        return "adult"
    if family_hit:
        return "family"
    return "neutral"


def audience_score(place_audience: str, preference: str | None) -> float:
    if preference is None:
        return 0.5
    if place_audience == preference:
        return 1.0
    if place_audience == "neutral":
        return 0.5
    return 0.0


def cuisine_score(types: list[str] | None, name: str, preference: str | None) -> float:
    if not preference:
        return 0.5
    pref = preference.lower().strip()
    types_set = {str(t).lower() for t in (types or [])}
    name_lower = (name or "").lower()

    keywords = CUISINE_KEYWORDS.get(pref, {pref})

    if any(k in name_lower for k in keywords):
        return 1.0
    if any(k in t for t in types_set for k in keywords):
        return 1.0
    if types_set & NEUTRAL_PLACE_TYPES:
        return 0.5
    return 0.0
