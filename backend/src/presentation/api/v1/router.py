from fastapi import APIRouter

from src.presentation.api.v1.endpoints import agents, dictionary, health, meeting_notes, slack

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(dictionary.router)
api_router.include_router(agents.router)
api_router.include_router(slack.router)
api_router.include_router(meeting_notes.router)
