# AGENTS.md

## Setup

```bash
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, GOOGLE_MAPS_API_KEY
```

Config is loaded from `.env` at **import time** as module-level globals (`app/config.py`). Changing `.env` requires restarting the process.

## Linting

```bash
pylint app main.py     # static analysis (config: .pylintrc)
```

## Coding Style

- a source code file shouldn't exceed 330 lines of code (docstrings and comments don't count)
- a function shouldn't exceed 50 lines of code (docstrings and comments don't count)

## Testing

```bash
pytest                                   # all unit tests (excludes smoke)
pytest tests/test_llm.py                # single file
pytest tests/test_llm.py::TestTranslateToTurkish::test_translate_returns_turkish_text  # single test
pytest tests/smoke/ -m smoke            # real API calls (requires .env keys)
pytest -m "not smoke"                   # explicit exclusion (same as bare pytest)
```

319 tests total (316 unit + 3 smoke). Smoke tests are gated with `@pytest.mark.smoke`.

## Two UI Modes

- `python main.py` → interactive menu (questionary/rich, arrow keys, `q` to go back)
- `python main.py summarize <url>` → direct CLI (click subcommands: summarize, recommend, plan)

Both share the same backend modules. The interactive menu lives in `app/ui/menu.py`.

## HTTP Server + SwiftUI Client

There is a third way to drive the same backend: a FastAPI server consumed by a native macOS SwiftUI app.

- **Server**: `app/server/main.py` defines the FastAPI `app` (title "TravelBuddy API"); routers under `app/server/routers/` are mounted under `/api` (`summarize`, `recommend`, `planner`, `profile`, `settings`). `main.py` has **no `__main__` runner** — launch with uvicorn:
  ```bash
  venv/bin/python -m uvicorn app.server.main:app --host 127.0.0.1 --port 8745
  ```
  Endpoints reuse the same backend functions (e.g. `recommend_by_categories`, `recommend_places`); request/response shapes are Pydantic models in `app/server/schemas.py`. The category endpoint `POST /api/recommend/categories` already accepts every refinement field (`max_price`, `audience`, `indoor_outdoor`, `vibe`, `estimate_missing_price`, `llm_*`, …).
- **SwiftUI client**: `TravelBuddy/` (macOS app). Build/test via SwiftPM — **not** the project venv:
  ```bash
  cd TravelBuddy && swift build && swift test
  ```
  Tests live in `TravelBuddy/Tests/TravelBuddyKitTests/`. The app auto-launches the backend itself via `Services/BackendManager.swift` (spawns the uvicorn command above on port **8745**; `baseURL = http://127.0.0.1:8745`).
- **Parity contract**: Swift `Codable` request structs (e.g. `CategoryRecommendRequest`, `RecommendRequest` in `Models/Place.swift`) must mirror the Pydantic schemas field-for-field, or `JSONDecoder` silently drops mismatched keys. When a feature exists in the CLI (`app/ui/menu.py` / `prompts.py`) but feels missing in the app, the gap is usually **client-side UI wiring** (the view-model not sending a field the server already accepts), not the backend.
- **Platform/API note**: package targets `.macOS(.v14)`. Map views use the macOS-14 `Map(position:)` + `MapContentBuilder` (`Annotation`) API — do **not** reintroduce the deprecated `Map(coordinateRegion:annotationItems:)` / `MapAnnotation`. `RecommendViewModel.mapRegion` is a `MapCameraPosition`.

## Architecture Gotchas

- `download_audio()` returns `tuple[str, str]` — `(filepath, video_id)`, not just a path
- `cleanup(video_id)` removes all `video_id.*` files from `downloads/` (wav, webm, mp4, etc.)
- Whisper transcription uses `fp16=torch.cuda.is_available()` to suppress CPU warning
- `recommend_places()` scoring: 8-factor weighted composite in `app/reviews/scoring.py::composite_score` — quality, volume, distance, cost, recency, sentiment, audience, cuisine, aspects. Each factor is normalized to 0..1 in `app/reviews/factors.py`; weights come from named profiles in `app/reviews/profiles.py` (`balanced`/`family`/`adult`/`foodie`/`budget`/`aspect-heavy`). Final score is `Σ(w_i · f_i) × 5`. Quality factor wraps the legacy `_bayesian_score` (still exported for tests).
- Each result carries `score`, `score_breakdown` (weighted contributions per factor, sum to final score), `score_raw` (unweighted 0..1 factor values), `audience_tag`, and `distance_km`.
- Distance uses haversine from a region centroid: explicit `location` if provided, else `_geocode_region(region)` which returns `(center, d_half, search_radius_m)` computed from the viewport diagonal. `search_radius_m` (half the viewport diagonal, capped at 50 km) is passed to `places_nearby()` for geographically diverse results. Falls back to 3.0 km half-life and text search if geocode fails.
- `CLOSED_PERMANENTLY` places are dropped in `search_places`.
- `recommend_places()` supports multi-type search via `place_types` param, deduplication, pagination, price/budget filtering, parallel detail fetching, and new params: `profile`, `cuisine`, `audience` (`"family"`/`"adult"`/`None`), `people`, `query`, `aspects`, `llm_parse`, `llm_rerank`, `llm_summarize`, `llm_aspects`, `lang`.
- LLM features (all gated/opt-in): `app/llm/recommender.py` — `parse_query` (free-form → structured prefs), `rerank_top_k`, `summarize_pros_cons`, `extract_aspects` (cached to `cache/`), `load_aspects_cache`. Supporting modules: `app/llm/prompts.py` (system-prompt strings + `ASPECT_KEYS`; `{lang}` placeholders are filled with `.replace`, not `.format`) and `app/llm/cache.py` (JSON-file cache helpers + `reviews_signature`/`format_review_excerpts`). The `*_CACHE` path globals stay in `recommender.py` so tests can monkeypatch them.
- Type-specific prompts in `app/ui/type_prompts.py` — restaurant asks cuisine, museum asks topic, bar asks vibe, etc.
- Evaluation framework: `python -m app.eval.run` (golden lists at `tests/golden/`) and `python -m app.eval.run --judge` (LLM judge). Token budget tracked per run in `app/eval/budget.py`.
- `_budget_to_max_price()` auto-derives max price level from budget (<$300→1, <$700→2, <$1500→3)
- `generate_plan()` has configurable `max_reviews_per_place` (default 3) and `max_review_length` (default 300)
- Config globals (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `GOOGLE_MAPS_API_KEY`, `APP_LANG`) are set once at import — patch at the module level in tests (e.g. `@patch("app.llm.client.LLM_API_KEY", "test-key")`)

## i18n Rules

- All user-facing strings go in `app/i18n/strings.py` via the `STRINGS` dict
- Every key must have both `"en"` and `"tr"` entries — `test_all_keys_have_both_languages` enforces this
- Use **named** format placeholders: `{region}`, `{count}` — not positional `{}`
- Use `t(key, lang, **kwargs)` to look up and format strings

## Import Convention

No `__init__.py` re-exports. Always use full module paths:
```python
from app.youtube.downloader import download_audio, cleanup
from app.llm.client import translate_to_turkish
```

## Data Flow

```
YouTube URL → download_audio → transcribe → translate_to_turkish → summarize_in_turkish
Region      → _geocode_region → search_places (places_nearby with viewport radius, pagination, price filter) → _deduplicate → composite_score → recommend_places (multi-type, parallel details, budget)
All of above → generate_plan (LLM itinerary)
```

See [design/recommendation-workflow.md](design/recommendation-workflow.md) for a
full prose walkthrough of the recommendation pipeline (triggers, geocoding,
scoring factors, LLM stages, and output shape).
