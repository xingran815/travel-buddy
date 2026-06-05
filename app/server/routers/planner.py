"""Itinerary endpoint wrapping ``app/planner/generator.generate_plan``."""

import asyncio

from fastapi import APIRouter

from app.planner.generator import generate_plan
from app.server.schemas import PlanRequest

router = APIRouter()


@router.post("/plan")
async def plan(req: PlanRequest) -> dict:
    """Generate a travel itinerary and return it with the echoed request params."""
    itinerary = await asyncio.to_thread(
        generate_plan,
        destination=req.destination,
        budget=req.budget,
        days=req.days,
        preferences=req.preferences,
        youtube_summary=req.youtube_summary,
        review_results=req.review_results,
        lang=req.lang,
    )
    return {
        "itinerary": itinerary,
        "destination": req.destination,
        "days": req.days,
        "budget": req.budget,
    }
