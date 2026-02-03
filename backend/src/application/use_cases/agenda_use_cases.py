"""Use cases for Agenda management.

Application layer use cases following clean architecture principles.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from slack_sdk.errors import SlackApiError

from src.domain.entities.agenda import Agenda
from src.domain.entities.agent import Agent
from src.domain.entities.knowledge import Knowledge
from src.domain.entities.meeting_transcript import MeetingTranscript
from src.domain.repositories.agenda_repository import AgendaRepository
from src.domain.repositories.agent_repository import AgentRepository
from src.domain.repositories.dictionary_repository import DictionaryRepository
from src.domain.repositories.knowledge_repository import KnowledgeRepository
from src.domain.repositories.meeting_transcript_repository import MeetingTranscriptRepository
from src.domain.repositories.recurring_meeting_repository import RecurringMeetingRepository
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
    has_knowledge: bool
    has_slack_messages: bool
    slack_message_count: int
    dictionary_entry_count: int
    has_transcripts: bool = False
    transcript_count: int = 0
    slack_error: str | None = None


class GenerateAgendaUseCase:
    """アジェンダ生成ユースケース."""

    TIMEOUT_SECONDS = 30

    def __init__(
        self,
        agenda_repository: AgendaRepository,
        agent_repository: AgentRepository,
        knowledge_repository: KnowledgeRepository,
        dictionary_repository: DictionaryRepository,
        slack_repository: SlackIntegrationRepository,
        generation_service: AgendaGenerationService,
        recurring_meeting_repository: RecurringMeetingRepository | None = None,
        meeting_transcript_repository: MeetingTranscriptRepository | None = None,
    ) -> None:
        self.agenda_repository = agenda_repository
        self.agent_repository = agent_repository
        self.knowledge_repository = knowledge_repository
        self.dictionary_repository = dictionary_repository
        self.slack_repository = slack_repository
        self.generation_service = generation_service
        self.recurring_meeting_repository = recurring_meeting_repository
        self.meeting_transcript_repository = meeting_transcript_repository

    async def execute(self, user_id: UUID, agent_id: UUID) -> GenerateResult:
        """アジェンダを生成する."""
        # エージェント確認
        agent = self.agent_repository.get_by_id(agent_id, user_id)
        if not agent:
            raise ValueError("Agent not found")

        # データ収集
        latest_knowledge = await self.knowledge_repository.get_latest_by_agent(agent_id, user_id)
        dictionary = await self.dictionary_repository.get_all(user_id)

        # 複数定例からトランスクリプトを収集
        transcripts = await self._collect_transcripts(agent)
        logger.info("Collected %d transcripts total", len(transcripts))

        # Slack取得範囲を計算
        slack_oldest = self._calculate_slack_oldest(agent, transcripts, latest_knowledge)

        # Slackメッセージ取得
        slack_messages = []
        slack_error: str | None = None
        if agent.slack_channel_id and slack_oldest:
            try:
                integrations = await self.slack_repository.get_all(user_id)
                if integrations:
                    integration = integrations[0]
                    token = decrypt_token(integration.encrypted_access_token)
                    client = SlackClient(token)
                    slack_messages = client.get_messages(
                        channel_id=agent.slack_channel_id,
                        oldest=slack_oldest,
                    )
            except SlackApiError as e:
                error_code = e.response.get("error", "")
                if error_code == "not_in_channel":
                    slack_error = (
                        "アプリがチャンネルに追加されていません。Slackでチャンネルにアプリを招待してください。"
                    )
                elif error_code == "ratelimited":
                    slack_error = "Slack APIのレート制限に達しました。しばらく待ってから再試行してください。"
                else:
                    slack_error = f"Slackからメッセージを取得できませんでした: {error_code}"
                logger.warning("Failed to get Slack messages: %s", e)
            except Exception as e:
                slack_error = "Slackからメッセージを取得できませんでした"
                logger.warning("Failed to get Slack messages: %s", e)

        # アジェンダ生成（タイムアウト付き）
        input_data = AgendaGenerationInput(
            latest_knowledge=latest_knowledge,
            slack_messages=slack_messages,
            dictionary=dictionary,
            transcripts=transcripts,
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
            source_knowledge_id=latest_knowledge.id if latest_knowledge else None,
            generated_at=datetime.now(),
            created_at=datetime.now(),
        )

        saved_agenda = await self.agenda_repository.create(agenda)

        return GenerateResult(
            agenda=saved_agenda,
            has_knowledge=latest_knowledge is not None,
            has_slack_messages=len(slack_messages) > 0,
            slack_message_count=len(slack_messages),
            dictionary_entry_count=len(dictionary),
            has_transcripts=len(transcripts) > 0,
            transcript_count=len(transcripts),
            slack_error=slack_error,
        )

    async def _collect_transcripts(self, agent: Agent) -> list[MeetingTranscript]:
        """複数定例からトランスクリプトを収集する.

        Args:
            agent: エージェントエンティティ

        Returns:
            収集したトランスクリプトのリスト（日付降順）
        """
        if not self.recurring_meeting_repository or not self.meeting_transcript_repository:
            return []

        recurring_meetings = await self.recurring_meeting_repository.get_list_by_agent_id(agent.id, agent.user_id)
        logger.info(
            "Collecting transcripts from %d recurring meetings",
            len(recurring_meetings),
        )

        all_transcripts: list[MeetingTranscript] = []
        for meeting in recurring_meetings:
            try:
                transcripts = await self.meeting_transcript_repository.get_by_recurring_meeting(
                    meeting.id, limit=agent.transcript_count
                )
                # 定例会議名をトランスクリプトにセット
                for transcript in transcripts:
                    transcript.recurring_meeting_title = meeting.title
                all_transcripts.extend(transcripts)
            except Exception as e:
                logger.warning(
                    "Failed to collect transcripts for meeting %s: %s",
                    meeting.id,
                    e,
                )
                continue

        # 日付降順でソート
        all_transcripts.sort(key=lambda t: t.meeting_date, reverse=True)
        return all_transcripts

    def _calculate_slack_oldest(
        self,
        agent: Agent,
        transcripts: list[MeetingTranscript],
        latest_knowledge: Knowledge | None,
    ) -> datetime | None:
        """Slack取得範囲の開始日時を計算する.

        Args:
            agent: エージェントエンティティ
            transcripts: 収集したトランスクリプト
            latest_knowledge: 最新のナレッジ

        Returns:
            Slack取得開始日時。取得不要な場合はNone。
        """
        # 最新トランスクリプトの日付があればそれを使用
        if transcripts:
            return transcripts[0].meeting_date

        # ナレッジがあればその日付を使用
        if latest_knowledge:
            return latest_knowledge.meeting_date

        # なければslack_message_days前から
        return datetime.now() - timedelta(days=agent.slack_message_days)


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
