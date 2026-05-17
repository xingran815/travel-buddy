from unittest.mock import patch, MagicMock
import pytest
from app.planner.generator import generate_plan


def _mock_response(text: str) -> MagicMock:
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp


class TestGeneratePlan:
    @patch("app.planner.generator._get_client")
    def test_generate_plan_returns_text(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("1. Gün: Sultanahmet...")

        result = generate_plan("Istanbul", 500, 3)
        assert "1. Gün" in result or "Gün" in result

    @patch("app.planner.generator._get_client")
    def test_generate_plan_includes_youtube_summary(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("Plan with video tips")

        generate_plan("Istanbul", 500, 3, youtube_summary="Great rooftop bars in Istanbul")
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "rooftop bars" in user_msg["content"]

    @patch("app.planner.generator._get_client")
    def test_generate_plan_includes_reviews(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("Plan with restaurant")

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
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "Nusr-Et" in user_msg["content"]

    @patch("app.planner.generator._get_client")
    def test_generate_plan_turkish_lang(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("Seyahat planı")

        generate_plan("Istanbul", 500, 3, lang="tr")
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "Türkçe" in system_msg["content"]

    @patch("app.planner.generator._get_client")
    def test_generate_plan_english_lang(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("Travel plan")

        generate_plan("Istanbul", 500, 3, lang="en")
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "English" in system_msg["content"]

    @patch("app.planner.generator._get_client")
    def test_generate_plan_passes_budget_and_days(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("Plan")

        generate_plan("Istanbul", 1000, 5)
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "$1000" in user_msg["content"]
        assert "5-day" in user_msg["content"]

    @patch("app.planner.generator._get_client")
    def test_generate_plan_no_optional_data(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("Basic plan")

        generate_plan("Ankara", 300, 2)
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "YouTube" not in user_msg["content"]
        assert "Recommended Places" not in user_msg["content"]
