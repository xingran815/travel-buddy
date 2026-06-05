# Recommendation Workflow

How a place recommendation is produced end to end, from a region name to a ranked,
annotated list. File references point at the functions that do each step.

The orchestrator is [`recommend_places`](../app/reviews/checker.py) in
`app/reviews/checker.py`; everything below is a stage it drives.

## 1. Triggers

A recommendation run starts from one of three entry points, all of which call
`recommend_places` (or `recommend_by_categories`):

- **CLI** — `recommend <region>` in [`main.py`](../main.py), with flags for type,
  budget, profile, and the optional `--llm-*` stages.
- **HTTP server** — `POST /api/recommend` in
  [`app/server/routers/recommend.py`](../app/server/routers/recommend.py), which
  runs the synchronous pipeline in a worker thread via `asyncio.to_thread`. The
  SwiftUI client consumes this.
- **Interactive menu** — the `run_recommend` flow in
  [`app/ui/menu.py`](../app/ui/menu.py), which enables LLM rerank, summaries, and
  missing-price estimation by default.

## 2. Optional query parsing

If `--llm-parse` is set and a free-form `query` is given,
`_merge_parsed_prefs` → [`parse_query`](../app/llm/recommender.py) asks the LLM to
extract structured preferences (cuisine, audience, aspects) and backfills any the
caller left blank.

## 3. Location resolution

`_resolve_search_points` turns the request into search probes:

- With an explicit `--location`, it searches that point at the given radius.
- Otherwise [`_geocode_region`](../app/reviews/search.py) geocodes the region name
  (cached 7 days) and reads the result's **viewport** to derive two values: the
  distance-decay half-life `d_half_km` (≈ a third of the viewport diagonal) and a
  search radius (≈ half the diagonal, capped at 50 km).
- [`_make_search_grid`](../app/reviews/search.py) spreads a large radius into a
  5-point cross (centre + four corners) so coverage doesn't collapse to the city
  centre. Small regions use a single probe.

Geocoding **before** searching is deliberate: searching by viewport radius with
`places_nearby` gives far better geographic spread than a bare text query.

## 4. Candidate retrieval

[`_search_all_types`](../app/reviews/checker.py) runs one
[`search_places`](../app/reviews/search.py) call per (place type × grid point),
concurrently. Each call:

- uses `places_nearby` when a location+radius is present, else a
  `"<type> in <region>"` text search;
- paginates up to `max_pages`, drops permanently-closed venues, and applies the
  price-level pre-filter (`_budget_to_max_price` maps a budget to a hard price cap);
- normalises each result to a common candidate dict.

Search/detail responses are cached in SQLite for 1 day. Results are then merged and
[`_deduplicate`](../app/reviews/search.py)d by place id and normalised name (the
grid points overlap, and chains repeat).

## 5. Scoring

[`score_all`](../app/reviews/pipeline.py) scores every candidate via
[`composite_score`](../app/reviews/scoring.py), which calls each factor in
[`app/reviews/factors.py`](../app/reviews/factors.py). The ten factors, each
normalised to `0–1` (with `0.5` as the neutral "unknown" default):

| Factor | What it measures |
| --- | --- |
| `quality` | Bayesian-adjusted star rating (shrinks low-review places toward 3.5) |
| `volume` | Review count, log-scaled, saturating ~5000 |
| `distance` | `exp(-distance_km / d_half)` proximity decay |
| `cost` | Fit of price level to the per-person budget |
| `recency` | Freshness of reviews, ~1-year decay |
| `sentiment` | Mean review rating rescaled to 0–1 |
| `audience` | Match of inferred adult/family/neutral to preference |
| `cuisine` | Keyword match of name/types to a preferred cuisine |
| `aspects` | Mean of LLM-extracted aspect scores for requested aspects |
| `history` | Personalisation from the user's past likes/dislikes |

Each factor is multiplied by its weight from the chosen **profile**
([`get_profile`](../app/reviews/profiles.py) — `balanced`, `foodie`, `budget`,
`atmosphere`). Profiles reserve a slice for `history`, fold unused
cuisine/audience weight into `quality`, and boost audience when a preference is
stated. The weighted sum is scaled to a `0–5` `score`; each place also carries
`score_breakdown` (weighted contributions) and `score_raw` (unweighted factors).
Results are sorted best-first.

### Personalisation

`history_score` reads the saved [`UserProfile`](../app/profile/store.py) via
`summary_for`, combining recent like/dislike/visit events (time-decayed, ~180-day
half-life) with compacted older tallies. Feedback is recorded with the CLI
`feedback` command or `POST /api/profile/feedback`.

## 6. Detail fetch + missing-price estimation

For the shortlist, [`_fetch_details_batch`](../app/reviews/search.py) fetches
reviews, phone, website, and geometry concurrently (Details is billed separately,
so only the top candidates are enriched). When `estimate_missing_price` is on,
[`fill_missing_prices_and_rescore`](../app/reviews/pipeline.py) asks the LLM to
infer a price level (1–4) from review text for venues Google left unpriced, then
rescores just those and re-sorts.

## 7. Optional LLM rerank / summaries / aspects

[`_apply_llm_rerank_and_summary`](../app/reviews/checker.py) applies the enabled
stages, all in [`app/llm/recommender.py`](../app/llm/recommender.py):

- **rerank** ([`rerank_top_k`](../app/llm/recommender.py)) — the LLM reorders the
  shortlist given the query and prefs, attaching an `llm_rationale` and `llm_rank`.
- **pros/cons** — when rerank and summaries are both on,
  [`rerank_with_pros_cons`](../app/llm/recommender.py) does it in one call;
  otherwise [`summarize_pros_cons_batch`](../app/llm/recommender.py) runs alone.
- **aspects** ([`extract_aspects`](../app/llm/recommender.py)) — scores places
  across an aspect vocabulary, feeding the `aspects` factor.

Each LLM stage is cached in a JSON file keyed by place id (+ language and a review
fingerprint), so repeat runs are cheap and stable.

## 8. Output

Each result is a dict: the place fields, the scoring fields (`score`,
`score_breakdown`, `score_raw`, `audience_tag`, `distance_km`, `d_half_km`),
detail fields (`reviews`, `phone`, `website`), and any LLM annotations (`pros`,
`cons`, `llm_rationale`, `llm_rank`, `price_level_source`).

- The CLI renders this via [`_print_place`](../app/cli/helpers.py); the interactive
  menu via [`show_recommendations`](../app/ui/display.py).
- The server returns `{places, region, profile}`; the SwiftUI client decodes it
  into structs that mirror the Pydantic schemas in
  [`app/server/schemas.py`](../app/server/schemas.py).

## Category browse

[`recommend_by_categories`](../app/reviews/checker.py) runs the same pipeline once
per category (e.g. `food`, `museums`, `nightlife`), expanding each into its Google
place types via [`app/reviews/categories.py`](../app/reviews/categories.py) and
returning `{category_id: [places]}`.
