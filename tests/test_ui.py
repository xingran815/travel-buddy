from unittest.mock import patch, MagicMock
import pytest
from app.ui.display import (
    show_welcome,
    show_translation,
    show_summary,
    show_recommendations,
    show_plan,
    show_error,
    show_info,
    show_success,
)
from app.ui.menu import run_summarize, run_recommend, run_plan, run_settings, _is_quit, _ask_place_types
from app.ui.prompts import _ask_categories, _ask_category_refinement


class TestDisplay:
    def test_is_quit_q(self):
        assert _is_quit("q") is True

    def test_is_quit_Q(self):
        assert _is_quit("Q") is True

    def test_is_quit_spaces(self):
        assert _is_quit("  q  ") is True

    def test_is_quit_not_q(self):
        assert _is_quit("istanbul") is False

    def test_is_quit_none(self):
        assert _is_quit(None) is False

    def test_is_quit_empty(self):
        assert _is_quit("") is False

    def test_show_welcome_en(self):
        show_welcome("en")

    def test_show_welcome_tr(self):
        show_welcome("tr")

    def test_show_translation(self):
        show_translation("İstanbul güzel bir şehir.", "tr")

    def test_show_summary(self):
        show_summary("Özet metin burada.", "tr")

    def test_show_recommendations_with_data(self):
        places = [
            {
                "name": "Nusr-Et",
                "rating": 4.5,
                "address": "Istanbul",
                "price_level": 3,
                "reviews": [{"author": "John", "rating": 5, "text": "Great steak!"}],
            }
        ]
        show_recommendations(places, "en")

    def test_show_recommendations_empty(self):
        show_recommendations([], "tr")

    def test_show_recommendations_no_reviews(self):
        places = [{"name": "Cafe", "rating": 4.0, "address": "Ankara"}]
        show_recommendations(places, "tr")

    def test_show_plan(self):
        show_plan("1. Gün: Sultanahmet\n2. Gün: Kapalıçarşı", "tr")

    def test_show_error(self):
        show_error("Something went wrong")

    def test_show_info(self):
        show_info("Processing...")

    def test_show_success(self):
        show_success("Done!")


class TestMenuSummarize:
    @patch("app.ui.menu.cleanup")
    @patch("app.ui.menu.summarize_in_turkish", return_value="Özet.")
    @patch("app.ui.menu.translate_to_turkish", return_value="Çeviri.")
    @patch("app.ui.menu.transcribe", return_value={"text": "Text", "language": "en"})
    @patch("app.ui.menu.get_video_title", return_value="Test Video")
    @patch("app.ui.menu.download_audio", return_value=("/tmp/test.wav", "test123"))
    @patch("app.ui.menu.questionary.text")
    def test_run_summarize_with_url(self, mock_text, mock_dl, mock_title, mock_transcribe, mock_translate, mock_summarize, mock_cleanup):
        mock_text.return_value.ask.return_value = "https://youtube.com/watch?v=test"
        run_summarize("tr")
        mock_cleanup.assert_called_with("test123")

    @patch("app.ui.menu.questionary.text")
    def test_run_summarize_no_url(self, mock_text):
        mock_text.return_value.ask.return_value = ""
        run_summarize("en")

    @patch("app.ui.menu.questionary.text")
    def test_run_summarize_q_goes_back(self, mock_text):
        mock_text.return_value.ask.return_value = "q"
        run_summarize("en")

    @patch("app.ui.menu.download_audio")
    def test_run_summarize_q_does_not_download(self, mock_dl):
        with patch("app.ui.menu.questionary.text") as mock_text:
            mock_text.return_value.ask.return_value = "q"
            run_summarize("tr")
        mock_dl.assert_not_called()


class TestMenuRecommend:
    @patch("app.ui.menu.recommend_places", return_value=[])
    @patch("app.ui.menu._ask_place_types", return_value=["restaurant"])
    @patch("app.ui.menu.questionary.select")
    @patch("app.ui.menu.questionary.text")
    def test_run_recommend_with_region(self, mock_text, mock_select, mock_types, mock_rec):
        mock_text.side_effect = [
            MagicMock(ask=MagicMock(return_value="Istanbul")),  # region
            MagicMock(ask=MagicMock(return_value="")),           # budget skip
            MagicMock(ask=MagicMock(return_value="")),           # cuisine skip
            MagicMock(ask=MagicMock(return_value="2")),          # people
        ]
        mock_select.return_value = MagicMock(ask=MagicMock(return_value="5"))
        run_recommend("en")

    @patch("app.ui.menu.questionary.text")
    def test_run_recommend_no_region(self, mock_text):
        mock_text.return_value.ask.return_value = ""
        run_recommend("en")

    @patch("app.ui.menu.questionary.text")
    def test_run_recommend_q_goes_back(self, mock_text):
        mock_text.return_value.ask.return_value = "q"
        run_recommend("en")

    @patch("app.ui.menu.recommend_places")
    def test_run_recommend_q_does_not_fetch(self, mock_rec):
        with patch("app.ui.menu.questionary.text") as mock_text:
            mock_text.return_value.ask.return_value = "q"
            run_recommend("tr")
        mock_rec.assert_not_called()


class TestMenuPlan:
    @patch("app.ui.menu.generate_plan", return_value="Travel plan...")
    @patch("app.ui.menu.recommend_places", return_value=[])
    @patch("app.ui.menu._ask_place_types", return_value=None)
    @patch("app.ui.menu.questionary.text")
    def test_run_plan_without_url(self, mock_text, mock_types, mock_rec, mock_plan):
        mock_text.side_effect = [
            MagicMock(ask=MagicMock(return_value="Istanbul")),
            MagicMock(ask=MagicMock(return_value="500")),
            MagicMock(ask=MagicMock(return_value="3")),
            MagicMock(ask=MagicMock(return_value="history")),
            MagicMock(ask=MagicMock(return_value="")),
        ]
        run_plan("en")

    @patch("app.ui.menu.questionary.text")
    def test_run_plan_no_region(self, mock_text):
        mock_text.return_value.ask.return_value = ""
        run_plan("tr")

    @patch("app.ui.menu.questionary.text")
    def test_run_plan_q_at_region_goes_back(self, mock_text):
        mock_text.return_value.ask.return_value = "q"
        run_plan("en")

    @patch("app.ui.menu.generate_plan")
    def test_run_plan_q_at_budget_goes_back(self, mock_plan):
        with patch("app.ui.menu.questionary.text") as mock_text:
            mock_text.side_effect = [
                MagicMock(ask=MagicMock(return_value="Istanbul")),
                MagicMock(ask=MagicMock(return_value="q")),
            ]
            run_plan("en")
        mock_plan.assert_not_called()

    @patch("app.ui.menu.generate_plan")
    def test_run_plan_q_at_days_goes_back(self, mock_plan):
        with patch("app.ui.menu.questionary.text") as mock_text:
            mock_text.side_effect = [
                MagicMock(ask=MagicMock(return_value="Istanbul")),
                MagicMock(ask=MagicMock(return_value="500")),
                MagicMock(ask=MagicMock(return_value="q")),
            ]
            run_plan("en")
        mock_plan.assert_not_called()

    @patch("app.ui.menu.generate_plan")
    def test_run_plan_q_at_preferences_goes_back(self, mock_plan):
        with patch("app.ui.menu.questionary.text") as mock_text:
            mock_text.side_effect = [
                MagicMock(ask=MagicMock(return_value="Istanbul")),
                MagicMock(ask=MagicMock(return_value="500")),
                MagicMock(ask=MagicMock(return_value="3")),
                MagicMock(ask=MagicMock(return_value="q")),
            ]
            run_plan("en")
        mock_plan.assert_not_called()

    @patch("app.ui.menu.generate_plan")
    def test_run_plan_q_at_url_goes_back(self, mock_plan):
        with patch("app.ui.menu.questionary.text") as mock_text:
            mock_text.side_effect = [
                MagicMock(ask=MagicMock(return_value="Istanbul")),
                MagicMock(ask=MagicMock(return_value="500")),
                MagicMock(ask=MagicMock(return_value="3")),
                MagicMock(ask=MagicMock(return_value="history")),
                MagicMock(ask=MagicMock(return_value="q")),
            ]
            run_plan("en")
        mock_plan.assert_not_called()


class TestAskCategories:
    @patch("app.ui.prompts.questionary.checkbox")
    def test_returns_none_on_cancel(self, mock_checkbox):
        mock_checkbox.return_value.ask.return_value = None
        assert _ask_categories("en") is None
        assert mock_checkbox.call_count == 1

    @patch("app.ui.prompts.questionary.checkbox")
    def test_re_prompts_on_empty(self, mock_checkbox):
        mock_checkbox.return_value.ask.side_effect = [[], ["Food & drink"]]
        result = _ask_categories("en")
        assert result == ["food"]
        assert mock_checkbox.call_count == 2

    @patch("app.ui.prompts.questionary.checkbox")
    def test_returns_none_after_two_empty_submits(self, mock_checkbox):
        mock_checkbox.return_value.ask.side_effect = [[], []]
        assert _ask_categories("en") is None
        assert mock_checkbox.call_count == 2

    @patch("app.ui.prompts.questionary.checkbox")
    def test_returns_selection_on_first_attempt(self, mock_checkbox):
        mock_checkbox.return_value.ask.return_value = ["Food & drink", "Sights & landmarks"]
        result = _ask_categories("en")
        assert result == ["food", "sights"]
        assert mock_checkbox.call_count == 1


class TestAskPlaceTypesMulti:
    @patch("app.ui.prompts.questionary.checkbox")
    @patch("app.ui.prompts.questionary.select")
    def test_re_prompts_on_empty(self, mock_select, mock_checkbox):
        mock_select.return_value.ask.return_value = "Multiple types"
        mock_checkbox.return_value.ask.side_effect = [[], ["Restaurant"]]
        result = _ask_place_types("en")
        assert result == ["restaurant"]
        assert mock_checkbox.call_count == 2

    @patch("app.ui.prompts.questionary.checkbox")
    @patch("app.ui.prompts.questionary.select")
    def test_returns_none_after_two_empty_submits(self, mock_select, mock_checkbox):
        mock_select.return_value.ask.return_value = "Multiple types"
        mock_checkbox.return_value.ask.side_effect = [[], []]
        assert _ask_place_types("en") is None
        assert mock_checkbox.call_count == 2

    @patch("app.ui.prompts.questionary.checkbox")
    @patch("app.ui.prompts.questionary.select")
    def test_returns_none_on_cancel(self, mock_select, mock_checkbox):
        mock_select.return_value.ask.return_value = "Multiple types"
        mock_checkbox.return_value.ask.return_value = None
        assert _ask_place_types("en") is None
        assert mock_checkbox.call_count == 1


class TestAskCategoryRefinement:
    @patch("app.ui.prompts.questionary.select")
    @patch("app.ui.prompts.questionary.text")
    def test_food_asks_vibe_and_budget_no_indoor_outdoor(self, mock_text, mock_select):
        # Audience=any, budget=mid; vibe text
        mock_select.return_value.ask.side_effect = ["Any", "Mid ($$)"]
        mock_text.return_value.ask.return_value = "casual"
        result = _ask_category_refinement(["food"], "en")
        assert result is not None
        assert result["audience"] is None
        assert result["max_price"] == 2
        assert result["vibe"] == "casual"
        assert "indoor_outdoor" not in result

    @patch("app.ui.prompts.questionary.select")
    @patch("app.ui.prompts.questionary.text")
    def test_sights_asks_indoor_outdoor_no_vibe(self, mock_text, mock_select):
        mock_select.return_value.ask.side_effect = ["Any", "Outdoor", "High ($$$)"]
        mock_text.return_value.ask.return_value = ""
        result = _ask_category_refinement(["sights"], "en")
        assert result is not None
        assert result["indoor_outdoor"] == "outdoor"
        assert result["max_price"] == 3
        assert "vibe" not in result

    @patch("app.ui.prompts.questionary.select")
    @patch("app.ui.prompts.questionary.text")
    def test_shopping_skips_both_extras(self, mock_text, mock_select):
        mock_select.return_value.ask.side_effect = ["Any", "Any"]
        result = _ask_category_refinement(["shopping"], "en")
        assert result is not None
        assert "indoor_outdoor" not in result
        assert "vibe" not in result
        assert result["max_price"] is None

    @patch("app.ui.prompts.questionary.select")
    def test_cancel_propagates_none(self, mock_select):
        mock_select.return_value.ask.return_value = None
        assert _ask_category_refinement(["food"], "en") is None


class TestPriceEstimatedBadge:
    def test_displays_estimated_marker(self, capsys):
        places = [{
            "name": "Mystery Bistro",
            "score": 3.5,
            "rating": 4.2,
            "price_level": 2,
            "price_level_source": "llm",
            "user_ratings_total": 50,
            "address": "Somewhere",
        }]
        show_recommendations(places, lang="en")
        out = capsys.readouterr().out
        assert "est." in out


class TestMenuSettings:
    @patch("app.ui.menu.questionary.select")
    def test_run_settings_english(self, mock_select):
        mock_select.return_value.ask.return_value = "English"
        result = run_settings("tr")
        assert result == "en"

    @patch("app.ui.menu.questionary.select")
    def test_run_settings_turkish(self, mock_select):
        mock_select.return_value.ask.return_value = "Türkçe"
        result = run_settings("en")
        assert result == "tr"
