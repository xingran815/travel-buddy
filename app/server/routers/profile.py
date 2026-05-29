from fastapi import APIRouter

from app.profile.store import load_profile, save_profile
from app.server.schemas import (
    FeedbackRequest,
    HistoryEventSchema,
    ProfileResponse,
    ProfileUpdate,
)

router = APIRouter()


def _profile_to_response(p) -> ProfileResponse:
    return ProfileResponse(
        cuisine_prefs=p.cuisine_prefs,
        default_budget=p.default_budget,
        default_language=p.default_language,
        disliked_keywords=p.disliked_keywords,
        history=[
            HistoryEventSchema(
                place_id=e.place_id,
                action=e.action,
                ts=e.ts,
                rating=e.rating,
            )
            for e in p.history
        ],
    )


@router.get("/profile")
def get_profile() -> ProfileResponse:
    return _profile_to_response(load_profile())


@router.put("/profile")
def update_profile(req: ProfileUpdate) -> ProfileResponse:
    p = load_profile()
    updates = req.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(p, field, value)
    save_profile(p)
    return _profile_to_response(p)


@router.post("/profile/feedback")
def record_feedback(req: FeedbackRequest) -> dict:
    p = load_profile()
    p.record(req.place_id, req.action, req.rating)
    save_profile(p)
    return {"status": "ok"}
