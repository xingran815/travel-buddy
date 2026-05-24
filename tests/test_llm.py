from unittest.mock import patch, MagicMock

from app.llm.base import LLMResult
from app.llm.client import translate_text, summarize_text


def _mock_result(text: str) -> LLMResult:
    return LLMResult(text=text)


def _get_messages(mock_chat) -> list[dict]:
    call_args = mock_chat.call_args
    if call_args.args:
        return call_args.args[0]
    return call_args.kwargs.get("messages", [])


class TestTranslateText:
    @patch("app.llm.client.get_provider")
    def test_translate_returns_turkish_text(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("İstanbul güzel bir şehirdir.")

        result = translate_text("Istanbul is a beautiful city.", "tr", "en")
        assert result == "İstanbul güzel bir şehirdir."

    @patch("app.llm.client.get_provider")
    def test_translate_to_english(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Istanbul is a beautiful city.")

        result = translate_text("İstanbul güzel bir şehirdir.", "en", "tr")
        assert result == "Istanbul is a beautiful city."
        messages = _get_messages(provider.chat_text)
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "English" in system_msg["content"]

    @patch("app.llm.client.get_provider")
    def test_translate_strips_whitespace(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("  Özet metin.  ")

        result = translate_text("Some text", "tr", "en")
        assert result == "Özet metin."

    @patch("app.llm.client.get_provider")
    def test_translate_sends_system_prompt(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Çeviri")

        translate_text("Hello", "tr", "en")
        messages = _get_messages(provider.chat_text)
        assert any("translator" in m["role"] or "translate" in m.get("content", "").lower() for m in messages)

    @patch("app.llm.client.get_provider")
    def test_translate_unknown_language(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Çeviri")

        translate_text("Some text", "tr", "unknown")
        messages = _get_messages(provider.chat_text)
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "from" not in user_msg["content"] or "unknown" not in user_msg["content"]


class TestSummarizeText:
    @patch("app.llm.client.get_provider")
    def test_summarize_returns_turkish_summary(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("İstanbul'da gezilecek yerler: Sultanahmet, Kapalıçarşı...")

        result = summarize_text("Long text about Istanbul...", "tr")
        assert "İstanbul" in result

    @patch("app.llm.client.get_provider")
    def test_summarize_uses_turkish_system_prompt(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Özet")

        summarize_text("Some text", "tr")
        messages = _get_messages(provider.chat_text)
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "Türkçe" in system_msg["content"]

    @patch("app.llm.client.get_provider")
    def test_summarize_uses_english_system_prompt(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("Summary")

        summarize_text("Some text", "en")
        messages = _get_messages(provider.chat_text)
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "English" in system_msg["content"]

    @patch("app.llm.client.get_provider")
    def test_summarize_strips_whitespace(self, mock_get_provider):
        provider = MagicMock()
        mock_get_provider.return_value = provider
        provider.chat_text.return_value = _mock_result("  Özet metin.  ")

        result = summarize_text("Text", "tr")
        assert result == "Özet metin."
