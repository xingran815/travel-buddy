from pathlib import Path
from unittest.mock import patch

import pytest

from app.setup_wizard import _append_to_env, missing_keys, run_wizard


class TestMissingKeys:
    def test_returns_empty_when_set(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "fake")
        assert missing_keys("places") == []

    def test_returns_key_when_unset(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
        assert missing_keys("places") == ["GOOGLE_MAPS_API_KEY"]

    def test_unknown_scope_returns_empty(self):
        assert missing_keys("nonsense") == []


class TestAppendToEnv:
    def test_creates_new_file(self, tmp_path):
        path = tmp_path / ".env"
        _append_to_env(path, {"FOO": "bar"})
        assert path.read_text() == "FOO=bar\n"

    def test_appends_to_existing_file_with_newline(self, tmp_path):
        path = tmp_path / ".env"
        path.write_text("OLD=value\n")
        _append_to_env(path, {"NEW": "added"})
        assert "OLD=value" in path.read_text()
        assert "NEW=added" in path.read_text()

    def test_appends_when_existing_lacks_trailing_newline(self, tmp_path):
        path = tmp_path / ".env"
        path.write_text("OLD=value")  # no trailing \n
        _append_to_env(path, {"NEW": "added"})
        contents = path.read_text()
        assert "OLD=value\nNEW=added\n" == contents


class TestRunWizard:
    def test_non_tty_is_noop(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
        with patch("app.setup_wizard.sys.stdin.isatty", return_value=False):
            assert run_wizard("places", env_path=tmp_path / ".env") is False
        assert not (tmp_path / ".env").exists()

    def test_writes_collected_keys(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
        with patch("app.setup_wizard.sys.stdin.isatty", return_value=True), \
             patch("app.setup_wizard.click.prompt", return_value="testkey123"):
            ok = run_wizard("places", env_path=tmp_path / ".env")
        assert ok is True
        assert "GOOGLE_MAPS_API_KEY=testkey123" in (tmp_path / ".env").read_text()

    def test_skips_when_user_enters_nothing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
        with patch("app.setup_wizard.sys.stdin.isatty", return_value=True), \
             patch("app.setup_wizard.click.prompt", return_value=""):
            ok = run_wizard("places", env_path=tmp_path / ".env")
        assert ok is False
        assert not (tmp_path / ".env").exists()

    def test_returns_false_when_nothing_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "already-set")
        with patch("app.setup_wizard.sys.stdin.isatty", return_value=True):
            assert run_wizard("places", env_path=tmp_path / ".env") is False
