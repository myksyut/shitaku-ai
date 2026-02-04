# OAuth State永続化 設計書

## 概要

サーバーレス環境（Vercel）でのOAuth認証を正常動作させるため、OAuth stateをSupabase（PostgreSQL）に永続化する。Slack/Google両方で共通のOAuthStateリポジトリを使用し、RLSでセキュリティを確保する。

## 設計サマリー（メタ）

```yaml
design_type: "拡張"
risk_level: "中"
main_constraints:
  - "既存OAuth認証フローとの互換性を維持"
  - "ADR-0004のRLSパターンに準拠"
  - "callback時はservice_roleでRLSバイパス"
biggest_risks:
  - "state検証失敗時のユーザー体験悪化"
  - "期限切れstateの蓄積によるDB肥大化"
unknowns:
  - "サーバーレス環境での実際のレイテンシ影響"
```

## 背景と経緯

### 前提となるADR

- [ADR-0007: OAuth State永続化](../adr/ADR-0007-oauth-state-persistence.md): インメモリからSupabaseへの移行決定
- [ADR-0004: RLSベースの認可アーキテクチャ](../adr/ADR-0004-rls-based-authorization.md): RLSパターンとクライアント使い分け
- [ADR-0003: Google Workspace連携の認証方式](../adr/ADR-0003-google-workspace-auth.md): Google OAuth設計

### 合意事項チェックリスト

#### スコープ
- [x] `oauth_states`テーブルの新規作成
- [x] `OAuthState`エンティティの定義
- [x] `OAuthStateRepository`インターフェースと実装
- [x] `StartSlackOAuthUseCase`のリポジトリDI化
- [x] `HandleSlackCallbackUseCase`のDB経由state検証
- [x] `StartGoogleOAuthUseCase`のリポジトリDI化
- [x] `HandleGoogleCallbackUseCase`のDB経由state検証
- [x] `StartAdditionalScopesUseCase`のリポジトリDI化
- [x] エンドポイントのDI変更

#### スコープ外（明示的に変更しないもの）
- [ ] OAuth認証URLの生成ロジック（既存ロジックを維持）
- [ ] トークン交換ロジック（既存ロジックを維持）
- [ ] 既存のSlack/Google連携リポジトリ
- [ ] フロントエンドのOAuth開始フロー

#### 制約
- [x] 並行運用: しない（即座に切り替え）
- [x] 後方互換性: 不要（内部実装変更のみ）
- [x] パフォーマンス計測: 推奨（DB書き込みレイテンシ）

### 解決すべき課題

1. **サーバーレス環境での状態消失**
   - 現状: OAuth stateがインメモリ管理
   - 問題: `/auth`と`/callback`が異なるインスタンスで処理され、state検証が失敗
   - 影響: 本番環境でSlack/Google連携が完全に機能しない

### 現状の課題

```python
# 現行実装（slack_use_cases.py / google_auth_use_cases.py）
_state_store: dict[str, tuple[UUID, datetime]] = {}  # インメモリストア

# 問題点
# 1. サーバーレス環境では各インスタンスが独立したメモリを持つ
# 2. /auth と /callback が異なるインスタンスで処理される可能性が高い
# 3. 結果: "Invalid state parameter" エラーが発生
```

### 要件

#### 機能要件

- OAuth stateをSupabaseテーブルに保存できる
- state保存時にユーザーID、プロバイダー、スコープを紐付ける
- callback時にstateを検証し、有効期限を確認できる
- 検証成功後にstateを削除できる
- 期限切れstateをクリーンアップできる

#### 非機能要件

- **パフォーマンス**: state保存/取得で50ms以内（DBアクセス）
- **スケーラビリティ**: 同時OAuth認証フロー数に制限なし
- **信頼性**: state消失によるOAuth失敗を0件にする
- **保守性**: Slack/Googleで共通リポジトリを使用

## 受入条件（AC）- EARS形式

### AC1: OAuth state保存

- [ ] **When** ユーザーがOAuth認証を開始すると、システムはstateをSupabaseに保存する
  - **Property**: `saved_state.user_id == authenticated_user_id`
  - **Property**: `saved_state.provider IN ('slack', 'google')`
  - **Property**: `saved_state.expires_at == now() + 5 minutes`
- [ ] **If** state保存に失敗した場合、**then** システムはHTTP 500エラーを返却する

### AC2: OAuth state検証

- [ ] **When** callbackでstateが渡されると、システムはDBからstateを取得して検証する
- [ ] **If** stateがDBに存在しない場合、**then** システムは「Invalid state parameter」エラーを返却する
- [ ] **If** stateが期限切れの場合、**then** システムは「State expired」エラーを返却する
- [ ] **When** state検証成功後、システムはそのstateレコードを削除する
  - **Property**: `deleted_count == 1`

### AC3: 期限切れstateのクリーンアップ

- [ ] **When** callback処理時、システムは期限切れ（5分超過）のstateも削除する
  - **Property**: `deleted_states.all(s => s.expires_at < now())`

### AC4: RLSセキュリティ

- [ ] ユーザーは自分のOAuth stateのみ作成できる
  - **Property**: `inserted_state.user_id == auth.uid()`
- [ ] ユーザーは自分のOAuth stateのみ読み取れる
  - **Property**: `selected_states.all(s => s.user_id == auth.uid())`
- [ ] callback処理（service_role）はRLSをバイパスして任意のstateを操作できる

## 既存コードベース分析

### 実装パスマッピング

| 種別 | パス | 説明 |
|-----|-----|-----|
| 既存 | `backend/src/application/use_cases/slack_use_cases.py` | Slack OAuthユースケース（インメモリstate） |
| 既存 | `backend/src/application/use_cases/google_auth_use_cases.py` | Google OAuthユースケース（インメモリstate） |
| 既存 | `backend/src/presentation/api/v1/endpoints/slack.py` | Slackエンドポイント |
| 既存 | `backend/src/presentation/api/v1/endpoints/google.py` | Googleエンドポイント |
| 既存 | `backend/src/infrastructure/external/supabase_client.py` | Supabaseクライアント |
| 既存 | `backend/src/presentation/api/v1/dependencies.py` | FastAPI依存性 |
| 新規 | `supabase/migrations/YYYYMMDDHHMMSS_create_oauth_states.sql` | マイグレーション |
| 新規 | `backend/src/domain/entities/oauth_state.py` | OAuthStateエンティティ |
| 新規 | `backend/src/domain/repositories/oauth_state_repository.py` | リポジトリインターフェース |
| 新規 | `backend/src/infrastructure/repositories/oauth_state_repository_impl.py` | リポジトリ実装 |

### 統合ポイント

- **統合先**: Slack/Google OAuthユースケース
- **呼び出し方式**: コンストラクタDIでリポジトリを注入

### 類似機能の検索結果

既存のリポジトリ実装パターン（`SlackIntegrationRepositoryImpl`等）を踏襲。
ADR-0004のRLSパターンに準拠したクライアント使い分けを適用。

## 設計

### 変更影響マップ

```yaml
変更対象: OAuth state管理
直接影響:
  - backend/src/application/use_cases/slack_use_cases.py（StartSlackOAuthUseCase, HandleSlackCallbackUseCase）
  - backend/src/application/use_cases/google_auth_use_cases.py（StartGoogleOAuthUseCase, HandleGoogleCallbackUseCase, StartAdditionalScopesUseCase）
  - backend/src/presentation/api/v1/endpoints/slack.py（DI変更）
  - backend/src/presentation/api/v1/endpoints/google.py（DI変更）
間接影響:
  - フロントエンドのOAuthリダイレクト処理（変更なし、動作に影響なし）
波及なし:
  - 既存のSlack/Google連携リポジトリ
  - トークン管理ロジック
  - 他のAPI エンドポイント
```

### アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Presentation Layer                               │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  /slack/auth                              /slack/callback           │ │
│  │    │                                         │                      │ │
│  │    │ get_current_user_id()                   │ (no auth required)   │ │
│  │    │ get_user_supabase_client()              │ get_callback_repos() │ │
│  │    ▼                                         ▼                      │ │
│  │  StartSlackOAuthUseCase              HandleSlackCallbackUseCase     │ │
│  │    │                                         │                      │ │
│  │    │ OAuthStateRepository                    │ OAuthStateRepository │ │
│  │    │ (user context)                          │ (service_role)       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Application Layer                                │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  StartSlackOAuthUseCase                                             │ │
│  │    1. Generate state token                                          │ │
│  │    2. oauth_state_repo.create({state, user_id, provider, expires})  │ │
│  │    3. Build authorization URL with state                            │ │
│  │    4. Return URL                                                    │ │
│  │                                                                     │ │
│  │  HandleSlackCallbackUseCase                                         │ │
│  │    1. oauth_state_repo.get_and_delete(state)                        │ │
│  │    2. Validate expiration                                           │ │
│  │    3. Exchange code for token                                       │ │
│  │    4. oauth_state_repo.cleanup_expired()                            │ │
│  │    5. Save integration                                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Infrastructure Layer                             │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  OAuthStateRepositoryImpl                                           │ │
│  │    - create(): INSERT oauth_states                                  │ │
│  │    - get_and_delete(): SELECT + DELETE (atomic)                     │ │
│  │    - cleanup_expired(): DELETE WHERE expires_at < now()             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Database Layer (Supabase)                        │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  oauth_states table                                                 │ │
│  │    - id: UUID (PK)                                                  │ │
│  │    - state: TEXT (UNIQUE)                                           │ │
│  │    - user_id: UUID (FK -> auth.users)                               │ │
│  │    - provider: TEXT ('slack' | 'google')                            │ │
│  │    - scopes: TEXT[]                                                 │ │
│  │    - expires_at: TIMESTAMPTZ                                        │ │
│  │    - created_at: TIMESTAMPTZ                                        │ │
│  │                                                                     │ │
│  │  RLS Policies:                                                      │ │
│  │    - INSERT: auth.uid() = user_id                                   │ │
│  │    - SELECT: auth.uid() = user_id                                   │ │
│  │    - DELETE: auth.uid() = user_id                                   │ │
│  │    (callback uses service_role to bypass RLS)                       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### データフロー

```
[OAuth開始フロー]
1. User -> /slack/auth (with JWT)
   │
   ▼
2. get_current_user_id() -> user_id
   get_user_supabase_client() -> Client (with user context)
   │
   ▼
3. StartSlackOAuthUseCase.execute(user_id)
   │
   ├── Generate state = secrets.token_urlsafe(32)
   │
   ├── OAuthStateRepository.create(OAuthState{
   │       state, user_id, provider='slack',
   │       expires_at=now()+5min
   │   })
   │   │
   │   └── INSERT INTO oauth_states ... (RLS: auth.uid() = user_id)
   │
   └── Return authorize_url with state
   │
   ▼
4. User -> Redirect to Slack OAuth

[OAuth Callbackフロー]
5. Slack -> /slack/callback?code=xxx&state=yyy (no JWT)
   │
   ▼
6. get_callback_oauth_state_repository() -> service_role client
   get_callback_repository() -> service_role client
   │
   ▼
7. HandleSlackCallbackUseCase.execute(code, state)
   │
   ├── OAuthStateRepository.get_and_delete(state)
   │   │
   │   ├── SELECT * FROM oauth_states WHERE state = :state
   │   │   (service_role bypasses RLS)
   │   │
   │   ├── DELETE FROM oauth_states WHERE state = :state
   │   │
   │   └── Return OAuthState or None
   │
   ├── If None -> raise ValueError("Invalid state parameter")
   │
   ├── If expires_at < now() -> raise ValueError("State expired")
   │
   ├── Exchange code for access_token
   │
   ├── OAuthStateRepository.cleanup_expired()
   │   │
   │   └── DELETE FROM oauth_states WHERE expires_at < now()
   │
   └── Save integration, redirect to success page
```

### 統合ポイント一覧

| 統合ポイント | 箇所 | 旧実装 | 新実装 | 切替方式 |
|------------|-----|-------|-------|---------|
| state保存 | StartSlackOAuthUseCase | `_state_store[state] = (user_id, datetime)` | `oauth_state_repo.create(OAuthState)` | リポジトリDI |
| state検証 | HandleSlackCallbackUseCase | `_state_store.pop(state)` | `oauth_state_repo.get_and_delete(state)` | リポジトリDI |
| state保存（Google） | StartGoogleOAuthUseCase | `_state_store[state] = (user_id, datetime, scopes)` | `oauth_state_repo.create(OAuthState)` | リポジトリDI |
| state検証（Google） | HandleGoogleCallbackUseCase | `_state_store.pop(state)` | `oauth_state_repo.get_and_delete(state)` | リポジトリDI |
| リポジトリ取得（auth） | slack.py / google.py | なし | `Depends(get_oauth_state_repository)` | FastAPI DI |
| リポジトリ取得（callback） | slack.py / google.py | なし | `get_callback_oauth_state_repository()` | 関数呼び出し |

### 主要コンポーネント

#### OAuthState エンティティ

- **責務**: OAuth stateの不変データを表現
- **インターフェース**:
  ```python
  @dataclass
  class OAuthState:
      id: UUID
      state: str
      user_id: UUID
      provider: str  # 'slack' | 'google'
      scopes: list[str] | None  # Googleの追加スコープ用
      expires_at: datetime
      created_at: datetime

      def is_expired(self) -> bool:
          """有効期限が切れているか確認."""
          return datetime.now(timezone.utc) > self.expires_at
  ```
- **依存関係**: なし（純粋なドメインエンティティ）

#### OAuthStateRepository インターフェース

- **責務**: OAuth stateの永続化操作を抽象化
- **インターフェース**:
  ```python
  class OAuthStateRepository(Protocol):
      async def create(self, oauth_state: OAuthState) -> OAuthState:
          """OAuth stateを作成する."""
          ...

      async def get_and_delete(self, state: str) -> OAuthState | None:
          """stateを取得し、同時に削除する（アトミック操作）."""
          ...

      async def cleanup_expired(self) -> int:
          """期限切れのstateを削除し、削除件数を返す."""
          ...
  ```
- **依存関係**: `OAuthState`

#### OAuthStateRepositoryImpl 実装

- **責務**: Supabaseを使用したOAuthState永続化
- **インターフェース**:
  ```python
  class OAuthStateRepositoryImpl(OAuthStateRepository):
      def __init__(self, client: Client) -> None:
          self._client = client

      async def create(self, oauth_state: OAuthState) -> OAuthState: ...
      async def get_and_delete(self, state: str) -> OAuthState | None: ...
      async def cleanup_expired(self) -> int: ...
  ```
- **依存関係**: `supabase.Client`, `OAuthState`

### 型定義

```python
# backend/src/domain/entities/oauth_state.py
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass
class OAuthState:
    """OAuth認証stateエンティティ.

    OAuth 2.0認証フローにおけるCSRF対策用stateを表現する。
    stateはユーザーID、プロバイダー、有効期限と紐付けて管理される。
    """

    id: UUID
    state: str
    user_id: UUID
    provider: str  # 'slack' | 'google'
    scopes: list[str] | None  # Google追加スコープ用
    expires_at: datetime
    created_at: datetime

    def is_expired(self) -> bool:
        """有効期限が切れているか確認する.

        Returns:
            True if expired, False otherwise.
        """
        now = datetime.now(timezone.utc)
        # expires_atがnaiveの場合はUTC想定で比較
        if self.expires_at.tzinfo is None:
            return now.replace(tzinfo=None) > self.expires_at
        return now > self.expires_at
```

```python
# backend/src/domain/repositories/oauth_state_repository.py
from typing import Protocol
from uuid import UUID

from src.domain.entities.oauth_state import OAuthState


class OAuthStateRepository(Protocol):
    """OAuth stateリポジトリのインターフェース.

    OAuth認証stateの永続化操作を定義する。
    実装はインフラストラクチャ層で提供される。
    """

    async def create(self, oauth_state: OAuthState) -> OAuthState:
        """OAuth stateを作成する.

        Args:
            oauth_state: 作成するOAuthStateエンティティ.

        Returns:
            作成されたOAuthStateエンティティ.
        """
        ...

    async def get_and_delete(self, state: str) -> OAuthState | None:
        """stateを取得し、同時に削除する.

        アトミック操作として実装される。
        stateが存在しない場合はNoneを返す。

        Args:
            state: 検索するstateトークン.

        Returns:
            OAuthStateエンティティ、または存在しない場合はNone.
        """
        ...

    async def cleanup_expired(self) -> int:
        """期限切れのstateを削除する.

        Returns:
            削除されたレコード数.
        """
        ...
```

### データ契約

#### OAuthStateRepositoryImpl.create

```yaml
入力:
  型: OAuthState
  前提条件:
    - state: 非空文字列、一意
    - user_id: 有効なauth.users.id
    - provider: 'slack' または 'google'
    - expires_at: 未来の日時
  バリデーション: DBのCHECK制約とUNIQUE制約

出力:
  型: OAuthState
  保証: DBに保存された状態を反映
  エラー時: Supabase例外（重複stateの場合）

不変条件:
  - stateトークンは一意
  - expires_atは常に未来日時で作成
```

#### OAuthStateRepositoryImpl.get_and_delete

```yaml
入力:
  型: str (state token)
  前提条件: 非空文字列
  バリデーション: なし（存在しなければNone返却）

出力:
  型: OAuthState | None
  保証: 取得と削除がアトミックに実行される
  エラー時: None（stateが存在しない場合）

不変条件:
  - 同一stateに対する2回目の呼び出しはNoneを返す
  - 削除されたstateは復元されない
```

#### OAuthStateRepositoryImpl.cleanup_expired

```yaml
入力:
  型: なし
  前提条件: なし
  バリデーション: なし

出力:
  型: int (削除件数)
  保証: expires_at < now() のレコードがすべて削除される
  エラー時: 0（削除対象がない場合）

不変条件:
  - 有効期限内のstateは削除されない
```

### 統合境界の約束

```yaml
境界名: Endpoint -> OAuthStateRepository
  入力: OAuthState (create) または state文字列 (get_and_delete)
  出力: OAuthState または None (非同期)
  エラー時: Supabase例外をドメイン例外に変換

境界名: OAuthStateRepository -> Supabase
  入力: SQL操作リクエスト
  出力: データ行
  エラー時: Supabase APIException

境界名: Supabase -> PostgreSQL RLS
  入力: JWT (Authorization header) または service_role key
  出力:
    - JWT: auth.uid()がセットされたセッション（自分のデータのみ）
    - service_role: RLSバイパス（全データアクセス可能）
  エラー時: RLS違反で空結果または操作失敗
```

### エラーハンドリング

| エラー種別 | 発生箇所 | 対処 |
|-----------|---------|------|
| state重複 | OAuthStateRepository.create | Supabase例外をキャッチ、再生成を試行 |
| state不存在 | OAuthStateRepository.get_and_delete | None返却、ユースケースでValueError |
| state期限切れ | ユースケース | ValueError("State expired") |
| DB接続エラー | リポジトリ操作 | 500 HTTPException |
| RLS拒否 | create（不正なuser_id） | 操作失敗、500 HTTPException |

### ロギングとモニタリング

- **INFO**: OAuth state作成成功 `Creating OAuth state: provider={provider}, user_id={user_id}`
- **INFO**: OAuth state検証成功 `Validated OAuth state: provider={provider}`
- **WARNING**: 期限切れstateの検証試行 `Expired OAuth state detected: state={state[:8]}...`
- **WARNING**: 存在しないstateの検証試行 `Invalid OAuth state: state={state[:8]}...`
- **INFO**: クリーンアップ実行 `Cleaned up {count} expired OAuth states`
- **ERROR**: DB操作失敗 `Failed to {operation} OAuth state: {error}`

## 実装計画

### 実装アプローチ

**選択したアプローチ**: 垂直スライス（機能駆動）

**選択理由**:
1. OAuth認証は独立した機能であり、他機能への依存が最小限
2. マイグレーション → エンティティ → リポジトリ → ユースケース → エンドポイントの順で完結
3. 各フェーズで動作確認が可能

### 技術的依存関係と実装順序

#### 必要な実装順序

1. **Phase 1: データベーススキーマ**
   - 技術的理由: 永続化層の基盤確立
   - 依存要素: リポジトリ実装がこのスキーマに依存
   - 内容: `oauth_states`テーブル作成、RLSポリシー設定
   - 確認レベル: L3（ビルド成功確認 = マイグレーション適用成功）

2. **Phase 2: ドメイン層**
   - 技術的理由: アプリケーション層とインフラ層の共通インターフェース
   - 前提条件: なし（純粋なPythonコード）
   - 内容: `OAuthState`エンティティ、`OAuthStateRepository`インターフェース
   - 確認レベル: L3（ビルド成功確認 = 型チェック通過）

3. **Phase 3: インフラストラクチャ層**
   - 技術的理由: Phase 1のスキーマ、Phase 2のインターフェースに依存
   - 前提条件: Phase 1, 2完了
   - 内容: `OAuthStateRepositoryImpl`実装
   - 確認レベル: L2（テスト動作確認）

4. **Phase 4: アプリケーション層**
   - 技術的理由: Phase 3のリポジトリを使用
   - 前提条件: Phase 3完了
   - 内容: ユースケースのリポジトリDI化、state管理ロジック変更
   - 確認レベル: L2（テスト動作確認）

5. **Phase 5: プレゼンテーション層**
   - 技術的理由: Phase 4のユースケースを使用
   - 前提条件: Phase 4完了
   - 内容: エンドポイントのDI変更
   - 確認レベル: L1（機能動作確認）

6. **Phase 6: 統合テスト**
   - 技術的理由: 全層の結合確認
   - 前提条件: Phase 5完了
   - 内容: E2E動作確認、クリーンアップ確認
   - 確認レベル: L1（機能動作確認）

### 統合ポイント

各統合ポイントでE2E確認が必要：

**統合ポイント1: Phase 3完了後**
- コンポーネント: OAuthStateRepositoryImpl -> Supabase
- 確認方法: 単体テストでCRUD操作が正常動作することを検証

**統合ポイント2: Phase 5完了後（最終）**
- コンポーネント: Endpoint -> UseCase -> Repository -> Supabase
- 確認方法:
  1. `/slack/auth`でstate保存されることをDBで確認
  2. `/slack/callback`でstate検証・削除されることをDBで確認
  3. 異なるインスタンス（別プロセス）からcallbackしても成功することを確認

### 移行戦略

1. **即時切り替え**: インメモリstate管理を完全にDB管理に置き換え
2. **ダウンタイムなし**: 新規OAuth開始からDB使用、進行中のOAuthは5分以内に期限切れ
3. **ロールバック**: マイグレーションのダウングレードで旧実装に戻せる（ただしインメモリに戻すとサーバーレス問題再発）

## テスト戦略

### 単体テスト

- `OAuthState.is_expired()`のテスト
- `OAuthStateRepositoryImpl`のCRUD操作テスト（モックSupabaseクライアント使用）
- ユースケースのstate保存・検証ロジックテスト（モックリポジトリ使用）

### 統合テスト

- 実Supabaseに対するリポジトリ操作テスト
- RLSポリシーの動作確認（異なるユーザーでのアクセス制限）
- 期限切れクリーンアップの動作確認

### E2Eテスト

- OAuth開始 → state保存 → callback → state検証 → 削除の一連のフロー
- サーバーレス環境を模した別プロセスからのcallback確認

## セキュリティ考慮事項

1. **stateトークンの強度**: `secrets.token_urlsafe(32)`で256ビットエントロピー確保
2. **CSRF防止**: stateとuser_idの紐付けでセッション固定攻撃を防止
3. **有効期限**: 5分で期限切れ、長期間の悪用を防止
4. **RLS保護**: 自分のstateのみ操作可能（callbackはservice_roleで例外的にバイパス）
5. **一回使用**: get_and_deleteでatomicに削除、再利用を防止

## 代替案

### 代替案1: Redis（Vercel KV）

- **概要**: Vercel KVまたはUpstash Redisでstate管理
- **メリット**: 高速、TTLネイティブサポート
- **デメリット**: 追加コスト、新規インフラ学習コスト
- **不採用理由**: ADR-0007で「コストゼロ運用」制約のため不採用

### 代替案2: Cookieセッション

- **概要**: stateをセッションCookieに保存
- **メリット**: 追加インフラ不要
- **デメリット**: サーバーレス環境でセッション維持困難、OAuth callbackはサードパーティリダイレクト
- **不採用理由**: 技術的に実現困難

## リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|-----|
| DBレイテンシによるUX悪化 | 中 | 低 | Supabase Edge Functionsは低レイテンシ、50ms以内を目標 |
| 期限切れstateの蓄積 | 低 | 中 | callback時のクリーンアップ、将来的にバッチ削除検討 |
| RLSポリシー設定ミス | 高 | 低 | 既存パターン踏襲、統合テストで検証 |
| state重複による衝突 | 中 | 極低 | 256ビットエントロピー、衝突確率は無視可能 |

## 参考資料

- [ADR-0007: OAuth State永続化](../adr/ADR-0007-oauth-state-persistence.md)
- [ADR-0004: RLSベースの認可アーキテクチャ](../adr/ADR-0004-rls-based-authorization.md)
- [OAuth 2.0 State Parameter Best Practices](https://auth0.com/docs/secure/attack-protection/state-parameters)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Vercel Serverless Functions](https://vercel.com/docs/functions/serverless-functions)

## 更新履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|-----|-----------|---------|-------|
| 2026-02-04 | 1.0 | 初版作成 | AI Assistant |
