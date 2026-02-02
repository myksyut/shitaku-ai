# Google Workspace連携機能 設計書

## 概要

Google Workspace連携機能を実装し、定例MTGの自動検出とMeetトランスクリプトの取得を実現する。これにより、コールドスタート問題を解消し、初回から価値を提供する。

## 設計サマリー（メタ）

```yaml
design_type: "新規機能"
risk_level: "高"
main_constraints:
  - "既存Slack連携パターンとの一貫性"
  - "ADR-0001クリーンアーキテクチャ準拠"
  - "Google API Services User Data Policy準拠"
biggest_risks:
  - "Google OAuth検証の遅延（公開審査が必要）"
  - "Meetトランスクリプトの形式変更への依存"
  - "レートリミット対応の複雑さ"
unknowns:
  - "トランスクリプトのファイル名形式（Googleが変更する可能性）"
  - "非正規定例の検出精度"
```

## 背景と経緯

### 前提となるADR

- **ADR-0001**: クリーンアーキテクチャ + DDD 採用 - ドメインエンティティ設計、層構造
- **ADR-0003**: Google Workspace連携の認証・トークン管理方式 - OAuth実装パターン
- **ADR-0005**: 1エージェント複数定例会議の紐付け対応 - 1対多対応の設計方針

### 合意事項チェックリスト

#### スコープ

- [x] Google OAuth認証（Incremental Authorization対応）
- [x] Calendar API - 定例MTG自動検出（RRULE解析）
- [x] Drive API + Docs API - トランスクリプト取得
- [x] カレンダー↔トランスクリプト自動紐付け
- [x] DBスキーマ: 新規テーブル4つ（google_integrations, recurring_meetings, meeting_transcripts, generated_agendas）
  - **Note**: `generated_agendas`テーブルはPhase 1でスキーマのみ作成し、Phase 2のアジェンダ生成機能実装時にすぐ利用可能な状態にしておく（マイグレーションの分割を避け、関連テーブルを一括で作成する方針）
- [x] **1エージェント複数定例紐付け対応**（ADR-0005）
  - DBスキーマは既に1対多対応済み（`recurring_meetings.agent_id`がFK）
  - アプリケーション層（リポジトリ、API、UI）を1対多に対応させる

#### スコープ外（明示的に変更しないもの）

- [x] アジェンダ生成ロジック（Phase 1ではトランスクリプト取得まで。ただし`generated_agendas`テーブルは先行作成）
- [x] Slack連携の既存機能
- [x] Meet REST API v2（Phase 2で対応）
- [x] 非正規定例のヒューリスティック検出（Phase 2で対応）

#### 制約

- [x] 暗号化方式: Fernet継続（Slack連携と同一）
- [x] 認証実装: バックエンド直接実装（Supabase Authは使用しない）
- [x] MVPでは内部アプリ（テストユーザー100人まで）

### 解決すべき課題

1. **コールドスタート問題**: 新規エージェント作成時に過去の文脈がない
2. **定例MTGの手動登録**: ユーザーが手動で定例情報を入力する必要がある
3. **議事録の分散**: Google Docs、Slack、手動入力など複数ソースに分散

### 要件

#### 機能要件

- ユーザーがGoogleアカウントでログイン/連携できる
- Calendar APIから繰り返し予定を自動検出し、定例MTG候補として表示
- Google Meetのトランスクリプトを自動取得し、カレンダーイベントと紐付け
- 紐付けの信頼度が低い場合は手動確認をリクエスト

#### 非機能要件

- **パフォーマンス**: Calendar取得は3秒以内、トランスクリプト取得は5秒以内
- **セキュリティ**: RLSによるマルチテナント分離、トークンのFernet暗号化
- **可用性**: Google APIエラー時のグレースフルデグラデーション

## 受入条件（AC）- EARS形式

### Google OAuth認証

- [x] **When** ユーザーが「Googleで連携」ボタンをクリックすると、システムはGoogle OAuth認可画面にリダイレクトする
- [x] **When** ユーザーがGoogleでスコープを許可すると、システムはRefresh Tokenを暗号化して保存し、フロントエンドの成功画面にリダイレクトする
- [x] **If** ユーザーが認可をキャンセルした場合、**then** システムはエラー画面にリダイレクトする
- [x] **When** 既存の連携がある場合、システムはRefresh Tokenを更新する（新規作成ではなく）

### 定例MTG同期・紐付け

- [ ] **When** ユーザーがGoogle連携を完了すると、システムはCalendar APIから繰り返し予定を自動同期する
- [ ] システムは繰り返しルール（RRULE）を持つイベントのみを同期対象とする
- [ ] システムは参加者2人以上のイベントのみを同期対象とする
- [ ] システムは過去3ヶ月以内に実績のあるイベントのみを同期対象とする
- [ ] **When** ユーザーがエージェント詳細画面で「定例を紐付け」をクリックすると、システムは同期済み定例一覧をモーダルで表示する
- [ ] **When** ユーザーが定例を選択すると、システムはエージェントと定例を紐付ける

### トランスクリプト取得

- [x] **When** 追加スコープ（drive.readonly, documents.readonly）が未許可の場合、システムはIncremental Authorization画面を表示する
- [x] **When** スコープが許可されている場合、システムはMeet Recordingsフォルダからトランスクリプトを検索する
- [x] システムはGoogle Docsからテキストコンテンツを取得し、話者・タイムスタンプ・発話内容を構造化する

### 紐付けロジック

- [x] システムはドキュメント名と会議名のマッチングを行う
- [x] システムはドキュメント作成日時とイベント日時を比較する（±24時間以内）
- [x] システムは参加者名とトランスクリプト内の話者名を照合する
- [x] **If** 信頼度スコアが閾値（0.7）以上の場合、**then** システムは自動紐付けを行う
- [x] **If** 信頼度スコアが閾値未満の場合、**then** システムは手動確認をリクエストする

### 1エージェント複数定例紐付け（ADR-0005対応）

- [ ] **AC1**: **When** ユーザーがエージェント詳細画面で定例紐付けモーダルから定例を選択すると、システムは選択された定例をエージェントに紐付ける。**Property**: 紐付け後、エージェントに関連する定例の件数が1増加する
- [ ] **AC2**: **When** ユーザーがエージェント詳細画面を開くと、システムは紐付け済みの定例一覧を表示する。**Property**: 一覧には紐付けられた全ての定例が表示され、各定例のタイトル・頻度・次回開催日時が確認できる
- [ ] **AC3**: **When** ユーザーが「定例を追加」ボタンをクリックすると、システムは定例選択モーダルを表示する。**Property**: モーダルには未紐付けの同期済み定例のみが表示される
- [ ] **AC4**: **When** ユーザーが紐付け済み定例の「解除」ボタンをクリックすると、システムはその定例とエージェントの紐付けを解除する。**Property**: 解除後、エージェントに関連する定例の件数が1減少し、解除された定例は定例選択モーダルで再び選択可能になる
- [ ] **AC5**: **When** アジェンダ生成がトリガーされると、システムは紐付けられた全ての定例からトランスクリプト・Slack履歴を収集し、統合したアジェンダを生成する。**Property**: 生成されたアジェンダには、紐付けられた全定例の情報源が「sources」フィールドに記録される

## 既存コードベース分析

### 実装パスマッピング

| 種別 | パス | 説明 |
|-----|-----|-----|
| 参照 | backend/src/application/use_cases/slack_use_cases.py | OAuth実装パターンの参照 |
| 参照 | backend/src/infrastructure/external/encryption.py | トークン暗号化モジュール |
| 参照 | backend/src/presentation/api/v1/endpoints/slack.py | APIエンドポイントパターン |
| 新規 | backend/src/domain/entities/google_integration.py | Google連携エンティティ |
| 新規 | backend/src/domain/entities/recurring_meeting.py | 定例MTGエンティティ |
| 新規 | backend/src/domain/entities/meeting_transcript.py | トランスクリプトエンティティ |
| 新規 | backend/src/domain/entities/generated_agenda.py | 生成アジェンダエンティティ |
| 新規 | backend/src/domain/repositories/google_integration_repository.py | リポジトリインターフェース |
| 新規 | backend/src/domain/repositories/recurring_meeting_repository.py | リポジトリインターフェース |
| 新規 | backend/src/domain/repositories/meeting_transcript_repository.py | リポジトリインターフェース |
| 新規 | backend/src/infrastructure/repositories/google_integration_repository_impl.py | リポジトリ実装 |
| 新規 | backend/src/infrastructure/repositories/recurring_meeting_repository_impl.py | リポジトリ実装 |
| 新規 | backend/src/infrastructure/repositories/meeting_transcript_repository_impl.py | リポジトリ実装 |
| 新規 | backend/src/infrastructure/external/google_oauth_client.py | Google OAuthクライアント |
| 新規 | backend/src/infrastructure/external/google_calendar_client.py | Calendar APIクライアント |
| 新規 | backend/src/infrastructure/external/google_drive_client.py | Drive APIクライアント |
| 新規 | backend/src/infrastructure/external/google_docs_client.py | Docs APIクライアント |
| 新規 | backend/src/application/use_cases/google_auth_use_cases.py | 認証ユースケース |
| 新規 | backend/src/application/use_cases/calendar_use_cases.py | カレンダーユースケース |
| 新規 | backend/src/application/use_cases/transcript_use_cases.py | トランスクリプトユースケース |
| 新規 | backend/src/presentation/api/v1/endpoints/google.py | APIエンドポイント |
| 新規 | backend/src/presentation/schemas/google.py | リクエスト/レスポンススキーマ |
| 新規 | supabase/migrations/YYYYMMDD_create_google_integrations.sql | DBマイグレーション |
| 新規 | supabase/migrations/YYYYMMDD_create_recurring_meetings.sql | DBマイグレーション |
| 新規 | supabase/migrations/YYYYMMDD_create_meeting_transcripts.sql | DBマイグレーション |
| 新規 | supabase/migrations/YYYYMMDD_create_generated_agendas.sql | DBマイグレーション |
| 新規 | frontend/src/features/google/GoogleIntegrationPage.tsx | Google連携ページ |
| 新規 | frontend/src/features/agents/RecurringMeetingSelector.tsx | 定例MTG紐付けモーダル |
| 変更 | frontend/src/features/agents/AgentDetailPage.tsx | 定例紐付けUI追加 |
| 新規 | frontend/src/features/google/TranscriptViewer.tsx | トランスクリプト表示 |
| 新規 | frontend/src/features/google/hooks.ts | カスタムフック |
| 新規 | frontend/src/features/google/api.ts | API呼び出し |
| 新規 | frontend/src/features/google/types.ts | 型定義 |

### 類似コンポーネント検索結果

- `slack_use_cases.py` / `slack.py`: OAuth認証パターン
- **判断**: Slack連携と同様のパターンで実装
- **根拠**: 既存の認証フロー、トークン管理、エンドポイント設計が参考になる

## 設計

### 変更影響マップ

```yaml
変更対象: Google Workspace連携機能全体
直接影響:
  - backend/src/domain/entities/: 新規エンティティ4つ
  - backend/src/domain/repositories/: 新規リポジトリインターフェース3つ
  - backend/src/infrastructure/external/: 新規クライアント4つ
  - backend/src/infrastructure/repositories/: 新規リポジトリ実装3つ
  - backend/src/application/use_cases/: 新規ユースケース3つ
  - backend/src/presentation/: 新規エンドポイント・スキーマ
  - backend/src/infrastructure/external/encryption.py: GOOGLE_TOKEN_ENCRYPTION_KEY対応追加
  - backend/src/config.py: Google OAuth設定追加
  - supabase/migrations/: 新規マイグレーション4つ
  - frontend/src/features/google/: 新規ディレクトリ
間接影響:
  - backend/src/presentation/api/v1/router.py: 新規ルーター登録
  - frontend/src/App.tsx: 新規ルート追加
波及なし:
  - Slack連携機能
  - 辞書機能
  - エージェント管理機能（データ連携は次フェーズ）
```

#### 1エージェント複数定例紐付け対応の変更影響マップ（ADR-0005）

```yaml
変更対象: エージェント・定例MTG紐付け機能
直接影響:
  - backend/src/domain/repositories/recurring_meeting_repository.py:
      - get_by_agent_id → get_list_by_agent_id（戻り値型変更）
      - link_to_agent / unlink_from_agent メソッド追加
  - backend/src/infrastructure/repositories/recurring_meeting_repository_impl.py:
      - maybe_single() → execute()（複数結果対応）
      - link/unlinkメソッド実装
  - backend/src/presentation/api/v1/endpoints/agents.py:
      - エンドポイント追加（GET/POST/DELETE /recurring-meetings）
  - backend/src/presentation/schemas/google.py:
      - LinkRecurringMeetingRequest/Response追加
  - frontend/src/features/agents/AgentDetailPage.tsx:
      - 紐付け済み定例一覧表示、追加ボタン、解除ボタン
  - frontend/src/features/agents/RecurringMeetingSelector.tsx:
      - 複数選択対応（未紐付け定例のフィルタリング）
  - frontend/src/features/google/hooks.ts:
      - useAgentRecurringMeetings, useLinkRecurringMeeting, useUnlinkRecurringMeeting追加
  - frontend/src/features/google/api.ts:
      - getAgentRecurringMeetings, linkRecurringMeeting, unlinkRecurringMeeting追加
間接影響:
  - backend/src/application/use_cases/calendar_use_cases.py: 複数定例取得対応
  - アジェンダ生成ロジック（Phase 2）: 複数定例からの情報統合
波及なし:
  - DBスキーマ（既に1対多対応済み）
  - Google OAuth認証
  - トランスクリプト取得
```

### アーキテクチャ概要

```mermaid
graph TD
    subgraph Frontend
        GIP[GoogleIntegrationPage]
        RML[RecurringMeetingList]
        TV[TranscriptViewer]
        GH[useGoogleIntegration]
    end

    subgraph Backend
        subgraph Presentation
            GAE[/api/v1/google/auth]
            GCE[/api/v1/google/calendar]
            GTE[/api/v1/google/transcripts]
        end

        subgraph Application
            GAUC[GoogleAuthUseCases]
            CUC[CalendarUseCases]
            TUC[TranscriptUseCases]
        end

        subgraph Domain
            GI[GoogleIntegration]
            RM[RecurringMeeting]
            MT[MeetingTranscript]
            REPO_IF[Repositories Interface]
        end

        subgraph Infrastructure
            GOC[GoogleOAuthClient]
            GCC[GoogleCalendarClient]
            GDC[GoogleDriveClient]
            GDOC[GoogleDocsClient]
            ENC[Encryption]
            REPO_IMPL[Repositories Impl]
            DB[(Supabase)]
        end
    end

    GIP --> GH
    RML --> GH
    TV --> GH
    GH --> GAE
    GH --> GCE
    GH --> GTE

    GAE --> GAUC
    GCE --> CUC
    GTE --> TUC

    GAUC --> GI
    GAUC --> REPO_IF
    CUC --> RM
    CUC --> REPO_IF
    TUC --> MT
    TUC --> REPO_IF

    REPO_IMPL --> REPO_IF
    REPO_IMPL --> DB
    GAUC --> GOC
    GAUC --> ENC
    CUC --> GCC
    TUC --> GDC
    TUC --> GDOC
```

### データフロー

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Google

    Note over User,Google: OAuth認証フロー
    User->>Frontend: 「Googleで連携」クリック
    Frontend->>Backend: GET /api/v1/google/auth
    Backend->>Backend: state生成・保存
    Backend-->>Frontend: authorize_url
    Frontend->>Google: リダイレクト
    User->>Google: スコープ許可
    Google->>Backend: callback (code, state)
    Backend->>Backend: state検証
    Backend->>Google: code → token交換
    Google-->>Backend: access_token, refresh_token
    Backend->>Backend: refresh_token暗号化・保存
    Backend-->>Frontend: リダイレクト（成功）

    Note over User,Google: 定例MTG自動同期フロー（OAuth完了時）
    Backend->>Backend: refresh_token復号
    Backend->>Google: Calendar API (singleEvents=false)
    Google-->>Backend: events[]
    Backend->>Backend: RRULE解析・フィルタリング
    Backend->>Backend: recurring_meetingsテーブルに保存

    Note over User,Google: 定例MTG紐付けフロー（複数紐付け対応）
    User->>Frontend: エージェント詳細で「定例を追加」クリック
    Frontend->>Backend: GET /api/v1/google/calendar/recurring
    Backend-->>Frontend: recurring_meetings[]
    Frontend->>Frontend: 未紐付け定例一覧モーダル表示
    User->>Frontend: 定例を選択
    Frontend->>Backend: POST /api/v1/agents/{id}/recurring-meetings
    Backend->>Backend: recurring_meeting.agent_id更新
    Backend-->>Frontend: 成功レスポンス
    Frontend-->>User: 紐付け完了、一覧に追加表示

    Note over User,Google: 定例MTG紐付け解除フロー
    User->>Frontend: 紐付け済み定例の「解除」クリック
    Frontend->>Backend: DELETE /api/v1/agents/{id}/recurring-meetings/{meeting_id}
    Backend->>Backend: recurring_meeting.agent_id = NULL
    Backend-->>Frontend: 成功レスポンス
    Frontend-->>User: 一覧から削除、解除完了表示

    Note over User,Google: 複数定例からの統合アジェンダ生成フロー
    User->>Frontend: アジェンダ生成ボタンクリック
    Frontend->>Backend: POST /api/v1/agents/{id}/generate-agenda
    Backend->>Backend: agent_idで紐付け定例一覧取得
    loop 各定例MTG
        Backend->>Backend: トランスクリプト取得
        Backend->>Backend: Slack履歴取得
    end
    Backend->>Backend: 時系列ソート・文脈統合
    Backend->>Backend: Claude Haiku 4.5でアジェンダ生成
    Backend-->>Frontend: 統合アジェンダ
    Frontend-->>User: アジェンダ表示
```

### 主要コンポーネント

#### GoogleIntegration（ドメインエンティティ）

```python
@dataclass
class GoogleIntegration:
    id: UUID
    user_id: UUID
    email: str
    encrypted_refresh_token: str
    granted_scopes: list[str]
    created_at: datetime
    updated_at: datetime | None

    def has_scope(self, scope: str) -> bool:
        """指定スコープが許可済みか確認"""

    def add_scopes(self, new_scopes: list[str]) -> None:
        """スコープを追加（Incremental Authorization用）"""
```

#### RecurringMeeting（ドメインエンティティ）

```python
@dataclass
class RecurringMeeting:
    id: UUID
    user_id: UUID
    google_event_id: str
    title: str
    rrule: str
    frequency: MeetingFrequency  # WEEKLY, BIWEEKLY, MONTHLY
    attendees: list[Attendee]
    next_occurrence: datetime
    agent_id: UUID | None  # エージェントとの紐付け（1対多：複数定例が同一agent_idを持つ）
    created_at: datetime
    updated_at: datetime | None

    def calculate_next_occurrence(self) -> datetime:
        """次回の開催日時を計算（dateutil.rrule使用）"""

    def link_to_agent(self, agent_id: UUID) -> None:
        """エージェントに紐付け"""
        self.agent_id = agent_id

    def unlink_from_agent(self) -> None:
        """エージェントとの紐付けを解除"""
        self.agent_id = None
```

#### RecurringMeetingRepository（リポジトリインターフェース）- 1対多対応

```python
from abc import ABC, abstractmethod

class RecurringMeetingRepository(ABC):
    @abstractmethod
    def get_by_id(self, id: UUID, user_id: UUID) -> RecurringMeeting | None:
        """IDで単一の定例MTGを取得"""
        pass

    @abstractmethod
    def get_list_by_agent_id(self, agent_id: UUID, user_id: UUID) -> list[RecurringMeeting]:
        """
        エージェントに紐付けられた定例MTG一覧を取得

        Note: ADR-0005により、1エージェントに複数定例を紐付け可能
        戻り値はlist型（従来のmaybe_single()からの変更）
        """
        pass

    @abstractmethod
    def get_unlinked_by_user_id(self, user_id: UUID) -> list[RecurringMeeting]:
        """未紐付けの定例MTG一覧を取得（agent_id IS NULL）"""
        pass

    @abstractmethod
    def link_to_agent(self, recurring_meeting_id: UUID, agent_id: UUID, user_id: UUID) -> RecurringMeeting:
        """定例MTGをエージェントに紐付け"""
        pass

    @abstractmethod
    def unlink_from_agent(self, recurring_meeting_id: UUID, user_id: UUID) -> None:
        """定例MTGとエージェントの紐付けを解除"""
        pass

    @abstractmethod
    def save(self, entity: RecurringMeeting) -> RecurringMeeting:
        """定例MTGを保存"""
        pass
```

#### MeetingTranscript（ドメインエンティティ）

```python
@dataclass
class MeetingTranscript:
    id: UUID
    recurring_meeting_id: UUID
    meeting_date: datetime
    google_doc_id: str
    raw_text: str
    structured_data: TranscriptStructuredData | None
    match_confidence: float  # 紐付け信頼度（0.0-1.0）
    created_at: datetime

@dataclass
class TranscriptStructuredData:
    entries: list[TranscriptEntry]

@dataclass
class TranscriptEntry:
    speaker: str
    timestamp: str
    text: str
```

### フロントエンド型定義（TypeScript）

```typescript
// frontend/src/features/google/types.ts

/** Google連携情報 */
export interface GoogleIntegration {
  id: string
  email: string
  granted_scopes: string[]
  created_at: string
  updated_at: string | null
}

/** 定例MTGの頻度 */
export type MeetingFrequency = 'weekly' | 'biweekly' | 'monthly'

/** 参加者情報 */
export interface Attendee {
  email: string
  name: string | null
}

/** 定例MTG */
export interface RecurringMeeting {
  id: string
  google_event_id: string
  title: string
  rrule: string
  frequency: MeetingFrequency
  attendees: Attendee[]
  next_occurrence: string
  agent_id: string | null
  created_at: string
  updated_at: string | null
}

/** トランスクリプトエントリ */
export interface TranscriptEntry {
  speaker: string
  timestamp: string
  text: string
}

/** 構造化トランスクリプトデータ */
export interface TranscriptStructuredData {
  entries: TranscriptEntry[]
}

/** 会議トランスクリプト */
export interface MeetingTranscript {
  id: string
  recurring_meeting_id: string
  meeting_date: string
  google_doc_id: string
  raw_text: string
  structured_data: TranscriptStructuredData | null
  match_confidence: number
  created_at: string
}

/** アジェンダステータス */
export type AgendaStatus = 'draft' | 'sent' | 'reviewed'

/** 生成アジェンダ */
export interface GeneratedAgenda {
  id: string
  recurring_meeting_id: string
  target_date: string
  agenda_content: Record<string, unknown>
  sources: Record<string, unknown>[]
  status: AgendaStatus
  delivered_via: string | null
  created_at: string
  updated_at: string | null
}

/** OAuth認証開始レスポンス */
export interface GoogleOAuthStartResponse {
  authorize_url: string
}

/** 定例MTG一覧取得レスポンス */
export type RecurringMeetingsResponse = RecurringMeeting[]

/** トランスクリプト一覧取得レスポンス */
export type MeetingTranscriptsResponse = MeetingTranscript[]

// === 1エージェント複数定例紐付け対応（ADR-0005）===

/** エージェントに紐付けられた定例MTG一覧取得レスポンス */
export type AgentRecurringMeetingsResponse = RecurringMeeting[]

/** 定例MTG紐付けリクエスト */
export interface LinkRecurringMeetingRequest {
  recurring_meeting_id: string
}

/** 定例MTG紐付けレスポンス */
export interface LinkRecurringMeetingResponse {
  message: string
  recurring_meeting: RecurringMeeting
}

/** 定例MTG紐付け解除レスポンス */
export interface UnlinkRecurringMeetingResponse {
  message: string
}
```

### データモデル

#### google_integrations

```sql
CREATE TABLE google_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    granted_scopes TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(user_id, email)
);

-- RLSポリシー
ALTER TABLE google_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY google_integrations_user_policy ON google_integrations
    FOR ALL USING (auth.uid() = user_id);
```

#### recurring_meetings

```sql
CREATE TABLE recurring_meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    google_event_id TEXT NOT NULL,
    title TEXT NOT NULL,
    rrule TEXT NOT NULL,
    frequency TEXT NOT NULL CHECK (frequency IN ('weekly', 'biweekly', 'monthly')),
    attendees JSONB NOT NULL DEFAULT '[]',
    next_occurrence TIMESTAMPTZ NOT NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(user_id, google_event_id)
);

-- RLSポリシー
ALTER TABLE recurring_meetings ENABLE ROW LEVEL SECURITY;

CREATE POLICY recurring_meetings_user_policy ON recurring_meetings
    FOR ALL USING (auth.uid() = user_id);

-- インデックス
CREATE INDEX idx_recurring_meetings_user_id ON recurring_meetings(user_id);
CREATE INDEX idx_recurring_meetings_next_occurrence ON recurring_meetings(next_occurrence);
```

#### meeting_transcripts

```sql
CREATE TABLE meeting_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recurring_meeting_id UUID NOT NULL REFERENCES recurring_meetings(id) ON DELETE CASCADE,
    meeting_date TIMESTAMPTZ NOT NULL,
    google_doc_id TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    structured_data JSONB,
    match_confidence REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(recurring_meeting_id, google_doc_id)
);

-- RLSポリシー（親テーブル経由でuser_id検証）
ALTER TABLE meeting_transcripts ENABLE ROW LEVEL SECURITY;

CREATE POLICY meeting_transcripts_user_policy ON meeting_transcripts
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM recurring_meetings rm
            WHERE rm.id = meeting_transcripts.recurring_meeting_id
            AND rm.user_id = auth.uid()
        )
    );

-- インデックス
CREATE INDEX idx_meeting_transcripts_recurring_meeting_id ON meeting_transcripts(recurring_meeting_id);
CREATE INDEX idx_meeting_transcripts_meeting_date ON meeting_transcripts(meeting_date);
```

#### generated_agendas

```sql
CREATE TABLE generated_agendas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recurring_meeting_id UUID NOT NULL REFERENCES recurring_meetings(id) ON DELETE CASCADE,
    target_date TIMESTAMPTZ NOT NULL,
    agenda_content JSONB NOT NULL,
    sources JSONB NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'reviewed')),
    delivered_via TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- RLSポリシー（親テーブル経由でuser_id検証）
ALTER TABLE generated_agendas ENABLE ROW LEVEL SECURITY;

CREATE POLICY generated_agendas_user_policy ON generated_agendas
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM recurring_meetings rm
            WHERE rm.id = generated_agendas.recurring_meeting_id
            AND rm.user_id = auth.uid()
        )
    );
```

### APIエンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/v1/google/auth` | OAuth認証URL取得 |
| GET | `/api/v1/google/callback` | OAuthコールバック |
| GET | `/api/v1/google/integrations` | Google連携一覧取得 |
| DELETE | `/api/v1/google/integrations/{id}` | Google連携削除 |
| GET | `/api/v1/google/auth/additional-scopes` | 追加スコープ認証URL取得 |
| GET | `/api/v1/google/calendar/recurring` | 定例MTG一覧取得 |
| POST | `/api/v1/google/calendar/recurring/{id}/sync` | 定例MTG同期 |
| GET | `/api/v1/google/transcripts` | トランスクリプト一覧取得 |
| POST | `/api/v1/google/transcripts/sync` | トランスクリプト同期 |
| POST | `/api/v1/google/transcripts/{id}/link` | 手動紐付け |
| **GET** | **`/api/v1/agents/{agent_id}/recurring-meetings`** | **エージェントに紐付けられた定例MTG一覧取得（ADR-0005）** |
| **POST** | **`/api/v1/agents/{agent_id}/recurring-meetings`** | **定例MTGをエージェントに紐付け（ADR-0005）** |
| **DELETE** | **`/api/v1/agents/{agent_id}/recurring-meetings/{meeting_id}`** | **定例MTGとエージェントの紐付け解除（ADR-0005）** |

#### エージェント定例紐付けAPI詳細（ADR-0005対応）

##### GET `/api/v1/agents/{agent_id}/recurring-meetings`

エージェントに紐付けられた定例MTG一覧を取得する。

**レスポンス**:
```json
[
  {
    "id": "uuid",
    "google_event_id": "event_id",
    "title": "週次進捗MTG",
    "rrule": "FREQ=WEEKLY;BYDAY=MO",
    "frequency": "weekly",
    "attendees": [{"email": "user@example.com", "name": "User"}],
    "next_occurrence": "2026-02-03T10:00:00Z",
    "agent_id": "agent_uuid",
    "created_at": "2026-02-01T00:00:00Z",
    "updated_at": null
  }
]
```

##### POST `/api/v1/agents/{agent_id}/recurring-meetings`

定例MTGをエージェントに紐付ける。

**リクエスト**:
```json
{
  "recurring_meeting_id": "uuid"
}
```

**レスポンス**:
```json
{
  "message": "定例MTGを紐付けました",
  "recurring_meeting": { ... }
}
```

**エラーケース**:
- 404: 定例MTGが見つからない
- 409: 既に他のエージェントに紐付け済み

##### DELETE `/api/v1/agents/{agent_id}/recurring-meetings/{meeting_id}`

定例MTGとエージェントの紐付けを解除する。

**レスポンス**:
```json
{
  "message": "紐付けを解除しました"
}
```

**エラーケース**:
- 404: 定例MTGが見つからない、または紐付けが存在しない

### 紐付けアルゴリズム

```python
def calculate_match_confidence(
    doc_name: str,
    doc_created: datetime,
    event_summary: str,
    event_datetime: datetime,
    event_attendees: list[str],
    transcript_speakers: list[str],
) -> float:
    """
    紐付け信頼度を計算する（0.0-1.0）

    スコア計算:
    - 会議名の類似度: 0.4 (Levenshtein距離)
    - 日時の近さ: 0.3 (±24時間以内で線形減衰)
    - 参加者の一致率: 0.3 (Jaccard係数)
    """
    score = 0.0

    # 会議名の類似度（0.4）
    name_similarity = calculate_string_similarity(doc_name, event_summary)
    score += name_similarity * 0.4

    # 日時の近さ（0.3）
    time_diff_hours = abs((doc_created - event_datetime).total_seconds() / 3600)
    if time_diff_hours <= 24:
        time_score = 1.0 - (time_diff_hours / 24)
        score += time_score * 0.3

    # 参加者の一致率（0.3）
    attendee_names = [extract_name(email) for email in event_attendees]
    attendee_match = calculate_jaccard(set(attendee_names), set(transcript_speakers))
    score += attendee_match * 0.3

    return score
```

### トランスクリプトパーサー

```python
import re

TRANSCRIPT_PATTERN = re.compile(
    r'^(?P<speaker>.+?)\s*\((?P<timestamp>\d{1,2}:\d{2})\)\s*$',
    re.MULTILINE
)

def parse_transcript(raw_text: str) -> list[TranscriptEntry]:
    """
    Google Meetトランスクリプトをパースする

    入力形式:
    ```
    宮木翔太 (10:02)
    じゃあ先週のタスクの進捗から確認しましょうか。

    金澤 (10:02)
    はい、RAGのチューニングは完了しました。
    ```
    """
    entries = []
    current_speaker = None
    current_timestamp = None
    current_text_lines = []

    for line in raw_text.split('\n'):
        match = TRANSCRIPT_PATTERN.match(line)
        if match:
            # 前の発話を保存
            if current_speaker:
                entries.append(TranscriptEntry(
                    speaker=current_speaker,
                    timestamp=current_timestamp,
                    text='\n'.join(current_text_lines).strip()
                ))
            # 新しい発話を開始
            current_speaker = match.group('speaker')
            current_timestamp = match.group('timestamp')
            current_text_lines = []
        elif line.strip():
            current_text_lines.append(line)

    # 最後の発話を保存
    if current_speaker:
        entries.append(TranscriptEntry(
            speaker=current_speaker,
            timestamp=current_timestamp,
            text='\n'.join(current_text_lines).strip()
        ))

    return entries
```

### エラーハンドリング

| エラー種別 | 発生箇所 | 対処 |
|-----------|---------|------|
| Invalid state | OAuthコールバック | 400 Bad Request、再認証を促す |
| Token expired | API呼び出し | 自動リフレッシュ、失敗時は再認証 |
| Rate limit | Google API | Exponential Backoff、最大5回リトライ |
| Insufficient scope | API呼び出し | Incremental Authorization画面を表示 |
| Meet Recordings not found | トランスクリプト取得 | 空リストを返却、ユーザーにガイダンス表示 |
| Parse error | トランスクリプト解析 | raw_textのみ保存、structured_dataはnull |

## 実装計画

### 実装アプローチ

**選択したアプローチ**: 垂直スライス
**選択理由**:
- OAuth認証が他の機能の前提条件
- 各機能が独立して価値を提供
- 段階的にリリース可能

### 技術的依存関係と実装順序

#### Phase 1-1: Google OAuth認証

1. **DBマイグレーション（google_integrations）**
   - 前提条件: なし
2. **ドメインエンティティ（GoogleIntegration）**
   - 前提条件: DBスキーマ確定
3. **リポジトリ（GoogleIntegrationRepository）**
   - 前提条件: エンティティ完成
4. **暗号化モジュール拡張**
   - 前提条件: なし
5. **Google OAuthクライアント**
   - 前提条件: 暗号化モジュール
6. **ユースケース（GoogleAuthUseCases）**
   - 前提条件: リポジトリ、OAuthクライアント
7. **APIエンドポイント**
   - 前提条件: ユースケース
8. **フロントエンド（GoogleIntegrationPage）**
   - 前提条件: APIエンドポイント

#### Phase 1-2: Calendar API - 定例MTG同期・紐付け（ADR-0005: 複数定例対応）

1. **DBマイグレーション（recurring_meetings）**
2. **ドメインエンティティ（RecurringMeeting）**
   - `link_to_agent()` / `unlink_from_agent()` メソッド追加
3. **リポジトリ（RecurringMeetingRepository）**
   - `get_list_by_agent_id()`: 複数定例取得（戻り値 `list[RecurringMeeting]`）
   - `get_unlinked_by_user_id()`: 未紐付け定例一覧取得
   - `link_to_agent()` / `unlink_from_agent()`: 紐付け操作
4. **Google Calendarクライアント**
5. **RRULEパーサー（dateutil.rrule活用）**
6. **ユースケース（CalendarUseCases）**
   - OAuth完了時の自動同期処理
   - 同期済み定例一覧取得
   - **エージェントへの複数定例紐付け**
7. **APIエンドポイント**
   - GET /api/v1/google/calendar/recurring（同期済み定例一覧）
   - **GET /api/v1/agents/{id}/recurring-meetings（紐付け済み定例一覧）**
   - **POST /api/v1/agents/{id}/recurring-meetings（紐付け追加）**
   - **DELETE /api/v1/agents/{id}/recurring-meetings/{meeting_id}（紐付け解除）**
8. **フロントエンド（RecurringMeetingSelector / AgentDetailPage）**
   - **AgentDetailPage**: 紐付け済み定例一覧表示 + 追加ボタン + 解除ボタン
   - **RecurringMeetingSelector**: 複数選択対応（未紐付け定例のみ表示）
   - モーダルで未紐付け定例一覧を表示（検索機能付き）
   - 定例選択でエージェントに追加紐付け

#### Phase 1-3: トランスクリプト取得

1. **DBマイグレーション（meeting_transcripts, generated_agendas）**
2. **ドメインエンティティ（MeetingTranscript, GeneratedAgenda）**
3. **リポジトリ**
4. **Google Drive/Docsクライアント**
5. **トランスクリプトパーサー**
6. **紐付けアルゴリズム**
7. **ユースケース（TranscriptUseCases）**
8. **APIエンドポイント**
9. **フロントエンド（TranscriptViewer）**

### 統合ポイント

**統合ポイント1: OAuth → Calendar**
- コンポーネント: GoogleIntegration → CalendarUseCases
- 確認方法: OAuth完了後にCalendar API呼び出しが成功
- 確認レベル: L1

**統合ポイント2: Calendar → Transcript**
- コンポーネント: RecurringMeeting → TranscriptUseCases
- 確認方法: 定例MTG選択後にトランスクリプト一覧が表示
- 確認レベル: L1

**統合ポイント3: Transcript → 紐付け**
- コンポーネント: MeetingTranscript → 紐付けアルゴリズム
- 確認方法: 信頼度スコアが正しく計算される
- 確認レベル: L1

**統合ポイント4: 複数定例紐付け（ADR-0005）**
- コンポーネント: AgentDetailPage → RecurringMeetingRepository → CalendarUseCases
- 確認方法:
  1. エージェント詳細画面で複数の定例を追加紐付けできる
  2. 紐付け済み定例一覧が正しく表示される
  3. 紐付け解除後、定例選択モーダルで再び選択可能になる
- 確認レベル: L1

**統合ポイント5: 複数定例からの統合アジェンダ生成（Phase 2）**
- コンポーネント: AgendaUseCases → RecurringMeetingRepository → TranscriptUseCases
- 確認方法:
  1. 複数の紐付け定例から全てのトランスクリプトが収集される
  2. 生成されたアジェンダのsourcesフィールドに全定例の情報が含まれる
- 確認レベル: L1

## テスト戦略

### 単体テスト

- **GoogleIntegration**: スコープ管理、トークン更新
- **RecurringMeeting**: 次回日時計算（dateutil.rrule）、`link_to_agent()` / `unlink_from_agent()` メソッド
- **MeetingTranscript**: トランスクリプトパース
- **紐付けアルゴリズム**: 各スコア計算、閾値判定

### 統合テスト

- **OAuth フロー**: state生成→検証→トークン交換
- **Calendar API**: モックレスポンスでのRRULE解析
- **Drive/Docs API**: モックレスポンスでのトランスクリプト取得
- **複数定例紐付けAPI（ADR-0005）**:
  - GET `/agents/{id}/recurring-meetings`: 紐付け済み定例一覧取得
  - POST `/agents/{id}/recurring-meetings`: 紐付け追加
  - DELETE `/agents/{id}/recurring-meetings/{meeting_id}`: 紐付け解除
  - 同一定例の重複紐付け防止
  - 他ユーザーの定例にはアクセス不可（RLS検証）

### E2Eテスト

- Google連携の開始から完了まで
- 定例MTG一覧表示
- トランスクリプト取得と紐付け
- **複数定例紐付けフロー（ADR-0005）**:
  - エージェント詳細から複数の定例を追加
  - 紐付け済み定例一覧の表示
  - 紐付け解除後の再選択

## セキュリティ考慮事項

- **RLSポリシー**: 全テーブルでuser_id単位のアクセス制御
- **トークン暗号化**: Fernet（AES-128-CBC with HMAC）
- **state検証**: CSRF対策として必須
- **スコープ最小化**: Incremental Authorizationで必要時のみ追加
- **Google API Services User Data Policy**: Limited Use要件の遵守

## 代替案

### 代替案1: Supabase Auth + Google Provider

- **概要**: Supabaseの組み込みGoogle認証を使用
- **メリット**: 実装コスト低、設定のみで完了
- **デメリット**: Incremental Authorization非対応、スコープ固定
- **不採用理由**: Calendar/Drive APIに必要なスコープを柔軟に制御できない

### 代替案2: Meet REST API v2優先

- **概要**: Drive/Docs APIではなくMeet REST APIを先に実装
- **メリット**: 構造化されたトランスクリプトが取得可能
- **デメリット**: Meet REST APIはまだベータ版、安定性に懸念
- **不採用理由**: Phase 2で対応し、Phase 1はDrive/Docsで安定稼働を優先

## リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|-------|-------|---------|-----|
| Google OAuth公開審査の遅延 | 高 | 中 | MVPでは内部アプリ（100ユーザーまで）で開発 |
| トランスクリプト形式の変更 | 中 | 低 | パーサーを疎結合に設計、フォールバック処理 |
| レートリミット超過 | 中 | 中 | Exponential Backoff、ユーザー単位のスロットリング |
| 紐付け精度の低さ | 中 | 中 | 手動確認フロー、フィードバックによる閾値調整 |
| Refresh Token失効 | 低 | 低 | 再認証フローの整備、ユーザー通知 |

## 参考資料

- [Google Calendar API - Recurring Events](https://developers.google.com/calendar/api/guides/recurringevents)
- [Google Drive API - Search for files](https://developers.google.com/drive/api/guides/search-files)
- [Google Docs API - Get document content](https://developers.google.com/docs/api/how-tos/documents)
- [Google Meet REST API - Transcripts](https://developers.google.com/meet/api/guides/artifacts)
- [ADR-0001: クリーンアーキテクチャ + DDD 採用](../adr/ADR-0001-clean-architecture-adoption.md)
- [ADR-0003: Google Workspace連携の認証・トークン管理方式](../adr/ADR-0003-google-workspace-auth.md)
- [ADR-0005: 1エージェント複数定例会議の紐付け対応](../adr/ADR-0005-agent-multiple-recurring-meetings.md)

## 付録: 1エージェント複数定例紐付け詳細設計（ADR-0005）

### フロントエンドコンポーネント詳細設計

#### AgentDetailPage - 紐付け済み定例一覧UI

```tsx
// frontend/src/features/agents/AgentDetailPage.tsx

interface LinkedRecurringMeetingsProps {
  agentId: string
}

function LinkedRecurringMeetings({ agentId }: LinkedRecurringMeetingsProps) {
  const { data: meetings, isLoading } = useAgentRecurringMeetings(agentId)
  const unlinkMutation = useUnlinkRecurringMeeting()
  const [showSelector, setShowSelector] = useState(false)

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">紐付け済み定例MTG</h3>
        <button
          onClick={() => setShowSelector(true)}
          className="btn btn-primary btn-sm"
        >
          定例を追加
        </button>
      </div>

      {meetings?.length === 0 ? (
        <p className="text-gray-500">紐付けられた定例MTGはありません</p>
      ) : (
        <ul className="divide-y">
          {meetings?.map((meeting) => (
            <li key={meeting.id} className="py-3 flex justify-between items-center">
              <div>
                <p className="font-medium">{meeting.title}</p>
                <p className="text-sm text-gray-500">
                  {meeting.frequency} / 次回: {formatDate(meeting.next_occurrence)}
                </p>
              </div>
              <button
                onClick={() => unlinkMutation.mutate({ agentId, meetingId: meeting.id })}
                className="btn btn-ghost btn-sm text-red-500"
              >
                解除
              </button>
            </li>
          ))}
        </ul>
      )}

      {showSelector && (
        <RecurringMeetingSelector
          agentId={agentId}
          onClose={() => setShowSelector(false)}
          excludeMeetingIds={meetings?.map((m) => m.id) ?? []}
        />
      )}
    </div>
  )
}
```

#### RecurringMeetingSelector - 複数選択対応モーダル

```tsx
// frontend/src/features/agents/RecurringMeetingSelector.tsx

interface RecurringMeetingSelectorProps {
  agentId: string
  onClose: () => void
  excludeMeetingIds: string[]  // 既に紐付け済みの定例IDリスト
}

function RecurringMeetingSelector({
  agentId,
  onClose,
  excludeMeetingIds,
}: RecurringMeetingSelectorProps) {
  const { data: allMeetings } = useRecurringMeetings()
  const linkMutation = useLinkRecurringMeeting()
  const [searchQuery, setSearchQuery] = useState('')

  // 未紐付けの定例のみ表示（既に紐付け済み + 他エージェントに紐付け済みを除外）
  const availableMeetings = allMeetings?.filter(
    (m) => !excludeMeetingIds.includes(m.id) && m.agent_id === null
  )

  // 検索フィルタ
  const filteredMeetings = availableMeetings?.filter((m) =>
    m.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleSelect = (meetingId: string) => {
    linkMutation.mutate(
      { agentId, recurringMeetingId: meetingId },
      { onSuccess: () => onClose() }
    )
  }

  return (
    <Modal onClose={onClose} title="定例MTGを追加">
      <input
        type="text"
        placeholder="定例名で検索..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="input input-bordered w-full mb-4"
      />

      {filteredMeetings?.length === 0 ? (
        <p className="text-gray-500">紐付け可能な定例MTGがありません</p>
      ) : (
        <ul className="divide-y max-h-96 overflow-y-auto">
          {filteredMeetings?.map((meeting) => (
            <li
              key={meeting.id}
              onClick={() => handleSelect(meeting.id)}
              className="py-3 px-2 cursor-pointer hover:bg-gray-100"
            >
              <p className="font-medium">{meeting.title}</p>
              <p className="text-sm text-gray-500">
                {meeting.frequency} / 次回: {formatDate(meeting.next_occurrence)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  )
}
```

#### カスタムフック

```typescript
// frontend/src/features/google/hooks.ts

/** エージェントに紐付けられた定例MTG一覧を取得 */
export function useAgentRecurringMeetings(agentId: string) {
  return useQuery({
    queryKey: ['agents', agentId, 'recurring-meetings'],
    queryFn: () => getAgentRecurringMeetings(agentId),
  })
}

/** 定例MTGをエージェントに紐付け */
export function useLinkRecurringMeeting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      agentId,
      recurringMeetingId,
    }: {
      agentId: string
      recurringMeetingId: string
    }) => linkRecurringMeeting(agentId, recurringMeetingId),
    onSuccess: (_, { agentId }) => {
      queryClient.invalidateQueries({ queryKey: ['agents', agentId, 'recurring-meetings'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-meetings'] })
    },
  })
}

/** 定例MTGとエージェントの紐付けを解除 */
export function useUnlinkRecurringMeeting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ agentId, meetingId }: { agentId: string; meetingId: string }) =>
      unlinkRecurringMeeting(agentId, meetingId),
    onSuccess: (_, { agentId }) => {
      queryClient.invalidateQueries({ queryKey: ['agents', agentId, 'recurring-meetings'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-meetings'] })
    },
  })
}
```

#### API関数

```typescript
// frontend/src/features/google/api.ts

/** エージェントに紐付けられた定例MTG一覧を取得 */
export async function getAgentRecurringMeetings(
  agentId: string
): Promise<AgentRecurringMeetingsResponse> {
  const response = await apiClient.get(`/api/v1/agents/${agentId}/recurring-meetings`)
  return response.data
}

/** 定例MTGをエージェントに紐付け */
export async function linkRecurringMeeting(
  agentId: string,
  recurringMeetingId: string
): Promise<LinkRecurringMeetingResponse> {
  const response = await apiClient.post(`/api/v1/agents/${agentId}/recurring-meetings`, {
    recurring_meeting_id: recurringMeetingId,
  })
  return response.data
}

/** 定例MTGとエージェントの紐付けを解除 */
export async function unlinkRecurringMeeting(
  agentId: string,
  meetingId: string
): Promise<UnlinkRecurringMeetingResponse> {
  const response = await apiClient.delete(
    `/api/v1/agents/${agentId}/recurring-meetings/${meetingId}`
  )
  return response.data
}
```

### 複数定例からの統合アジェンダ生成ロジック（Phase 2）

#### 情報収集と統合フロー

```mermaid
sequenceDiagram
    participant UC as AgendaUseCases
    participant RM_REPO as RecurringMeetingRepo
    participant MT_REPO as MeetingTranscriptRepo
    participant SLACK as SlackClient
    participant LLM as Claude Haiku 4.5

    UC->>RM_REPO: get_list_by_agent_id(agent_id)
    RM_REPO-->>UC: list[RecurringMeeting]

    loop 各定例MTG
        UC->>MT_REPO: get_latest_by_recurring_meeting_id(meeting_id)
        MT_REPO-->>UC: MeetingTranscript | None
        UC->>SLACK: get_messages(channel_id, since=prev_meeting_date)
        SLACK-->>UC: list[SlackMessage]
    end

    UC->>UC: 時系列ソート・文脈統合
    UC->>LLM: アジェンダ生成プロンプト
    LLM-->>UC: 統合アジェンダ
```

#### 情報統合ロジック（マージ戦略）

```python
# backend/src/application/use_cases/agenda_use_cases.py

from dataclasses import dataclass

@dataclass
class AgendaSource:
    """アジェンダ生成に使用した情報源"""
    recurring_meeting_id: UUID
    meeting_title: str
    source_type: str  # "transcript" | "slack"
    date: datetime
    summary: str

class AgendaUseCases:
    async def generate_agenda(self, agent_id: UUID, user_id: UUID) -> GeneratedAgenda:
        """複数定例から統合アジェンダを生成"""

        # 1. エージェントに紐付けられた全定例を取得
        recurring_meetings = await self.recurring_meeting_repo.get_list_by_agent_id(
            agent_id, user_id
        )

        if not recurring_meetings:
            raise NoLinkedMeetingsError("紐付けられた定例MTGがありません")

        # 2. 各定例から情報を収集
        all_sources: list[AgendaSource] = []

        for meeting in recurring_meetings:
            # 最新のトランスクリプトを取得
            transcript = await self.transcript_repo.get_latest_by_recurring_meeting_id(
                meeting.id
            )
            if transcript:
                all_sources.append(AgendaSource(
                    recurring_meeting_id=meeting.id,
                    meeting_title=meeting.title,
                    source_type="transcript",
                    date=transcript.meeting_date,
                    summary=self._summarize_transcript(transcript),
                ))

            # Slack履歴を取得（紐付けられたチャンネルがある場合）
            if meeting.slack_channel_id:
                since_date = transcript.meeting_date if transcript else meeting.created_at
                messages = await self.slack_client.get_messages(
                    channel_id=meeting.slack_channel_id,
                    since=since_date,
                )
                if messages:
                    all_sources.append(AgendaSource(
                        recurring_meeting_id=meeting.id,
                        meeting_title=meeting.title,
                        source_type="slack",
                        date=since_date,
                        summary=self._summarize_slack_messages(messages),
                    ))

        # 3. 時系列ソート
        all_sources.sort(key=lambda s: s.date)

        # 4. プロンプト構築と生成
        prompt = self._build_multi_source_prompt(recurring_meetings, all_sources)
        agenda_content = await self.llm_client.generate(prompt)

        # 5. 結果を保存
        return await self.agenda_repo.save(GeneratedAgenda(
            id=uuid4(),
            recurring_meeting_id=recurring_meetings[0].id,  # 代表として最初の定例を使用
            target_date=self._calculate_next_meeting_date(recurring_meetings),
            agenda_content=agenda_content,
            sources=[asdict(s) for s in all_sources],
            status="draft",
        ))

    def _build_multi_source_prompt(
        self,
        meetings: list[RecurringMeeting],
        sources: list[AgendaSource],
    ) -> str:
        """複数定例からの情報を統合したプロンプトを構築"""

        meeting_names = ", ".join(m.title for m in meetings)

        context_sections = []
        for source in sources:
            context_sections.append(f"""
【{source.meeting_title}】({source.source_type}, {source.date.strftime('%Y-%m-%d')})
{source.summary}
""")

        return f"""
以下は、{meeting_names} の複数の定例MTGに関連する情報です。
これらの情報を統合して、次回MTGのアジェンダを提案してください。

## 情報源
{''.join(context_sections)}

## アジェンダ生成の指針
1. 複数の定例MTGに共通するテーマがあれば、横断的に整理してください
2. 各定例MTGの進捗状況を踏まえ、次回議論すべきポイントを抽出してください
3. 未解決の議題や継続中のタスクがあれば、フォローアップ項目として記載してください
4. 新しい議題があれば、どの定例MTGの文脈から発生したか明記してください
"""
```

### 統合境界の約束

```yaml
境界名: AgentRecurringMeetingsAPI
  入力:
    GET: agent_id (path), user_id (認証)
    POST: agent_id (path), recurring_meeting_id (body), user_id (認証)
    DELETE: agent_id (path), meeting_id (path), user_id (認証)
  出力:
    GET: list[RecurringMeeting] (同期)
    POST: LinkRecurringMeetingResponse (同期)
    DELETE: UnlinkRecurringMeetingResponse (同期)
  エラー時:
    404: 定例MTGが見つからない
    409: 既に他のエージェントに紐付け済み（POST時）
    403: 他ユーザーの定例にアクセス試行（RLSで拒否）

境界名: AgendaGenerationWithMultipleMeetings
  入力: agent_id, user_id
  出力: GeneratedAgenda (非同期、処理時間に応じて)
  エラー時:
    400: 紐付けられた定例MTGがない
    500: LLM呼び出し失敗（リトライ後も失敗した場合）
```

## 更新履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|-----|-----------|---------|-------|
| 2026-02-01 | 1.0 | 初版作成 | AI |
| 2026-02-01 | 1.1 | レビュー指摘対応: TypeScript型定義追加、generated_agendas作成意図明記 | AI |
| 2026-02-02 | 1.2 | 仕様変更: 定例MTG検出→エージェント詳細からの紐付け方式に変更。Google連携時に定例を自動同期し、エージェント詳細画面でモーダルから紐付ける形式に | AI |
| 2026-02-02 | 1.3 | ADR-0005対応: 1エージェント複数定例紐付け機能を追加。API変更（複数形エンドポイント）、リポジトリ変更（1対多対応）、フロントエンドUI変更（一覧表示+追加/解除ボタン）、統合アジェンダ生成ロジックを追加 | AI |
