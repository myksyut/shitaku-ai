from fastapi import APIRouter

from src.presentation.api.v1.endpoints import google, health, series, slack, team_memory

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(slack.router)
api_router.include_router(google.router)
api_router.include_router(series.router)
api_router.include_router(series.calendar_router)
api_router.include_router(team_memory.router)
