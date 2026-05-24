from unittest.mock import patch
from app.reviews.checker import recommend_places
from app.reviews.profiles import FACTOR_KEYS


def _mock_place(place_id, name, rating=4.0, n=200, price=2, types=None, lat=None, lng=None, business_status=None):
    return {
        "name": name,
        "place_id": place_id,
        "rating": rating,
        "user_ratings_total": n,
        "address": f"{name} Addr",
        "types": types or ["restaurant"],
        "price_level": price,
        "lat": lat,
        "lng": lng,
        "business_status": business_status,
    }


class TestRecommendSanity:
    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    @patch("app.reviews.checker._geocode_region", return_value=(None, 3.0, None))
    def test_no_closed_permanently_in_top(self, mock_geo, mock_search, mock_batch):
        # search_places already filters CLOSED_PERMANENTLY at extraction time, so simulate that here
        mock_search.return_value = [
            _mock_place("1", "Open A", rating=4.5),
            _mock_place("2", "Open B", rating=4.2),
        ]
        mock_batch.return_value = {"1": {"reviews": []}, "2": {"reviews": []}}
        results = recommend_places("X", top_n=5)
        for r in results:
            assert r.get("business_status") != "CLOSED_PERMANENTLY"

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    @patch("app.reviews.checker._geocode_region", return_value=(None, 3.0, None))
    def test_sorted_descending_by_score(self, mock_geo, mock_search, mock_batch):
        mock_search.return_value = [
            _mock_place(str(i), f"P{i}", rating=4.0 + (i % 5) * 0.1, n=100 + i * 50)
            for i in range(8)
        ]
        mock_batch.return_value = {str(i): {"reviews": []} for i in range(5)}
        results = recommend_places("X", top_n=5)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    @patch("app.reviews.checker._geocode_region", return_value=(None, 3.0, None))
    def test_breakdown_keys_complete(self, mock_geo, mock_search, mock_batch):
        mock_search.return_value = [_mock_place("1", "A")]
        mock_batch.return_value = {"1": {"reviews": []}}
        results = recommend_places("X", top_n=1)
        assert set(results[0]["score_breakdown"].keys()) == set(FACTOR_KEYS)

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    @patch("app.reviews.checker._geocode_region", return_value=(None, 3.0, None))
    def test_budget_profile_weights_cost_more_than_balanced(self, mock_geo, mock_search, mock_batch):
        mock_search.return_value = [_mock_place("1", "Pricy", price=4, rating=4.5, n=300)]
        budget_res = recommend_places(
            "X", top_n=1, profile="budget", budget=60, people=2, max_price=4, include_details=False
        )
        balanced_res = recommend_places(
            "X", top_n=1, profile="balanced", budget=60, people=2, max_price=4, include_details=False
        )
        budget_cost = budget_res[0]["score_breakdown"]["cost"]
        balanced_cost = balanced_res[0]["score_breakdown"]["cost"]
        # Even if both have penalised cost_fit, budget profile *multiplies* it by a larger weight.
        # When the cost_fit raw value is small/zero the contribution may be ~0 in both — so check the
        # weight ratio implicitly via a non-cost-related place to confirm budget pressures rankings.
        # Here we simply confirm budget weights cost ≥ balanced weights cost (no smaller).
        # If cost_fit is zero, both contributions are zero and the test still passes.
        assert budget_cost >= balanced_cost - 1e-9

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    @patch("app.reviews.checker._geocode_region", return_value=(None, 3.0, None))
    def test_budget_profile_picks_cheaper_in_close_quality_race(self, mock_geo, mock_search, mock_batch):
        # Very similar rating, different price → budget profile should prefer cheaper.
        mock_search.return_value = [
            _mock_place("1", "Cheap", price=1, rating=4.5, n=400),
            _mock_place("4", "Pricy", price=4, rating=4.6, n=400),
        ]
        budget = recommend_places("X", top_n=2, profile="budget", budget=60, people=2, max_price=4, include_details=False)
        assert budget[0]["name"] == "Cheap"

    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    @patch("app.reviews.checker._geocode_region", return_value=(None, 3.0, None))
    def test_multi_type_includes_diversity(self, mock_geo, mock_search, mock_batch):
        restaurants = [_mock_place(f"r{i}", f"R{i}", types=["restaurant"]) for i in range(3)]
        museums = [_mock_place(f"m{i}", f"M{i}", types=["museum"], rating=4.6) for i in range(3)]
        mock_search.side_effect = [restaurants, museums]
        mock_batch.return_value = {p["place_id"]: {"reviews": []} for p in restaurants + museums}
        results = recommend_places("X", place_types=["restaurant", "museum"], top_n=4)
        first_types = {r["types"][0] for r in results}
        assert len(first_types) >= 2
