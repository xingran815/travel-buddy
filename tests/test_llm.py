from unittest.mock import patch, MagicMock

from app.llm.base import LLMResult
from app.llm.client import translate_to_turkish, summarize_in_turkish


def _mock_result(text: str) -> LLMResult:
    return LLMResult(text=text)


def _get_messages(mock_chat) -> list[dict]:
    call_args = mock_chat.call_args
    if call_args.args:
        return call_args.args[0]
    return call_args.kwargs.get("messages", [])


class TestTranslateToTurkish:
    @patch("app.llm.client.get_provider")
    def test_translate_returns_turkish_text(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("İstanbul güzel bir şehirdir.")

        result = translate_to_turkish("Istanbul is a beautiful city.", "en")
        assert result == "İstanbul güzel bir şehirdir."

    @patch("app.llm.client.get_provider")
    def test_translate_strips_whitespace(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("  Özet metin.  ")

        result = translate_to_turkish("Some text", "en")
        assert result == "Özet metin."

    @patch("app.llm.client.get_provider")
    def test_translate_sends_system_prompt(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Çeviri")

        translate_to_turkish("Hello", "en")
        messages = _get_messages(provider.chat_text)
        assert any("translator" in m["role"] or "translate" in m.get("content", "").lower() for m in messages)

    @patch("app.llm.client.get_provider")
    def test_translate_unknown_language(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Çeviri")

        translate_to_turkish("Some text", "unknown")
        messages = _get_messages(provider.chat_text)
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "from" not in user_msg["content"] or "unknown" not in user_msg["content"]


class TestSummarizeInTurkish:
    @patch("app.llm.client.get_provider")
    def test_summarize_returns_turkish_summary(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("İstanbul'da gezilecek yerler: Sultanahmet, Kapalıçarşı...")

        result = summarize_in_turkish("Long text about Istanbul...")
        assert "İstanbul" in result

    @patch("app.llm.client.get_provider")
    def test_summarize_uses_turkish_system_prompt(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Özet")

        summarize_in_turkish("Some text")
        messages = _get_messages(provider.chat_text)
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "Türkçe" in system_msg["content"]

    @patch("app.llm.client.get_provider")
    def test_summarize_strips_whitespace(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("  Özet metin.  ")

        result = summarize_in_turkish("Text")
        assert result == "Özet metin."
