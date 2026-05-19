import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.eval.golden import normalize_name, name_matches, evaluate_query, load_golden
from app.eval.budget import TokenBudget


class TestNormalize:
    def test_lowercases(self):
        assert normalize_name("Mikla") == "mikla"

    def test_strips_punctuation(self):
        assert normalize_name("Çiya Sofrası") == "ciya sofrasi"

    def test_turkish_fold(self):
        assert normalize_name("Köfteci Yusuf") == "kofteci yusuf"

    def test_empty(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""


class TestNameMatch:
    def test_exact(self):
        assert name_matches("Mikla", "Mikla") is True

    def test_diacritic_insensitive(self):
        assert name_matches("Çiya Sofrası", "Ciya Sofrasi") is True

    def test_substring(self):
        assert name_matches("Hagia Sophia", "Hagia Sophia Museum") is True

    def test_token_overlap(self):
        assert name_matches("Topkapı Palace Museum", "Topkapi Palace") is True

    def test_different_names(self):
        assert name_matches("Mikla", "Septime") is False


class TestEvaluateQuery:
    def test_perfect_precision(self):
        expected = ["A", "B", "C", "D", "E"]
        results = [{"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "D"}, {"name": "E"}]
        m = evaluate_query(expected, results, k=5)
        assert m["precision@5"] == 1.0
        assert m["recall"] == 1.0

    def test_partial(self):
        expected = ["A", "B", "C", "D", "E"]
        results = [{"name": "A"}, {"name": "Z"}, {"name": "B"}, {"name": "Y"}, {"name": "C"}]
        m = evaluate_query(expected, results, k=5)
        assert m["precision@5"] == 0.6  # 3 of 5
        assert m["recall"] == 0.6

    def test_no_match(self):
        m = evaluate_query(["A"], [{"name": "Z"}], k=5)
        assert m["precision@5"] == 0.0
        assert m["recall"] == 0.0

    def test_missed_and_extra(self):
        m = evaluate_query(["A", "B"], [{"name": "A"}, {"name": "Z"}], k=2)
        assert "B" in m["missed"]
        assert "Z" in m["extra"]

    def test_ndcg_rewards_top_positions(self):
        expected = ["A", "B"]
        good = [{"name": "A"}, {"name": "B"}, {"name": "Z"}]
        bad = [{"name": "Z"}, {"name": "A"}, {"name": "B"}]
        g = evaluate_query(expected, good, k=3)
        b = evaluate_query(expected, bad, k=3)
        assert g["ndcg@3"] > b["ndcg@3"]


class TestLoadGolden:
    def test_loads_istanbul(self):
        path = Path(__file__).resolve().parent / "golden" / "istanbul.json"
        data = load_golden(path)
        assert data["region"] == "Istanbul"
        assert any(q["place_type"] == "restaurant" for q in data["queries"])


class TestTokenBudget:
    def test_starts_empty(self):
        b = TokenBudget()
        assert b.estimate_usd() == 0.0
        assert b.calls == 0

    def test_accumulates(self):
        b = TokenBudget()
        usage1 = MagicMock(prompt_tokens=1000, completion_tokens=500)
        usage2 = MagicMock(prompt_tokens=2000, completion_tokens=1000)
        b.add_usage(usage1)
        b.add_usage(usage2)
        assert b.input_tokens == 3000
        assert b.output_tokens == 1500
        assert b.calls == 2
        assert b.estimate_usd() > 0

    def test_handles_none(self):
        b = TokenBudget()
        b.add_usage(None)
        assert b.calls == 0
