from unittest.mock import patch

import pytest

from app.reviews.categories import CATEGORIES, CATEGORY_ORDER, get_category
from app.reviews.checker import recommend_by_categories


class TestTaxonomy:
    def test_every_category_id_matches_self(self):
        for cid, cat in CATEGORIES.items():
            assert cat.id == cid

    def test_categories_have_non_empty_google_types(self):
        for cat in CATEGORIES.values():
            assert isinstance(cat.google_types, tuple)
            assert len(cat.google_types) >= 1
            for t in cat.google_types:
                assert isinstance(t, str) and t

    def test_category_order_matches_categories_keys(self):
        assert set(CATEGORY_ORDER) == set(CATEGORIES.keys())
        assert len(CATEGORY_ORDER) == len(CATEGORIES)

    def test_categories_are_frozen_dataclasses(self):
        with pytest.raises(Exception):
            CATEGORIES["food"].google_types = ("x",)  # frozen → AttributeError or FrozenInstanceError

    def test_get_category_known(self):
        cat = get_category("food")
        assert cat.id == "food"

    def test_get_category_unknown_raises(self):
        with pytest.raises(ValueError):
            get_category("not_a_category")


class TestRecommendByCategories:
    def test_empty_list_returns_empty_dict(self):
        assert recommend_by_categories("Istanbul", []) == {}

    def test_unknown_category_raises(self):
        with pytest.raises(ValueError):
            recommend_by_categories("Istanbul", ["not_a_category"])

    def test_blocked_kwargs_rejected(self):
        with pytest.raises(TypeError):
            recommend_by_categories("Istanbul", ["food"], place_type="restaurant")
        with pytest.raises(TypeError):
            recommend_by_categories("Istanbul", ["food"], place_types=["restaurant"])
        with pytest.raises(TypeError):
            recommend_by_categories("Istanbul", ["food"], top_n=5)

    @patch("app.reviews.checker.recommend_places")
    def test_returns_dict_keyed_by_category_id(self, mock_rec):
        mock_rec.return_value = [{"place_id": "x", "name": "X", "score": 4.0}]
        out = recommend_by_categories("Istanbul", ["food", "sights"], top_n_per=3)
        assert set(out.keys()) == {"food", "sights"}
        assert mock_rec.call_count == 2

    @patch("app.reviews.checker.recommend_places")
    def test_passes_category_google_types(self, mock_rec):
        mock_rec.return_value = []
        recommend_by_categories("Istanbul", ["food"], top_n_per=2)
        _, kwargs = mock_rec.call_args
        assert kwargs["place_types"] == list(CATEGORIES["food"].google_types)
        assert kwargs["top_n"] == 2

    @patch("app.reviews.checker.recommend_places")
    def test_threads_shared_kwargs(self, mock_rec):
        mock_rec.return_value = []
        recommend_by_categories(
            "Istanbul", ["food"], top_n_per=4, budget=200, profile="foodie", cuisine="japanese"
        )
        _, kwargs = mock_rec.call_args
        assert kwargs["budget"] == 200
        assert kwargs["profile"] == "foodie"
        assert kwargs["cuisine"] == "japanese"
