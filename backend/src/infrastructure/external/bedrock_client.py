"""AWS Bedrock client module for Claude and Titan Embeddings invocations."""

import json
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from src.config import settings

# Model IDs
CLAUDE_HAIKU_MODEL_ID = "anthropic.claude-haiku-4-5-20251001-v1:0"
TITAN_EMBEDDINGS_MODEL_ID = "amazon.titan-embed-text-v2:0"


def get_bedrock_client() -> Any | None:
    """Initialize and return a Bedrock Runtime client.

    Returns:
        Boto3 Bedrock Runtime client if credentials are configured, None otherwise.
    """
    if settings.AWS_ACCESS_KEY_ID is None or settings.AWS_SECRET_ACCESS_KEY is None:
        return None

    config = Config(
        region_name=settings.AWS_REGION,
        retries={"max_attempts": 3, "mode": "standard"},
    )

    return boto3.client(
        "bedrock-runtime",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=config,
    )


def invoke_claude(prompt: str, max_tokens: int = 512) -> str | None:
    """Invoke Claude Haiku 4.5 model via Bedrock.

    Args:
        prompt: The user prompt to send to Claude.
        max_tokens: Maximum number of tokens in the response.

    Returns:
        Generated text response if successful, None otherwise.
    """
    client = get_bedrock_client()
    if client is None:
        return None

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }

    try:
        response = client.invoke_model(
            modelId=CLAUDE_HAIKU_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
        )

        response_body = json.loads(response["body"].read())
        content = response_body.get("content", [])

        if content and isinstance(content, list) and len(content) > 0:
            first_content = content[0]
            if isinstance(first_content, dict) and first_content.get("type") == "text":
                return str(first_content.get("text", ""))

        return None

    except (BotoCoreError, ClientError, json.JSONDecodeError, KeyError):
        return None


def invoke_embeddings(text: str, dimensions: int = 1024) -> list[float] | None:
    """Invoke Titan Embeddings V2 model via Bedrock.

    Args:
        text: The input text to generate embeddings for.
        dimensions: The dimension of the output embeddings (256, 512, or 1024).

    Returns:
        List of embedding floats if successful, None otherwise.
    """
    client = get_bedrock_client()
    if client is None:
        return None

    if dimensions not in (256, 512, 1024):
        return None

    request_body = {
        "inputText": text,
        "dimensions": dimensions,
        "normalize": True,
    }

    try:
        response = client.invoke_model(
            modelId=TITAN_EMBEDDINGS_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
        )

        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding")

        if isinstance(embedding, list):
            return [float(x) for x in embedding]

        return None

    except (BotoCoreError, ClientError, json.JSONDecodeError, KeyError):
        return None
