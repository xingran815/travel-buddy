from unittest.mock import patch, MagicMock
import pytest
from app.reviews.checker import (
    search_places,
    get_place_details,
    recommend_places,
    _bayesian_score,
    _deduplicate,
    _filter_by_price,
    _budget_to_max_price,
    _fetch_details_batch,
)


MOCK_PLACES_RESULT = {
    "results": [
        {
            "name": "Nusr-Et",
            "place_id": "place_1",
            "rating": 4.5,
            "user_ratings_total": 5000,
            "formatted_address": "Nisbetiye Cd, Istanbul",
            "types": ["restaurant", "food"],
        },
        {
            "name": "Köfteci Ramiz",
            "place_id": "place_2",
            "rating": 4.0,
            "user_ratings_total": 200,
            "formatted_address": "Sultanahmet, Istanbul",
            "types": ["restaurant", "food"],
        },
        {
            "name": "Bad Restaurant",
            "place_id": "place_3",
            "rating": 2.0,
            "user_ratings_total": 10,
            "formatted_address": "Taksim, Istanbul",
            "types": ["restaurant", "food"],
        },
    ]
}

MOCK_PLACE_DETAIL = {
    "result": {
        "name": "Nusr-Et",
        "rating": 4.5,
        "formatted_address": "Nisbetiye Cd, Istanbul",
        "price_level": 3,
        "international_phone_number": "+90 212 000 0000",
        "website": "https://nusr-et.com",
        "reviews": [
            {"author_name": "John", "rating": 5, "text": "Great steak!"},
            {"author_name": "Ayse", "rating": 4, "text": "Nice atmosphere."},
        ],
    }
}


class TestSearchPlaces:
    @patch("app.reviews.checker.get_client")
    def test_search_returns_list_of_places(self, mock_get_client):
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        mock_gmaps.places.return_value = MOCK_PLACES_RESULT

        result = search_places("Istanbul")
        assert len(result) == 3
        assert result[0]["name"] == "Nusr-Et"
        assert result[0]["rating"] == 4.5

    @patch("app.reviews.checker.get_client")
    def test_search_with_place_type(self, mock_get_client):
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        mock_gmaps.places.return_value = {"results": []}

        search_places("Istanbul", place_type="museum")
        mock_gmaps.places.assert_called_with(query="museum in Istanbul")


class TestGetPlaceDetails:
    @patch("app.reviews.checker.get_client")
    def test_get_details_returns_reviews(self, mock_get_client):
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        mock_gmaps.place.return_value = MOCK_PLACE_DETAIL

        result = get_place_details("place_1")
        assert result["name"] == "Nusr-Et"
        assert len(result["reviews"]) == 2
        assert result["reviews"][0]["author"] == "John"
        assert result["price_level"] == 3
        assert result["website"] == "https://nusr-et.com"

    @patch("app.reviews.checker.get_client")
    def test_get_details_empty_reviews(self, mock_get_client):
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        mock_gmaps.place.return_value = {"result": {"name": "Empty Place", "rating": 3.0, "formatted_address": "Somewhere"}}

        result = get_place_details("place_x")
        assert result["reviews"] == []
        assert result["name"] == "Empty Place"


class TestRecommendPlaces:
    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    def test_recommend_returns_top_n(self, mock_search, mock_batch):
        mock_search.return_value = [
            {"name": "A", "place_id": "1", "rating": 4.5, "user_ratings_total": 5000, "address": "Addr A", "types": ["restaurant"], "price_level": None},
            {"name": "B", "place_id": "2", "rating": 4.0, "user_ratings_total": 200, "address": "Addr B", "types": ["restaurant"], "price_level": None},
            {"name": "C", "place_id": "3", "rating": 2.0, "user_ratings_total": 10, "address": "Addr C", "types": ["restaurant"], "price_level": None},
        ]
        mock_batch.return_value = {"1": {"name": "A", "rating": 4.5, "reviews": []}, "2": {"name": "B", "rating": 4.0, "reviews": []}}

        result = recommend_places("Istanbul", top_n=2)
        assert len(result) == 2

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    def test_recommend_sorts_by_score(self, mock_search, mock_batch):
        place_a = {"name": "Low", "place_id": "1", "rating": 2.0, "user_ratings_total": 10, "address": "Addr", "types": [], "price_level": None}
        place_b = {"name": "High", "place_id": "2", "rating": 4.8, "user_ratings_total": 2000, "address": "Addr", "types": [], "price_level": None}

        mock_search.return_value = [place_a, place_b]
        mock_batch.return_value = {
            "1": {"name": "Low", "rating": 2.0, "reviews": []},
            "2": {"name": "High", "rating": 4.8, "reviews": []},
        }

        result = recommend_places("Istanbul", top_n=2)
        assert result[0]["name"] == "High"

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    def test_recommend_default_top_5(self, mock_search, mock_batch):
        places = [{"name": f"P{i}", "place_id": str(i), "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": [], "price_level": None} for i in range(8)]
        mock_search.return_value = places
        mock_batch.return_value = {str(i): {"name": f"P{i}", "reviews": []} for i in range(5)}

        result = recommend_places("Istanbul")
        assert len(result) == 5

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    def test_recommend_include_details_false(self, mock_search, mock_batch):
        places = [{"name": f"P{i}", "place_id": str(i), "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": [], "price_level": None} for i in range(3)]
        mock_search.return_value = places

        result = recommend_places("Istanbul", include_details=False)
        assert len(result) == 3
        assert result[0]["score"] is not None
        mock_batch.assert_not_called()


class TestBayesianScore:
    def test_high_review_count_trusts_own_rating(self):
        score = _bayesian_score(4.8, 2000, C=25, M=3.5)
        assert score > 4.7

    def test_low_review_count_blends_toward_prior(self):
        score = _bayesian_score(5.0, 1, C=25, M=3.5)
        assert 3.5 < score < 4.0

    def test_zero_reviews_returns_prior(self):
        score = _bayesian_score(0.0, 0, C=25, M=3.5)
        assert score == pytest.approx(3.5)

    def test_better_than_old_formula_for_low_counts(self):
        old = 4.8 * min(50, 100) / 100
        bayesian = _bayesian_score(4.8, 50, C=25, M=3.5)
        assert bayesian > old

    def test_custom_C_and_M(self):
        score = _bayesian_score(4.0, 10, C=50, M=3.0)
        assert 3.0 < score < 4.0


class TestDeduplication:
    def test_removes_exact_duplicates(self):
        places = [
            {"name": "Place A", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": []},
            {"name": "Place A", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": []},
        ]
        result = _deduplicate(places)
        assert len(result) == 1

    def test_removes_chain_duplicates_by_name(self):
        places = [
            {"name": "Starbucks #1", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": []},
            {"name": "Starbucks #2", "place_id": "2", "rating": 4.2, "user_ratings_total": 80, "address": "Addr2", "types": []},
        ]
        result = _deduplicate(places)
        assert len(result) == 1
        assert result[0]["name"] == "Starbucks #1"

    def test_keeps_different_places(self):
        places = [
            {"name": "Place A", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": []},
            {"name": "Place B", "place_id": "2", "rating": 4.5, "user_ratings_total": 200, "address": "Addr2", "types": []},
        ]
        result = _deduplicate(places)
        assert len(result) == 2

    def test_case_insensitive_dedup(self):
        places = [
            {"name": "Nusr-Et", "place_id": "1", "rating": 4.5, "user_ratings_total": 100, "address": "Addr", "types": []},
            {"name": "nusr-et", "place_id": "2", "rating": 4.0, "user_ratings_total": 50, "address": "Addr2", "types": []},
        ]
        result = _deduplicate(places)
        assert len(result) == 1

    def test_empty_list(self):
        result = _deduplicate([])
        assert result == []


class TestPagination:
    @patch("app.reviews.checker.get_client")
    def test_single_page_no_token(self, mock_get_client):
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        mock_gmaps.places.return_value = {"results": [{"name": "A", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "formatted_address": "Addr", "types": []}]}

        result = search_places("Istanbul", max_pages=1)
        assert len(result) == 1
        assert mock_gmaps.places.call_count == 1

    @patch("app.reviews.checker.get_client")
    def test_multiple_pages_with_token(self, mock_get_client):
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        page1 = {"results": [{"name": "A", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "formatted_address": "Addr", "types": []}], "next_page_token": "token123"}
        page2 = {"results": [{"name": "B", "place_id": "2", "rating": 4.5, "user_ratings_total": 200, "formatted_address": "Addr2", "types": []}]}
        mock_gmaps.places.side_effect = [page1, page2]

        result = search_places("Istanbul", max_pages=2)
        assert len(result) == 2
        assert mock_gmaps.places.call_count == 2

    @patch("app.reviews.checker.get_client")
    def test_stops_early_if_no_token(self, mock_get_client):
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        mock_gmaps.places.return_value = {"results": [{"name": "A", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "formatted_address": "Addr", "types": []}]}

        result = search_places("Istanbul", max_pages=3)
        assert mock_gmaps.places.call_count == 1


class TestMultiTypeSearch:
    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    def test_multi_type_merges_results(self, mock_search, mock_batch):
        restaurants = [
            {"name": "Resto A", "place_id": "r1", "rating": 4.5, "user_ratings_total": 500, "address": "Addr", "types": ["restaurant"], "price_level": None},
        ]
        museums = [
            {"name": "Museum B", "place_id": "m1", "rating": 4.8, "user_ratings_total": 1000, "address": "Addr2", "types": ["museum"], "price_level": None},
        ]
        mock_search.side_effect = [restaurants, museums]
        mock_batch.return_value = {
            "r1": {"name": "Resto A", "rating": 4.5, "reviews": []},
            "m1": {"name": "Museum B", "rating": 4.8, "reviews": []},
        }

        result = recommend_places("Istanbul", place_types=["restaurant", "museum"], top_n=5)
        assert len(result) == 2
        assert result[0]["name"] == "Museum B"

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    def test_single_type_fallback(self, mock_search, mock_batch):
        mock_search.return_value = [
            {"name": "A", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": ["restaurant"], "price_level": None},
        ]
        mock_batch.return_value = {"1": {"name": "A", "rating": 4.0, "reviews": []}}

        result = recommend_places("Istanbul", place_type="restaurant")
        mock_search.assert_called_once()


class TestPriceFiltering:
    def test_filter_by_max_price(self):
        places = [
            {"name": "Cheap", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": [], "price_level": 1},
            {"name": "Expensive", "place_id": "2", "rating": 4.5, "user_ratings_total": 200, "address": "Addr2", "types": [], "price_level": 4},
        ]
        result = _filter_by_price(places, max_price=2)
        assert len(result) == 1
        assert result[0]["name"] == "Cheap"

    def test_filter_by_min_price(self):
        places = [
            {"name": "Cheap", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": [], "price_level": 1},
            {"name": "Fancy", "place_id": "2", "rating": 4.5, "user_ratings_total": 200, "address": "Addr2", "types": [], "price_level": 3},
        ]
        result = _filter_by_price(places, min_price=2)
        assert len(result) == 1
        assert result[0]["name"] == "Fancy"

    def test_keeps_no_price_level_when_no_max(self):
        places = [
            {"name": "Unknown", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": [], "price_level": None},
        ]
        result = _filter_by_price(places)
        assert len(result) == 1

    def test_removes_no_price_level_when_min_set(self):
        places = [
            {"name": "Unknown", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": [], "price_level": None},
        ]
        result = _filter_by_price(places, min_price=1)
        assert len(result) == 0

    def test_removes_no_price_level_when_max_set(self):
        places = [
            {"name": "Unknown", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": [], "price_level": None},
        ]
        result = _filter_by_price(places, max_price=2)
        assert len(result) == 1


class TestBudgetToMaxPrice:
    def test_low_budget(self):
        assert _budget_to_max_price(200) == 1

    def test_medium_budget(self):
        assert _budget_to_max_price(500) == 2

    def test_high_budget(self):
        assert _budget_to_max_price(1000) == 3

    def test_very_high_budget(self):
        assert _budget_to_max_price(2000) is None

    def test_none_budget(self):
        assert _budget_to_max_price(None) is None


class TestGeocodeRegion:
    @patch("app.reviews.checker.get_client")
    def test_returns_default_d_half_when_no_viewport(self, mock_get_client):
        from app.reviews.checker import _geocode_region, DEFAULT_D_HALF_KM
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        mock_gmaps.geocode.return_value = [{"geometry": {"location": {"lat": 41.0, "lng": 29.0}}}]
        center, d_half = _geocode_region("Istanbul")
        assert center == (41.0, 29.0)
        assert d_half == DEFAULT_D_HALF_KM

    @patch("app.reviews.checker.get_client")
    def test_returns_d_half_from_viewport(self, mock_get_client):
        from app.reviews.checker import _geocode_region
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        # ~12 km between corners along a diagonal (rough)
        mock_gmaps.geocode.return_value = [{
            "geometry": {
                "location": {"lat": 41.0, "lng": 29.0},
                "viewport": {
                    "northeast": {"lat": 41.05, "lng": 29.05},
                    "southwest": {"lat": 40.95, "lng": 28.95},
                },
            }
        }]
        _, d_half = _geocode_region("CityA")
        assert d_half > 0.5

    @patch("app.reviews.checker.get_client")
    def test_big_viewport_yields_larger_d_half(self, mock_get_client):
        from app.reviews.checker import _geocode_region
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps

        small = {
            "geometry": {
                "location": {"lat": 41.0, "lng": 29.0},
                "viewport": {
                    "northeast": {"lat": 41.02, "lng": 29.02},
                    "southwest": {"lat": 40.98, "lng": 28.98},
                },
            }
        }
        big = {
            "geometry": {
                "location": {"lat": 41.0, "lng": 29.0},
                "viewport": {
                    "northeast": {"lat": 41.50, "lng": 29.50},
                    "southwest": {"lat": 40.50, "lng": 28.50},
                },
            }
        }
        mock_gmaps.geocode.side_effect = [[small], [big]]
        _, d_small = _geocode_region("SmallTown")
        _, d_big = _geocode_region("BigCity")
        assert d_big > d_small * 5

    @patch("app.reviews.checker.get_client", side_effect=Exception("no api key"))
    def test_failure_returns_default(self, mock_get_client):
        from app.reviews.checker import _geocode_region, DEFAULT_D_HALF_KM
        center, d_half = _geocode_region("Nowhere")
        assert center is None
        assert d_half == DEFAULT_D_HALF_KM


class TestClosedFiltering:
    @patch("app.reviews.checker.get_client")
    def test_closed_permanently_excluded(self, mock_get_client):
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        mock_gmaps.places.return_value = {
            "results": [
                {"name": "Open", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "formatted_address": "Addr", "types": [], "business_status": "OPERATIONAL"},
                {"name": "Closed", "place_id": "2", "rating": 4.5, "user_ratings_total": 200, "formatted_address": "Addr2", "types": [], "business_status": "CLOSED_PERMANENTLY"},
            ]
        }
        result = search_places("Istanbul")
        names = [p["name"] for p in result]
        assert "Open" in names
        assert "Closed" not in names

    @patch("app.reviews.checker.get_client")
    def test_extracts_lat_lng_from_geometry(self, mock_get_client):
        mock_gmaps = MagicMock()
        mock_get_client.return_value = mock_gmaps
        mock_gmaps.places.return_value = {
            "results": [
                {"name": "X", "place_id": "1", "rating": 4.0, "user_ratings_total": 100, "formatted_address": "Addr", "types": [],
                 "geometry": {"location": {"lat": 41.0, "lng": 29.0}}},
            ]
        }
        result = search_places("Istanbul")
        assert result[0]["lat"] == 41.0
        assert result[0]["lng"] == 29.0


class TestRecommendBreakdown:
    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    @patch("app.reviews.checker._geocode_region", return_value=(None, 3.0))
    def test_results_include_breakdown(self, mock_geo, mock_search, mock_batch):
        mock_search.return_value = [
            {"name": "A", "place_id": "1", "rating": 4.5, "user_ratings_total": 200, "address": "Addr", "types": ["restaurant"], "price_level": 2, "lat": None, "lng": None},
        ]
        mock_batch.return_value = {"1": {"name": "A", "rating": 4.5, "reviews": []}}

        result = recommend_places("Istanbul", top_n=1)
        assert "score" in result[0]
        assert "score_breakdown" in result[0]
        assert set(result[0]["score_breakdown"].keys()) == {
            "quality", "volume", "distance", "cost", "recency", "sentiment", "audience", "cuisine", "aspects",
        }

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    @patch("app.reviews.checker._geocode_region", return_value=(None, 3.0))
    def test_profile_changes_ordering(self, mock_geo, mock_search, mock_batch):
        # Place A: high rating but expensive. Place B: average rating but very cheap.
        mock_search.return_value = [
            {"name": "Fancy", "place_id": "1", "rating": 4.7, "user_ratings_total": 500, "address": "Addr", "types": ["restaurant"], "price_level": 4, "lat": None, "lng": None},
            {"name": "Cheap", "place_id": "2", "rating": 4.0, "user_ratings_total": 500, "address": "Addr", "types": ["restaurant"], "price_level": 1, "lat": None, "lng": None},
        ]
        mock_batch.return_value = {
            "1": {"name": "Fancy", "rating": 4.7, "reviews": []},
            "2": {"name": "Cheap", "rating": 4.0, "reviews": []},
        }

        foodie = recommend_places("Istanbul", top_n=2, profile="foodie", budget=100, people=2)
        budget = recommend_places("Istanbul", top_n=2, profile="budget", budget=100, people=2)
        assert foodie[0]["name"] == "Fancy"
        assert budget[0]["name"] == "Cheap"


class TestParallelDetails:
    @patch("app.reviews.checker.get_place_details")
    def test_fetch_details_batch(self, mock_details):
        mock_details.side_effect = [
            {"name": "A", "rating": 4.5, "reviews": []},
            {"name": "B", "rating": 4.0, "reviews": []},
        ]
        result = _fetch_details_batch(["1", "2"])
        assert len(result) == 2
        assert "1" in result
        assert "2" in result

    @patch("app.reviews.checker.get_place_details")
    def test_fetch_details_batch_empty(self, mock_details):
        result = _fetch_details_batch([])
        assert result == {}
