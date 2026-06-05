"""Google Places access layer: geocoding, search-grid construction, and lookups.

This module is the only one that talks to the Google Maps API. It wraps the
``googlemaps`` client in ``app/places/cache.CachedGmaps`` for transparent SQLite
caching and exposes the pieces the orchestrator (``app/reviews/checker.py``)
composes:

* ``_geocode_region`` turns a region name into a centre point plus a viewport-
  derived distance-decay half-life (``d_half``) and search radius.
* ``_make_search_grid`` spreads that radius into up to five overlapping probe
  points so a single large region doesn't return only city-centre results.
* ``search_places`` runs one nearby/text search; ``get_place_details`` and
  ``_fetch_details_batch`` enrich the chosen candidates with reviews/contact info.

The geocode-then-``places_nearby`` ordering is deliberate: searching by viewport
radius around the geocoded centre gives far better geographic spread than a bare
``"<type> in <region>"`` text query.
"""

import math
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import click
import googlemaps
from app.config import GOOGLE_MAPS_API_KEY
from app.places.cache import CachedGmaps
from app.reviews import factors


_CLIENT_LOCK = threading.Lock()
_CLIENT_HOLDER: list[CachedGmaps] = []


def get_client() -> CachedGmaps:
    """Return the process-wide cached Maps client, building it once on demand.

    Double-checked locking keeps a single ``CachedGmaps`` shared across the
    worker threads used for parallel search/detail calls."""
    if not _CLIENT_HOLDER:
        with _CLIENT_LOCK:
            if not _CLIENT_HOLDER:
                _CLIENT_HOLDER.append(CachedGmaps(googlemaps.Client(key=GOOGLE_MAPS_API_KEY)))
    return _CLIENT_HOLDER[0]


def _deduplicate(places: list[dict]) -> list[dict]:
    """Drop duplicate places by ``place_id`` and by normalised name.

    Overlapping grid points and chains return the same venue repeatedly; names
    are lower-cased and stripped of any ``"#<branch>"`` suffix before comparison,
    keeping the first occurrence."""
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
    """Keep places within the ``[min_price, max_price]`` Google price levels.

    A ``min_price`` excludes places with an unknown price level; ``max_price``
    keeps unknowns (so budget filtering doesn't silently drop unpriced venues
    that later get an LLM-estimated level)."""
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
    """Hard cap: total budget to max Google price_level for the price-filter
    pre-fetch. Coarser than the per-person scoring target in factors._budget_to_target_price."""
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


def _candidate_summary(c: dict) -> str:
    """Format a geocode candidate as ``"address (lat, lng)"`` for prompts/logs."""
    geom = c.get("geometry") or {}
    loc = geom.get("location") or {}
    addr = c.get("formatted_address") or "?"
    try:
        lat = float(loc.get("lat"))
        lng = float(loc.get("lng"))
        return f"{addr} ({lat:.4f}, {lng:.4f})"
    except (TypeError, ValueError):
        return addr


def _pick_geocode_candidate(candidates: list[dict], region: str) -> dict:
    """Choose among ambiguous geocode matches for ``region``.

    Interactively prompts the user when stdin is a TTY; otherwise logs the
    ambiguity and falls back to Google's first (highest-ranked) candidate."""
    if len(candidates) <= 1:
        return candidates[0]
    if not sys.stdin.isatty():
        click.echo(
            f"[geocode] {len(candidates)} matches for {region!r}; using: {_candidate_summary(candidates[0])}",
            err=True,
        )
        return candidates[0]
    click.echo(f"Multiple regions matched {region!r}. Pick one:")
    for i, c in enumerate(candidates, 1):
        click.echo(f"  {i}. {_candidate_summary(c)}")
    while True:
        try:
            choice = click.prompt("Choice", type=int, default=1)
        except click.Abort:
            return candidates[0]
        if 1 <= choice <= len(candidates):
            return candidates[choice - 1]


MAX_SEARCH_RADIUS_M = 50_000


def _geocode_region(region: str) -> tuple[tuple[float, float] | None, float, int | None]:
    """Geocode a region into ``(center, d_half_km, search_radius_m)``.

    Derives both tuning knobs from the result's viewport: ``d_half`` (distance-
    decay half-life) is a third of the viewport diagonal, and the search radius
    is half the diagonal, capped at ``MAX_SEARCH_RADIUS_M`` (50 km). When no
    viewport is available it falls back to ``DEFAULT_D_HALF_KM`` and no radius
    (callers then do a plain text search). Any API/parse error degrades to
    ``(None, DEFAULT_D_HALF_KM, None)`` rather than raising."""
    try:
        gmaps = get_client()
        results = gmaps.geocode(region)
        if not results:
            return None, DEFAULT_D_HALF_KM, None
        chosen = _pick_geocode_candidate(results, region)
        geom = chosen["geometry"]
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
            d_half = max(0.5, diag / 3.0)
            search_radius_m = int(min(diag * 1000 / 2, MAX_SEARCH_RADIUS_M))
        else:
            d_half = DEFAULT_D_HALF_KM
            search_radius_m = None
        return center, d_half, search_radius_m
    except Exception:
        return None, DEFAULT_D_HALF_KM, None


_GRID_MIN_RADIUS_M = 5000


def _make_search_grid(
    center: tuple[float, float],
    search_radius_m: int,
) -> list[tuple[tuple[float, float], int]]:
    """Build the ``(point, radius)`` probes for a region's nearby searches.

    Small regions (≤ ``_GRID_MIN_RADIUS_M``) get a single centre probe. Larger
    ones get a 5-point cross — centre plus four corners offset by 40% of the
    radius — so coverage doesn't collapse to the city centre. Offsets convert
    metres to degrees using the standard ~111.32 km/degree, adjusting longitude
    by ``cos(latitude)``. Each probe uses half the region radius."""
    sub_radius = int(min(search_radius_m * 0.5, MAX_SEARCH_RADIUS_M))
    if search_radius_m <= _GRID_MIN_RADIUS_M:
        return [(center, sub_radius)]
    offset_m = search_radius_m * 0.4
    lat, lng = center
    dlat = offset_m / 111_320
    dlng = offset_m / (111_320 * math.cos(math.radians(lat)))
    return [
        (center, sub_radius),
        ((lat + dlat, lng + dlng), sub_radius),
        ((lat + dlat, lng - dlng), sub_radius),
        ((lat - dlat, lng + dlng), sub_radius),
        ((lat - dlat, lng - dlng), sub_radius),
    ]


def search_places(
    region: str,
    place_type: str = "restaurant",
    max_pages: int = 1,
    min_price: int | None = None,
    max_price: int | None = None,
    location: tuple[float, float] | None = None,
    radius: int | None = None,
) -> list[dict]:
    """Search one place type and return normalised candidate dicts.

    Uses ``places_nearby`` (viewport-bounded) when a ``location`` and ``radius``
    are given, otherwise a ``"<type> in <region>"`` text search. Paginates up to
    ``max_pages`` (Google requires a ~2s pause before each next-page token),
    drops permanently-closed venues, normalises lat/lng, and applies the
    price-level filter. Each result is flattened to the common candidate schema
    consumed by the scorer."""
    gmaps = get_client()
    query = f"{place_type} in {region}"
    all_raw = []
    token = None

    for _ in range(max_pages):
        if token:
            time.sleep(2)
            results = gmaps.places(query=query, page_token=token)
        elif location and radius:
            results = gmaps.places_nearby(location=location, radius=radius, type=place_type)
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
    """Fetch enriched details for one place: reviews, contact info, geometry.

    Requests only the fields the pipeline uses and returns them flattened, with
    up to five reviews normalised to ``{author, rating, text, time, language}``.
    Used to enrich the top candidates after scoring (a Details call is billed
    separately from search, so only the shortlist is fetched)."""
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


def _fetch_details_batch(place_ids: list[str], max_workers: int | None = None) -> dict[str, dict]:
    """Fetch details for many places concurrently, keyed by ``place_id``.

    Runs up to 10 ``get_place_details`` calls in parallel (each is independent
    and I/O-bound). Returns ``{}`` for an empty input."""
    if not place_ids:
        return {}
    workers = max_workers if max_workers is not None else min(len(place_ids), 10)
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(get_place_details, pid): pid for pid in place_ids}
        for future in as_completed(futures):
            pid = futures[future]
            results[pid] = future.result()
    return results
