import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from app.eval.golden import load_golden, evaluate_query
from app.eval.budget import TokenBudget
from app.reviews.checker import recommend_places


GOLDEN_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "golden"
EVALS_DIR = Path(__file__).resolve().parent.parent.parent / "evals"


def _expected_from_query(q: dict) -> list[str]:
    for k in ("expected_top_15", "expected_top_10", "expected_top_5", "expected"):
        if k in q:
            return q[k]
    return []


def run_golden(city_filter: str | None = None, top_n: int = 10, profile_override: str | None = None) -> dict:
    files = sorted(GOLDEN_DIR.glob("*.json"))
    if not files:
        print(f"No golden files in {GOLDEN_DIR}", file=sys.stderr)
        return {}

    summary = {"runs": []}
    for path in files:
        data = load_golden(path)
        region = data["region"]
        if city_filter and city_filter.lower() not in region.lower():
            continue
        for q in data.get("queries", []):
            expected = _expected_from_query(q)
            profile = profile_override or q.get("profile", "balanced")
            place_type = q.get("place_type", "restaurant")

            results = recommend_places(
                region,
                place_type=place_type,
                top_n=top_n,
                profile=profile,
                include_details=False,
            )
            metrics = evaluate_query(expected, results, k=min(5, top_n))
            row = {
                "region": region,
                "place_type": place_type,
                "profile": profile,
                "n_results": len(results),
                "n_expected": len(expected),
                **metrics,
                "results": [r["name"] for r in results[:top_n]],
            }
            summary["runs"].append(row)
            _print_row(row)

    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    out = EVALS_DIR / f"golden_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out}")
    return summary


def _print_row(row: dict) -> None:
    print(
        f"\n[{row['region']}] {row['place_type']} · profile={row['profile']}: "
        f"precision@5={row.get('precision@5', '-')}, recall={row.get('recall', '-')}, "
        f"ndcg@5={row.get('ndcg@5', '-')}"
    )
    if row.get("missed"):
        print(f"  missed: {row['missed'][:5]}")
    if row.get("extra"):
        print(f"  extra:  {row['extra'][:5]}")


def run_judge(city_filter: str | None = None, top_n: int = 5, profile_override: str | None = None, baseline: str | None = None) -> dict:
    from app.eval.llm_judge import judge
    budget = TokenBudget()
    files = sorted(GOLDEN_DIR.glob("*.json"))
    rows = []
    for path in files:
        data = load_golden(path)
        region = data["region"]
        if city_filter and city_filter.lower() not in region.lower():
            continue
        for q in data.get("queries", []):
            profile = profile_override or q.get("profile", "balanced")
            place_type = q.get("place_type", "restaurant")
            results = recommend_places(
                region,
                place_type=place_type,
                top_n=top_n,
                profile=profile,
                include_details=True,
            )
            verdict = judge(
                {"region": region, "place_type": place_type, "profile": profile},
                results,
                budget=budget,
            )
            row = {"region": region, "place_type": place_type, "profile": profile, "verdict": verdict}
            if baseline:
                base_results = recommend_places(
                    region,
                    place_type=place_type,
                    top_n=top_n,
                    profile="balanced",
                    include_details=True,
                )
                base_verdict = judge(
                    {"region": region, "place_type": place_type, "profile": "baseline-" + baseline},
                    base_results,
                    budget=budget,
                )
                row["baseline_verdict"] = base_verdict
                row["delta_overall"] = (verdict.get("overall", 0) - base_verdict.get("overall", 0))
            rows.append(row)
            _print_judge_row(row)

    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    out = EVALS_DIR / f"judge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {out}")
    print(budget.report())
    return {"runs": rows}


def _print_judge_row(row: dict) -> None:
    v = row["verdict"]
    print(
        f"\n[{row['region']}] {row['place_type']} · profile={row['profile']}: "
        f"overall={v.get('overall', '-'):.1f} "
        f"(relevance={v.get('relevance', '-')}, diversity={v.get('diversity', '-')}, "
        f"coverage={v.get('coverage', '-')}, freshness={v.get('freshness', '-')})"
    )
    if "delta_overall" in row:
        print(f"  Δ vs baseline: {row['delta_overall']:+.2f}")
    if v.get("rationale"):
        print(f"  rationale: {v['rationale']}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="app.eval.run", description="Evaluate recommendation quality")
    p.add_argument("--city", default=None, help="Filter golden files by region substring (e.g. 'istanbul')")
    p.add_argument("--top-n", type=int, default=10)
    p.add_argument("--profile-override", default=None)
    p.add_argument("--judge", action="store_true", help="Use LLM-as-judge instead of golden lists")
    p.add_argument("--baseline", default=None, help="In judge mode, compare against this baseline label (e.g. 'old_bayesian')")
    args = p.parse_args(argv)

    if args.judge:
        run_judge(city_filter=args.city, top_n=args.top_n, profile_override=args.profile_override, baseline=args.baseline)
    else:
        run_golden(city_filter=args.city, top_n=args.top_n, profile_override=args.profile_override)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
