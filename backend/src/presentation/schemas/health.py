from pydantic import BaseModel


class ServiceHealthResponse(BaseModel):
    """Service health check response schema."""

    supabase_db: bool
    supabase_auth: bool
    bedrock_claude: bool
    bedrock_embeddings: bool
    details: dict[str, str | None]
