"""Tests for the bilingual string table and the t() lookup helper (fallbacks and placeholders)."""

import pytest
from app.i18n.strings import t, STRINGS


def test_t_default_turkish():
    assert t("welcome") == STRINGS["welcome"]["tr"]


def test_t_english():
    assert t("welcome", "en") == STRINGS["welcome"]["en"]


def test_t_turkish():
    assert t("welcome", "tr") == STRINGS["welcome"]["tr"]


def test_t_with_format_kwargs():
    result = t("fetching_reviews", "en", region="Istanbul")
    assert "Istanbul" in result


def test_t_missing_key_returns_key():
    assert t("nonexistent_key", "en") == "nonexistent_key"


def test_t_missing_lang_falls_back_to_en():
    custom = {"test_key": {"en": "hello"}}
    STRINGS["test_key"] = custom["test_key"]
    assert t("test_key", "xx") == "hello"
    del STRINGS["test_key"]


def test_all_keys_have_both_languages():
    for key, translations in STRINGS.items():
        assert "en" in translations, f"Missing 'en' for key '{key}'"
        assert "tr" in translations, f"Missing 'tr' for key '{key}'"
