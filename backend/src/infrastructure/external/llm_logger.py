"""LLM logging module for storing prompts and responses to Supabase Storage."""

import json
import logging
import threading
import uuid
from datetime import UTC, datetime

from src.infrastructure.external.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

BUCKET_NAME = "llm-logs"


def _upload_log(trace_id: str, log_data: dict[str, object]) -> None:
    """Upload log data to Supabase Storage (internal, runs in background thread).

    Args:
        trace_id: Unique identifier for this LLM invocation.
        log_data: Dictionary containing log information.
    """
    try:
        client = get_supabase_client()
        if client is None:
            return

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        path = f"{date_str}/{trace_id}.json"
        content = json.dumps(log_data, ensure_ascii=False, indent=2)

        client.storage.from_(BUCKET_NAME).upload(
            path=path,
            file=content.encode("utf-8"),
            file_options={"content-type": "application/json"},
        )
    except Exception as e:
        # fail-silent: ログ失敗は本番機能に影響させない
        logger.warning(f"Failed to upload LLM log: {e}")


def log_llm_invocation(prompt: str, response: str | None) -> None:
    """Log LLM invocation asynchronously (fire-and-forget).

    Args:
        prompt: The input prompt sent to LLM.
        response: The response from LLM (None if failed).
    """
    trace_id = str(uuid.uuid4())
    timestamp = datetime.now(UTC).isoformat()

    log_data: dict[str, object] = {
        "trace_id": trace_id,
        "timestamp": timestamp,
        "request": {"prompt": prompt},
        "response": {"text": response},
    }

    # 非同期でアップロード（fire-and-forget）
    thread = threading.Thread(target=_upload_log, args=(trace_id, log_data), daemon=True)
    thread.start()
