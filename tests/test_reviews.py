from unittest.mock import patch, MagicMock
import pytest
from app.reviews.checker import search_places, get_place_details, recommend_places


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
    @patch("app.reviews.checker.get_place_details")
    @patch("app.reviews.checker.search_places")
    def test_recommend_returns_top_n(self, mock_search, mock_details):
        mock_search.return_value = [
            {"name": "A", "place_id": "1", "rating": 4.5, "user_ratings_total": 5000, "address": "Addr A", "types": ["restaurant"], "score": 4.5},
            {"name": "B", "place_id": "2", "rating": 4.0, "user_ratings_total": 200, "address": "Addr B", "types": ["restaurant"], "score": 4.0},
            {"name": "C", "place_id": "3", "rating": 2.0, "user_ratings_total": 10, "address": "Addr C", "types": ["restaurant"], "score": 2.0},
        ]
        mock_details.return_value = {"name": "A", "rating": 4.5, "reviews": []}

        result = recommend_places("Istanbul", top_n=2)
        assert len(result) == 2

    @patch("app.reviews.checker.get_place_details")
    @patch("app.reviews.checker.search_places")
    def test_recommend_sorts_by_score(self, mock_search, mock_details):
        place_a = {"name": "Low", "place_id": "1", "rating": 2.0, "user_ratings_total": 10, "address": "Addr", "types": [], "score": 0.2}
        place_b = {"name": "High", "place_id": "2", "rating": 4.8, "user_ratings_total": 2000, "address": "Addr", "types": [], "score": 4.8}

        mock_search.return_value = [place_a, place_b]
        mock_details.side_effect = lambda pid: {"name": "High" if pid == "2" else "Low", "rating": 4.8 if pid == "2" else 2.0, "reviews": []}

        result = recommend_places("Istanbul", top_n=2)
        assert result[0]["name"] == "High"

    @patch("app.reviews.checker.get_place_details")
    @patch("app.reviews.checker.search_places")
    def test_recommend_default_top_5(self, mock_search, mock_details):
        places = [{"name": f"P{i}", "place_id": str(i), "rating": 4.0, "user_ratings_total": 100, "address": "Addr", "types": [], "score": 4.0} for i in range(8)]
        mock_search.return_value = places
        mock_details.return_value = {"name": "Place", "reviews": []}

        result = recommend_places("Istanbul")
        assert len(result) == 5
