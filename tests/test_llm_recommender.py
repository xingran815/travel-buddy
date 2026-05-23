import json
from unittest.mock import patch, MagicMock

import pytest

from app.llm import recommender
from app.llm.base import LLMResult, LLMUsage


def _mock_result(content: dict, prompt_tokens: int = 100, completion_tokens: int = 50) -> LLMResult:
    return LLMResult(
        text=json.dumps(content),
        usage=LLMUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


@pytest.fixture
def temp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(recommender, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(recommender, "ASPECTS_CACHE", tmp_path / "aspects.json")
    monkeypatch.setattr(recommender, "PROS_CONS_CACHE", tmp_path / "pros_cons.json")
    monkeypatch.setattr(recommender, "PRICE_LEVEL_CACHE", tmp_path / "price_level.json")
    return tmp_path


class TestParseQuery:
    @patch("app.llm.recommender.get_provider")
    def test_returns_structured(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({
            "cuisine": "seafood",
            "audience": "adult",
            "aspects": ["romantic", "view"],
            "near": "Bosphorus",
            "price_level": 3,
        })
        out = recommender.parse_query("romantic seafood dinner with view near Bosphorus", lang="en")
        assert out["cuisine"] == "seafood"
        assert "romantic" in out["aspects"]
        assert out["raw"]

    def test_empty_query_skips_llm(self):
        with patch("app.llm.recommender.get_provider") as mock_get_provider:
            out = recommender.parse_query("", lang="en")
        assert out == {}
        mock_get_provider.assert_not_called()

    @patch("app.llm.recommender.get_provider")
    def test_llm_error_returns_raw(self, mock_get_provider):
        mock_get_provider.side_effect = Exception("network down")
        out = recommender.parse_query("foo", lang="en")
        assert out == {"raw": "foo"}


class TestRerank:
    @patch("app.llm.recommender.get_provider")
    def test_reorders_by_llm(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({
            "order": [
                {"place_id": "B", "rationale": "Best fit"},
                {"place_id": "A", "rationale": "Runner up"},
            ]
        })
        places = [
            {"place_id": "A", "name": "Alpha", "score_breakdown": {}, "reviews": []},
            {"place_id": "B", "name": "Beta", "score_breakdown": {}, "reviews": []},
        ]
        out = recommender.rerank_top_k(places, query="any", profile="balanced", prefs={}, k_out=2)
        assert [p["place_id"] for p in out] == ["B", "A"]
        assert out[0]["llm_rationale"] == "Best fit"

    def test_short_list_passes_through(self):
        places = [{"place_id": "A", "name": "X", "score_breakdown": {}, "reviews": []}]
        out = recommender.rerank_top_k(places, query="any", profile="balanced", prefs={}, k_out=5)
        assert out == places

    @patch("app.llm.recommender.get_provider")
    def test_llm_error_falls_back(self, mock_get_provider):
        mock_get_provider.side_effect = Exception("err")
        places = [
            {"place_id": "A", "name": "Alpha", "score_breakdown": {}, "reviews": []},
            {"place_id": "B", "name": "Beta", "score_breakdown": {}, "reviews": []},
        ]
        out = recommender.rerank_top_k(places, query="x", profile="balanced", prefs={}, k_out=2)
        assert out == places[:2]


class TestRerankWithProsCons:
    @patch("app.llm.recommender.get_provider")
    def test_merged_returns_order_and_pros_cons(self, mock_get_provider, temp_cache):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({
            "order": [
                {
                    "place_id": "B", "rationale": "Better view",
                    "pros": ["Stunning view", "Cozy"],
                    "cons": ["Pricey", "Slow service"],
                },
                {
                    "place_id": "A", "rationale": "Solid backup",
                    "pros": ["Reliable", "Friendly"],
                    "cons": ["Plain decor", "Limited menu"],
                },
            ]
        })
        places = [
            {"place_id": "A", "name": "Alpha", "score_breakdown": {},
             "reviews": [{"rating": 5, "text": "Loved it"}]},
            {"place_id": "B", "name": "Beta", "score_breakdown": {},
             "reviews": [{"rating": 4, "text": "Nice"}]},
        ]
        out = recommender.rerank_with_pros_cons(
            places, query="x", profile="balanced", prefs={}, k_out=2, lang="en",
        )
        assert [p["place_id"] for p in out] == ["B", "A"]
        assert out[0]["llm_rationale"] == "Better view"
        assert out[0]["pros"] == ["Stunning view", "Cozy"]
        assert out[0]["cons"] == ["Pricey", "Slow service"]
        assert out[1]["pros"] == ["Reliable", "Friendly"]
        assert provider.chat_json.call_count == 1

    @patch("app.llm.recommender.get_provider")
    def test_merged_prewarms_pros_cons_cache(self, mock_get_provider, temp_cache):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({
            "order": [
                {"place_id": "A", "rationale": "Top",
                 "pros": ["Good food"], "cons": ["Loud"]},
            ]
        })
        places = [
            {"place_id": "A", "name": "Alpha", "score_breakdown": {},
             "reviews": [{"rating": 5, "text": "Great steak"}]},
            {"place_id": "B", "name": "Beta", "score_breakdown": {},
             "reviews": [{"rating": 4, "text": "Decent"}]},
        ]
        recommender.rerank_with_pros_cons(
            places, query="x", profile="balanced", prefs={}, k_out=1, lang="en",
        )
        place_a = places[0]
        # A separate summarize call for the same place + lang should hit the warmed cache.
        out = recommender.summarize_pros_cons(place_a, lang="en")
        assert out == {"pros": ["Good food"], "cons": ["Loud"]}
        assert provider.chat_json.call_count == 1  # cache hit, no second LLM call

    @patch("app.llm.recommender.rerank_top_k")
    @patch("app.llm.recommender.get_provider")
    def test_merged_falls_back_on_failure(self, mock_get_provider, mock_rerank, temp_cache):
        mock_get_provider.side_effect = Exception("network down")
        mock_rerank.return_value = [{"place_id": "A"}, {"place_id": "B"}]
        places = [
            {"place_id": "A", "name": "Alpha", "score_breakdown": {}, "reviews": []},
            {"place_id": "B", "name": "Beta", "score_breakdown": {}, "reviews": []},
        ]
        out = recommender.rerank_with_pros_cons(
            places, query="x", profile="balanced", prefs={}, k_out=2, lang="en",
        )
        assert mock_rerank.called
        assert [p["place_id"] for p in out] == ["A", "B"]

    def test_merged_short_list_passes_through(self):
        places = [{"place_id": "A", "name": "X", "score_breakdown": {}, "reviews": []}]
        out = recommender.rerank_with_pros_cons(
            places, query="any", profile="balanced", prefs={}, k_out=5,
        )
        assert out == places


class TestProsCons:
    @patch("app.llm.recommender.get_provider")
    def test_returns_pros_cons(self, mock_get_provider, temp_cache):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({
            "pros": ["Great steak", "Lively"],
            "cons": ["Expensive", "Loud"],
        })
        place = {
            "place_id": "p1",
            "name": "Nusr-Et",
            "reviews": [{"rating": 5, "text": "Great steak!"}],
        }
        out = recommender.summarize_pros_cons(place, lang="en")
        assert out["pros"] == ["Great steak", "Lively"]
        assert out["cons"] == ["Expensive", "Loud"]

    def test_empty_reviews(self, temp_cache):
        out = recommender.summarize_pros_cons({"place_id": "x", "reviews": []})
        assert out == {"pros": [], "cons": []}

    @patch("app.llm.recommender.get_provider")
    def test_cache_hit_skips_llm(self, mock_get_provider, temp_cache):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({
            "pros": ["A"], "cons": ["B"],
        })
        place = {"place_id": "p2", "name": "X", "reviews": [{"rating": 5, "text": "Good"}]}
        recommender.summarize_pros_cons(place, lang="en")
        recommender.summarize_pros_cons(place, lang="en")
        assert provider.chat_json.call_count == 1


class TestExtractAspects:
    @patch("app.llm.recommender.get_provider")
    def test_writes_to_cache(self, mock_get_provider, temp_cache):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({
            "atmosphere": 0.8, "service": 0.5, "value": 0.4,
            "cleanliness": 0.7, "view": 0.1, "romantic": 0.3,
            "noise": 0.6, "kid_friendly": 0.2, "quiet": 0.4,
        })
        place = {"place_id": "p_aspects", "name": "X", "types": ["restaurant"], "user_ratings_total": 100, "reviews": []}
        out = recommender.extract_aspects(place)
        assert out["atmosphere"] == 0.8
        cache = recommender.load_aspects_cache()
        assert "p_aspects" in cache
        assert cache["p_aspects"]["atmosphere"] == 0.8

    @patch("app.llm.recommender.get_provider")
    def test_cache_hit_skips_llm(self, mock_get_provider, temp_cache):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({
            k: 0.5 for k in recommender.ASPECT_KEYS
        })
        place = {"place_id": "p_cached", "name": "X", "types": [], "user_ratings_total": 100, "reviews": []}
        recommender.extract_aspects(place)
        recommender.extract_aspects(place)  # same n → cache hit
        assert provider.chat_json.call_count == 1


class TestSplitReviews:
    def test_top_and_bottom_disjoint(self):
        reviews = [
            {"rating": 5, "text": "Amazing"},
            {"rating": 4, "text": "Good"},
            {"rating": 3, "text": "OK"},
            {"rating": 2, "text": "Meh"},
            {"rating": 1, "text": "Terrible"},
        ]
        top, bot = recommender._split_reviews_by_rating(reviews, n_top=2, n_bot=2)
        top_ratings = {r["rating"] for r in top}
        bot_ratings = {r["rating"] for r in bot}
        assert top_ratings == {5, 4}
        assert bot_ratings == {1, 2}
        assert not top_ratings & bot_ratings

    def test_drops_blank_text_reviews(self):
        reviews = [
            {"rating": 5, "text": "Great"},
            {"rating": 1, "text": ""},
            {"rating": 1, "text": "   "},
            {"rating": 2, "text": "Bad"},
        ]
        top, bot = recommender._split_reviews_by_rating(reviews, n_top=3, n_bot=3)
        assert all(r["text"].strip() for r in top + bot)
        assert {r["rating"] for r in top} == {5}
        assert {r["rating"] for r in bot} == {2}

    def test_small_set_no_overlap(self):
        reviews = [
            {"rating": 5, "text": "Loved"},
            {"rating": 1, "text": "Hated"},
        ]
        top, bot = recommender._split_reviews_by_rating(reviews, n_top=3, n_bot=3)
        assert len(top) == 1
        assert len(bot) == 1
        assert top[0]["rating"] == 5
        assert bot[0]["rating"] == 1


class TestPlaceSummary:
    def test_emits_good_and_bad_reviews(self):
        place = {
            "place_id": "p1",
            "name": "Test",
            "rating": 4.2,
            "user_ratings_total": 500,
            "reviews": [
                {"rating": 5, "text": "Stunning food"},
                {"rating": 1, "text": "Overpriced and rude"},
                {"rating": 4, "text": "Solid"},
            ],
        }
        summary = recommender._place_summary(place)
        assert "good_reviews" in summary
        assert "bad_reviews" in summary
        assert "review_excerpts" not in summary
        assert summary["good_reviews"][0]["rating"] == 5
        assert summary["bad_reviews"][0]["rating"] == 1


class TestEstimatePriceLevel:
    @patch("app.llm.recommender.get_provider")
    def test_returns_level(self, mock_get_provider, temp_cache):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({"level": 3, "confidence": "med"})
        place = {
            "place_id": "p_est",
            "name": "Fancy",
            "reviews": [{"rating": 4, "text": "Pricey but worth it"}],
        }
        assert recommender.estimate_price_level(place) == 3

    def test_empty_reviews_returns_none(self, temp_cache):
        assert recommender.estimate_price_level({"place_id": "x", "reviews": []}) is None

    @patch("app.llm.recommender.get_provider")
    def test_cache_hit_skips_llm(self, mock_get_provider, temp_cache):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({"level": 2, "confidence": "high"})
        place = {
            "place_id": "p_cached",
            "name": "X",
            "reviews": [{"rating": 4, "text": "Reasonable"}],
        }
        recommender.estimate_price_level(place)
        recommender.estimate_price_level(place)
        assert provider.chat_json.call_count == 1

    @patch("app.llm.recommender.get_provider")
    def test_invalid_level_returns_none(self, mock_get_provider, temp_cache):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_json.return_value = _mock_result({"level": None, "confidence": "low"})
        place = {
            "place_id": "p_null",
            "name": "X",
            "reviews": [{"rating": 3, "text": "Ambiguous"}],
        }
        assert recommender.estimate_price_level(place) is None

    @patch("app.llm.recommender.get_provider")
    def test_llm_error_returns_none(self, mock_get_provider, temp_cache):
        mock_get_provider.side_effect = Exception("boom")
        place = {"place_id": "p_err", "name": "X", "reviews": [{"rating": 3, "text": "x"}]}
        assert recommender.estimate_price_level(place) is None


class TestAspectsScoreIntegration:
    @patch("app.reviews.checker._geocode_region", return_value=(None, 3.0))
    @patch("app.reviews.checker._fetch_details_batch")
    @patch("app.reviews.checker.search_places")
    @patch("app.llm.recommender.load_aspects_cache")
    def test_aspects_lookup_applied_to_scoring(self, mock_cache, mock_search, mock_batch, mock_geo):
        from app.reviews.checker import recommend_places
        mock_search.return_value = [
            {"name": "Romantic", "place_id": "r1", "rating": 4.0, "user_ratings_total": 200, "address": "Addr", "types": ["restaurant"], "price_level": 2, "lat": None, "lng": None},
            {"name": "Loud", "place_id": "l1", "rating": 4.0, "user_ratings_total": 200, "address": "Addr2", "types": ["restaurant"], "price_level": 2, "lat": None, "lng": None},
        ]
        mock_batch.return_value = {"r1": {"reviews": []}, "l1": {"reviews": []}}
        mock_cache.return_value = {
            "r1": {"romantic": 0.95, "view": 0.8},
            "l1": {"romantic": 0.05, "view": 0.1},
        }
        results = recommend_places("X", top_n=2, profile="atmosphere", aspects=["romantic", "view"])
        assert results[0]["name"] == "Romantic"
