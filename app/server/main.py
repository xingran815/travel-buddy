from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.server.routers import summarize, recommend, planner, profile, settings

app = FastAPI(title="TravelBuddy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(summarize.router, prefix="/api")
app.include_router(recommend.router, prefix="/api")
app.include_router(planner.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
