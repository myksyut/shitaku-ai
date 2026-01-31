from pydantic import BaseModel


class ServiceHealthResponse(BaseModel):
    """サービス接続確認レスポンス"""

    supabase_db: bool
    supabase_auth: bool
    bedrock_claude: bool
    bedrock_embeddings: bool
    details: dict[str, str | None]
