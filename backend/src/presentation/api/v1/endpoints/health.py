from fastapi import APIRouter

from src.presentation.schemas.health import ServiceHealthResponse

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/health/services", response_model=ServiceHealthResponse)
def service_health_check() -> ServiceHealthResponse:
    """外部サービスの接続状態を確認するエンドポイント

    現時点では接続確認は未実装のため、すべてFalseを返す。
    各サービス接続が実装されたタイミングで順次更新する。
    """
    return ServiceHealthResponse(
        supabase_db=False,
        supabase_auth=False,
        bedrock_claude=False,
        bedrock_embeddings=False,
        details={
            "supabase_db": "Not implemented",
            "supabase_auth": "Not implemented",
            "bedrock_claude": "Not implemented",
            "bedrock_embeddings": "Not implemented",
        },
    )
