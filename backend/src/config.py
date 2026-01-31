from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "FastAPI Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/app"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Supabase
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None
    SUPABASE_DATABASE_URL: str | None = None
    SUPABASE_JWT_SECRET: str | None = None

    # AWS Bedrock (API Key Authentication)
    AWS_BEARER_TOKEN_BEDROCK: str | None = None
    AWS_BEDROCK_ENDPOINT: str = "https://bedrock-runtime.us-east-1.amazonaws.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
