"""Tests for the composite scoring engine: profile weights and the individual per-factor scores."""

import math
import time
import pytest
from app.reviews import factors
from app.reviews.profiles import PROFILES, DEFAULT_PROFILE, FACTOR_KEYS, get_profile
from app.reviews.scoring import composite_score


class TestProfiles:
    def test_each_profile_sums_to_one(self):
        for name, weights in PROFILES.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-9, f"Profile {name} sums to {total}"

    def test_each_profile_has_all_factors(self):
        for name, weights in PROFILES.items():
            for k in FACTOR_KEYS:
                assert k in weights, f"Profile {name} missing {k}"

    def test_default_profile_exists(self):
        assert DEFAULT_PROFILE in PROFILES

    def test_get_profile_returns_copy(self):
        w = get_profile("balanced")
        w["quality"] = 999
        assert PROFILES["balanced"]["quality"] != 999

    def test_get_profile_redistributes_missing_cuisine(self):
        baseline = PROFILES["balanced"]
        w = get_profile("balanced", has_cuisine=False, has_audience=False)
        assert w["cuisine"] == 0.0
        assert w["audience"] == 0.0
        assert abs(
            w["quality"] - (baseline["quality"] + baseline["cuisine"] + baseline["audience"])
        ) < 1e-9
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_get_profile_redistributes_missing_audience(self):
        baseline = PROFILES["balanced"]
        w = get_profile("balanced", has_cuisine=True, has_audience=False)
        assert w["audience"] == 0.0
        assert abs(w["quality"] - (baseline["quality"] + baseline["audience"])) < 1e-9
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_get_profile_boosts_audience_when_set(self):
        baseline = PROFILES["balanced"]
        w = get_profile("balanced", has_cuisine=True, has_audience=True)
        assert w["audience"] > baseline["audience"]
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_family_adult_presets_removed(self):
        assert "family" not in PROFILES
        assert "adult" not in PROFILES

    def test_get_profile_unknown_raises(self):
        with pytest.raises(ValueError):
            get_profile("nonexistent")


class TestQualityFactor:
    def test_high_count_high_rating_near_one(self):
        assert factors.quality_score(4.8, 2000) > 0.94

    def test_zero_reviews_returns_prior(self):
        assert factors.quality_score(0.0, 0) == pytest.approx(0.7)  # 3.5/5

    def test_low_count_blends_toward_prior(self):
        assert 0.7 < factors.quality_score(5.0, 1) < 0.8

    def test_clamped_to_unit_interval(self):
        assert 0.0 <= factors.quality_score(5.0, 10000) <= 1.0


class TestVolumeFactor:
    def test_zero_count_zero(self):
        assert factors.volume_score(0) == 0.0

    def test_monotonic(self):
        assert factors.volume_score(10) < factors.volume_score(100) < factors.volume_score(1000)

    def test_capped_at_one(self):
        assert factors.volume_score(50000) == pytest.approx(1.0, abs=0.05)


class TestDistanceFactor:
    def test_same_point_one(self):
        assert factors.distance_score((41.0, 29.0), (41.0, 29.0)) == pytest.approx(1.0)

    def test_far_point_decays(self):
        near = factors.distance_score((41.0, 29.0), (41.01, 29.01))
        far = factors.distance_score((41.0, 29.0), (42.0, 30.0))
        assert near > far

    def test_missing_inputs_neutral(self):
        assert factors.distance_score(None, (41.0, 29.0)) == 0.5
        assert factors.distance_score((41.0, 29.0), None) == 0.5

    def test_larger_d_half_means_higher_score_at_distance(self):
        small = factors.distance_score((41.0, 29.0), (41.05, 29.05), d_half=1.0)
        large = factors.distance_score((41.0, 29.0), (41.05, 29.05), d_half=10.0)
        assert large > small


class TestAspectsFactor:
    def test_no_request_neutral(self):
        assert factors.aspects_score({"romantic": 0.9}, None) == 0.5

    def test_no_place_aspects_neutral(self):
        assert factors.aspects_score(None, ["romantic"]) == 0.5

    def test_match_returns_mean(self):
        assert factors.aspects_score({"romantic": 0.8, "view": 0.6}, ["romantic", "view"]) == pytest.approx(0.7)

    def test_missing_aspect_skipped(self):
        # only "view" present, "romantic" absent → mean over present
        assert factors.aspects_score({"view": 0.6}, ["romantic", "view"]) == pytest.approx(0.6)

    def test_clamped(self):
        assert factors.aspects_score({"x": 1.5, "y": -0.2}, ["x", "y"]) == pytest.approx(0.5)


class TestCostFit:
    def test_unknown_price_neutral(self):
        assert factors.cost_fit(None, 500, people=2) == 0.5

    def test_no_budget_neutral(self):
        assert factors.cost_fit(2, None, people=2) == 0.5

    def test_within_budget_perfect(self):
        assert factors.cost_fit(1, 60, people=2) == 1.0

    def test_over_budget_penalized(self):
        cheap = factors.cost_fit(1, 60, people=2)
        pricey = factors.cost_fit(4, 60, people=2)
        assert cheap > pricey

    def test_high_per_person_budget_targets_4(self):
        assert factors.cost_fit(4, 1000, people=2) == 1.0


class TestRecency:
    def test_no_reviews_neutral(self):
        assert factors.recency_score([]) == 0.5

    def test_reviews_without_time_neutral(self):
        assert factors.recency_score([{"rating": 5}]) == 0.5

    def test_fresh_review_near_one(self):
        now = 1_700_000_000
        score = factors.recency_score([{"time": now - 86400, "rating": 5}], now=now)
        assert score > 0.99

    def test_old_review_decayed(self):
        now = 1_700_000_000
        score = factors.recency_score([{"time": now - 3 * 365 * 86400}], now=now)
        assert score < 0.1


class TestSentiment:
    def test_no_reviews_uses_fallback(self):
        assert factors.sentiment_score([], fallback=0.7) == 0.7

    def test_all_5s_high(self):
        assert factors.sentiment_score([{"rating": 5}, {"rating": 5}]) == 1.0

    def test_all_1s_zero(self):
        assert factors.sentiment_score([{"rating": 1}]) == 0.0


class TestAudience:
    def test_bar_is_adult(self):
        assert factors.infer_audience(["bar"], "Some Bar") == "adult"

    def test_zoo_is_family(self):
        assert factors.infer_audience(["zoo"], "City Zoo") == "family"

    def test_plain_restaurant_neutral(self):
        assert factors.infer_audience(["restaurant", "food"], "Köfteci") == "neutral"

    def test_keyword_pub_in_name_adult(self):
        assert factors.infer_audience(["restaurant"], "Irish Pub House") == "adult"

    def test_adult_wins_tie(self):
        assert factors.infer_audience(["bar", "park"], "Family Bar") == "adult"

    def test_audience_score_match(self):
        assert factors.audience_score("family", "family") == 1.0

    def test_audience_score_mismatch(self):
        assert factors.audience_score("adult", "family") == 0.0

    def test_audience_score_neutral(self):
        assert factors.audience_score("neutral", "family") == 0.5

    def test_audience_score_no_preference(self):
        assert factors.audience_score("adult", None) == 0.5


class TestCuisine:
    def test_no_preference_neutral(self):
        assert factors.cuisine_score(["restaurant"], "X", None) == 0.5

    def test_match_in_name(self):
        assert factors.cuisine_score(["restaurant"], "Best Sushi Place", "japanese") == 1.0

    def test_match_via_keyword(self):
        assert factors.cuisine_score(["restaurant"], "Köftecim", "turkish") == 1.0

    def test_partial_match_neutral_for_restaurant(self):
        assert factors.cuisine_score(["restaurant"], "Plain Diner", "japanese") == 0.5

    def test_mismatch_non_restaurant_zero(self):
        assert factors.cuisine_score(["museum"], "Some Museum", "italian") == 0.0


class TestCompositeScore:
    def test_breakdown_keys_complete(self):
        place = {"name": "Test", "rating": 4.5, "user_ratings_total": 200, "price_level": 2, "types": ["restaurant"]}
        weights = get_profile("balanced")
        result = composite_score(place, weights)
        for k in FACTOR_KEYS:
            assert k in result["breakdown"]
            assert k in result["raw"]

    def test_total_equals_sum_of_breakdown(self):
        place = {"name": "Test", "rating": 4.5, "user_ratings_total": 200, "price_level": 2, "types": ["restaurant"]}
        weights = get_profile("foodie")
        result = composite_score(place, weights)
        assert abs(result["total"] - sum(result["breakdown"].values())) < 1e-9

    def test_total_in_unit_interval(self):
        place = {"name": "Test", "rating": 4.5, "user_ratings_total": 200, "price_level": 2, "types": ["restaurant"]}
        weights = get_profile("balanced")
        result = composite_score(place, weights)
        assert 0.0 <= result["total"] <= 1.0

    def test_distance_affects_total(self):
        place = {"name": "Test", "rating": 4.5, "user_ratings_total": 200, "lat": 41.0, "lng": 29.0, "types": ["restaurant"]}
        weights = get_profile("balanced")
        near = composite_score(place, weights, center=(41.0, 29.0))
        far = composite_score(place, weights, center=(45.0, 35.0))
        assert near["total"] > far["total"]

    def test_audience_pref_boosts_match(self):
        place = {"name": "City Zoo", "rating": 4.5, "user_ratings_total": 200, "types": ["zoo"]}
        weights = get_profile("balanced", has_audience=True)
        with_pref = composite_score(place, weights, audience="family")
        without_pref = composite_score(place, weights, audience=None)
        assert with_pref["breakdown"]["audience"] > without_pref["breakdown"]["audience"]

    def test_cuisine_pref_boosts_match(self):
        place = {"name": "Sushi Master", "rating": 4.5, "user_ratings_total": 200, "types": ["restaurant"]}
        weights = get_profile("foodie")
        match = composite_score(place, weights, cuisine="japanese")
        miss = composite_score(place, weights, cuisine="italian")
        assert match["breakdown"]["cuisine"] > miss["breakdown"]["cuisine"]
