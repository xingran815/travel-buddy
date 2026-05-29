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
    profile = load_profile()
    kwargs = req.model_dump()
    kwargs["user_profile"] = profile
    places = await asyncio.to_thread(recommend_places, **kwargs)
    return {"places": places, "region": req.region, "profile": req.profile}


@router.post("/recommend/categories")
async def recommend_categories(req: CategoryRecommendRequest) -> dict:
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
    return list(PROFILES.keys())
