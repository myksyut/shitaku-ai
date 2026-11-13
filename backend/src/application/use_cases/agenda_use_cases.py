import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from slack_sdk.errors import SlackApiError, SlackClientError

from src.domain.entities.agenda import Agenda
from src.domain.entities.series import CalendarErrorCode, CreatorAccess, Occurrence, Series, SeriesError, SlackErrorCode
from src.domain.entities.team_memory import ActionItem, Decision, OpenIssue
from src.domain.repositories.dictionary_repository import DictionaryRepository
from src.domain.repositories.knowledge_repository import KnowledgeRepository
from src.domain.repositories.occurrence_repository import OccurrenceRepository
from src.domain.repositories.series_repository import SeriesRepository
from src.domain.repositories.team_memory_repository import TeamMemoryRepository
from src.domain.services.agenda_rules import render_agenda
from src.domain.services.team_memory_rules import with_carry_over
from src.infrastructure.external.series_calendar_mirror import SeriesCalendarMirror
from src.infrastructure.external.series_credentials import CredentialUnavailableError, SeriesCredentials
from src.infrastructure.external.slack_client import SlackMessageData
from src.infrastructure.services.agenda_generation_service import AgendaContext, AgendaGenerationService


def _slack_error_code(error: SlackApiError) -> SlackErrorCode:
    codes: dict[str, SlackErrorCode] = {
        "invalid_auth": "not_connected",
        "not_authed": "not_connected",
        "token_revoked": "not_connected",
        "account_inactive": "not_connected",
        "not_in_channel": "not_in_channel",
        "channel_not_found": "not_in_channel",
        "ratelimited": "rate_limited",
    }
    code = error.response.get("error")
    return codes.get(code, "slack_unavailable") if isinstance(code, str) else "slack_unavailable"


@dataclass(frozen=True, slots=True)
class AgendaSources:
    """Counts and visible errors for the exact persisted agenda inputs."""

    topics: int
    carried_action_items: int
    open_issues: int
    knowledge: int
    slack_messages: int
    slack_error: SlackErrorCode | None
    calendar_error: CalendarErrorCode | None


@dataclass(frozen=True, slots=True)
class GeneratedAgenda:
    """Persisted agenda and its source report."""

    agenda: Agenda
    sources: AgendaSources


class GenerateAgenda:
    """Guarantee required content before adding any optional model proposals."""

    def __init__(
        self,
        series: SeriesRepository,
        content: OccurrenceRepository,
        memory: TeamMemoryRepository,
        knowledge: KnowledgeRepository,
        dictionary: DictionaryRepository,
        credentials: SeriesCredentials,
        mirror: SeriesCalendarMirror,
        writer: AgendaGenerationService,
    ) -> None:
        self.series, self.content, self.memory = series, content, memory
        self.knowledge, self.dictionary = knowledge, dictionary
        self.credentials, self.mirror, self.writer = credentials, mirror, writer

    async def _slack(
        self, series: Series, previous: Occurrence | None, target: Occurrence
    ) -> tuple[list[SlackMessageData], SlackErrorCode | None]:
        if series.slack is None:
            return [], None
        oldest = previous.start_at if previous else target.start_at - timedelta(days=series.slack_message_days)
        now = datetime.now(UTC)
        try:
            client = await self.credentials.slack_for_series(series)
            if client is None:
                return [], None
            messages: list[SlackMessageData] = []
            for channel in series.slack.channels:
                messages.extend(await asyncio.to_thread(client.get_messages, channel.id, oldest, now))
            return sorted(
                (m for m in messages if oldest <= m.posted_at <= now), key=lambda m: float(m.ts), reverse=True
            )[:100], None
        except CredentialUnavailableError as error:
            return [], "not_connected" if error.code == "not_connected" else "slack_unavailable"
        except SlackApiError as error:
            return [], _slack_error_code(error)
        except (SeriesError, SlackClientError):
            return [], "slack_unavailable"

    async def execute(self, access: CreatorAccess, occurrence_id: UUID) -> GeneratedAgenda:
        """Refresh calendar best-effort, then persist deterministic sections and proposals."""
        series = await self.series.get(access.series_id)
        if series is None:
            raise SeriesError(404, "Series not found")
        calendar_error = await self.mirror.refresh(series)
        series = await self.series.get(access.series_id)
        if series is None:
            raise SeriesError(404, "Series not found")
        occurrences = await self.series.occurrences(access.series_id)
        target = next((o for o in occurrences if o.id == occurrence_id), None)
        if target is None:
            raise SeriesError(404, "Occurrence not found")
        if target.is_cancelled:
            raise SeriesError(422, "Occurrence is cancelled")
        now = datetime.now(UTC)
        items = with_carry_over(await self.memory.list_items(access.series_id), occurrences, target.start_at, now)
        carried = sorted(
            (i for i in items if i.closed_at is None and i.origin_start_at < target.start_at),
            key=lambda i: i.origin_start_at,
        )
        actions = tuple(i for i in carried if isinstance(i, ActionItem))
        issues = tuple(i for i in carried if isinstance(i, OpenIssue))
        decisions = tuple(i for i in reversed(carried) if isinstance(i, Decision))[:10]
        previous = [o for o in occurrences if not o.is_cancelled and o.start_at < target.start_at]
        selected_ids = [o.id for o in previous[-series.minutes_count :]] if series.minutes_count else []
        knowledge = await self.knowledge.for_occurrences(access.series_id, selected_ids)
        starts = {o.id: o.start_at for o in previous}
        knowledge.sort(key=lambda k: (starts[k.occurrence_id], k.created_at), reverse=True)
        knowledge = knowledge[: series.minutes_count]
        slack, slack_error = await self._slack(series, previous[-1] if previous else None, target)
        topics = await self.content.topics(access.series_id, occurrence_id)
        context = AgendaContext(
            series.title,
            series.description,
            tuple(topics),
            actions,
            issues,
            decisions,
            tuple(knowledge),
            tuple(slack),
            tuple(await self.dictionary.list_entries(access.series_id)),
        )
        proposal = await self.writer.propose(context)
        agenda = await self.content.save_generated(
            access, occurrence_id, render_agenda(topics, actions, issues, proposal)
        )
        return GeneratedAgenda(
            agenda,
            AgendaSources(
                len(topics), len(actions), len(issues), len(knowledge), len(slack), slack_error, calendar_error
            ),
        )
