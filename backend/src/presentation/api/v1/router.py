from fastapi import APIRouter

from src.presentation.api.v1.endpoints import (
    agendas,
    agent_dictionary,
    agents,
    calendar,
    dictionary,
    google,
    health,
    knowledge,
    slack,
    transcripts,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(dictionary.router)
api_router.include_router(agents.router)
api_router.include_router(agent_dictionary.router)
api_router.include_router(slack.router)
api_router.include_router(google.router)
api_router.include_router(calendar.router)
api_router.include_router(knowledge.router)
api_router.include_router(agendas.router)
api_router.include_router(transcripts.router)
