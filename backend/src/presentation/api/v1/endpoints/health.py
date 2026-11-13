import httpx
from fastapi import APIRouter

from src.config import settings
from src.infrastructure.external.bedrock_client import invoke_claude, is_bedrock_configured
from src.presentation.schemas.health import ServiceHealthResponse

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return basic process health."""
    return {"status": "healthy"}


@router.get("/health/services", response_model=ServiceHealthResponse)
def service_health_check() -> ServiceHealthResponse:
    """Probe public service endpoints without privileged database access."""
    database = auth = False
    details: dict[str, str | None] = {}
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        try:
            with httpx.Client(timeout=10) as client:
                db = client.get(f"{settings.SUPABASE_URL}/rest/v1/", headers={"apikey": settings.SUPABASE_KEY})
                jwks = client.get(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")
            database, auth = db.is_success, jwks.is_success
        except httpx.HTTPError as error:
            details["supabase"] = str(error)
    claude = is_bedrock_configured() and invoke_claude("Say OK only.", max_tokens=10) is not None
    return ServiceHealthResponse(supabase_db=database, supabase_auth=auth, bedrock_claude=claude, details=details)
