"""RecurringMeetingRepositoryImpl tests with mocked Supabase client."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.domain.entities.recurring_meeting import RecurringMeeting
from src.infrastructure.repositories.recurring_meeting_repository_impl import (
    RecurringMeetingRepositoryImpl,
)


class TestRecurringMeetingRepositoryImpl:
    """RecurringMeetingRepositoryImplのテスト"""

    @pytest.fixture
    def mock_supabase_client(self) -> MagicMock:
        """モック化されたSupabaseクライアントを返す"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_supabase_client: MagicMock) -> RecurringMeetingRepositoryImpl:
        """リポジトリインスタンスを返す"""
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=mock_supabase_client,
        ):
            return RecurringMeetingRepositoryImpl()

    @pytest.fixture
    def sample_meeting(self) -> RecurringMeeting:
        """サンプルのRecurringMeetingエンティティを返す"""
        return RecurringMeeting(
            id=uuid4(),
            user_id=uuid4(),
            google_event_id="google_event_123",
            title="週次定例MTG",
            rrule="FREQ=WEEKLY;BYDAY=MO",
            frequency="weekly",
            attendees=["user1@example.com", "user2@example.com"],
            next_occurrence=datetime(2024, 1, 8, 10, 0, 0),
            agent_id=uuid4(),
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=None,
        )

    def test_get_by_id_success(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """IDで定例MTGを正しく取得できる"""
        # Arrange
        meeting_id = uuid4()
        user_id = uuid4()
        agent_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data={
                "id": str(meeting_id),
                "user_id": str(user_id),
                "google_event_id": "google_event_123",
                "title": "週次定例MTG",
                "rrule": "FREQ=WEEKLY;BYDAY=MO",
                "frequency": "weekly",
                "attendees": ["user1@example.com"],
                "next_occurrence": "2024-01-08T10:00:00",
                "agent_id": str(agent_id),
                "created_at": "2024-01-01T12:00:00",
                "updated_at": None,
            }
        )

        # Act
        result = repository.get_by_id(meeting_id, user_id)

        # Assert
        assert result is not None
        assert result.title == "週次定例MTG"
        assert result.google_event_id == "google_event_123"
        mock_supabase_client.table.assert_called_with("recurring_meetings")

    def test_get_by_id_not_found(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """存在しないIDの場合Noneを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=None)

        # Act
        result = repository.get_by_id(uuid4(), uuid4())

        # Assert
        assert result is None

    def test_get_by_id_returns_none_when_client_is_none(self) -> None:
        """Supabaseクライアントがnullの場合、Noneを返す"""
        # Arrange
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=None,
        ):
            repository = RecurringMeetingRepositoryImpl()

        # Act
        result = repository.get_by_id(uuid4(), uuid4())

        # Assert
        assert result is None

    def test_get_by_google_event_id_success(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Google CalendarイベントIDで定例MTGを正しく取得できる"""
        # Arrange
        meeting_id = uuid4()
        user_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data={
                "id": str(meeting_id),
                "user_id": str(user_id),
                "google_event_id": "google_event_456",
                "title": "月次レビュー",
                "rrule": "FREQ=MONTHLY",
                "frequency": "monthly",
                "attendees": [],
                "next_occurrence": "2024-02-01T14:00:00",
                "agent_id": None,
                "created_at": "2024-01-01T12:00:00",
                "updated_at": None,
            }
        )

        # Act
        result = repository.get_by_google_event_id("google_event_456", user_id)

        # Assert
        assert result is not None
        assert result.google_event_id == "google_event_456"
        assert result.title == "月次レビュー"

    def test_get_by_google_event_id_not_found(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """存在しないGoogle CalendarイベントIDの場合Noneを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=None)

        # Act
        result = repository.get_by_google_event_id("nonexistent_event", uuid4())

        # Assert
        assert result is None

    def test_get_by_google_event_id_returns_none_when_client_is_none(self) -> None:
        """Supabaseクライアントがnullの場合、Noneを返す"""
        # Arrange
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=None,
        ):
            repository = RecurringMeetingRepositoryImpl()

        # Act
        result = repository.get_by_google_event_id("google_event_123", uuid4())

        # Assert
        assert result is None

    def test_get_all_success(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """ユーザーの全定例MTGを取得できる"""
        # Arrange
        user_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(uuid4()),
                    "user_id": str(user_id),
                    "google_event_id": "event_1",
                    "title": "週次定例",
                    "rrule": "FREQ=WEEKLY",
                    "frequency": "weekly",
                    "attendees": ["a@example.com"],
                    "next_occurrence": "2024-01-08T10:00:00",
                    "agent_id": None,
                    "created_at": "2024-01-01T12:00:00",
                    "updated_at": None,
                },
                {
                    "id": str(uuid4()),
                    "user_id": str(user_id),
                    "google_event_id": "event_2",
                    "title": "月次レビュー",
                    "rrule": "FREQ=MONTHLY",
                    "frequency": "monthly",
                    "attendees": ["b@example.com"],
                    "next_occurrence": "2024-02-01T14:00:00",
                    "agent_id": None,
                    "created_at": "2024-01-02T12:00:00",
                    "updated_at": None,
                },
            ]
        )

        # Act
        result = repository.get_all(user_id)

        # Assert
        assert len(result) == 2
        assert result[0].title == "週次定例"
        assert result[1].title == "月次レビュー"

    def test_get_all_empty(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """定例MTGがない場合は空リストを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Act
        result = repository.get_all(uuid4())

        # Assert
        assert result == []

    def test_get_all_returns_empty_when_client_is_none(self) -> None:
        """Supabaseクライアントがnullの場合、空リストを返す"""
        # Arrange
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=None,
        ):
            repository = RecurringMeetingRepositoryImpl()

        # Act
        result = repository.get_all(uuid4())

        # Assert
        assert result == []

    def test_create_success(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
        sample_meeting: RecurringMeeting,
    ) -> None:
        """定例MTGを正しく作成できる"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{}])

        # Act
        result = repository.create(sample_meeting)

        # Assert
        assert result == sample_meeting
        mock_supabase_client.table.assert_called_once_with("recurring_meetings")
        mock_table.insert.assert_called_once()
        insert_data = mock_table.insert.call_args[0][0]
        assert insert_data["title"] == "週次定例MTG"
        assert insert_data["google_event_id"] == "google_event_123"
        assert insert_data["attendees"] == json.dumps(["user1@example.com", "user2@example.com"])

    def test_create_returns_meeting_when_client_is_none(
        self,
        sample_meeting: RecurringMeeting,
    ) -> None:
        """Supabaseクライアントがnullの場合、meetingをそのまま返す"""
        # Arrange
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=None,
        ):
            repository = RecurringMeetingRepositoryImpl()

        # Act
        result = repository.create(sample_meeting)

        # Assert
        assert result == sample_meeting

    def test_update_success(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
        sample_meeting: RecurringMeeting,
    ) -> None:
        """定例MTGを正しく更新できる"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{}])

        # Act
        result = repository.update(sample_meeting)

        # Assert
        assert result == sample_meeting
        mock_supabase_client.table.assert_called_once_with("recurring_meetings")
        mock_table.update.assert_called_once()

    def test_update_returns_meeting_when_client_is_none(
        self,
        sample_meeting: RecurringMeeting,
    ) -> None:
        """Supabaseクライアントがnullの場合、meetingをそのまま返す"""
        # Arrange
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=None,
        ):
            repository = RecurringMeetingRepositoryImpl()

        # Act
        result = repository.update(sample_meeting)

        # Assert
        assert result == sample_meeting

    def test_delete_success(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """定例MTGを正しく削除できる"""
        # Arrange
        meeting_id = uuid4()
        user_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": str(meeting_id)}])

        # Act
        result = repository.delete(meeting_id, user_id)

        # Assert
        assert result is True

    def test_delete_not_found(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """存在しない定例MTGを削除しようとするとFalseを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Act
        result = repository.delete(uuid4(), uuid4())

        # Assert
        assert result is False

    def test_delete_returns_false_when_client_is_none(self) -> None:
        """Supabaseクライアントがnullの場合、Falseを返す"""
        # Arrange
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=None,
        ):
            repository = RecurringMeetingRepositoryImpl()

        # Act
        result = repository.delete(uuid4(), uuid4())

        # Assert
        assert result is False

    def test_exists_returns_true(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """定例MTGが存在する場合Trueを返す"""
        # Arrange
        meeting_id = uuid4()
        user_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": str(meeting_id)}])

        # Act
        result = repository.exists(meeting_id, user_id)

        # Assert
        assert result is True

    def test_exists_returns_false(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """定例MTGが存在しない場合Falseを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Act
        result = repository.exists(uuid4(), uuid4())

        # Assert
        assert result is False

    def test_exists_returns_false_when_client_is_none(self) -> None:
        """Supabaseクライアントがnullの場合、Falseを返す"""
        # Arrange
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=None,
        ):
            repository = RecurringMeetingRepositoryImpl()

        # Act
        result = repository.exists(uuid4(), uuid4())

        # Assert
        assert result is False

    def test_get_unlinked_success(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """エージェント未紐付けの定例MTGを取得できる"""
        # Arrange
        user_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.is_.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(uuid4()),
                    "user_id": str(user_id),
                    "google_event_id": "unlinked_event",
                    "title": "未紐付けMTG",
                    "rrule": "FREQ=WEEKLY",
                    "frequency": "weekly",
                    "attendees": [],
                    "next_occurrence": "2024-01-15T10:00:00",
                    "agent_id": None,
                    "created_at": "2024-01-01T12:00:00",
                    "updated_at": None,
                },
            ]
        )

        # Act
        result = repository.get_unlinked(user_id)

        # Assert
        assert len(result) == 1
        assert result[0].title == "未紐付けMTG"
        assert result[0].agent_id is None

    def test_get_unlinked_empty(
        self,
        repository: RecurringMeetingRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """未紐付けの定例MTGがない場合は空リストを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.is_.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Act
        result = repository.get_unlinked(uuid4())

        # Assert
        assert result == []

    def test_get_unlinked_returns_empty_when_client_is_none(self) -> None:
        """Supabaseクライアントがnullの場合、空リストを返す"""
        # Arrange
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=None,
        ):
            repository = RecurringMeetingRepositoryImpl()

        # Act
        result = repository.get_unlinked(uuid4())

        # Assert
        assert result == []


class TestToEntity:
    """_to_entityメソッドのテスト"""

    @pytest.fixture
    def repository(self) -> RecurringMeetingRepositoryImpl:
        """リポジトリインスタンスを返す"""
        with patch(
            "src.infrastructure.repositories.recurring_meeting_repository_impl.get_supabase_client",
            return_value=None,
        ):
            return RecurringMeetingRepositoryImpl()

    def test_to_entity_with_all_fields(self, repository: RecurringMeetingRepositoryImpl) -> None:
        """全フィールドが正しく変換される"""
        # Arrange
        meeting_id = uuid4()
        user_id = uuid4()
        agent_id = uuid4()
        data = {
            "id": str(meeting_id),
            "user_id": str(user_id),
            "google_event_id": "google_event_123",
            "title": "週次定例MTG",
            "rrule": "FREQ=WEEKLY;BYDAY=MO",
            "frequency": "weekly",
            "attendees": ["user1@example.com", "user2@example.com"],
            "next_occurrence": "2024-01-08T10:00:00",
            "agent_id": str(agent_id),
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T12:00:00",
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.id == meeting_id
        assert result.user_id == user_id
        assert result.title == "週次定例MTG"
        assert result.attendees == ["user1@example.com", "user2@example.com"]
        assert result.agent_id == agent_id
        assert result.updated_at is not None

    def test_to_entity_with_json_string_attendees(self, repository: RecurringMeetingRepositoryImpl) -> None:
        """attendeesがJSON文字列の場合も正しく変換される"""
        # Arrange
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "google_event_id": "google_event_123",
            "title": "テストMTG",
            "rrule": "FREQ=WEEKLY",
            "frequency": "weekly",
            "attendees": json.dumps(["a@example.com", "b@example.com"]),
            "next_occurrence": "2024-01-08T10:00:00",
            "agent_id": None,
            "created_at": "2024-01-01T12:00:00",
            "updated_at": None,
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.attendees == ["a@example.com", "b@example.com"]

    def test_to_entity_with_none_attendees(self, repository: RecurringMeetingRepositoryImpl) -> None:
        """attendeesがNoneの場合は空リストになる"""
        # Arrange
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "google_event_id": "google_event_123",
            "title": "テストMTG",
            "rrule": "FREQ=WEEKLY",
            "frequency": "weekly",
            "attendees": None,
            "next_occurrence": "2024-01-08T10:00:00",
            "agent_id": None,
            "created_at": "2024-01-01T12:00:00",
            "updated_at": None,
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.attendees == []

    def test_to_entity_with_empty_attendees(self, repository: RecurringMeetingRepositoryImpl) -> None:
        """attendeesが空配列の場合はそのまま空リスト"""
        # Arrange
        data: dict[str, str | list[str] | None] = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "google_event_id": "google_event_123",
            "title": "テストMTG",
            "rrule": "FREQ=WEEKLY",
            "frequency": "weekly",
            "attendees": [],
            "next_occurrence": "2024-01-08T10:00:00",
            "agent_id": None,
            "created_at": "2024-01-01T12:00:00",
            "updated_at": None,
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.attendees == []

    def test_to_entity_with_none_agent_id(self, repository: RecurringMeetingRepositoryImpl) -> None:
        """agent_idがNoneの場合はNoneのまま"""
        # Arrange
        data: dict[str, str | list[str] | None] = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "google_event_id": "google_event_123",
            "title": "テストMTG",
            "rrule": "FREQ=WEEKLY",
            "frequency": "weekly",
            "attendees": [],
            "next_occurrence": "2024-01-08T10:00:00",
            "agent_id": None,
            "created_at": "2024-01-01T12:00:00",
            "updated_at": None,
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.agent_id is None

    def test_to_entity_with_none_updated_at(self, repository: RecurringMeetingRepositoryImpl) -> None:
        """updated_atがNoneの場合はNoneのまま"""
        # Arrange
        data: dict[str, str | list[str] | None] = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "google_event_id": "google_event_123",
            "title": "テストMTG",
            "rrule": "FREQ=WEEKLY",
            "frequency": "weekly",
            "attendees": [],
            "next_occurrence": "2024-01-08T10:00:00",
            "agent_id": None,
            "created_at": "2024-01-01T12:00:00",
            "updated_at": None,
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.updated_at is None
