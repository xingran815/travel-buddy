"""Recommendation endpoints: ranked places, category browse, and metadata.

The heavy ``recommend_places`` / ``recommend_by_categories`` work is synchronous
and CPU/IO-bound, so each handler offloads it to a thread via
``asyncio.to_thread`` to keep the event loop responsive.
"""

import asyncio

from fastapi import APIRouter

from app.i18n.strings import t
from app.profile.store import load_profile
from app.reviews.categories import CATEGORIES, CATEGORY_ORDER
from app.reviews.checker import recommend_by_categories, recommend_places
from app.reviews.profiles import PROFILES
from app.server.schemas import (
    CategoryRecommendRequest,
    CategorySchema,
    RecommendRequest,
)

router = APIRouter()


@router.post("/recommend")
async def recommend(req: RecommendRequest) -> dict:
    """Run the recommendation pipeline for one region and return ranked places."""
    profile = load_profile()
    kwargs = req.model_dump()
    kwargs["user_profile"] = profile
    places = await asyncio.to_thread(recommend_places, **kwargs)
    return {"places": places, "region": req.region, "profile": req.profile}


@router.post("/recommend/categories")
async def recommend_categories(req: CategoryRecommendRequest) -> dict:
    """Recommend places grouped by category, returning ``{results, region}``."""
    profile = load_profile()
    kwargs = req.model_dump()
    category_ids = kwargs.pop("category_ids")
    region = kwargs.pop("region")  # passed positionally below
    kwargs["user_profile"] = profile
    results = await asyncio.to_thread(
        recommend_by_categories, region, category_ids, **kwargs
    )
    return {"results": results, "region": region}


@router.get("/categories")
def list_categories() -> list[CategorySchema]:
    """List browsable categories with English/Turkish names, in display order."""
    out = []
    for cid in CATEGORY_ORDER:
        cat = CATEGORIES[cid]
        out.append(
            CategorySchema(
                id=cid,
                name_en=t(f"category_{cid}", "en"),
                name_tr=t(f"category_{cid}", "tr"),
                google_types=list(cat.google_types),
            )
        )
    return out


@router.get("/profiles")
def list_profiles() -> list[str]:
    """List the available scoring-profile names."""
    return list(PROFILES.keys())
