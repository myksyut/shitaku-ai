import json
import logging

import httpx
from pydantic import BaseModel, Field

from src.config import settings
from src.infrastructure.external.llm_logger import log_llm_invocation

logger = logging.getLogger(__name__)

# Model IDs (using system-defined inference profiles)
CLAUDE_HAIKU_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def _get_headers() -> dict[str, str] | None:
    """Get headers for Bedrock API requests.

    Returns:
        Headers dict with Bearer token if configured, None otherwise.
    """
    if settings.AWS_BEARER_TOKEN_BEDROCK is None:
        return None

    return {
        "Authorization": f"Bearer {settings.AWS_BEARER_TOKEN_BEDROCK}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def invoke_claude(prompt: str, max_tokens: int = 512) -> str | None:
    """Invoke Claude Haiku 4.5 model via Bedrock.

    Args:
        prompt: The user prompt to send to Claude.
        max_tokens: Maximum number of tokens in the response.

    Returns:
        Generated text response if successful, None otherwise.
    """
    headers = _get_headers()
    if headers is None:
        return None

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }

    url = f"{settings.AWS_BEDROCK_ENDPOINT}/model/{CLAUDE_HAIKU_MODEL_ID}/invoke"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=request_body)
            response.raise_for_status()

            response_body = response.json()
            content = response_body.get("content", [])

            if content and isinstance(content, list) and len(content) > 0:
                first_content = content[0]
                if isinstance(first_content, dict) and first_content.get("type") == "text":
                    result = str(first_content.get("text", ""))
                    log_llm_invocation(prompt, result)
                    return result

            log_llm_invocation(prompt, None)
            return None

    except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
        logger.error("Bedrock API error: %s", e)
        log_llm_invocation(prompt, None)
        return None


def is_bedrock_configured() -> bool:
    """Check if Bedrock API key is configured.

    Returns:
        True if AWS_BEARER_TOKEN_BEDROCK is set, False otherwise.
    """
    return settings.AWS_BEARER_TOKEN_BEDROCK is not None


class ToolBlock(BaseModel):
    """A Claude response content block."""

    type: str
    name: str | None = None
    input: dict[str, object] | None = None


class ToolResponse(BaseModel):
    """Claude content blocks."""

    content: list[ToolBlock] = Field(default_factory=list)


def invoke_claude_tool(prompt: str, tool: dict[str, object], max_tokens: int = 4096) -> dict[str, object] | None:
    """Force one named tool and return only its structured input."""
    headers = _get_headers()
    if headers is None:
        return None
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": tool["name"]},
    }
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{settings.AWS_BEDROCK_ENDPOINT}/model/{CLAUDE_HAIKU_MODEL_ID}/invoke", headers=headers, json=body
            )
            response.raise_for_status()
        parsed = ToolResponse.model_validate(response.json())
        result = next((b.input for b in parsed.content if b.type == "tool_use" and b.name == tool["name"]), None)
        log_llm_invocation(prompt, json.dumps(result, ensure_ascii=False) if result is not None else None)
        return result
    except (httpx.HTTPError, ValueError) as error:
        logger.error("Bedrock tool invocation failed: %s", error)
        log_llm_invocation(prompt, None)
        return None
