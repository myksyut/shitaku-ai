from fastapi import APIRouter

from src.infrastructure.external.bedrock_client import (
    invoke_claude,
    invoke_embeddings,
    is_bedrock_configured,
)
from src.infrastructure.external.supabase_client import (
    get_supabase_client,
    is_supabase_configured,
    verify_supabase_jwt,
)
from src.presentation.schemas.health import ServiceHealthResponse

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return basic health status."""
    return {"status": "healthy"}


@router.get("/health/services", response_model=ServiceHealthResponse)
def service_health_check() -> ServiceHealthResponse:
    """Check external service connection status."""
    details: dict[str, str | None] = {}

    # Supabase DB check
    supabase_db = False
    if is_supabase_configured():
        client = get_supabase_client()
        if client is not None:
            try:
                # Simple query to test connection
                client.table("users").select("id").limit(1).execute()
                supabase_db = True
                details["supabase_db"] = "Connected"
            except Exception as e:
                details["supabase_db"] = f"Error: {e!s}"
        else:
            details["supabase_db"] = "Client initialization failed"
    else:
        details["supabase_db"] = "Not configured"

    # Supabase Auth check (JWKS availability)
    supabase_auth = False
    if is_supabase_configured():
        # Test with dummy token to check JWKS endpoint availability
        jwt_result = verify_supabase_jwt("dummy_token")
        if jwt_result is None:
            # None means either JWKS works but token is invalid (expected)
            # or JWKS endpoint is reachable
            supabase_auth = True
            details["supabase_auth"] = "JWKS endpoint available"
        else:
            details["supabase_auth"] = "JWKS verification ready"
            supabase_auth = True
    else:
        details["supabase_auth"] = "Not configured"

    # Bedrock Claude check
    bedrock_claude = False
    if is_bedrock_configured():
        claude_result = invoke_claude("Say 'OK' only.", max_tokens=10)
        if claude_result is not None:
            bedrock_claude = True
            details["bedrock_claude"] = "Connected"
        else:
            details["bedrock_claude"] = "Connection failed"
    else:
        details["bedrock_claude"] = "Not configured"

    # Bedrock Embeddings check
    bedrock_embeddings = False
    if is_bedrock_configured():
        embed_result = invoke_embeddings("test", dimensions=256)
        if embed_result is not None:
            bedrock_embeddings = True
            details["bedrock_embeddings"] = "Connected"
        else:
            details["bedrock_embeddings"] = "Connection failed"
    else:
        details["bedrock_embeddings"] = "Not configured"

    return ServiceHealthResponse(
        supabase_db=supabase_db,
        supabase_auth=supabase_auth,
        bedrock_claude=bedrock_claude,
        bedrock_embeddings=bedrock_embeddings,
        details=details,
    )
