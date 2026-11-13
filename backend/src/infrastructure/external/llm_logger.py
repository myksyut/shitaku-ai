import logging

logger = logging.getLogger(__name__)


def log_llm_invocation(prompt: str, response: str | None) -> None:
    """Log an LLM call's sizes and outcome."""
    logger.info(
        "LLM invocation input_chars=%d output_chars=%d succeeded=%s",
        len(prompt),
        len(response) if response is not None else 0,
        response is not None,
    )
