# RLSポリシーパターン リファレンス

## 概要

Shitaku.ai MVPにおけるRow Level Security（RLS）ポリシーの設計パターンを定義する。
全テーブルは`auth.users(id)`をUUIDで参照し、`auth.uid()`関数でユーザーを識別する。

## 基本原則

1. **全テーブルでRLSを有効化**: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
2. **ユーザー分離**: 各ユーザーは自分のデータのみアクセス可能
3. **UUID型統一**: `user_id UUID NOT NULL REFERENCES auth.users(id)`
4. **CASCADE削除**: ユーザー削除時に関連データも削除

## RLSポリシーパターン

### パターン1: 直接所有（Direct Ownership）

テーブルが直接`user_id`カラムを持つ場合に使用。

```sql
-- テーブル定義
CREATE TABLE public.{table_name} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- ... other columns
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS有効化
ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;

-- ポリシー定義（全操作を1つのポリシーで制御）
CREATE POLICY "Users can manage own {table_name}" ON public.{table_name}
    FOR ALL USING (auth.uid() = user_id);
```

**適用テーブル:**
| テーブル | 説明 |
|---------|------|
| `agents` | MTGエージェント |
| `dictionary_entries` | 辞書エントリ |
| `meeting_notes` | 議事録 |
| `slack_integrations` | Slack連携 |
| `agendas` | アジェンダ |

### パターン2: 親テーブル経由（Parent Lookup）

テーブルが親テーブルを介してユーザーに紐づく場合に使用。

```sql
-- テーブル定義
CREATE TABLE public.{child_table} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    {parent_id} UUID NOT NULL REFERENCES public.{parent_table}(id) ON DELETE CASCADE,
    -- ... other columns
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS有効化
ALTER TABLE public.{child_table} ENABLE ROW LEVEL SECURITY;

-- ポリシー定義（親テーブル経由でユーザーを確認）
CREATE POLICY "Users can manage own {child_table}" ON public.{child_table}
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.{parent_table}
            WHERE id = {parent_id} AND user_id = auth.uid()
        )
    );
```

**適用テーブル:**
| テーブル | 親テーブル | 参照カラム |
|---------|-----------|-----------|
| `dictionary_variants` | `dictionary_entries` | `entry_id` |
| `slack_messages` | `slack_integrations` | `integration_id` |

## テーブル別RLSポリシー一覧

### agents
```sql
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own agents" ON public.agents
    FOR ALL USING (auth.uid() = user_id);
```

### dictionary_entries
```sql
ALTER TABLE public.dictionary_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own dictionary entries" ON public.dictionary_entries
    FOR ALL USING (auth.uid() = user_id);
```

### dictionary_variants
```sql
ALTER TABLE public.dictionary_variants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own variants" ON public.dictionary_variants
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.dictionary_entries
            WHERE id = entry_id AND user_id = auth.uid()
        )
    );
```

### meeting_notes
```sql
ALTER TABLE public.meeting_notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own meeting notes" ON public.meeting_notes
    FOR ALL USING (auth.uid() = user_id);
```

### slack_integrations
```sql
ALTER TABLE public.slack_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own slack integrations" ON public.slack_integrations
    FOR ALL USING (auth.uid() = user_id);
```

### slack_messages
```sql
ALTER TABLE public.slack_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own slack messages" ON public.slack_messages
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.slack_integrations
            WHERE id = integration_id AND user_id = auth.uid()
        )
    );
```

### agendas
```sql
ALTER TABLE public.agendas ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own agendas" ON public.agendas
    FOR ALL USING (auth.uid() = user_id);
```

## 注意事項

### auth.uid()の動作条件
- `auth.uid()`はSupabase Auth経由のアクセスでのみ機能する
- サービスロールキー使用時はRLSをバイパス可能
- バックエンドからの直接DB接続時は、適切なJWT設定が必要

### パフォーマンス考慮
- パターン2（親テーブル経由）は`EXISTS`サブクエリを使用するため、インデックスが重要
- 親テーブルの`id`と`user_id`にインデックスを設定すること

### FOR ALL vs 個別操作
- MVPでは`FOR ALL`で全操作を統一制御
- 将来的に読み取り専用共有などが必要な場合は、`FOR SELECT`/`FOR INSERT`等に分離

## マイグレーション作成時のチェックリスト

新規テーブル作成時は以下を確認:

- [ ] `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`（パターン1の場合）
- [ ] 親テーブルへの外部キー`ON DELETE CASCADE`（パターン2の場合）
- [ ] `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- [ ] `CREATE POLICY`でRLSポリシー定義
- [ ] 必要なインデックス作成（`user_id`、`{parent_id}`）

## 参考資料

- [Supabase RLS Best Practices](https://supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices-Z5Jjwv)
- [Design Doc: MVP Core Features](./mvp-core-features.md)
