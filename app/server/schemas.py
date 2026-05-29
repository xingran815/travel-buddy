"""Pydantic request/response models — the HTTP contract for the FastAPI server.

These mirror the CLI arguments and the pipeline's outputs, and must stay in sync
with the SwiftUI client's ``Codable`` structs (see the parity contract in the
project memory): a field renamed here is a breaking change for the macOS app.
``Request`` models are inbound bodies; ``Response``/``Schema`` models shape what
the routers return.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SummarizeRequest(BaseModel):
    """Body for ``POST /summarize``: a video URL and output language."""

    url: str
    lang: str = "en"


class SummarizeEvent(BaseModel):
    """One server-sent progress event during summarization (step + 0–1 progress)."""

    step: str
    progress: float
    data: dict | None = None


class RecommendRequest(BaseModel):
    """Body for ``POST /recommend`` — mirrors ``recommend_places`` arguments."""

    region: str
    place_type: str = "restaurant"
    place_types: list[str] | None = None
    top_n: int = 5
    max_pages: int = 1
    min_price: int | None = None
    max_price: int | None = None
    budget: float | None = None
    location: tuple[float, float] | None = None
    radius: int | None = None
    include_details: bool = True
    profile: str = "balanced"
    cuisine: str | None = None
    audience: str | None = None
    people: int = 2
    query: str | None = None
    aspects: list[str] | None = None
    indoor_outdoor: str | None = None
    vibe: str | None = None
    estimate_missing_price: bool = False
    llm_parse: bool = False
    llm_rerank: bool = False
    llm_summarize: bool = False
    llm_aspects: bool = False
    lang: str = "en"


class CategoryRecommendRequest(BaseModel):
    """Body for ``POST /recommend/categories`` — mirrors ``recommend_by_categories``."""

    region: str
    category_ids: list[str]
    top_n_per: int = 5
    max_price: int | None = None
    budget: float | None = None
    profile: str = "balanced"
    cuisine: str | None = None
    audience: str | None = None
    people: int = 2
    indoor_outdoor: str | None = None
    vibe: str | None = None
    estimate_missing_price: bool = False
    llm_rerank: bool = False
    llm_summarize: bool = False
    llm_aspects: bool = False
    lang: str = "en"


class PlanRequest(BaseModel):
    """Body for ``POST /plan`` — itinerary inputs, optionally with prior results."""

    destination: str
    budget: float = 500
    days: int = 3
    preferences: str = ""
    youtube_summary: str = ""
    review_results: list[dict] | None = None
    lang: str = "en"


class FeedbackRequest(BaseModel):
    """Body for recording a like/dislike/visit event against a place."""

    place_id: str
    action: Literal["liked", "disliked", "visited"]
    rating: int | None = None


class ProfileUpdate(BaseModel):
    """Partial profile edit — only the provided fields are changed."""

    cuisine_prefs: list[str] | None = None
    default_budget: float | None = None
    default_language: str | None = None
    disliked_keywords: list[str] | None = None


class SettingsUpdate(BaseModel):
    """Partial settings edit (API keys, provider, model, language)."""

    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    google_maps_api_key: str | None = None
    app_lang: str | None = None


class CacheClearRequest(BaseModel):
    """Body for clearing the places cache, the LLM caches, or both."""

    target: Literal["places", "llm", "all"] = "all"


class HealthResponse(BaseModel):
    """Liveness/version payload for the health endpoint."""

    status: str = "ok"
    version: str = "1.0.0"


class SettingsResponse(BaseModel):
    """Current settings, with API keys reported only as set/unset booleans."""

    llm_provider: str
    llm_model: str
    llm_base_url: str
    llm_api_key_set: bool
    google_maps_api_key_set: bool
    app_lang: str


class CacheStatsResponse(BaseModel):
    """On-disk cache sizes/entry counts for the settings screen."""

    places_size_bytes: int = 0
    places_entries: int = 0
    pros_cons_entries: int = 0
    aspects_entries: int = 0


class HistoryEventSchema(BaseModel):
    """One serialized feedback event in a profile's history."""

    place_id: str
    action: str
    ts: float
    rating: int | None = None


class ProfileResponse(BaseModel):
    """The persisted user profile as returned to the client."""

    cuisine_prefs: list[str]
    default_budget: float | None
    default_language: str
    disliked_keywords: list[str]
    history: list[HistoryEventSchema]


class CategorySchema(BaseModel):
    """A browse category with localized names and its Google Place types."""

    id: str
    name_en: str
    name_tr: str
    google_types: list[str]
