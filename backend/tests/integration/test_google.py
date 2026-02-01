# Google Integration Test - Design Doc: google-workspace-integration-design.md
# Generated: 2026-02-02 | Quota: 3/3 integration, 0/2 E2E
"""
Google Workspace連携機能の統合テスト

テスト対象: F5 Google Workspace連携
- OAuth認証フローのCSRF防止
- 連携開始からトークン保存までの流れ
- 追加スコープ（Incremental Authorization）
"""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.application.use_cases import google_auth_use_cases
from src.domain.entities.google_integration import GoogleIntegration
from src.infrastructure.external.google_oauth_client import (
    GoogleTokenResponse,
    GoogleUserInfo,
)
from src.main import app
from src.presentation.api.v1.dependencies import get_current_user_id
from src.presentation.api.v1.endpoints.google import get_repository

# テスト用の固定UUID
TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_OTHER_USER_ID = UUID("99999999-9999-9999-9999-999999999999")
TEST_INTEGRATION_ID = UUID("22222222-2222-2222-2222-222222222222")


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


@pytest.fixture(autouse=True)
def clear_state_store() -> Generator[None, None, None]:
    """各テスト前後で_state_storeをクリア（テスト間分離）."""
    google_auth_use_cases._state_store.clear()
    yield
    google_auth_use_cases._state_store.clear()


@pytest.fixture
def mock_google_oauth_client() -> Generator[MagicMock, None, None]:
    """GoogleOAuthClientをモック化."""
    with patch("src.application.use_cases.google_auth_use_cases.GoogleOAuthClient") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        # get_authorization_urlのモック
        mock_instance.get_authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/v2/auth?state=test_state"
        )

        # exchange_codeのモック（非同期）
        mock_instance.exchange_code = AsyncMock(
            return_value=GoogleTokenResponse(
                access_token="test_access_token",
                refresh_token="test_refresh_token",
                expires_in=3600,
                token_type="Bearer",
                scope="openid email profile",
            )
        )

        # get_user_infoのモック（非同期）
        mock_instance.get_user_info = AsyncMock(
            return_value=GoogleUserInfo(
                email="test@example.com",
                name="Test User",
                picture="https://example.com/picture.jpg",
            )
        )

        # parse_scopesのモック（静的メソッド）
        mock_class.parse_scopes.return_value = ["openid", "email", "profile"]

        yield mock_instance


@pytest.fixture
def mock_repository() -> MagicMock:
    """GoogleIntegrationRepositoryをモック化."""
    mock_repo = MagicMock()
    mock_repo.get_all = AsyncMock(return_value=[])
    mock_repo.get_by_id = AsyncMock(return_value=None)
    mock_repo.get_by_email = AsyncMock(return_value=None)
    mock_repo.create = AsyncMock()
    mock_repo.update = AsyncMock()
    mock_repo.delete = AsyncMock(return_value=True)
    return mock_repo


@pytest.fixture
def mock_repository_with_integration(mock_repository: MagicMock) -> MagicMock:
    """既存の連携があるリポジトリをモック化."""
    integration = GoogleIntegration(
        id=TEST_INTEGRATION_ID,
        user_id=TEST_USER_ID,
        email="test@example.com",
        encrypted_refresh_token="encrypted_token",
        granted_scopes=["openid", "email", "profile"],
        created_at=datetime.now(),
        updated_at=None,
    )
    mock_repository.get_all = AsyncMock(return_value=[integration])
    mock_repository.get_by_id = AsyncMock(return_value=integration)
    mock_repository.get_by_email = AsyncMock(return_value=integration)
    return mock_repository


class TestGoogleIntegration:
    """Google Workspace連携の統合テスト"""

    # AC: "When GoogleからOAuthコールバックを受信すると、
    #      システムはstateパラメータを検証しCSRF攻撃を防止する"
    # Property: `callback_state == session_state`
    # ROI: 64/11 = 5.8 | ビジネス価値: 9 | 頻度: 5 | 法的: true
    # 振る舞い: OAuthコールバック受信 -> state検証 -> 一致すれば続行、不一致なら400エラー
    # @category: core-functionality
    # @dependency: GoogleOAuthClient, StateStore
    # @complexity: medium
    #
    # 検証項目:
    # - 正しいstateの場合、302リダイレクトが返却される
    # - 不正なstateの場合、エラーページにリダイレクトされる
    # - CSRF攻撃パターンが拒否される
    def test_oauth_callback_validates_state_csrf_protection(
        self,
        authenticated_client: TestClient,
        mock_google_oauth_client: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """AC2: OAuthコールバックでstateを検証しCSRF攻撃を防止する"""
        # Arrange: OAuth開始でstateを生成しStateStoreに保存
        app.dependency_overrides[get_repository] = lambda: mock_repository

        # 新しい連携を作成するモック設定
        new_integration = GoogleIntegration(
            id=uuid4(),
            user_id=TEST_USER_ID,
            email="test@example.com",
            encrypted_refresh_token="encrypted_token",
            granted_scopes=["openid", "email", "profile"],
            created_at=datetime.now(),
            updated_at=None,
        )
        mock_repository.create = AsyncMock(return_value=new_integration)

        # 暗号化をモック
        with patch("src.application.use_cases.google_auth_use_cases.encrypt_google_token") as mock_encrypt:
            mock_encrypt.return_value = "encrypted_token"

            # OAuth開始でstateを生成
            start_response = authenticated_client.get("/api/v1/google/auth")
            assert start_response.status_code == 200

            # モックが呼ばれた際に渡されたstateを取得
            call_args = mock_google_oauth_client.get_authorization_url.call_args
            valid_state = call_args[1]["state"]

            # Act & Assert (正常系): 正しいstateでコールバック
            response = authenticated_client.get(
                f"/api/v1/google/callback?code=test_code&state={valid_state}",
                follow_redirects=False,
            )

            # リダイレクトが返却される（成功ページへ）
            # FastAPIのRedirectResponseは307を返すことがある
            assert response.status_code in (302, 307)
            assert "/google/success" in response.headers["location"]
            assert "email=test@example.com" in response.headers["location"]

        # Act & Assert (異常系): 不正なstateでコールバック
        response_invalid = authenticated_client.get(
            "/api/v1/google/callback?code=test_code&state=invalid_state",
            follow_redirects=False,
        )

        # リダイレクトが返却される（エラーページへ）
        assert response_invalid.status_code in (302, 307)
        assert "/google/error" in response_invalid.headers["location"]
        # URLエンコードされた "Invalid state" を検証（%20または+）
        location = response_invalid.headers["location"]
        assert "Invalid" in location and "state" in location

        app.dependency_overrides.pop(get_repository, None)

    # AC: "When ユーザーがGoogle連携ボタンをクリックすると、
    #      システムは一意のstateパラメータを生成しStateStoreに保存した上で、
    #      Google OAuth画面へのURLを返す"
    # ROI: 48/11 = 4.4 | ビジネス価値: 8 | 頻度: 5
    # 振る舞い: 連携ボタンクリック -> state生成 -> StateStore保存 -> 認証URL返却
    # @category: core-functionality
    # @dependency: GoogleOAuthClient, StateStore
    # @complexity: low
    #
    # 検証項目:
    # - レスポンスにauthorize_urlが含まれる
    # - URLにstateパラメータが含まれる
    # - stateがStateStoreに保存されている
    def test_start_google_oauth_generates_state(
        self,
        authenticated_client: TestClient,
        mock_google_oauth_client: MagicMock,
    ) -> None:
        """AC1: Google連携開始でstateを生成しOAuth URLを返す"""
        # Arrange: 認証済みユーザー（authenticated_clientで準備済み）

        # Act: GET /api/v1/google/auth
        response = authenticated_client.get("/api/v1/google/auth")

        # Assert: 200レスポンス
        assert response.status_code == 200

        # Assert: レスポンスにauthorize_urlが含まれる
        data = response.json()
        assert "authorize_url" in data
        authorize_url = data["authorize_url"]

        # Assert: URLにstateパラメータが含まれる
        assert "state=" in authorize_url

        # Assert: stateがStateStoreに保存されている
        # モックが呼ばれた際に渡されたstateを確認
        assert mock_google_oauth_client.get_authorization_url.called
        call_args = mock_google_oauth_client.get_authorization_url.call_args
        actual_state = call_args[1]["state"]
        assert actual_state in google_auth_use_cases._state_store

        # Assert: stateに紐づくユーザーIDが正しい
        user_id, _, _ = google_auth_use_cases._state_store[actual_state]
        assert user_id == TEST_USER_ID

    # AC: "When ユーザーがGoogle連携一覧を取得すると、
    #      システムは該当ユーザーの全連携情報を返す"
    # ROI: 32/8 = 4.0 | ビジネス価値: 6 | 頻度: 6
    # 振る舞い: 連携一覧要求 -> ユーザーID検証 -> DB検索 -> 連携情報返却
    # @category: core-functionality
    # @dependency: GoogleIntegrationRepository
    # @complexity: low
    #
    # 検証項目:
    # - 認証済みユーザーの連携のみが返却される
    # - 他ユーザーの連携は含まれない
    # - 連携がない場合は空配列が返却される
    def test_get_google_integrations_returns_user_integrations(
        self,
        authenticated_client: TestClient,
        mock_repository_with_integration: MagicMock,
    ) -> None:
        """AC3: Google連携一覧取得でユーザーの連携のみ返す"""
        # Arrange: リポジトリをモックに差し替え
        app.dependency_overrides[get_repository] = lambda: mock_repository_with_integration

        try:
            # Act: GET /api/v1/google/integrations
            response = authenticated_client.get("/api/v1/google/integrations")

            # Assert: 200レスポンス
            assert response.status_code == 200

            # Assert: 認証ユーザーの連携のみが返却される
            data = response.json()
            assert len(data) == 1
            integration = data[0]

            # Assert: 各連携にid, email, granted_scopes, created_at, updated_atが含まれる
            assert "id" in integration
            assert integration["email"] == "test@example.com"
            assert "granted_scopes" in integration
            assert "openid" in integration["granted_scopes"]
            assert "created_at" in integration
            assert "updated_at" in integration

            # Assert: リポジトリがユーザーIDで呼び出されている
            mock_repository_with_integration.get_all.assert_called_once_with(TEST_USER_ID)
        finally:
            app.dependency_overrides.pop(get_repository, None)

    def test_get_google_integrations_returns_empty_when_no_integrations(
        self,
        authenticated_client: TestClient,
        mock_repository: MagicMock,
    ) -> None:
        """連携がない場合は空配列が返却される"""
        # Arrange: 空のリポジトリをモックに差し替え
        app.dependency_overrides[get_repository] = lambda: mock_repository

        try:
            # Act: GET /api/v1/google/integrations
            response = authenticated_client.get("/api/v1/google/integrations")

            # Assert: 200レスポンスで空配列
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.pop(get_repository, None)

    # AC: "When ユーザーがGoogle連携を削除すると、
    #      システムは該当連携を削除し204を返す"
    # ROI: 24/6 = 4.0 | ビジネス価値: 5 | 頻度: 3
    # 振る舞い: 削除要求 -> 所有権検証 -> DB削除 -> 204返却
    # @category: core-functionality
    # @dependency: GoogleIntegrationRepository
    # @complexity: low
    #
    # 検証項目:
    # - 所有する連携の削除で204が返却される
    # - 他ユーザーの連携削除で404が返却される
    # - 存在しない連携削除で404が返却される
    def test_delete_google_integration_removes_integration(
        self,
        authenticated_client: TestClient,
        mock_repository_with_integration: MagicMock,
    ) -> None:
        """AC4: Google連携削除で204を返す"""
        # Arrange: リポジトリをモックに差し替え
        app.dependency_overrides[get_repository] = lambda: mock_repository_with_integration

        try:
            # Act: DELETE /api/v1/google/integrations/{integration_id}
            response = authenticated_client.delete(f"/api/v1/google/integrations/{TEST_INTEGRATION_ID}")

            # Assert: 204レスポンス
            assert response.status_code == 204

            # Assert: リポジトリのdeleteが正しく呼び出されている
            mock_repository_with_integration.delete.assert_called_once_with(TEST_INTEGRATION_ID, TEST_USER_ID)
        finally:
            app.dependency_overrides.pop(get_repository, None)

    def test_delete_google_integration_returns_404_when_not_found(
        self,
        authenticated_client: TestClient,
        mock_repository: MagicMock,
    ) -> None:
        """存在しない連携削除で404が返却される"""
        # Arrange: 削除がFalseを返すリポジトリ
        mock_repository.delete = AsyncMock(return_value=False)
        app.dependency_overrides[get_repository] = lambda: mock_repository

        try:
            # Act: DELETE /api/v1/google/integrations/{integration_id}
            non_existent_id = uuid4()
            response = authenticated_client.delete(f"/api/v1/google/integrations/{non_existent_id}")

            # Assert: 404レスポンス
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_repository, None)

    # AC: "When ユーザーが追加スコープを要求すると、
    #      システムは既存の連携情報を保持したまま追加スコープのOAuth URLを返す"
    # ROI: 40/10 = 4.0 | ビジネス価値: 7 | 頻度: 4
    # 振る舞い: 追加スコープ要求 -> 既存連携確認 -> OAuth URL生成（include_granted_scopes=true）
    # @category: core-functionality
    # @dependency: GoogleOAuthClient, GoogleIntegrationRepository
    # @complexity: medium
    #
    # 検証項目:
    # - 既存連携がある場合、追加スコープURLが返却される
    # - 既存連携がない場合、400エラーが返却される
    # - URLにinclude_granted_scopesパラメータが含まれる
    def test_additional_scopes_returns_incremental_auth_url(
        self,
        authenticated_client: TestClient,
        mock_google_oauth_client: MagicMock,
        mock_repository_with_integration: MagicMock,
    ) -> None:
        """AC5: 追加スコープ要求でIncremental Authorization URLを返す"""
        # Arrange: リポジトリをモックに差し替え
        app.dependency_overrides[get_repository] = lambda: mock_repository_with_integration

        try:
            # Act: GET /api/v1/google/auth/additional-scopes?integration_id=xxx
            response = authenticated_client.get(
                f"/api/v1/google/auth/additional-scopes?integration_id={TEST_INTEGRATION_ID}"
            )

            # Assert: 200レスポンス
            assert response.status_code == 200

            # Assert: レスポンスにauthorize_urlが含まれる
            data = response.json()
            assert "authorize_url" in data

            # Assert: URLにinclude_granted_scopes=trueが含まれる
            # モックのget_authorization_urlがこのパラメータで呼ばれたことを確認
            mock_google_oauth_client.get_authorization_url.assert_called()
            call_kwargs = mock_google_oauth_client.get_authorization_url.call_args
            assert call_kwargs[1].get("include_granted_scopes") is True
        finally:
            app.dependency_overrides.pop(get_repository, None)

    def test_additional_scopes_returns_400_when_integration_not_found(
        self,
        authenticated_client: TestClient,
        mock_google_oauth_client: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """既存連携がない場合、400エラーが返却される"""
        # Arrange: 連携が見つからないリポジトリ
        mock_repository.get_by_id = AsyncMock(return_value=None)
        app.dependency_overrides[get_repository] = lambda: mock_repository

        try:
            # Act: GET /api/v1/google/auth/additional-scopes?integration_id=xxx
            non_existent_id = uuid4()
            response = authenticated_client.get(
                f"/api/v1/google/auth/additional-scopes?integration_id={non_existent_id}"
            )

            # Assert: 400エラー
            assert response.status_code == 400
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_repository, None)

    # AC: "When ユーザーがOAuth認可をキャンセルすると、
    #      システムはエラーページにリダイレクトする"
    # ROI: 20/5 = 4.0 | ビジネス価値: 4 | 頻度: 2
    # 振る舞い: コールバック（error付き） -> エラーページリダイレクト
    # @category: error-handling
    # @dependency: None
    # @complexity: low
    #
    # 検証項目:
    # - errorパラメータがある場合、エラーページにリダイレクトされる
    # - エラー内容がURLに含まれる
    def test_oauth_callback_handles_user_denial(
        self,
        authenticated_client: TestClient,
    ) -> None:
        """AC6: ユーザーが認可をキャンセルした場合エラーページにリダイレクト"""
        # Arrange: エラーパラメータを含むコールバックURLを準備
        # stateは必要（FastAPIのQuery(...)で必須）
        test_state = "test_state_for_denial"

        # Act: GET /api/v1/google/callback?error=access_denied&state=xxx&code=dummy
        response = authenticated_client.get(
            f"/api/v1/google/callback?error=access_denied&state={test_state}&code=dummy",
            follow_redirects=False,
        )

        # Assert: リダイレクト（302または307）
        assert response.status_code in (302, 307)

        # Assert: リダイレクト先がエラーページ
        location = response.headers["location"]
        assert "/google/error" in location

        # Assert: エラー内容がURLに含まれる
        assert "access_denied" in location
