# RLSポリシーパターン リファレンス

## 概要

Shitaku.ai の RLS は2つのパターンだけで書く。どちらを使うかは、行の持ち主で決まる。

| 持ち主 | パターン | テーブル |
|-------|---------|---------|
| 定例シリーズ | シリーズ参加者 | `series`, `series_attendees`, `occurrences`, `agenda_topics`, `memory_items`, `knowledge`, `agendas`, `dictionary_entries` |
| ユーザー | 本人のみ | `google_integrations`, `slack_integrations`, `oauth_states` |

背景は [ADR-0008](../adr/ADR-0008-team-owned-meeting-series.md) と [設計書](./team-owned-meeting-series.md)。

## パターン1: シリーズ参加者

参加者の定義は `public.my_series_roles()` だけ。呼び出したユーザーのロールを `(series_id, role)` で返す。`role` は `creator` か `member`。

- `creator`: `series.created_by = auth.uid()`
- `member`: `series_attendees.email` が、呼び出し元の Google 確認済み `auth.identities` のメールと一致する

ポリシーは「参加者が読む」「作成者が書く」の2本を基本にする。

```sql
create policy {table}_read_members on public.{table} for select to authenticated
  using (series_id in (select r.series_id from public.my_series_roles() r));

create policy {table}_write_creator on public.{table} for all to authenticated
  using      (series_id in (select r.series_id from public.my_series_roles() r where r.role = 'creator'))
  with check (series_id in (select r.series_id from public.my_series_roles() r where r.role = 'creator'));
```

`my_series_roles()` は引数のない副問い合わせで、文ごとに1回だけ評価される。SECURITY DEFINER なので、ポリシーから呼んでも再帰しない。

### 参加者が書ける例外

| 書き込み | 方法 |
|---------|------|
| 議題の投稿 | `agenda_topics` の INSERT ポリシー。`submitted_by = auth.uid()` かつ参加者で、未来のキャンセルされていない回に限る |
| 自分の議題の取り下げ | `agenda_topics` の DELETE ポリシー。投稿者本人または作成者 |
| アクションアイテムの解決状態 | `set_memory_item_resolution(item_id, resolution)`（SECURITY DEFINER）。参加者はアクションアイテムだけ、作成者は全種類 |

### カレンダー由来のデータ

`series` の作成、カレンダー由来の列（`ical_uid`, `creator_event_id`, `title`, `rrule`, `calendar_synced_at`, `calendar_sync_error`, `google_integration_id`）、`series_attendees`、`occurrences` には、`authenticated` への書き込み GRANT を与えない。書くのは `SeriesCalendarMirror`（service role）だけ。作成者の UPDATE は列単位の GRANT で設定列に限る。

### 資格情報の参照

シリーズから作成者の連携を参照するときは、複合外部キーで作成者本人の行に限る。

```sql
constraint series_google_owned_by_creator foreign key (google_integration_id, created_by)
  references public.google_integrations (id, user_id) on delete set null (google_integration_id)
```

外部キーのチェックには RLS が効かないため、この制約がないと他人の連携 ID を結び付けられる。

## パターン2: 本人のみ

```sql
create policy "Users can manage own {table}" on public.{table}
  for all using (auth.uid() = user_id);
```

参加者は作成者の資格情報を読めない。作成者の資格情報は、作成者本人の操作か `SeriesCalendarMirror` だけが使う。

## SECURITY DEFINER 関数の決まり

- `set search_path = ''` にし、参照はすべてスキーマ名付きで書く。
- `public` と `anon` から EXECUTE を取り消し、必要なロールにだけ与える。
- 呼び出し元のロールを返す関数は、引数を取らない。他人の情報を引けるようにしない。
- service role 専用の関数（カレンダーのスナップショット反映など）は `authenticated` から EXECUTE を取り消す。

## 検証

`make test-rls` が、ローカルの Supabase で実ユーザーと実 JWT を使って全テーブルと全 RPC を確かめる（`backend/tests/rls/`）。新しいテーブルを足したら、作成者・参加者・部外者の3人で SELECT / INSERT / UPDATE / DELETE を確かめるテストを足す。
