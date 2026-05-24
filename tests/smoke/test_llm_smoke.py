import pytest
from app.llm.client import translate_text, summarize_text
from app.config import LLM_API_KEY


@pytest.mark.smoke
class TestLLMSmoke:
    def test_translate_to_turkish_real(self):
        if not LLM_API_KEY or LLM_API_KEY == "your_api_key_here":
            pytest.skip("LLM_API_KEY not configured")
        result = translate_text("Istanbul is a beautiful city with great food.", "tr", "en")
        assert len(result) > 10
        assert any(c in result for c in "ıİöÖüÜşŞğĞçÇ")

    def test_summarize_in_turkish_real(self):
        if not LLM_API_KEY or LLM_API_KEY == "your_api_key_here":
            pytest.skip("LLM_API_KEY not configured")
        text = "I visited Istanbul last summer. The Hagia Sophia was amazing. We ate at a great restaurant near Sultanahmet. The Grand Bazaar was crowded but fun."
        result = summarize_text(text, "tr")
        assert len(result) > 10
        assert any(c in result for c in "ıİöÖüÜşŞğĞçÇ")
