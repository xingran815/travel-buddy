"""Tests for itinerary generation, including review/summary inclusion and budget/day handling."""

from unittest.mock import patch, MagicMock

from app.llm.base import LLMResult
from app.planner.generator import generate_plan


def _mock_result(text: str) -> LLMResult:
    return LLMResult(text=text)


def _get_messages(mock_chat) -> list[dict]:
    call_args = mock_chat.call_args
    if call_args.args:
        return call_args.args[0]
    return call_args.kwargs.get("messages", [])


class TestGeneratePlan:
    @patch("app.planner.generator.get_provider")
    def test_generate_plan_returns_text(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("1. Gün: Sultanahmet...")

        result = generate_plan("Istanbul", 500, 3)
        assert "1. Gün" in result or "Gün" in result

    @patch("app.planner.generator.get_provider")
    def test_generate_plan_includes_youtube_summary(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Plan with video tips")

        generate_plan("Istanbul", 500, 3, youtube_summary="Great rooftop bars in Istanbul")
        messages = _get_messages(provider.chat_text)
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "rooftop bars" in user_msg["content"]

    @patch("app.planner.generator.get_provider")
    def test_generate_plan_includes_reviews(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Plan with restaurant")

        reviews = [
            {
                "name": "Nusr-Et",
                "rating": 4.5,
                "address": "Istanbul",
                "price_level": 3,
                "reviews": [{"rating": 5, "text": "Great steak!"}],
            }
        ]
        generate_plan("Istanbul", 500, 3, review_results=reviews)
        messages = _get_messages(provider.chat_text)
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "Nusr-Et" in user_msg["content"]

    @patch("app.planner.generator.get_provider")
    def test_generate_plan_turkish_lang(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Seyahat planı")

        generate_plan("Istanbul", 500, 3, lang="tr")
        messages = _get_messages(provider.chat_text)
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "Türkçe" in system_msg["content"]

    @patch("app.planner.generator.get_provider")
    def test_generate_plan_english_lang(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Travel plan")

        generate_plan("Istanbul", 500, 3, lang="en")
        messages = _get_messages(provider.chat_text)
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "English" in system_msg["content"]

    @patch("app.planner.generator.get_provider")
    def test_generate_plan_passes_budget_and_days(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Plan")

        generate_plan("Istanbul", 1000, 5)
        messages = _get_messages(provider.chat_text)
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "$1000" in user_msg["content"]
        assert "5-day" in user_msg["content"]

    @patch("app.planner.generator.get_provider")
    def test_generate_plan_no_optional_data(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Basic plan")

        generate_plan("Ankara", 300, 2)
        messages = _get_messages(provider.chat_text)
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "YouTube" not in user_msg["content"]
        assert "Recommended Places" not in user_msg["content"]

    @patch("app.planner.generator.get_provider")
    def test_generate_plan_default_review_truncation(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Plan")

        long_text = "A" * 500
        reviews = [
            {
                "name": "Test",
                "rating": 4.5,
                "address": "Addr",
                "reviews": [{"rating": 5, "text": long_text}] * 5,
            }
        ]
        generate_plan("Istanbul", 500, 3, review_results=reviews)
        messages = _get_messages(provider.chat_text)
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert long_text[:300] in user_msg["content"]
        assert long_text[:301] not in user_msg["content"]
        review_lines = [line for line in user_msg["content"].split("\n") if "Review" in line and "5/5" in line]
        assert len(review_lines) == 3

    @patch("app.planner.generator.get_provider")
    def test_generate_plan_custom_review_truncation(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Plan")

        long_text = "B" * 500
        reviews = [
            {
                "name": "Test",
                "rating": 4.5,
                "address": "Addr",
                "reviews": [{"rating": 5, "text": long_text}] * 5,
            }
        ]
        generate_plan("Istanbul", 500, 3, review_results=reviews, max_reviews_per_place=2, max_review_length=50)
        messages = _get_messages(provider.chat_text)
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert long_text[:50] in user_msg["content"]
        assert long_text[:51] not in user_msg["content"]
        review_lines = [line for line in user_msg["content"].split("\n") if "Review" in line and "5/5" in line]
        assert len(review_lines) == 2
