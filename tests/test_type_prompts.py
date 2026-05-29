"""Tests for the place-type-to-prompt mapping and prompt merging across multiple types."""

from app.ui.type_prompts import prompts_for_types, PROMPTS_BY_TYPE, DEFAULT_PROMPTS


class TestPromptsForTypes:
    def test_restaurant_asks_cuisine(self):
        prompts = prompts_for_types(["restaurant"])
        assert "cuisine" in prompts
        assert "audience" in prompts

    def test_museum_asks_topic_not_cuisine(self):
        prompts = prompts_for_types(["museum"])
        assert "topic" in prompts
        assert "cuisine" not in prompts

    def test_bar_asks_vibe(self):
        prompts = prompts_for_types(["bar"])
        assert "vibe" in prompts

    def test_lodging_asks_nights(self):
        prompts = prompts_for_types(["lodging"])
        assert "nights" in prompts
        assert "rooms" in prompts

    def test_multi_type_union_deduped(self):
        prompts = prompts_for_types(["restaurant", "museum"])
        # cuisine from restaurant, topic from museum, both audience (dedup)
        assert "cuisine" in prompts
        assert "topic" in prompts
        assert prompts.count("audience") == 1

    def test_unknown_type_uses_defaults(self):
        prompts = prompts_for_types(["unknown_type"])
        assert prompts == DEFAULT_PROMPTS

    def test_empty_uses_defaults(self):
        assert prompts_for_types([]) == DEFAULT_PROMPTS
        assert prompts_for_types(None) == DEFAULT_PROMPTS

    def test_all_registered_types_have_audience(self):
        # consistent across types so we can always ask audience
        for tp, prompts in PROMPTS_BY_TYPE.items():
            assert "audience" in prompts, f"{tp} missing audience prompt"
