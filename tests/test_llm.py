from unittest.mock import patch, MagicMock
import pytest
from app.llm.client import translate_to_turkish, summarize_in_turkish, get_client


def _mock_response(text: str) -> MagicMock:
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp


class TestTranslateToTurkish:
    @patch("app.llm.client.get_client")
    def test_translate_returns_turkish_text(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("İstanbul güzel bir şehirdir.")

        result = translate_to_turkish("Istanbul is a beautiful city.", "en")
        assert result == "İstanbul güzel bir şehirdir."

    @patch("app.llm.client.get_client")
    def test_translate_strips_whitespace(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("  Özet metin.  ")

        result = translate_to_turkish("Some text", "en")
        assert result == "Özet metin."

    @patch("app.llm.client.get_client")
    def test_translate_sends_system_prompt(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("Çeviri")

        translate_to_turkish("Hello", "en")
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        assert any("translator" in m["role"] or "translate" in m.get("content", "").lower() for m in messages)

    @patch("app.llm.client.get_client")
    def test_translate_unknown_language(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("Çeviri")

        translate_to_turkish("Some text", "unknown")
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "from" not in user_msg["content"] or "unknown" not in user_msg["content"]


class TestSummarizeInTurkish:
    @patch("app.llm.client.get_client")
    def test_summarize_returns_turkish_summary(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("İstanbul'da gezilecek yerler: Sultanahmet, Kapalıçarşı...")

        result = summarize_in_turkish("Long text about Istanbul...")
        assert "İstanbul" in result

    @patch("app.llm.client.get_client")
    def test_summarize_uses_turkish_system_prompt(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("Özet")

        summarize_in_turkish("Some text")
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "Türkçe" in system_msg["content"]

    @patch("app.llm.client.get_client")
    def test_summarize_strips_whitespace(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response("  Özet metin.  ")

        result = summarize_in_turkish("Text")
        assert result == "Özet metin."


class TestGetClient:
    @patch("app.llm.client.LLM_API_KEY", "test-key")
    def test_get_client_returns_openai_instance(self):
        client = get_client()
        assert hasattr(client, "chat")
