from unittest.mock import patch, MagicMock, call
import pytest
from app.llm.client import translate_to_turkish, summarize_in_turkish, get_client, _chunk_text


def _mock_response(text: str) -> MagicMock:
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp


class TestChunkText:
    def test_short_text_single_chunk(self):
        result = _chunk_text("Hello world", max_chars=100)
        assert len(result) == 1
        assert result[0] == "Hello world"

    def test_long_text_multiple_chunks(self):
        text = "\n".join([f"Paragraph {i} with some content." for i in range(100)])
        result = _chunk_text(text, max_chars=200)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= 250

    def test_empty_text(self):
        result = _chunk_text("", max_chars=100)
        assert len(result) == 1

    def test_chunk_preserves_content(self):
        text = "First paragraph\nSecond paragraph\nThird paragraph"
        result = _chunk_text(text, max_chars=1000)
        assert "First paragraph" in result[0]
        assert "Third paragraph" in result[-1]


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
        assert any("translate" in m.get("content", "").lower() for m in messages)

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

    @patch("app.llm.client.get_client")
    def test_translate_long_text_chunks(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _mock_response("Bölüm 1 çeviri."),
            _mock_response("Bölüm 2 çeviri."),
        ]

        long_text = "A\n" * 2000
        result = translate_to_turkish(long_text, "en")
        assert "Bölüm 1" in result
        assert "Bölüm 2" in result
        assert mock_client.chat.completions.create.call_count == 2

    @patch("app.llm.client.get_client")
    def test_translate_second_chunk_has_continuation_prompt(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _mock_response("Birinci"),
            _mock_response("İkinci"),
        ]

        long_text = "A\n" * 2000
        translate_to_turkish(long_text, "en")
        second_call = mock_client.chat.completions.create.call_args_list[1]
        messages = second_call.kwargs.get("messages") or second_call[1].get("messages")
        system_msg = [m for m in messages if m["role"] == "system"][0]
        assert "Continue" in system_msg["content"]


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

    @patch("app.llm.client.get_client")
    def test_summarize_long_text_chunks_then_merges(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _mock_response("Kısa özet 1."),
            _mock_response("Kısa özet 2."),
            _mock_response("Birleştirilmiş özet."),
        ]

        long_text = "A\n" * 2000
        result = summarize_in_turkish(long_text)
        assert result == "Birleştirilmiş özet."
        assert mock_client.chat.completions.create.call_count == 3


class TestGetClient:
    @patch("app.llm.client.LLM_API_KEY", "test-key")
    def test_get_client_returns_openai_instance(self):
        client = get_client()
        assert hasattr(client, "chat")
