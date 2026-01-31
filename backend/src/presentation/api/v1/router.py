from fastapi import APIRouter

from src.presentation.api.v1.endpoints import dictionary, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(dictionary.router)
