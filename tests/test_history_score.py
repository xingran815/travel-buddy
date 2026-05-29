"""Tests for the history scoring factor: like/dislike weighting, time decay, and compacted entries."""

from app.profile.history import CompactedEntry
from app.profile.store import UserProfile
from app.reviews.factors import history_score


class TestUnseenAndEmpty:
    def test_no_profile_returns_novelty_baseline(self):
        assert history_score("any_id", None) == 0.55

    def test_empty_place_id_returns_novelty_baseline(self):
        profile = UserProfile()
        assert history_score("", profile) == 0.55

    def test_unseen_place_returns_novelty_baseline(self):
        profile = UserProfile()
        profile.record("other_place", "liked", now=1000.0)
        assert history_score("unseen_place", profile, now=1000.0) == 0.55


class TestVisited:
    def test_visited_only_returns_neutral(self):
        profile = UserProfile()
        profile.record("p1", "visited", now=1000.0)
        # No like/dislike signal, but visited
        assert history_score("p1", profile, now=1000.0) == 0.5


class TestLikedDisliked:
    def test_liked_above_neutral(self):
        profile = UserProfile()
        profile.record("p1", "liked", rating=5, now=1000.0)
        score = history_score("p1", profile, now=1000.0)
        assert score > 0.5
        assert score <= 1.0

    def test_disliked_below_neutral(self):
        profile = UserProfile()
        profile.record("p1", "disliked", now=1000.0)
        score = history_score("p1", profile, now=1000.0)
        assert score < 0.5
        assert score >= 0.0

    def test_high_rating_pushes_higher_than_low_rating(self):
        a = UserProfile()
        a.record("pA", "liked", rating=5, now=1000.0)
        b = UserProfile()
        b.record("pB", "liked", rating=3, now=1000.0)
        sa = history_score("pA", a, now=1000.0)
        sb = history_score("pB", b, now=1000.0)
        assert sa > sb

    def test_mixed_likes_and_dislikes_average(self):
        profile = UserProfile()
        profile.record("p1", "liked", rating=5, now=1000.0)
        profile.record("p1", "disliked", now=1000.0)
        score = history_score("p1", profile, now=1000.0)
        assert 0.0 <= score <= 1.0


class TestDecay:
    def test_old_likes_decay_toward_neutral(self):
        recent = UserProfile()
        recent.record("p", "liked", rating=5, now=1000.0)
        old = UserProfile()
        old.record("p", "liked", rating=5, now=0.0)
        score_recent = history_score("p", recent, now=1000.0)
        score_old = history_score("p", old, now=1000.0 + 86400 * 365 * 5)
        assert score_recent > score_old


class TestCompactedCounts:
    def test_compacted_likes_lift_score(self):
        profile = UserProfile()
        profile.compacted["p"] = CompactedEntry(liked_count=5)
        score = history_score("p", profile, now=1000.0)
        assert score > 0.5

    def test_compacted_dislikes_lower_score(self):
        profile = UserProfile()
        profile.compacted["p"] = CompactedEntry(disliked_count=5)
        score = history_score("p", profile, now=1000.0)
        assert score < 0.5
