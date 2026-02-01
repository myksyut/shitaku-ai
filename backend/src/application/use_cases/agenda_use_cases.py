"""Use cases for Agenda management.

Application layer use cases following clean architecture principles.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities.agenda import Agenda
from src.domain.repositories.agenda_repository import AgendaRepository
from src.domain.repositories.agent_repository import AgentRepository
from src.domain.repositories.dictionary_repository import DictionaryRepository
from src.domain.repositories.meeting_note_repository import MeetingNoteRepository
from src.domain.repositories.slack_integration_repository import SlackIntegrationRepository
from src.infrastructure.external.encryption import decrypt_token
from src.infrastructure.external.slack_client import SlackClient
from src.infrastructure.services.agenda_generation_service import (
    AgendaGenerationInput,
    AgendaGenerationService,
)

logger = logging.getLogger(__name__)


@dataclass
class GenerateResult:
    """アジェンダ生成結果."""

    agenda: Agenda
    has_meeting_note: bool
    has_slack_messages: bool
    slack_message_count: int
    dictionary_entry_count: int


class GenerateAgendaUseCase:
    """アジェンダ生成ユースケース."""

    TIMEOUT_SECONDS = 30

    def __init__(
        self,
        agenda_repository: AgendaRepository,
        agent_repository: AgentRepository,
        note_repository: MeetingNoteRepository,
        dictionary_repository: DictionaryRepository,
        slack_repository: SlackIntegrationRepository,
        generation_service: AgendaGenerationService,
    ) -> None:
        self.agenda_repository = agenda_repository
        self.agent_repository = agent_repository
        self.note_repository = note_repository
        self.dictionary_repository = dictionary_repository
        self.slack_repository = slack_repository
        self.generation_service = generation_service

    async def execute(self, user_id: UUID, agent_id: UUID) -> GenerateResult:
        """アジェンダを生成する."""
        # エージェント確認
        agent = self.agent_repository.get_by_id(agent_id, user_id)
        if not agent:
            raise ValueError("Agent not found")

        # データ収集
        latest_note = await self.note_repository.get_latest_by_agent(agent_id, user_id)
        dictionary = await self.dictionary_repository.get_all(user_id)

        # Slackメッセージ取得
        slack_messages = []
        if agent.slack_channel_id and latest_note:
            try:
                integrations = await self.slack_repository.get_all(user_id)
                if integrations:
                    integration = integrations[0]
                    token = decrypt_token(integration.encrypted_access_token)
                    client = SlackClient(token)
                    slack_messages = client.get_messages(
                        channel_id=agent.slack_channel_id,
                        oldest=latest_note.meeting_date,
                    )
            except Exception as e:
                logger.warning("Failed to get Slack messages: %s", e)

        # アジェンダ生成（タイムアウト付き）
        input_data = AgendaGenerationInput(
            latest_note=latest_note,
            slack_messages=slack_messages,
            dictionary=dictionary,
        )

        try:
            content = await asyncio.wait_for(
                self.generation_service.generate(input_data),
                timeout=self.TIMEOUT_SECONDS,
            )
        except TimeoutError as e:
            raise TimeoutError("Agenda generation timed out") from e

        # アジェンダを保存
        agenda = Agenda(
            id=uuid4(),
            agent_id=agent_id,
            user_id=user_id,
            content=content,
            source_note_id=latest_note.id if latest_note else None,
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )

        saved_agenda = await self.agenda_repository.create(agenda)

        return GenerateResult(
            agenda=saved_agenda,
            has_meeting_note=latest_note is not None,
            has_slack_messages=len(slack_messages) > 0,
            slack_message_count=len(slack_messages),
            dictionary_entry_count=len(dictionary),
        )


class GetAgendasUseCase:
    """アジェンダ一覧取得ユースケース."""

    def __init__(self, repository: AgendaRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        agent_id: UUID,
        user_id: UUID,
        limit: int | None = None,
    ) -> list[Agenda]:
        """エージェントのアジェンダ一覧を取得する."""
        return await self.repository.get_by_agent(agent_id, user_id, limit)


class GetAgendaUseCase:
    """アジェンダ取得ユースケース."""

    def __init__(self, repository: AgendaRepository) -> None:
        self.repository = repository

    async def execute(self, agenda_id: UUID, user_id: UUID) -> Agenda | None:
        """IDでアジェンダを取得する."""
        return await self.repository.get_by_id(agenda_id, user_id)


class UpdateAgendaUseCase:
    """アジェンダ更新ユースケース."""

    def __init__(self, repository: AgendaRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        agenda_id: UUID,
        user_id: UUID,
        content: str,
    ) -> Agenda | None:
        """アジェンダを更新する."""
        agenda = await self.repository.get_by_id(agenda_id, user_id)
        if not agenda:
            return None

        agenda.update_content(content)
        return await self.repository.update(agenda)


class DeleteAgendaUseCase:
    """アジェンダ削除ユースケース."""

    def __init__(self, repository: AgendaRepository) -> None:
        self.repository = repository

    async def execute(self, agenda_id: UUID, user_id: UUID) -> bool:
        """アジェンダを削除する."""
        return await self.repository.delete(agenda_id, user_id)
