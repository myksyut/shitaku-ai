# RLS認可アーキテクチャ 設計書

## 概要

ユーザーJWTを活用してSupabase RLSに認可を委譲するアーキテクチャへの移行設計。現在のservice_roleキーによるRLSバイパスを廃止し、行レベルでの認可を実現する。

## 設計サマリー（メタ）

```yaml
design_type: "リファクタリング"
risk_level: "中"
main_constraints:
  - "既存のRLSポリシーとの互換性を維持"
  - "httpxクライアント生成のパフォーマンス影響を最小化"
  - "段階的移行によるサービス継続"
biggest_risks:
  - "RLS有効化後のクエリ失敗（ポリシー設定ミス）"
  - "パフォーマンス劣化（クライアント生成コスト）"
unknowns:
  - "supabase-pyでのユーザーJWT設定の最適な方法"
  - "httpxクライアント共有時の動作安定性"
```

## 背景と経緯

### 前提となるADR

- [ADR-0001: クリーンアーキテクチャ採用](../adr/ADR-0001-clean-architecture-adoption.md): 4層構造とリポジトリパターン
- [ADR-0004: RLSベースの認可アーキテクチャ](../adr/ADR-0004-rls-based-authorization.md): 本設計の根拠となる技術決定

### 合意事項チェックリスト

#### スコープ
- [x] Supabaseクライアントのユーザーコンテキスト対応
- [x] httpxクライアントのシングルトン化
- [x] リポジトリの依存性注入統一
- [x] FastAPI依存性注入の拡張
- [x] UPDATE操作のuser_idフィルタ追加（短期対策）

#### スコープ外（明示的に変更しないもの）
- [ ] RLSポリシーの新規作成（既存ポリシーを使用）
- [ ] フロントエンドの認証フロー変更
- [ ] JWTの検証ロジック変更（既存のJWKS検証を維持）

#### 制約
- [x] 並行運用: する（段階的移行）
- [x] 後方互換性: 必要（既存APIの動作を維持）
- [x] パフォーマンス計測: 必要（httpxクライアント生成のオーバーヘッド）

### 解決すべき課題

1. UPDATE操作でuser_idフィルタが欠落しており、他ユーザーのデータを更新可能な脆弱性が存在
2. 認可ロジックが各リポジトリに分散しており、実装漏れのリスクが高い
3. service_roleキーの使用によりRLSがバイパスされ、防御の深さが確保できていない

### 現状の課題

**脆弱性のあるコード例（agent_repository_impl.py L85）:**
```python
def update(self, agent: Agent) -> Agent:
    data = {"name": agent.name, ...}
    # user_idフィルタがない - 任意のagent.idを指定すれば他ユーザーのデータを更新可能
    self._client.table("agents").update(data).eq("id", str(agent.id)).execute()
```

**同様の問題が存在するファイル:**
- `dictionary_repository_impl.py` L81
- `slack_integration_repository_impl.py` L110
- `google_integration_repository_impl.py` L111

### 要件

#### 機能要件

- ユーザーJWTを使用してSupabaseクライアントを初期化できる
- RLSポリシーにより行レベルの認可が実施される
- 既存のCRUD操作が正常に動作する

#### 非機能要件

- **パフォーマンス**: httpxクライアント生成を1回に抑え、リクエストあたりのオーバーヘッドを最小化
- **スケーラビリティ**: リクエストごとのクライアント生成でもスレッドセーフに動作
- **信頼性**: RLSポリシー適用によりデータ分離を保証
- **保守性**: 認可ロジックをRLSに集約し、リポジトリ実装をシンプル化

## 受入条件（AC）- EARS形式

### AC1: ユーザーコンテキスト付きSupabaseクライアント

- [x] **When** 認証済みユーザーがAPIリクエストを送信すると、システムはユーザーのJWTを使用してSupabaseクライアントを初期化する
- [x] **If** JWTが無効または期限切れの場合、**then** システムは401エラーを返却する
- [x] **When** ユーザーコンテキスト付きクライアントでデータを取得すると、RLSポリシーによりそのユーザーのデータのみが返却される
  - **Property**: `result.all(item => item.user_id == authenticated_user_id)`

### AC2: UPDATE操作のセキュリティ

- [x] **When** ユーザーがagent/dictionary/integrationを更新しようとすると、RLSポリシーにより自分のデータのみが更新対象となる
- [x] **If** 他ユーザーのデータIDを指定してUPDATEを試みた場合、**then** 影響を受ける行数は0となる
  - **Property**: `affected_rows == 0 when target.user_id != authenticated_user_id`

### AC3: httpxクライアントのシングルトン化

- [x] システムはアプリケーション起動時に1つのhttpxクライアントインスタンスを生成する
- [x] **While** アプリケーションが稼働している間、全リクエストは同一のhttpxクライアントインスタンスを共有する
- [x] **When** アプリケーションがシャットダウンすると、httpxクライアントが適切にクローズされる

### AC4: 依存性注入の統一

- [x] 全リポジトリ実装はコンストラクタでSupabaseクライアントを受け取る
- [x] **When** エンドポイントが呼び出されると、FastAPIの依存性注入によりユーザーコンテキスト付きクライアントが注入される

## 既存コードベース分析

### 実装パスマッピング

| 種別 | パス | 説明 |
|-----|-----|-----|
| 既存 | `src/infrastructure/external/supabase_client.py` | Supabaseクライアント生成（service_role使用） |
| 既存 | `src/presentation/api/v1/dependencies.py` | JWT検証とuser_id取得 |
| 既存 | `src/infrastructure/repositories/*_repository_impl.py` | 各リポジトリ実装 |
| 新規 | `src/infrastructure/external/supabase_client.py` | ユーザーコンテキスト付きクライアント生成を追加 |
| 新規 | `src/presentation/api/v1/dependencies.py` | ユーザーSupabaseクライアント依存性を追加 |

### 統合ポイント

- **統合先**: FastAPI依存性注入システム
- **呼び出し方式**: `Depends(get_user_supabase_client)` でリクエストスコープのクライアントを取得

### 類似機能の検索結果

既存のSupabaseクライアント生成ロジック（`get_supabase_client()`）を拡張する形で実装。新規の認可フレームワークは導入しない。

## 設計

### 変更影響マップ

```yaml
変更対象: Supabaseクライアント生成とリポジトリ依存性注入
直接影響:
  - src/infrastructure/external/supabase_client.py（クライアント生成ロジック追加）
  - src/presentation/api/v1/dependencies.py（依存性追加）
  - src/infrastructure/repositories/agent_repository_impl.py（DI統一）
  - src/infrastructure/repositories/dictionary_repository_impl.py（変更なし、既にDI対応）
  - src/infrastructure/repositories/meeting_note_repository_impl.py（変更なし、既にDI対応）
  - src/infrastructure/repositories/slack_integration_repository_impl.py（DI統一）
  - src/infrastructure/repositories/google_integration_repository_impl.py（DI統一）
  - src/presentation/api/v1/endpoints/agents.py（依存性変更）
  - src/presentation/api/v1/endpoints/slack.py（依存性変更）
  - src/presentation/api/v1/endpoints/google.py（依存性変更）
間接影響:
  - RLSポリシーの動作確認が必要
  - 統合テストでのRLS検証が必要
波及なし:
  - フロントエンド認証フロー
  - JWT検証ロジック（既存を維持）
  - ドメイン層、アプリケーション層
```

### アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Endpoint                                         │  │
│  │    │                                                      │  │
│  │    ├── Depends(get_current_user_id) → UUID               │  │
│  │    │                                                      │  │
│  │    └── Depends(get_user_supabase_client) → Client        │  │
│  │              │                                            │  │
│  │              ▼                                            │  │
│  │    ┌─────────────────────────────────────────────┐       │  │
│  │    │ create_user_client(jwt_token)               │       │  │
│  │    │   - shared_httpx_client (singleton)         │       │  │
│  │    │   - Authorization: Bearer {user_jwt}        │       │  │
│  │    └─────────────────────────────────────────────┘       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Repository Implementation                                │  │
│  │    - __init__(client: Client)                            │  │
│  │    - Uses injected client for all operations             │  │
│  │    - No user_id filter needed (RLS handles it)           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Supabase (PostgreSQL + RLS)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PostgREST                                                │  │
│  │    - Verifies JWT signature                              │  │
│  │    - Sets role to 'authenticated'                        │  │
│  │    - auth.uid() returns user ID from JWT                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  RLS Policy                                               │  │
│  │    FOR ALL USING (auth.uid() = user_id)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### データフロー

```
1. Client Request
   │
   ▼
2. FastAPI Middleware
   │  - Extract JWT from Authorization header
   │
   ▼
3. get_current_user_id (Depends)
   │  - Verify JWT using JWKS
   │  - Extract user_id (sub claim)
   │
   ▼
4. get_user_supabase_client (Depends)
   │  - Get JWT token from request
   │  - Create Supabase client with user JWT
   │  - Reuse shared httpx client
   │
   ▼
5. Repository Operation
   │  - Use injected client
   │  - Execute query (no explicit user_id filter)
   │
   ▼
6. Supabase PostgREST
   │  - Parse Authorization header
   │  - Verify JWT, set auth.uid()
   │
   ▼
7. PostgreSQL + RLS
   │  - Apply RLS policy: auth.uid() = user_id
   │  - Return only authorized rows
   │
   ▼
8. Response
```

### 統合ポイント一覧

| 統合ポイント | 箇所 | 旧実装 | 新実装 | 切替方式 |
|------------|-----|-------|-------|---------|
| Supabaseクライアント取得 | dependencies.py | なし | get_user_supabase_client() | 新規追加 |
| Agentリポジトリ | agents.py | get_repository() 内部生成 | Depends()で注入 | DI変更 |
| Slackリポジトリ | slack.py | 内部生成 | Depends()で注入 | DI変更 |
| Googleリポジトリ | google.py | 内部生成 | Depends()で注入 | DI変更 |

### 主要コンポーネント

#### supabase_client.py（拡張）

- **責務**: Supabaseクライアントの生成と管理
- **インターフェース**:
  ```python
  def get_shared_httpx_client() -> httpx.Client
  def create_user_supabase_client(access_token: str) -> Client
  def get_supabase_client() -> Client | None  # 既存（service_role用、管理タスク向け）
  ```
- **依存関係**: httpx, supabase-py, config

#### dependencies.py（拡張）

- **責務**: FastAPI依存性の提供
- **インターフェース**:
  ```python
  async def get_current_user_id(...) -> UUID  # 既存
  async def get_user_supabase_client(...) -> Client  # 新規
  ```
- **依存関係**: supabase_client, FastAPI security

#### Repository実装（統一）

- **責務**: データアクセス
- **インターフェース**: コンストラクタで`Client`を受け取る
- **依存関係**: domain entities, supabase Client

### 型定義

```python
from typing import Protocol
from uuid import UUID
from supabase import Client

class SupabaseClientFactory(Protocol):
    """Supabaseクライアント生成のプロトコル."""

    def create_user_client(self, access_token: str) -> Client:
        """ユーザーJWTを使用してクライアントを生成."""
        ...

class UserContext:
    """リクエストスコープのユーザーコンテキスト."""

    user_id: UUID
    access_token: str
    supabase_client: Client
```

### データ契約

#### create_user_supabase_client

```yaml
入力:
  型: str (JWT access_token)
  前提条件: 有効なSupabase JWT形式
  バリデーション: 空文字列でないこと

出力:
  型: supabase.Client
  保証: Authorization headerにユーザーJWTが設定されている
  エラー時: 例外をスロー（設定不備の場合）

不変条件:
  - 共有httpxクライアントは変更されない
  - 返却されるClientはリクエストスコープで使用
```

### 統合境界の約束

```yaml
境界名: FastAPI Endpoint -> Repository
  入力: Supabase Client (user context付き)
  出力: Domain Entity (同期/非同期)
  エラー時: Supabase例外をドメイン例外に変換

境界名: Repository -> Supabase
  入力: SQL操作リクエスト
  出力: データ行 (RLSフィルタ適用済み)
  エラー時: Supabase APIException

境界名: Supabase -> PostgreSQL RLS
  入力: JWT (Authorization header)
  出力: auth.uid() がセットされたセッション
  エラー時: 401 Unauthorized (JWT無効時)
```

### エラーハンドリング

| エラー種別 | 発生箇所 | 対処 |
|-----------|---------|------|
| JWT無効/期限切れ | get_current_user_id | 401 HTTPException |
| Supabase設定不備 | create_user_supabase_client | 500 HTTPException + ログ |
| RLSポリシー拒否 | Repository操作 | 空結果または影響行数0 |
| DB接続エラー | Repository操作 | 503 HTTPException |

### ロギングとモニタリング

- **INFO**: ユーザーコンテキスト付きクライアント生成
- **WARNING**: RLSにより結果が0件の更新/削除操作
- **ERROR**: JWT検証失敗、DB接続エラー

## 実装計画

### 実装アプローチ

**選択したアプローチ**: 水平スライス（基盤駆動）+ 短期対策の垂直スライス

**選択理由**:
1. セキュリティ脆弱性の即時対処が必要（短期対策：user_idフィルタ追加）
2. 基盤となるSupabaseクライアント改善を先行し、全リポジトリで統一的に利用
3. ADR-0001のクリーンアーキテクチャに沿った層別の段階的改善

### 技術的依存関係と実装順序

#### 必要な実装順序

1. **Phase 1: 短期対策（セキュリティ修正）**
   - 技術的理由: 脆弱性の即時対処
   - 依存要素: なし
   - 内容: UPDATE操作にuser_idフィルタを追加
   - 確認レベル: L2（テスト動作確認）

2. **Phase 2: httpxクライアントシングルトン化**
   - 技術的理由: パフォーマンス基盤の確立
   - 前提条件: なし
   - 内容: 共有httpxクライアントの実装
   - 確認レベル: L3（ビルド成功確認）

3. **Phase 3: ユーザーコンテキスト付きクライアント生成**
   - 技術的理由: Phase 2の共有クライアントを活用
   - 前提条件: Phase 2完了
   - 内容: create_user_supabase_client()の実装
   - 確認レベル: L2（テスト動作確認）

4. **Phase 4: FastAPI依存性注入拡張**
   - 技術的理由: Phase 3のクライアント生成をDIで提供
   - 前提条件: Phase 3完了
   - 内容: get_user_supabase_client()依存性の追加
   - 確認レベル: L2（テスト動作確認）

5. **Phase 5: リポジトリ依存性注入統一**
   - 技術的理由: Phase 4の依存性を利用
   - 前提条件: Phase 4完了
   - 内容: 全リポジトリでコンストラクタDIに統一
   - 確認レベル: L1（機能動作確認）

6. **Phase 6: エンドポイント統合**
   - 技術的理由: Phase 5のリポジトリを利用
   - 前提条件: Phase 5完了
   - 内容: 各エンドポイントでユーザーSupabaseクライアントを注入
   - 確認レベル: L1（機能動作確認）

### 統合ポイント

各統合ポイントでE2E確認が必要：

**統合ポイント1: Phase 1完了後**
- コンポーネント: Repository -> Database
- 確認方法: UPDATE操作が自分のデータのみ更新することをテストで検証

**統合ポイント2: Phase 4完了後**
- コンポーネント: Endpoint -> Supabase Client
- 確認方法: ユーザーJWTがSupabaseクライアントに正しく設定されることを検証

**統合ポイント3: Phase 6完了後（最終）**
- コンポーネント: Full Stack (Endpoint -> Repository -> RLS)
- 確認方法: 異なるユーザーでログインし、相互のデータにアクセスできないことを検証

### 移行戦略

1. **短期対策（Phase 1）**: 即座にuser_idフィルタを追加し、脆弱性を解消
2. **並行運用**: Phase 2-5の間、既存のservice_roleクライアントとユーザーコンテキストクライアントを並行運用
3. **段階的切り替え**: Phase 6で各エンドポイントを順次ユーザーコンテキストクライアントに切り替え
4. **service_roleキーの用途限定**: 管理タスク（マイグレーション、バッチ処理）のみに限定

## テスト戦略

### 単体テスト

- `create_user_supabase_client()`が正しいヘッダーでクライアントを生成することを検証
- `get_shared_httpx_client()`がシングルトンであることを検証
- リポジトリがコンストラクタで受け取ったクライアントを使用することを検証

### 統合テスト

- ユーザーJWTを使用してSupabaseにアクセスし、RLSが適用されることを検証
- 異なるユーザーのJWTで同じリソースにアクセスし、データ分離を検証
- UPDATE/DELETE操作が他ユーザーのデータに影響しないことを検証

### E2Eテスト

- 認証フローからデータ操作まで、ユーザー単位でのデータ分離を検証
- セッション切り替え時のデータ分離を検証

## セキュリティ考慮事項

1. **JWT漏洩リスク**: JWTはリクエストスコープでのみ使用し、ログに出力しない
2. **service_roleキー**: 管理タスク専用に限定し、通常のAPI操作には使用しない
3. **RLSバイパス**: service_roleキーの使用箇所を明示的に管理し、監査可能にする
4. **トークン有効期限**: Supabase Authのデフォルト有効期限（1時間）を尊重

## 代替案

### 代替案1: JWTからユーザーIDを抽出し、全クエリにフィルタ追加

- **概要**: 現状のservice_roleキーを維持し、アプリケーション層で全クエリにuser_idフィルタを追加
- **メリット**: 既存アーキテクチャの変更が少ない
- **デメリット**: 実装漏れリスクが継続、防御の深さがない
- **不採用理由**: 今回検出された脆弱性と同様の問題が再発するリスクが高い

### 代替案2: カスタムミドルウェアでRLSセッション変数を設定

- **概要**: PostgreSQL接続時にセッション変数（`app.current_user_id`）を設定し、RLSポリシーで参照
- **メリット**: supabase-pyの制約を回避可能
- **デメリット**: Supabase標準のauth.uid()を使用できない、カスタム実装が必要
- **不採用理由**: Supabase標準のRLSパターンから逸脱し、保守性が低下

## リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|-----|
| RLSポリシー設定ミスによるデータアクセス不可 | 高 | 中 | 既存ポリシーのテスト、段階的ロールアウト |
| httpxクライアント共有による競合 | 中 | 低 | スレッドセーフな実装、負荷テスト |
| パフォーマンス劣化 | 中 | 中 | httpxシングルトン化、メトリクス監視 |
| JWTの不正使用 | 高 | 低 | 既存のJWKS検証を維持、ログ監視 |

## 参考資料

- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase Token Security](https://supabase.com/docs/guides/auth/oauth-server/token-security)
- [supabase-py GitHub Repository](https://github.com/supabase-community/supabase-py)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [httpx Client Lifecycle](https://www.python-httpx.org/advanced/clients/)

## 更新履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|-----|-----------|---------|-------|
| 2026-02-02 | 1.0 | 初版作成 | AI Assistant |
