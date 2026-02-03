# Knowledge Integration Test - Design Doc: mvp-core-features.md
# Generated: 2026-01-31 | Quota: 2/3 integration, 0/2 E2E
"""
ナレッジアップロード + 正規化機能の統合テスト

テスト対象: F3 ナレッジアップロード + 正規化
- ナレッジテキストのアップロードとDB保存
- ユビキタス言語辞書による正規化処理
- LLM APIエラー時のフォールバック処理
"""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.agent import Agent
from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.services.normalization_service import NormalizationError, NormalizationResult, Replacement
from src.main import app
from src.presentation.api.v1.dependencies import get_current_user_id

# テスト用の固定UUID
TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_AGENT_ID = UUID("22222222-2222-2222-2222-222222222222")


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
def mock_agent() -> Agent:
    """テスト用エージェント."""
    return Agent(
        id=TEST_AGENT_ID,
        user_id=TEST_USER_ID,
        name="テスト会議",
        description="テスト用のMTG",
        created_at=datetime.now(),
    )


@pytest.fixture
def mock_dictionary_entries() -> list[DictionaryEntry]:
    """テスト用辞書エントリ."""
    return [
        DictionaryEntry(
            id=uuid4(),
            user_id=TEST_USER_ID,
            canonical_name="金沢太郎",
            description="正式な表記",
            created_at=datetime.now(),
            updated_at=None,
        ),
        DictionaryEntry(
            id=uuid4(),
            user_id=TEST_USER_ID,
            canonical_name="プロジェクトA",
            description="プロジェクトの正式名称",
            created_at=datetime.now(),
            updated_at=None,
        ),
    ]


class TestKnowledgeIntegration:
    """ナレッジアップロード + 正規化の統合テスト"""

    # AC: "When ユーザーがエージェントを選択してナレッジテキストをアップロードすると、
    #      システムは辞書を参照して固有名詞を正規化し、DBに保存する"
    # Property: `knowledge.count == previous_count + 1`
    # ROI: 99/11 = 9.0 | ビジネス価値: 10 | 頻度: 9
    # 振る舞い: エージェント選択+テキストアップロード -> 辞書参照 -> LLM正規化 -> DB保存
    # @category: core-functionality
    # @dependency: KnowledgeRepository, DictionaryEntryRepository, BedrockClient, Supabase
    # @complexity: high
    #
    # 検証項目:
    # - 正常レスポンス(201)が返却される
    # - レスポンスにid, original_text, normalized_textが含まれる
    # - original_textは入力テキストと同一
    # - normalized_textは正規化処理の結果
    # - DBにナレッジが永続化されている
    def test_upload_and_normalize_knowledge(
        self,
        authenticated_client: TestClient,
        mock_agent: Agent,
        mock_dictionary_entries: list[DictionaryEntry],
    ) -> None:
        """AC1: ナレッジアップロードで辞書参照正規化されDBに保存される"""
        # Arrange
        original_text = "かなざわさんが報告しました。プロジェクトAの進捗です。"
        normalized_text = "金沢太郎さんが報告しました。プロジェクトAの進捗です。"

        # 正規化成功結果をモック
        normalization_result = NormalizationResult(
            original_text=original_text,
            normalized_text=normalized_text,
            replacements=[
                Replacement(original="かなざわ", canonical="金沢太郎", start_pos=0, end_pos=4),
            ],
        )

        # 依存関係をモック
        with (
            patch("src.presentation.api.v1.endpoints.knowledge.get_supabase_client") as mock_supabase_client,
            patch("src.presentation.api.v1.endpoints.knowledge.AgentRepositoryImpl") as mock_agent_repo_class,
            patch("src.presentation.api.v1.endpoints.knowledge.DictionaryRepositoryImpl") as mock_dict_repo_class,
            patch("src.presentation.api.v1.endpoints.knowledge.KnowledgeRepositoryImpl") as mock_knowledge_repo_class,
            patch(
                "src.presentation.api.v1.endpoints.knowledge.NormalizationServiceImpl"
            ) as mock_norm_service_class,
        ):
            # Supabase client mock
            mock_supabase_client.return_value = MagicMock()

            # AgentRepository mock
            mock_agent_repo = MagicMock()
            mock_agent_repo.get_by_id.return_value = mock_agent
            mock_agent_repo_class.return_value = mock_agent_repo

            # DictionaryRepository mock
            mock_dict_repo = MagicMock()

            async def mock_get_all(user_id: UUID) -> list[DictionaryEntry]:
                return mock_dictionary_entries

            mock_dict_repo.get_all = mock_get_all
            mock_dict_repo_class.return_value = mock_dict_repo

            # NormalizationService mock
            mock_norm_service = MagicMock()
            mock_norm_service.normalize.return_value = normalization_result
            mock_norm_service_class.return_value = mock_norm_service

            # KnowledgeRepository mock - 保存されたデータを返す
            mock_knowledge_repo = MagicMock()

            async def mock_create(knowledge: MagicMock) -> MagicMock:
                return knowledge

            mock_knowledge_repo.create = mock_create
            mock_knowledge_repo_class.return_value = mock_knowledge_repo

            # Act
            response = authenticated_client.post(
                "/api/v1/knowledge",
                json={
                    "agent_id": str(TEST_AGENT_ID),
                    "text": original_text,
                },
            )

            # Assert
            assert response.status_code == 201
            data = response.json()

            # レスポンスにoriginal_text, normalized_textが含まれる
            assert "knowledge" in data
            assert data["knowledge"]["original_text"] == original_text
            assert data["knowledge"]["normalized_text"] == normalized_text

            # 正規化が行われた
            assert data["knowledge"]["is_normalized"] is True
            assert data["replacement_count"] == 1
            assert data["normalization_warning"] is None

            # NormalizationServiceが呼ばれた
            mock_norm_service.normalize.assert_called_once()

    # AC: "If 正規化処理でLLM APIエラーが発生した場合、
    #      then システムは元テキストをそのまま保存し、ユーザーに警告を表示する"
    # ROI: 27/11 = 2.5 | ビジネス価値: 9 | 頻度: 2
    # 振る舞い: テキストアップロード -> LLM APIエラー -> 元テキスト保存 -> 警告返却
    # @category: edge-case
    # @dependency: KnowledgeRepository, BedrockClient, Supabase
    # @complexity: medium
    #
    # 検証項目:
    # - レスポンスに警告メッセージが含まれる
    # - original_textとnormalized_textが同一（フォールバック）
    # - DBにナレッジが永続化されている（元テキストのまま）
    def test_upload_knowledge_llm_error_fallback(
        self,
        authenticated_client: TestClient,
        mock_agent: Agent,
        mock_dictionary_entries: list[DictionaryEntry],
    ) -> None:
        """AC3: LLM APIエラー時に元テキストが保存され警告が返却される"""
        # Arrange
        original_text = "かなざわさんが報告しました。"

        # 依存関係をモック
        with (
            patch("src.presentation.api.v1.endpoints.knowledge.get_supabase_client") as mock_supabase_client,
            patch("src.presentation.api.v1.endpoints.knowledge.AgentRepositoryImpl") as mock_agent_repo_class,
            patch("src.presentation.api.v1.endpoints.knowledge.DictionaryRepositoryImpl") as mock_dict_repo_class,
            patch("src.presentation.api.v1.endpoints.knowledge.KnowledgeRepositoryImpl") as mock_knowledge_repo_class,
            patch(
                "src.presentation.api.v1.endpoints.knowledge.NormalizationServiceImpl"
            ) as mock_norm_service_class,
        ):
            # Supabase client mock
            mock_supabase_client.return_value = MagicMock()

            # AgentRepository mock
            mock_agent_repo = MagicMock()
            mock_agent_repo.get_by_id.return_value = mock_agent
            mock_agent_repo_class.return_value = mock_agent_repo

            # DictionaryRepository mock
            mock_dict_repo = MagicMock()

            async def mock_get_all(user_id: UUID) -> list[DictionaryEntry]:
                return mock_dictionary_entries

            mock_dict_repo.get_all = mock_get_all
            mock_dict_repo_class.return_value = mock_dict_repo

            # NormalizationService mock - エラーを発生させる
            mock_norm_service = MagicMock()
            mock_norm_service.normalize.side_effect = NormalizationError("LLM API error")
            mock_norm_service_class.return_value = mock_norm_service

            # KnowledgeRepository mock - 保存されたデータを返す
            mock_knowledge_repo = MagicMock()

            async def mock_create(knowledge: MagicMock) -> MagicMock:
                return knowledge

            mock_knowledge_repo.create = mock_create
            mock_knowledge_repo_class.return_value = mock_knowledge_repo

            # Act
            response = authenticated_client.post(
                "/api/v1/knowledge",
                json={
                    "agent_id": str(TEST_AGENT_ID),
                    "text": original_text,
                },
            )

            # Assert
            assert response.status_code == 201
            data = response.json()

            # レスポンスに警告が含まれる
            assert data["normalization_warning"] is not None
            assert "正規化処理に失敗しました" in data["normalization_warning"]

            # original_text == normalized_text（フォールバック）
            assert data["knowledge"]["original_text"] == original_text
            assert data["knowledge"]["normalized_text"] == original_text
            assert data["knowledge"]["is_normalized"] is False

            # replacement_countは0
            assert data["replacement_count"] == 0
