from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SummarizeRequest(BaseModel):
    url: str
    lang: str = "en"


class SummarizeEvent(BaseModel):
    step: str
    progress: float
    data: dict | None = None


class RecommendRequest(BaseModel):
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
    destination: str
    budget: float = 500
    days: int = 3
    preferences: str = ""
    youtube_summary: str = ""
    review_results: list[dict] | None = None
    lang: str = "en"


class FeedbackRequest(BaseModel):
    place_id: str
    action: Literal["liked", "disliked", "visited"]
    rating: int | None = None


class ProfileUpdate(BaseModel):
    cuisine_prefs: list[str] | None = None
    default_budget: float | None = None
    default_language: str | None = None
    disliked_keywords: list[str] | None = None


class SettingsUpdate(BaseModel):
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    google_maps_api_key: str | None = None
    app_lang: str | None = None


class CacheClearRequest(BaseModel):
    target: Literal["places", "llm", "all"] = "all"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"


class SettingsResponse(BaseModel):
    llm_provider: str
    llm_model: str
    llm_base_url: str
    llm_api_key_set: bool
    google_maps_api_key_set: bool
    app_lang: str


class CacheStatsResponse(BaseModel):
    places_size_bytes: int = 0
    places_entries: int = 0
    pros_cons_entries: int = 0
    aspects_entries: int = 0


class HistoryEventSchema(BaseModel):
    place_id: str
    action: str
    ts: float
    rating: int | None = None


class ProfileResponse(BaseModel):
    cuisine_prefs: list[str]
    default_budget: float | None
    default_language: str
    disliked_keywords: list[str]
    history: list[HistoryEventSchema]


class CategorySchema(BaseModel):
    id: str
    name_en: str
    name_tr: str
    google_types: list[str]
