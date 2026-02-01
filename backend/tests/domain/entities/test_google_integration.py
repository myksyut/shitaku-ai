"""GoogleIntegration entity tests."""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.google_integration import GoogleIntegration


class TestGoogleIntegration:
    """GoogleIntegrationエンティティのテスト"""

    def test_create_google_integration(self) -> None:
        """GoogleIntegrationが正しくインスタンス化できる"""
        # Arrange
        integration_id = uuid4()
        user_id = uuid4()
        now = datetime.now()

        # Act
        integration = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="encrypted_token_here",
            granted_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            created_at=now,
            updated_at=None,
        )

        # Assert
        assert integration.id == integration_id
        assert integration.user_id == user_id
        assert integration.email == "test@example.com"
        assert integration.encrypted_refresh_token == "encrypted_token_here"
        assert integration.granted_scopes == ["https://www.googleapis.com/auth/calendar.readonly"]
        assert integration.created_at == now
        assert integration.updated_at is None

    def test_has_scope_returns_true_when_scope_exists(self) -> None:
        """has_scopeは許可済みスコープに対してTrueを返す"""
        # Arrange
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=[
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
            created_at=datetime.now(),
            updated_at=None,
        )

        # Act & Assert
        assert integration.has_scope("https://www.googleapis.com/auth/calendar.readonly") is True
        assert integration.has_scope("https://www.googleapis.com/auth/drive.readonly") is True

    def test_has_scope_returns_false_when_scope_not_exists(self) -> None:
        """has_scopeは未許可スコープに対してFalseを返す"""
        # Arrange
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            created_at=datetime.now(),
            updated_at=None,
        )

        # Act & Assert
        assert integration.has_scope("https://www.googleapis.com/auth/drive.readonly") is False

    def test_has_scope_returns_false_when_scopes_empty(self) -> None:
        """has_scopeはスコープが空の場合Falseを返す"""
        # Arrange
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=[],
            created_at=datetime.now(),
            updated_at=None,
        )

        # Act & Assert
        assert integration.has_scope("https://www.googleapis.com/auth/calendar.readonly") is False

    def test_add_scopes_adds_new_scopes(self) -> None:
        """add_scopesで新しいスコープが追加される"""
        # Arrange
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            created_at=datetime.now(),
            updated_at=None,
        )

        # Act
        integration.add_scopes(["https://www.googleapis.com/auth/drive.readonly"])

        # Assert
        assert "https://www.googleapis.com/auth/calendar.readonly" in integration.granted_scopes
        assert "https://www.googleapis.com/auth/drive.readonly" in integration.granted_scopes
        assert len(integration.granted_scopes) == 2

    def test_add_scopes_updates_updated_at(self) -> None:
        """add_scopesでupdated_atが更新される"""
        # Arrange
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=[],
            created_at=datetime.now(),
            updated_at=None,
        )

        # Act
        integration.add_scopes(["https://www.googleapis.com/auth/calendar.readonly"])

        # Assert
        assert integration.updated_at is not None

    def test_add_scopes_does_not_duplicate_existing_scopes(self) -> None:
        """add_scopesは既存スコープを重複追加しない"""
        # Arrange
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            created_at=datetime.now(),
            updated_at=None,
        )

        # Act
        integration.add_scopes(
            [
                "https://www.googleapis.com/auth/calendar.readonly",  # existing
                "https://www.googleapis.com/auth/drive.readonly",  # new
            ]
        )

        # Assert
        assert len(integration.granted_scopes) == 2
        assert integration.granted_scopes.count("https://www.googleapis.com/auth/calendar.readonly") == 1

    def test_add_scopes_with_empty_list_does_not_change_scopes(self) -> None:
        """add_scopesに空リストを渡してもスコープは変わらない"""
        # Arrange
        original_scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=original_scopes.copy(),
            created_at=datetime.now(),
            updated_at=None,
        )

        # Act
        integration.add_scopes([])

        # Assert
        assert integration.granted_scopes == original_scopes

    def test_update_token(self) -> None:
        """update_tokenでトークンが更新される"""
        # Arrange
        integration = GoogleIntegration(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            encrypted_refresh_token="old_token",
            granted_scopes=[],
            created_at=datetime.now(),
            updated_at=None,
        )

        # Act
        integration.update_token("new_encrypted_token")

        # Assert
        assert integration.encrypted_refresh_token == "new_encrypted_token"
        assert integration.updated_at is not None

    def test_google_integration_equality(self) -> None:
        """同じ値を持つGoogleIntegrationは等しい"""
        # Arrange
        integration_id = uuid4()
        user_id = uuid4()
        now = datetime.now()

        integration1 = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=["scope1"],
            created_at=now,
            updated_at=None,
        )
        integration2 = GoogleIntegration(
            id=integration_id,
            user_id=user_id,
            email="test@example.com",
            encrypted_refresh_token="token",
            granted_scopes=["scope1"],
            created_at=now,
            updated_at=None,
        )

        # Assert
        assert integration1 == integration2
