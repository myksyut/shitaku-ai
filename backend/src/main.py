import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError
from starlette.requests import Request

from src.config import settings
from src.domain.entities.series import SeriesError
from src.presentation.api.v1.router import api_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ルーター登録
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.exception_handler(SeriesError)
    def series_error_handler(request: Request, error: SeriesError) -> JSONResponse:
        return JSONResponse({"detail": error.detail}, status_code=error.status)

    @app.exception_handler(APIError)
    def database_error_handler(request: Request, error: APIError) -> JSONResponse:
        logger.warning("Database API error: code=%s message=%s details=%s", error.code, error.message, error.details)
        code = {"P0002": 404, "42501": 403, "23503": 422, "23514": 422, "23505": 409}.get(error.code or "", 500)
        return JSONResponse({"detail": "Database operation rejected"}, status_code=code)

    return app


app = create_app()
