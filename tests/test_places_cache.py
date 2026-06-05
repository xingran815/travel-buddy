"""Tests for the SQLite places cache: key generation, TTL expiry, and the CachedGmaps wrapper."""

from unittest.mock import MagicMock

import pytest

from app.places.cache import (
    CachedGmaps,
    DETAILS_TTL,
    GEOCODE_TTL,
    PlacesCache,
    SEARCH_TTL,
)


@pytest.fixture
def cache(tmp_path):
    return PlacesCache(tmp_path / "places.sqlite")


@pytest.fixture
def fake_client():
    client = MagicMock()
    client.geocode.return_value = [{"formatted_address": "Istanbul, TR", "geometry": {"location": {"lat": 41.0, "lng": 29.0}}}]
    client.places.return_value = {"results": [{"name": "Mikla"}], "next_page_token": None}
    client.places_nearby.return_value = {"results": [{"name": "Nearby"}]}
    client.place.return_value = {"result": {"name": "Mikla", "rating": 4.6}}
    return client


class TestPlacesCacheStore:
    def test_round_trips_response(self, cache):
        key = PlacesCache.make_key("geocode", ("Istanbul",), {})
        cache.set(key, [{"a": 1}], ttl=60)
        assert cache.get(key) == [{"a": 1}]

    def test_miss_returns_none(self, cache):
        assert cache.get("missing-key") is None

    def test_expired_entry_returns_none(self, cache):
        key = PlacesCache.make_key("place", (), {"place_id": "X"})
        cache.set(key, {"r": 1}, ttl=10, now=1000.0)
        assert cache.get(key, now=1011.0) is None
        assert cache.get(key, now=1009.9) == {"r": 1}

    def test_make_key_is_kwargs_order_independent(self):
        a = PlacesCache.make_key("place", (), {"place_id": "X", "fields": ["name", "rating"]})
        b = PlacesCache.make_key("place", (), {"fields": ["name", "rating"], "place_id": "X"})
        assert a == b

    def test_make_key_differs_by_method(self):
        a = PlacesCache.make_key("geocode", ("Istanbul",), {})
        b = PlacesCache.make_key("place", ("Istanbul",), {})
        assert a != b


class TestCachedGmapsHitMiss:
    def test_first_call_is_a_miss(self, fake_client, cache):
        gm = CachedGmaps(fake_client, cache=cache, enabled=True)
        gm.geocode("Istanbul")
        assert gm.misses == 1
        assert gm.hits == 0
        assert fake_client.geocode.call_count == 1

    def test_second_call_is_a_hit_and_skips_client(self, fake_client, cache):
        gm = CachedGmaps(fake_client, cache=cache, enabled=True)
        first = gm.geocode("Istanbul")
        second = gm.geocode("Istanbul")
        assert first == second
        assert gm.hits == 1
        assert gm.misses == 1
        assert fake_client.geocode.call_count == 1

    def test_different_args_are_different_keys(self, fake_client, cache):
        gm = CachedGmaps(fake_client, cache=cache, enabled=True)
        gm.geocode("Istanbul")
        gm.geocode("Ankara")
        assert fake_client.geocode.call_count == 2

    def test_disabled_cache_passes_through(self, fake_client, cache):
        gm = CachedGmaps(fake_client, cache=cache, enabled=False)
        gm.geocode("Istanbul")
        gm.geocode("Istanbul")
        assert fake_client.geocode.call_count == 2
        assert gm.hits == 0
        assert gm.misses == 0

    def test_places_details_and_nearby_each_cache(self, fake_client, cache):
        gm = CachedGmaps(fake_client, cache=cache, enabled=True)
        gm.places(query="bar in Istanbul")
        gm.places(query="bar in Istanbul")
        gm.places_nearby(location=(41.0, 29.0), radius=1000, type="restaurant", keyword="Istanbul")
        gm.places_nearby(location=(41.0, 29.0), radius=1000, type="restaurant", keyword="Istanbul")
        gm.place(place_id="X", fields=["name", "rating"])
        gm.place(place_id="X", fields=["name", "rating"])
        assert fake_client.places.call_count == 1
        assert fake_client.places_nearby.call_count == 1
        assert fake_client.place.call_count == 1

    def test_unknown_method_passes_through(self, fake_client, cache):
        fake_client.directions.return_value = "ROUTE"
        gm = CachedGmaps(fake_client, cache=cache, enabled=True)
        assert gm.directions("A", "B") == "ROUTE"
        # Should not have cached this — second call still hits client
        gm.directions("A", "B")
        assert fake_client.directions.call_count == 2


class TestEnvVarBypass:
    def test_places_cache_off_env_disables(self, fake_client, cache, monkeypatch):
        monkeypatch.setenv("PLACES_CACHE", "off")
        gm = CachedGmaps(fake_client, cache=cache)
        gm.geocode("Istanbul")
        gm.geocode("Istanbul")
        assert fake_client.geocode.call_count == 2

    def test_places_cache_unset_enables(self, fake_client, cache, monkeypatch):
        monkeypatch.delenv("PLACES_CACHE", raising=False)
        gm = CachedGmaps(fake_client, cache=cache)
        gm.geocode("Istanbul")
        gm.geocode("Istanbul")
        assert fake_client.geocode.call_count == 1


class TestClear:
    def test_clear_removes_all_entries(self, cache):
        key = PlacesCache.make_key("geocode", ("Istanbul",), {})
        cache.set(key, [{"a": 1}], ttl=60)
        cache.clear()
        assert cache.get(key) is None

    def test_clear_on_empty_cache_is_noop(self, cache):
        cache.clear()  # must not raise


class TestTTLs:
    def test_ttl_constants_are_distinct(self):
        assert GEOCODE_TTL > SEARCH_TTL
        assert DETAILS_TTL == 86400
        assert SEARCH_TTL == 86400
        assert GEOCODE_TTL == 7 * 86400
