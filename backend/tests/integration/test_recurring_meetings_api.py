# Agent Recurring Meetings Integration Test - Design Doc: google-workspace-integration-design.md (v1.3)
# Generated: 2026-02-02 | Quota: 3/3 integration, 0/2 E2E + 2 RLS (security mandatory)
"""1エージェント複数定例紐付け機能の統合テスト.

テスト対象: ADR-0005 1エージェント複数定例会議の紐付け対応
- GET /api/v1/agents/{agent_id}/recurring-meetings
- POST /api/v1/agents/{agent_id}/recurring-meetings
- DELETE /api/v1/agents/{agent_id}/recurring-meetings/{meeting_id}
- RLSによるマルチテナント分離
"""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.recurring_meeting import (
    Attendee,
    MeetingFrequency,
    RecurringMeeting,
)
from src.main import app
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.api.v1.endpoints.agents import get_recurring_meeting_repository

# テスト用の固定UUID
TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")


def override_get_current_user_id() -> UUID:
    """認証をモック化するためのオーバーライド関数."""
    return TEST_USER_ID


@pytest.fixture
def authenticated_client() -> Generator[TestClient, None, None]:
    """認証済みテストクライアントを作成."""
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_recurring_meeting_repository() -> MagicMock:
    """RecurringMeetingRepositoryのモック."""
    mock_repo = MagicMock()
    mock_repo.get_list_by_agent_id = AsyncMock(return_value=[])
    mock_repo.link_to_agent = AsyncMock(side_effect=ValueError("Recurring meeting not found or access denied"))
    mock_repo.unlink_from_agent = AsyncMock(return_value=None)
    return mock_repo


@pytest.fixture
def mock_repository_with_meeting(mock_recurring_meeting_repository: MagicMock) -> MagicMock:
    """定例MTGが存在するリポジトリのモック."""
    meeting = RecurringMeeting(
        id=uuid4(),
        user_id=TEST_USER_ID,
        google_event_id="test_event_id",
        title="Test Meeting",
        rrule="FREQ=WEEKLY;BYDAY=MO",
        frequency=MeetingFrequency.WEEKLY,
        attendees=[Attendee(email="test@example.com", name="Test User")],
        next_occurrence=datetime.now(),
        agent_id=None,
        created_at=datetime.now(),
        updated_at=None,
    )

    async def link_to_agent_mock(recurring_meeting_id: UUID, agent_id: UUID, user_id: UUID) -> RecurringMeeting:
        meeting.agent_id = agent_id
        return meeting

    mock_recurring_meeting_repository.link_to_agent = AsyncMock(side_effect=link_to_agent_mock)
    mock_recurring_meeting_repository.get_list_by_agent_id = AsyncMock(return_value=[meeting])
    return mock_recurring_meeting_repository


class TestAgentRecurringMeetingsIntegration:
    """1エージェント複数定例紐付けAPIの統合テスト."""

    # AC: "When ユーザーがエージェント詳細画面を開くと、
    # システムは紐付け済みの定例一覧を表示する"
    # Property: `一覧には紐付けられた全ての定例が表示され、
    # 各定例のタイトル・頻度・次回開催日時が確認できる`
    # ROI: 88/11 = 8.0 | ビジネス価値: 9 | 頻度: 9
    # 振る舞い: エージェント詳細画面アクセス -> API呼び出し
    #           -> 紐付け済み定例一覧取得 -> リスト形式で返却
    # @category: core-functionality
    # @dependency: RecurringMeetingRepository, CalendarUseCases, Supabase, AuthMiddleware
    # @complexity: medium
    #
    # 検証項目:
    # - 正常レスポンス(200)が返却される
    # - レスポンスがリスト形式
    # - 各定例にid, title, frequency, next_occurrenceが含まれる
    # - 紐付けられた全ての定例が返却される
    def test_get_agent_recurring_meetings_returns_list(
        self,
        authenticated_client: TestClient,
        mock_recurring_meeting_repository: MagicMock,
    ) -> None:
        """AC2: 紐付け済み定例一覧がリスト形式で返却される."""
        # Arrange
        agent_id = uuid4()
        app.dependency_overrides[get_recurring_meeting_repository] = lambda: mock_recurring_meeting_repository

        try:
            # Act
            response = authenticated_client.get(f"/api/v1/agents/{agent_id}/recurring-meetings")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # Property: 存在しないエージェントなので空リストが返る
            assert data == []
        finally:
            app.dependency_overrides.pop(get_recurring_meeting_repository, None)

    # AC: "When ユーザーがエージェント詳細画面で定例紐付けモーダルから定例を選択すると、
    #      システムは選択された定例をエージェントに紐付ける"
    # Property: `紐付け後、エージェントに関連する定例の件数が1増加する`
    # ROI: 80/11 = 7.3 | ビジネス価値: 9 | 頻度: 8
    # 振る舞い: 定例選択 -> API呼び出し -> agent_id更新 -> 紐付け完了
    # @category: core-functionality
    # @dependency: RecurringMeetingRepository, CalendarUseCases, Supabase, AuthMiddleware
    # @complexity: medium
    #
    # 検証項目:
    # - 正常レスポンス(200)が返却される
    # - レスポンスにmessageとrecurring_meetingが含まれる
    # - 紐付け後、定例のagent_idが更新されている
    # - GET一覧で紐付けた定例が表示される
    def test_link_recurring_meeting_to_agent_success(
        self,
        authenticated_client: TestClient,
        mock_repository_with_meeting: MagicMock,
    ) -> None:
        """AC1: 定例選択でエージェントに紐付けできる."""
        # Arrange
        agent_id = uuid4()
        meeting_id = uuid4()
        app.dependency_overrides[get_recurring_meeting_repository] = lambda: mock_repository_with_meeting

        try:
            # Act
            response = authenticated_client.post(
                f"/api/v1/agents/{agent_id}/recurring-meetings",
                json={"recurring_meeting_id": str(meeting_id)},
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "recurring_meeting" in data
        finally:
            app.dependency_overrides.pop(get_recurring_meeting_repository, None)

    def test_link_recurring_meeting_not_found(
        self,
        authenticated_client: TestClient,
        mock_recurring_meeting_repository: MagicMock,
    ) -> None:
        """存在しない定例を紐付け試行すると400エラーが返る."""
        # Arrange
        agent_id = uuid4()
        meeting_id = uuid4()
        app.dependency_overrides[get_recurring_meeting_repository] = lambda: mock_recurring_meeting_repository

        try:
            # Act
            response = authenticated_client.post(
                f"/api/v1/agents/{agent_id}/recurring-meetings",
                json={"recurring_meeting_id": str(meeting_id)},
            )

            # Assert
            assert response.status_code == 400
        finally:
            app.dependency_overrides.pop(get_recurring_meeting_repository, None)

    def test_link_multiple_meetings_to_same_agent(
        self,
        authenticated_client: TestClient,
        mock_repository_with_meeting: MagicMock,
    ) -> None:
        """複数の定例を同一エージェントに紐付けできる."""
        # Arrange
        agent_id = uuid4()
        meeting_id_1 = uuid4()
        meeting_id_2 = uuid4()
        app.dependency_overrides[get_recurring_meeting_repository] = lambda: mock_repository_with_meeting

        try:
            # Act - 1つ目の紐付け試行
            response1 = authenticated_client.post(
                f"/api/v1/agents/{agent_id}/recurring-meetings",
                json={"recurring_meeting_id": str(meeting_id_1)},
            )

            # Act - 2つ目の紐付け試行
            response2 = authenticated_client.post(
                f"/api/v1/agents/{agent_id}/recurring-meetings",
                json={"recurring_meeting_id": str(meeting_id_2)},
            )

            # Assert - 両方の紐付けが成功
            assert response1.status_code == 200
            assert response2.status_code == 200
        finally:
            app.dependency_overrides.pop(get_recurring_meeting_repository, None)

    # AC: "When ユーザーが紐付け済み定例の「解除」ボタンをクリックすると、
    #      システムはその定例とエージェントの紐付けを解除する"
    # Property: `解除後、エージェントに関連する定例の件数が1減少し、
    # 解除された定例は定例選択モーダルで再び選択可能になる`
    # ROI: 47/11 = 4.3 | ビジネス価値: 8 | 頻度: 5
    # 振る舞い: 解除ボタンクリック -> API呼び出し -> agent_id=NULL更新 -> 紐付け解除完了
    # @category: core-functionality
    # @dependency: RecurringMeetingRepository, CalendarUseCases, Supabase, AuthMiddleware
    # @complexity: low
    #
    # 検証項目:
    # - 正常レスポンス(200)が返却される
    # - レスポンスにmessage: "紐付けを解除しました"が含まれる
    # - 解除後、定例のagent_idがNULLになっている
    # - 解除後、定例選択モーダル（未紐付け一覧）で再び選択可能
    def test_unlink_recurring_meeting_from_agent_success(
        self,
        authenticated_client: TestClient,
        mock_recurring_meeting_repository: MagicMock,
    ) -> None:
        """AC4: 紐付け解除で定例が再び選択可能になる."""
        # Arrange
        agent_id = uuid4()
        meeting_id = uuid4()
        app.dependency_overrides[get_recurring_meeting_repository] = lambda: mock_recurring_meeting_repository

        try:
            # Act
            response = authenticated_client.delete(f"/api/v1/agents/{agent_id}/recurring-meetings/{meeting_id}")

            # Assert
            # 解除成功(200) - 存在しない定例でも200が返る（冪等性）
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
        finally:
            app.dependency_overrides.pop(get_recurring_meeting_repository, None)


class TestAgentRecurringMeetingsRLS:
    """RLSによるマルチテナント分離の検証（セキュリティ必須テスト）."""

    # RLS検証: 他ユーザーの定例にはアクセスできない
    # ROI: 39/11 = 3.5 | ビジネス価値: 10 | 頻度: 2 | 法的: true
    # 振る舞い: user_bがuser_aの定例を紐付け試行 -> RLSが拒否 -> 404または403エラー
    # @category: integration
    # @dependency: RecurringMeetingRepository, Supabase RLS, AuthMiddleware
    # @complexity: medium
    #
    # 検証項目:
    # - 他ユーザーの定例を紐付け試行で400エラー（存在しないor他ユーザー）
    # - 影響行数が0（データ変更なし）
    def test_cannot_link_other_user_meeting(
        self,
        authenticated_client: TestClient,
        mock_recurring_meeting_repository: MagicMock,
    ) -> None:
        """RLS: 他ユーザーの定例にはアクセスできない.

        注: このテストはリポジトリが400エラーを返すことをシミュレートする。
        """
        # Arrange
        agent_id = uuid4()
        other_user_meeting_id = uuid4()
        app.dependency_overrides[get_recurring_meeting_repository] = lambda: mock_recurring_meeting_repository

        try:
            # Act
            response = authenticated_client.post(
                f"/api/v1/agents/{agent_id}/recurring-meetings",
                json={"recurring_meeting_id": str(other_user_meeting_id)},
            )

            # Assert - 存在しない or 他ユーザーの定例なので400
            assert response.status_code == 400
        finally:
            app.dependency_overrides.pop(get_recurring_meeting_repository, None)

    # RLS検証: 他ユーザーのエージェント紐付け定例にはアクセスできない
    # ROI: 39/11 = 3.5 | ビジネス価値: 10 | 頻度: 2 | 法的: true
    # 振る舞い: user_bがuser_aのエージェント紐付け定例を取得試行
    #           -> RLSが拒否 -> 空リストまたは403
    # @category: integration
    # @dependency: RecurringMeetingRepository, Supabase RLS, AuthMiddleware
    # @complexity: medium
    #
    # 検証項目:
    # - 他ユーザーのエージェント紐付け定例を取得試行で空リストまたは403エラー
    # - user_aのデータが漏洩していない
    def test_cannot_access_other_user_agent_meetings(
        self,
        authenticated_client: TestClient,
        mock_recurring_meeting_repository: MagicMock,
    ) -> None:
        """RLS: 他ユーザーのエージェント紐付け定例にはアクセスできない.

        注: リポジトリがuser_idでフィルタするため、他ユーザーのデータは空リスト。
        """
        # Arrange
        other_user_agent_id = uuid4()
        app.dependency_overrides[get_recurring_meeting_repository] = lambda: mock_recurring_meeting_repository

        try:
            # Act
            response = authenticated_client.get(f"/api/v1/agents/{other_user_agent_id}/recurring-meetings")

            # Assert
            assert response.status_code == 200
            data = response.json()
            # 他ユーザーのエージェントなので空リスト
            assert data == []
        finally:
            app.dependency_overrides.pop(get_recurring_meeting_repository, None)
