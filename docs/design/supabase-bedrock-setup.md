# Supabase + Bedrock 統合セットアップ 設計書

## 概要

本設計書は、Shitaku.aiにSupabase（Auth + Database）とAWS Bedrock（Claude + Embeddings）を統合するための初期セットアップ設計を定義する。同時にクリーンアーキテクチャへの全体移行を実施する。スコープは「接続確認のみ」に限定し、本格的な機能実装は別タスクとする。

## 設計サマリー（メタ）

```yaml
design_type: "新機能 + アーキテクチャ移行"
risk_level: "中"
main_constraints:
  - "スコープは接続確認のみ（本格実装は別タスク）"
  - "コストゼロ運用（Supabase無料枠 + AWS Activateクレジット）"
  - "クリーンアーキテクチャ + DDDへの全体移行"
biggest_risks:
  - "アーキテクチャ移行による既存機能の破壊"
  - "Supabase無料枠の制限（500MB DB、50,000 MAU）"
  - "AWS Bedrockのリージョン制約とクォータ"
unknowns:
  - "Supabase Auth移行時のセッション管理方式"
  - "既存JWT認証との並行運用期間"
```

## 背景と経緯

### 前提となるADR

- **ADR-0001**: クリーンアーキテクチャ + DDD 採用 (Accepted)
  - 4層構造（domain/application/infrastructure/presentation）への移行
  - 依存性の方向: 外側から内側への一方向のみ

### 合意事項チェックリスト

#### スコープ
- [x] クリーンアーキテクチャへの全体移行
- [x] Supabase DB接続確認（SQLAlchemy経由）
- [x] Supabase Auth動作確認（トークン検証）
- [x] Bedrock Claude API呼び出し確認
- [x] Bedrock Embeddings API呼び出し確認
- [x] 環境変数の追加・設定

#### スコープ外（明示的に変更しないもの）
- [ ] 本格的なSupabase Auth統合
- [ ] アジェンダ生成機能の実装
- [ ] ユビキタス言語辞書の実装

#### 制約
- [x] 並行運用: する（既存Docker PostgreSQL + Supabase両対応）
- [x] 後方互換性: 必要（既存API動作を維持）
- [ ] パフォーマンス計測: 不要（接続確認のみ）

## 受入条件（AC）- EARS形式

### AC1: Supabase DB接続確認

- [ ] **When** `SUPABASE_DATABASE_URL`環境変数が設定されている場合、システムはSupabase PostgreSQLに接続できる
  - **Property**: `connection.is_connected == True`
- [ ] **When** Supabase DB接続後にSELECTクエリを実行すると、結果が正常に返却される
- [ ] **If** `SUPABASE_DATABASE_URL`が未設定の場合、**then** 既存の`DATABASE_URL`（Docker PostgreSQL）にフォールバックする

### AC2: Supabase Auth動作確認

- [ ] **When** 有効なSupabase JWTトークンを含むリクエストを受信すると、システムはトークンを検証しユーザー情報を取得できる
- [ ] **If** JWTトークンが無効な場合、**then** システムは401 Unauthorizedを返却する
- [ ] **When** `SUPABASE_JWT_SECRET`が設定されている場合、システムはSupabase Authのトークン検証を有効化する

### AC3: Bedrock Claude API呼び出し確認

- [ ] **When** Bedrock Claude APIにプロンプトを送信すると、システムはテキスト応答を受信する
  - **Property**: `response.content.length > 0`
- [ ] **When** Claude Haiku 4.5モデル（`anthropic.claude-haiku-4-5-20251001-v1:0`）を指定した場合、正常に応答が返却される
- [ ] **If** AWS認証情報が無効な場合、**then** システムは適切なエラーメッセージを返却する

### AC4: Bedrock Embeddings API呼び出し確認

- [ ] **When** Bedrock Titan Embeddings V2 APIにテキストを送信すると、システムは埋め込みベクトルを受信する
  - **Property**: `len(embedding) == 1024`（デフォルト次元数）
- [ ] **When** 次元数を256に指定した場合、256次元のベクトルが返却される
  - **Property**: `len(embedding) == 256`

## ディレクトリ構造（クリーンアーキテクチャ）

### 移行前（現状）

```
backend/
  app/
    api/v1/endpoints/  # APIエンドポイント
    core/              # コア設定
    crud/              # CRUD操作
    db/                # DB接続
    models/            # SQLAlchemyモデル
    schemas/           # Pydanticスキーマ
    services/          # サービス
    config.py
    main.py
```

### 移行後（新構造）

```
backend/
  src/
    domain/                          # ドメイン層（最内層）
      entities/
        __init__.py
        user.py                      # Userエンティティ（ピュアPython）
      repositories/
        __init__.py
        user_repository.py           # リポジトリIF（抽象基底クラス）
      services/
        __init__.py
    application/                     # アプリケーション層
      use_cases/
        __init__.py
      dto/
        __init__.py
    infrastructure/                  # インフラ層
      database/
        __init__.py
        session.py                   # DB接続（Supabase対応）
        models/
          __init__.py
          user.py                    # SQLAlchemyモデル
      external/
        __init__.py
        supabase_client.py           # Supabaseクライアント
        bedrock_client.py            # Bedrockクライアント
      repositories/
        __init__.py
        user_repository_impl.py      # リポジトリ実装
    presentation/                    # プレゼンテーション層（最外層）
      api/
        __init__.py
        v1/
          __init__.py
          endpoints/
            __init__.py
            health.py
            health_check.py          # 接続確認エンドポイント
            users.py
          router.py
      schemas/
        __init__.py
        user.py
        health.py
    config.py                        # 設定
    main.py                          # エントリポイント
  tests/
    unit/
    integration/
```

## 設計

### 変更影響マップ

```yaml
変更対象: 全体アーキテクチャ、外部サービス統合
直接影響:
  - backend/app/ -> backend/src/ （全ファイル移行）
  - 新規: infrastructure/external/supabase_client.py
  - 新規: infrastructure/external/bedrock_client.py
  - 新規: presentation/api/v1/endpoints/health_check.py
間接影響:
  - docker-compose.yml（環境変数追加）
  - backend/.env.example（サンプル更新）
  - pyproject.toml（依存関係追加）
波及なし:
  - フロントエンド（API契約維持）
```

### アーキテクチャ概要

```mermaid
graph TB
    subgraph "Presentation Layer"
        API[FastAPI Endpoints]
        Schemas[Request/Response Schemas]
    end

    subgraph "Application Layer"
        UseCases[Use Cases]
        DTO[DTOs]
    end

    subgraph "Domain Layer"
        Entities[Entities]
        RepoIF[Repository Interfaces]
        DomainServices[Domain Services]
    end

    subgraph "Infrastructure Layer"
        RepoImpl[Repository Implementations]
        DBSession[Database Session]
        SQLAlchemy[SQLAlchemy Models]
        SupabaseClient[Supabase Client]
        BedrockClient[Bedrock Client]
    end

    subgraph "External Services"
        SupabaseDB[(Supabase PostgreSQL)]
        SupabaseAuth[Supabase Auth]
        BedrockClaude[Bedrock Claude Haiku 4.5]
        BedrockEmbed[Bedrock Titan Embeddings V2]
    end

    API --> UseCases
    UseCases --> Entities
    UseCases --> RepoIF
    RepoImpl -.-> RepoIF
    RepoImpl --> SQLAlchemy
    DBSession --> SupabaseDB
    SupabaseClient --> SupabaseAuth
    BedrockClient --> BedrockClaude
    BedrockClient --> BedrockEmbed
```

### 依存性の方向

```
presentation → application → domain ← infrastructure
```

- 外側から内側への一方向のみ
- ドメイン層は他のどの層にも依存しない
- インフラ層はドメイン層のインターフェースを実装（依存性逆転）

### 主要コンポーネント

#### infrastructure/external/supabase_client.py

- **責務**: Supabase Python Clientの初期化とJWT検証
- **配置層**: Infrastructure
- **インターフェース**:
  ```python
  def get_supabase_client() -> Client | None
  def verify_supabase_jwt(token: str) -> dict | None
  ```
- **依存関係**: supabase-py、pyjwt

#### infrastructure/external/bedrock_client.py

- **責務**: AWS Bedrock Clientの初期化とモデル呼び出し
- **配置層**: Infrastructure
- **インターフェース**:
  ```python
  def get_bedrock_client() -> boto3.client
  def invoke_claude(prompt: str, max_tokens: int = 512) -> str
  def invoke_embeddings(text: str, dimensions: int = 1024) -> list[float]
  ```
- **依存関係**: boto3

#### presentation/api/v1/endpoints/health_check.py

- **責務**: 各サービスへの接続確認エンドポイント提供
- **配置層**: Presentation
- **インターフェース**:
  ```python
  @router.get("/health/services")
  def check_services() -> ServiceHealthResponse
  ```

### 型定義

```python
# presentation/schemas/health.py
from pydantic import BaseModel

class ServiceHealthResponse(BaseModel):
    """サービス接続確認レスポンス"""
    supabase_db: bool
    supabase_auth: bool
    bedrock_claude: bool
    bedrock_embeddings: bool
    details: dict[str, str | None]
```

### データ契約

#### Bedrock Claude API

```yaml
入力:
  型: |
    {
      "anthropic_version": "bedrock-2023-05-31",
      "max_tokens": int,
      "messages": [{"role": "user", "content": [{"type": "text", "text": str}]}]
    }

出力:
  型: |
    {
      "content": [{"type": "text", "text": str}],
      "usage": {"input_tokens": int, "output_tokens": int}
    }

不変条件:
  - モデルID: anthropic.claude-haiku-4-5-20251001-v1:0
  - リージョン: us-east-1
```

#### Bedrock Titan Embeddings V2

```yaml
入力:
  型: |
    {
      "inputText": str,
      "dimensions": 256 | 512 | 1024,
      "normalize": bool
    }

出力:
  型: |
    {
      "embedding": list[float],
      "inputTextTokenCount": int
    }

不変条件:
  - モデルID: amazon.titan-embed-text-v2:0
  - リージョン: us-east-1
```

## 実装計画

### 実装アプローチ

**選択したアプローチ**: 垂直スライス（機能駆動）+ 段階的移行

**フェーズ分割**:

1. **Phase 1: ディレクトリ構造構築**
   - `backend/src/`ディレクトリ構造作成
   - 空の`__init__.py`配置

2. **Phase 2: 既存コード移行**
   - `app/config.py` → `src/config.py`
   - `app/db/` → `src/infrastructure/database/`
   - `app/models/` → `src/infrastructure/database/models/`
   - `app/crud/` → `src/infrastructure/repositories/`
   - `app/schemas/` → `src/presentation/schemas/`
   - `app/api/` → `src/presentation/api/`
   - `app/main.py` → `src/main.py`

3. **Phase 3: ドメイン層抽出**
   - Userエンティティ作成（ピュアPython）
   - リポジトリインターフェース定義

4. **Phase 4: Supabase統合**
   - `infrastructure/external/supabase_client.py`作成
   - DB接続のSupabase対応
   - JWT検証機能追加

5. **Phase 5: Bedrock統合**
   - `infrastructure/external/bedrock_client.py`作成
   - Claude/Embeddings呼び出し機能

6. **Phase 6: 接続確認エンドポイント**
   - `health_check.py`作成
   - 全サービスの接続確認

### 環境変数追加

```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxxx
SUPABASE_DATABASE_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres
SUPABASE_JWT_SECRET=your-jwt-secret

# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
```

### 依存関係追加

```toml
# pyproject.toml
dependencies = [
    # 既存...
    "supabase>=2.0.0",
    "boto3>=1.35.0",
]
```

## テスト戦略

### 単体テスト

- **ドメイン層**: 外部依存なし、ピュアPythonでテスト可能
- **インフラ層**: モック使用でクライアント初期化テスト
- カバレッジ目標: 80%以上

### 統合テスト

- 実際のSupabase/Bedrock接続確認（テスト用プロジェクト使用）
- 最小リクエストで課金最小化

### E2Eテスト

- `/api/v1/health/services`エンドポイントの動作確認
- 自動化は本格実装フェーズで検討

## セキュリティ考慮事項

| 項目 | 対策 |
|-----|-----|
| AWS認証情報 | 環境変数で管理、コードに含めない |
| Supabase API Key | 環境変数で管理、service_role_keyは使用しない |
| JWT Secret | 環境変数で管理、ログ出力禁止 |
| エラーメッセージ | 機密情報を含めない |

## リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|-----|
| 移行中の既存機能破壊 | 高 | 中 | 段階的移行、各フェーズでテスト実行 |
| import文の修正漏れ | 中 | 高 | IDE検索で網羅的確認 |
| Supabase無料枠超過 | 中 | 低 | 使用量モニタリング |
| Bedrockクォータ制限 | 中 | 中 | リクエストレート制限 |

## 参考資料

- [ADR-0001: クリーンアーキテクチャ + DDD 採用](../adr/ADR-0001-clean-architecture-adoption.md)
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Supabase Python Client](https://github.com/supabase/supabase-py)
- [Amazon Bedrock Runtime SDK](https://docs.aws.amazon.com/bedrock/latest/userguide/)

## 更新履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|-----|-----------|---------|-------|
| 2026-01-31 | 1.0 | 初版作成 | AI Assistant |
| 2026-01-31 | 2.0 | クリーンアーキテクチャ対応に全面改訂 | AI Assistant |
