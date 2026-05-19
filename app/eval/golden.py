import json
import math
import re
import unicodedata
from pathlib import Path

_TURKISH_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def normalize_name(name: str) -> str:
    if not name:
        return ""
    s = name.translate(_TURKISH_FOLD)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def name_matches(a: str, b: str) -> bool:
    na = normalize_name(a)
    nb = normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na in nb or nb in na:
        return True
    a_tokens = set(na.split())
    b_tokens = set(nb.split())
    if not a_tokens or not b_tokens:
        return False
    overlap = len(a_tokens & b_tokens)
    smaller = min(len(a_tokens), len(b_tokens))
    return overlap / smaller >= 0.6


def load_golden(path: str | Path) -> dict:
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def evaluate_query(expected: list[str], results: list[dict], k: int = 5) -> dict:
    result_names = [r.get("name", "") for r in results]
    top_k = result_names[:k]

    hits_at_k = sum(1 for r in top_k if any(name_matches(r, e) for e in expected))
    precision_k = hits_at_k / k if k else 0.0

    all_hits = sum(1 for e in expected if any(name_matches(e, r) for r in result_names))
    recall = all_hits / len(expected) if expected else 0.0

    ndcg = _ndcg(result_names, expected, k=k)

    missed = [e for e in expected if not any(name_matches(e, r) for r in result_names)]
    extra = [r for r in top_k if not any(name_matches(r, e) for e in expected)]

    return {
        f"precision@{k}": round(precision_k, 3),
        "recall": round(recall, 3),
        f"ndcg@{k}": round(ndcg, 3),
        "missed": missed,
        "extra": extra,
    }


def _ndcg(result_names: list[str], expected: list[str], k: int = 5) -> float:
    dcg = 0.0
    for i, name in enumerate(result_names[:k]):
        rel = 1.0 if any(name_matches(name, e) for e in expected) else 0.0
        dcg += rel / math.log2(i + 2)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(expected))))
    if ideal == 0:
        return 0.0
    return dcg / ideal
