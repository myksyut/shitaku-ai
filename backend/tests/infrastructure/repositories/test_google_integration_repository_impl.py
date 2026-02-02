"""GoogleIntegrationRepositoryImpl tests with mocked Supabase client."""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.domain.entities.google_integration import GoogleIntegration
from src.infrastructure.repositories.google_integration_repository_impl import (
    GoogleIntegrationRepositoryImpl,
)


class TestGoogleIntegrationRepositoryImpl:
    """GoogleIntegrationRepositoryImplのテスト"""

    @pytest.fixture
    def mock_supabase_client(self) -> MagicMock:
        """モック化されたSupabaseクライアントを返す"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_supabase_client: MagicMock) -> GoogleIntegrationRepositoryImpl:
        """リポジトリインスタンスを返す"""
        return GoogleIntegrationRepositoryImpl(mock_supabase_client)

    @pytest.fixture
    def sample_integration(self) -> GoogleIntegration:
        """サンプルのGoogleIntegrationエンティティを返す"""
        return GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="encrypted_token",
            granted_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=None,
        )

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: GoogleIntegrationRepositoryImpl,
        mock_supabase_client: MagicMock,
        sample_integration: GoogleIntegration,
    ) -> None:
        """Google連携を正しく作成できる"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{}])

        # Act
        result = await repository.create(sample_integration)

        # Assert
        assert result == sample_integration
        mock_supabase_client.table.assert_called_once_with("google_integrations")
        mock_table.insert.assert_called_once()
        insert_data = mock_table.insert.call_args[0][0]
        assert insert_data["email"] == "test@example.com"
        assert insert_data["granted_scopes"] == ["https://www.googleapis.com/auth/calendar.readonly"]

    @pytest.mark.asyncio
    async def test_create_returns_integration_when_client_is_none(
        self,
        sample_integration: GoogleIntegration,
    ) -> None:
        """Supabaseクライアントがnullの場合、integrationをそのまま返す"""
        # Arrange - client is None (型無視でテスト)
        repository = GoogleIntegrationRepositoryImpl(None)  # type: ignore[arg-type]

        # Act
        result = await repository.create(sample_integration)

        # Assert
        assert result == sample_integration

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        repository: GoogleIntegrationRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """IDでGoogle連携を正しく取得できる"""
        # Arrange
        integration_id = uuid4()
        user_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data={
                "id": str(integration_id),
                "user_id": str(user_id),
                "email": "test@example.com",
                "encrypted_refresh_token": "encrypted_token",
                "granted_scopes": ["scope1", "scope2"],
                "created_at": "2024-01-01T12:00:00",
                "updated_at": None,
            }
        )

        # Act
        result = await repository.get_by_id(integration_id, user_id)

        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        assert result.granted_scopes == ["scope1", "scope2"]

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: GoogleIntegrationRepositoryImpl,
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
        result = await repository.get_by_id(uuid4(), uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_success(
        self,
        repository: GoogleIntegrationRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """メールアドレスでGoogle連携を正しく取得できる"""
        # Arrange
        user_id = uuid4()
        integration_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.maybe_single.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data={
                "id": str(integration_id),
                "user_id": str(user_id),
                "email": "test@example.com",
                "encrypted_refresh_token": "encrypted_token",
                "granted_scopes": [],
                "created_at": "2024-01-01T12:00:00",
                "updated_at": None,
            }
        )

        # Act
        result = await repository.get_by_email(user_id, "test@example.com")

        # Assert
        assert result is not None
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_all_success(
        self,
        repository: GoogleIntegrationRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """ユーザーの全Google連携を取得できる"""
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
                    "email": "test1@example.com",
                    "encrypted_refresh_token": "token1",
                    "granted_scopes": ["scope1"],
                    "created_at": "2024-01-01T12:00:00",
                    "updated_at": None,
                },
                {
                    "id": str(uuid4()),
                    "user_id": str(user_id),
                    "email": "test2@example.com",
                    "encrypted_refresh_token": "token2",
                    "granted_scopes": ["scope2"],
                    "created_at": "2024-01-02T12:00:00",
                    "updated_at": None,
                },
            ]
        )

        # Act
        result = await repository.get_all(user_id)

        # Assert
        assert len(result) == 2
        assert result[0].email == "test1@example.com"
        assert result[1].email == "test2@example.com"

    @pytest.mark.asyncio
    async def test_get_all_empty(
        self,
        repository: GoogleIntegrationRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """連携がない場合は空リストを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Act
        result = await repository.get_all(uuid4())

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: GoogleIntegrationRepositoryImpl,
        mock_supabase_client: MagicMock,
        sample_integration: GoogleIntegration,
    ) -> None:
        """Google連携を正しく更新できる"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{}])

        # Act
        result = await repository.update(sample_integration)

        # Assert
        assert result == sample_integration
        mock_supabase_client.table.assert_called_once_with("google_integrations")
        mock_table.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: GoogleIntegrationRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Google連携を正しく削除できる"""
        # Arrange
        integration_id = uuid4()
        user_id = uuid4()
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": str(integration_id)}])

        # Act
        result = await repository.delete(integration_id, user_id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: GoogleIntegrationRepositoryImpl,
        mock_supabase_client: MagicMock,
    ) -> None:
        """存在しない連携を削除しようとするとFalseを返す"""
        # Arrange
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        # Act
        result = await repository.delete(uuid4(), uuid4())

        # Assert
        assert result is False


class TestToEntity:
    """_to_entityメソッドのテスト"""

    @pytest.fixture
    def mock_supabase_client(self) -> MagicMock:
        """モック化されたSupabaseクライアントを返す"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_supabase_client: MagicMock) -> GoogleIntegrationRepositoryImpl:
        """リポジトリインスタンスを返す"""
        return GoogleIntegrationRepositoryImpl(mock_supabase_client)

    def test_to_entity_with_all_fields(self, repository: GoogleIntegrationRepositoryImpl) -> None:
        """全フィールドが正しく変換される"""
        # Arrange
        integration_id = uuid4()
        user_id = uuid4()
        data = {
            "id": str(integration_id),
            "user_id": str(user_id),
            "email": "test@example.com",
            "encrypted_refresh_token": "token",
            "granted_scopes": ["scope1", "scope2"],
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T12:00:00",
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.id == integration_id
        assert result.user_id == user_id
        assert result.email == "test@example.com"
        assert result.granted_scopes == ["scope1", "scope2"]
        assert result.updated_at is not None

    def test_to_entity_with_none_granted_scopes(self, repository: GoogleIntegrationRepositoryImpl) -> None:
        """granted_scopesがNoneの場合は空リストになる"""
        # Arrange
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "email": "test@example.com",
            "encrypted_refresh_token": "token",
            "granted_scopes": None,
            "created_at": "2024-01-01T12:00:00",
            "updated_at": None,
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.granted_scopes == []

    def test_to_entity_with_empty_granted_scopes(self, repository: GoogleIntegrationRepositoryImpl) -> None:
        """granted_scopesが空配列の場合はそのまま空リスト"""
        # Arrange
        data: dict[str, str | list[str] | None] = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "email": "test@example.com",
            "encrypted_refresh_token": "token",
            "granted_scopes": [],
            "created_at": "2024-01-01T12:00:00",
            "updated_at": None,
        }

        # Act
        result = repository._to_entity(data)

        # Assert
        assert result.granted_scopes == []
