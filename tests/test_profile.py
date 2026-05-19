import json
import time
from pathlib import Path

import pytest

from app.profile.history import CompactedEntry, HistoryEvent
from app.profile.store import (
    DEFAULT_KEEP_RECENT,
    UserProfile,
    default_profile_path,
    load_profile,
    save_profile,
)


class TestSummaryFor:
    def test_no_history_returns_none(self):
        profile = UserProfile()
        assert profile.summary_for("p1") is None

    def test_empty_place_id_returns_none(self):
        profile = UserProfile()
        profile.record("p1", "liked", now=1000.0)
        assert profile.summary_for("") is None

    def test_records_events_in_summary(self):
        profile = UserProfile()
        profile.record("p1", "liked", rating=5, now=1000.0)
        profile.record("p1", "visited", now=2000.0)
        summary = profile.summary_for("p1")
        assert summary is not None
        assert len(summary.events) == 2
        actions = [a for a, _, _ in summary.events]
        assert "liked" in actions
        assert "visited" in actions
        assert summary.visited is True

    def test_visited_flag_from_compacted_only(self):
        profile = UserProfile()
        profile.compacted["p1"] = CompactedEntry(visited_count=1, last_seen_ts=500.0)
        summary = profile.summary_for("p1")
        assert summary is not None
        assert summary.visited is True


class TestRecord:
    def test_unknown_action_raises(self):
        profile = UserProfile()
        with pytest.raises(ValueError):
            profile.record("p1", "loved")  # not in ACTIONS

    def test_appends_to_history(self):
        profile = UserProfile()
        profile.record("p1", "liked", now=10.0)
        profile.record("p1", "disliked", now=20.0)
        assert len(profile.history) == 2


class TestCompaction:
    def test_does_not_compact_under_threshold(self):
        profile = UserProfile()
        for i in range(5):
            profile.record(f"p{i}", "liked", now=float(i), keep_recent=10)
        assert len(profile.history) == 5
        assert profile.compacted == {}

    def test_compacts_over_threshold(self):
        profile = UserProfile()
        # 12 events with keep_recent=10 → 2 should compact, 10 remain
        for i in range(12):
            profile.record("p1", "liked", now=float(i), keep_recent=10)
        assert len(profile.history) == 10
        assert profile.compacted["p1"].liked_count == 2

    def test_compacted_tracks_action_buckets(self):
        profile = UserProfile()
        events = [("liked", 1.0), ("disliked", 2.0), ("visited", 3.0), ("liked", 4.0)]
        for action, ts in events:
            profile.record("p1", action, now=ts, keep_recent=1)
        # Only the last event remains uncompacted
        assert len(profile.history) == 1
        c = profile.compacted["p1"]
        assert c.liked_count == 1  # one liked compacted (the other is in history)
        assert c.disliked_count == 1
        assert c.visited_count == 1
        assert c.last_seen_ts == 3.0


class TestPersistence:
    def test_roundtrip(self, tmp_path):
        profile = UserProfile(
            cuisine_prefs=["japanese", "italian"],
            default_audience="adult",
            default_budget=200.0,
            default_language="tr",
            disliked_keywords=["loud"],
        )
        profile.record("p_liked", "liked", rating=5, now=1000.0)
        profile.compacted["p_old"] = CompactedEntry(liked_count=3, last_seen_ts=900.0)

        path = tmp_path / "profile.json"
        save_profile(profile, path)
        loaded = load_profile(path)

        assert loaded.cuisine_prefs == ["japanese", "italian"]
        assert loaded.default_audience == "adult"
        assert loaded.default_budget == 200.0
        assert loaded.default_language == "tr"
        assert loaded.disliked_keywords == ["loud"]
        assert len(loaded.history) == 1
        assert loaded.history[0].place_id == "p_liked"
        assert loaded.history[0].rating == 5
        assert loaded.compacted["p_old"].liked_count == 3

    def test_missing_file_returns_empty_profile(self, tmp_path):
        loaded = load_profile(tmp_path / "nonexistent.json")
        assert loaded.history == []
        assert loaded.compacted == {}

    def test_corrupt_file_returns_empty_profile(self, tmp_path):
        path = tmp_path / "profile.json"
        path.write_text("not-valid-json{")
        loaded = load_profile(path)
        assert loaded.history == []

    def test_save_creates_parent_dir(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "profile.json"
        save_profile(UserProfile(), nested)
        assert nested.exists()

    def test_default_path_uses_xdg_config_home(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        path = default_profile_path()
        assert path == tmp_path / "youtube_summary" / "profile.json"

    def test_default_keep_recent_is_1000(self):
        # Regression: bound history at 1000 most-recent per Phase 3 plan
        assert DEFAULT_KEEP_RECENT == 1000
