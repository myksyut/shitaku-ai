from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.domain.entities.knowledge import Knowledge
from src.domain.entities.series import SeriesError
from src.infrastructure.external.slack_client import SlackMessageData
from src.infrastructure.services.agenda_generation_service import (
    MAX_AGENDA_INPUT_CHARS,
    AgendaContext,
    AgendaGenerationService,
    build_agenda_prompt,
)
from src.infrastructure.services.meeting_memory_extractor import MAX_INPUT_CHARS, build_extraction_prompt
from tests.unit.test_memory_extraction import context as extraction_context


def agenda_context() -> AgendaContext:
    return AgendaContext("Weekly", None, (), (), (), (), (), (), ())


def test_agenda_notes_and_slack_share_one_budget() -> None:
    now = datetime.now(UTC)
    knowledge = Knowledge(uuid4(), uuid4(), uuid4(), "upload", None, None, "Notes", "n" * 20000, now)
    slack = SlackMessageData("1", "Member", "s" * MAX_AGENDA_INPUT_CHARS, now)
    prompt, truncated = build_agenda_prompt(replace(agenda_context(), knowledge=(knowledge,), slack=(slack,)))
    assert prompt is not None and len(prompt) == MAX_AGENDA_INPUT_CHARS and truncated
    assert "n" * 20000 in prompt and "s" * 1000 in prompt


async def test_optional_proposal_reports_unavailable_model_without_losing_budget_signal() -> None:
    with patch("src.infrastructure.services.agenda_generation_service.invoke_claude", return_value=None) as invoke:
        result = await AgendaGenerationService().propose(agenda_context())
    assert result.content is None and result.truncated is False
    invoke.assert_called_once()


async def test_oversized_agenda_metadata_skips_only_optional_proposals() -> None:
    with patch("src.infrastructure.services.agenda_generation_service.invoke_claude") as invoke:
        result = await AgendaGenerationService().propose(replace(agenda_context(), title="x" * MAX_AGENDA_INPUT_CHARS))
    assert result.content is None and result.truncated
    invoke.assert_not_called()


def test_extraction_truncates_notes_without_cutting_reference_metadata() -> None:
    context = extraction_context()
    source = Knowledge(
        uuid4(), uuid4(), context.occurrence_id, "upload", None, None, "Notes", "x" * MAX_INPUT_CHARS, context.start_at
    )
    prompt, truncated = build_extraction_prompt(replace(context, sources=(source,)))
    assert len(prompt) == MAX_INPUT_CHARS and truncated
    assert '"references"' in prompt and '"A1"' in prompt and '"D1"' in prompt
    with pytest.raises(SeriesError) as error:
        build_extraction_prompt(replace(context, title="x" * MAX_INPUT_CHARS))
    assert error.value.status == 413
