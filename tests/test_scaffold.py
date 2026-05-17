def test_imports():
    from app.config import LLM_BASE_URL, APP_LANG
    from app.i18n.strings import t, STRINGS

    assert isinstance(STRINGS, dict)
    assert callable(t)
