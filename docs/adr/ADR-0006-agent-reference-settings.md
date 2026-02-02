# ADR-0006 アジェンダ生成の参照情報設定

## ステータス

Proposed

## 経緯

現在のアジェンダ生成実装には以下の課題がある：

1. **トランスクリプト参照なし**: `GenerateAgendaUseCase`は`latest_note`（議事録）のみを参照し、Google Meet由来のトランスクリプト（`meeting_transcripts`テーブル）を全く参照していない
2. **Slackメッセージ取得範囲固定**: `get_messages`は`oldest`パラメータのみを受け取り、現在時刻までの全メッセージを取得。取得範囲をユーザーが制御できない
3. **複数定例会議の参照未対応**: ADR-0005で1対多対応が決定されたが、アジェンダ生成時に全ての紐付け定例を参照する仕組みがない

### 現在のデータフロー

```
Agent → latest_note（1件）→ アジェンダ生成
      → Slack messages（oldest〜now、全件）
      → dictionary（全件）
```

### 期待されるデータフロー

```
Agent → transcripts（N件、設定可能）→ アジェンダ生成
      → Slack messages（設定日数分）
      → dictionary（全件）
      → 複数recurring_meetings経由でデータ収集
```

## 決定事項

エージェントに参照情報の設定を追加する。設定の保存方法として**Agentテーブルへの直接カラム追加（Option A）**を採用する。

### 決定の詳細

| 項目 | 内容 |
|-----|-----|
| **決定** | Agentテーブルに`transcript_count`（integer, default 3）と`slack_message_days`（integer, default 7）を追加 |
| **なぜ今か** | アジェンダ生成がコア機能であり、トランスクリプト参照なしでは価値が半減する。ADR-0005の複数定例対応と合わせて実装が必要 |
| **なぜこれか** | 設定項目が2つのみで拡張予定もなく、JOINなしでの取得、型安全性、RLS対応の全てが既存agentsテーブルの設計で担保される |
| **既知の不確実性** | 将来的に設定項目が大幅に増加した場合、カラム追加のマイグレーションコストが増大する可能性 |
| **撤回基準** | 設定項目が10個以上に増加し、agentsテーブルの責務が肥大化した場合 |

## 根拠

### 検討した選択肢

#### 選択肢1: Agentテーブルに直接カラム追加（採用）

```sql
ALTER TABLE public.agents
ADD COLUMN transcript_count INTEGER NOT NULL DEFAULT 3,
ADD COLUMN slack_message_days INTEGER NOT NULL DEFAULT 7;
```

- メリット:
  - **シンプルな実装**: JOINなしでエージェントと設定を同時取得
  - **型安全性**: PostgreSQLの型チェックと制約をそのまま活用
  - **RLS不要**: 既存のagentsテーブルのRLSポリシーがそのまま適用
  - **マイグレーション1回**: 追加カラムのみで完結
  - **既存エンティティ拡張**: Agentエンティティにフィールド追加するだけ
- デメリット:
  - **カラム増加**: 設定項目が増えるたびにスキーマ変更が必要
  - **柔軟性の欠如**: 動的な設定追加には対応できない
  - **責務の肥大化リスク**: 設定が増えすぎるとAgentの責務が曖昧になる

#### 選択肢2: Agent設定用の別テーブル作成

```sql
CREATE TABLE public.agent_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    transcript_count INTEGER NOT NULL DEFAULT 3,
    slack_message_days INTEGER NOT NULL DEFAULT 7,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(agent_id)
);
```

- メリット:
  - **責務分離**: エージェント本体と設定を明確に分離
  - **拡張性**: 設定専用テーブルとして将来の設定追加に対応しやすい
  - **監査性**: 設定変更の履歴を別途追跡可能
- デメリット:
  - **JOIN必須**: エージェント取得時に常にJOINが必要
  - **RLS追加設定**: 新テーブルに対して別途RLSポリシー設定が必要
  - **整合性管理**: エージェント作成時に設定レコードも作成する必要あり（2テーブル操作）
  - **過剰設計**: 現時点で2項目のみの設定に対してテーブル分離は冗長

#### 選択肢3: AgentテーブルにJSONBカラム追加

```sql
ALTER TABLE public.agents
ADD COLUMN settings JSONB NOT NULL DEFAULT '{"transcript_count": 3, "slack_message_days": 7}';
```

- メリット:
  - **柔軟性**: スキーマ変更なしで設定項目を追加可能
  - **単一カラム**: 設定がいくつ増えても1カラムで管理
  - **PostgreSQL最適化**: GINインデックスによる高速検索が可能
- デメリット:
  - **型安全性の欠如**: JSONBの内容は実行時まで検証されない
  - **統計情報なし**: PostgreSQLはJSONBキーの統計を保持しないため、クエリプランナーの最適化が効かない
  - **アプリケーション検証必須**: 必須キーの存在確認、型チェックをアプリケーション層で実装する必要
  - **マイグレーション複雑化**: デフォルト値変更時に既存データの更新ロジックが複雑になる
  - **過剰な柔軟性**: 現時点で2項目のみの固定設定に対してJSONBは過剰

### 比較マトリクス

| 評価軸 | Option A（採用） | Option B | Option C |
|--------|-----------------|----------|----------|
| 実装工数 | 低（1日） | 中（2日） | 低（1日） |
| 型安全性 | 高（DB + Python） | 高（DB + Python） | 低（Python検証のみ） |
| クエリ性能 | 高（JOINなし） | 中（JOIN必要） | 中（JSONB展開） |
| RLS対応 | 既存ポリシー適用 | 新規ポリシー必要 | 既存ポリシー適用 |
| 将来の拡張性 | 低〜中 | 高 | 高 |
| コードベース整合性 | 高（既存パターン踏襲） | 中（新パターン導入） | 低（JSONBパターン新規） |

### 選択理由

1. **YAGNI原則**: 現時点で必要な設定は2項目のみであり、将来の拡張を過度に考慮する必要がない
2. **既存パターンとの整合性**: Agentテーブルに`slack_channel_id`が直接カラムとして存在するように、関連設定を同テーブルに追加するのは自然
3. **クリーンアーキテクチャとの親和性**: ADR-0001で採用したクリーンアーキテクチャにおいて、エンティティのフィールド追加はシンプルかつ影響範囲が明確
4. **PostgreSQLベストプラクティス**: 頻繁に使用される固定属性はカラムとして定義するのが推奨される

## 影響

### ポジティブな影響

- **トランスクリプト参照の実現**: ユーザーは参照するトランスクリプト件数を制御可能に
- **Slack取得範囲の制御**: 過去7日間（デフォルト）から変更可能に
- **アジェンダ品質向上**: より多くの関連情報を参照することでアジェンダ生成の精度が向上
- **設定のUI対応**: フロントエンドで設定変更UIを容易に追加可能

### ネガティブな影響

- **マイグレーション必要**: 既存のagentsテーブルにカラム追加のマイグレーションが必要
- **エンティティ変更**: `Agent`エンティティにフィールド追加が必要
- **ユースケース変更**: `GenerateAgendaUseCase`の修正が必要

### 中立的な影響

- **デフォルト値適用**: 既存エージェントにはデフォルト値（transcript_count: 3, slack_message_days: 7）が自動適用

## 実装指針

### データモデル変更

- Agentテーブルに`transcript_count`と`slack_message_days`カラムを追加
- DEFAULT値とNOT NULL制約を設定し、既存データの整合性を保証
- CHECK制約で妥当な範囲を強制（例: transcript_count >= 0 AND transcript_count <= 10）

### エンティティ変更

- `Agent`エンティティに新フィールドを追加
- 更新メソッド`update_reference_settings`を追加

### アジェンダ生成フロー変更

- `GenerateAgendaUseCase`でトランスクリプト取得ロジックを追加
- 複数定例からのトランスクリプト収集に対応
- `slack_message_days`を使用してSlackメッセージの取得範囲を制御

### RLSポリシー

- 新規ポリシー追加不要（既存のagentsテーブルポリシーがそのまま適用）

## 関連情報

- [ADR-0001: クリーンアーキテクチャ採用](./ADR-0001-clean-architecture-adoption.md)
- [ADR-0004: RLSベースの認可アーキテクチャ](./ADR-0004-rls-based-authorization.md)
- [ADR-0005: 1エージェント複数定例会議の紐付け対応](./ADR-0005-agent-multiple-recurring-meetings.md)
- DBスキーマ: `supabase/migrations/20260201013253_create_agents_table.sql`
- 現在の実装: `backend/src/application/use_cases/agenda_use_cases.py`

## 参考資料

- [When To Avoid JSONB In A PostgreSQL Schema | Heap](https://www.heap.io/blog/when-to-avoid-jsonb-in-a-postgresql-schema) - JSONBの適用判断基準
- [PostgreSQL: Documentation: 18: 8.14. JSON Types](https://www.postgresql.org/docs/current/datatype-json.html) - PostgreSQL公式ドキュメント
- [PostgreSQL as a JSON database: Advanced patterns and best practices | AWS](https://aws.amazon.com/blogs/database/postgresql-as-a-json-database-advanced-patterns-and-best-practices/) - JSONBのベストプラクティス
