# Claude Code 開発ルール

AI実行精度最大化のための中核ルール。全ての指示はこのファイルに従う。

## 🚨 最重要原則：調査OK、実装STOP

**すべてのEdit/Write/MultiEditツール使用前にユーザー承認が必須**

理由：ユーザーの意図と異なる実装を防ぎ、正しい方向性を確保するため

## 必須実行プロセス

### 実行フロー（必須手順）
1. **TodoWriteでタスク分解** → なければ実装ステップに進めない
   理由：タスクを構造化し、進捗を追跡可能にするため
2. **rule-advisor実行** → タスクの本質を理解し適切なルールを選択
   理由：適切なルールを選択し、タスクの本質を理解するため
3. **Edit/Write/MultiEdit使用** → ユーザー承認が必須
   理由：最重要原則の実践（調査OK、実装STOP）
4. **実装実行** → 品質チェックエラーは完了条件を満たさない
   理由：高品質なコードを保証するため
5. **ファイル数カウント** → 閾値超過で自動停止
   理由：影響範囲が大きくなる前に確認を取るため

### TodoWriteとメタ認知の統合
**実行ルール**：
- `pending → in_progress`時: rule-advisorの出力が必須
- **rule-advisor実行後**: 必ずTodoWriteを以下の形式で更新
  1. metaCognitiveGuidance.firstStepをTodoの先頭タスクとして追加
  2. metaCognitiveGuidance.taskEssenceを各タスクの完了判断基準として記録
  3. warningPatternsを実行中の確認項目として記録
- TodoWriteなしでEditツール使用: ルール違反として停止
- 各タスクのステータス更新時: 実施内容の記録を必須化（空白不可）

### 実行前提条件
1. **rule-advisorエージェント実行(Taskツールで呼び出すこと)** → JSONレスポンスが存在すること
2. **TodoWriteのタスク** → in_progressステータスが存在すること
3. **ユーザー承認記録** → Edit/Write前に明示的承認があること
4. **品質チェック結果** → エラー0でなければ完了不可

### 必須の代替パターン
- **any型の代わり** → unknown型と型ガードを使用
  理由：型安全性を確保し、実行時エラーを防止するため
- **Edit使用時** → 必ずTodoWriteでタスク管理を先行
  理由：進捗追跡と品質保証を可能にするため
- **Edit/Write/MultiEdit使用時** → ユーザー承認を取得してから実行
  理由：最重要原則（調査OK、実装STOP）を遵守するため
- **完了宣言時** → 品質チェックエラー0を確認してから宣言
  理由：完全なコードのみをマージするため

## メタ認知実行（タスク開始時必須）

### rule-advisorから取得した情報でメタ認知
1. **taskEssence（タスクの本質）を理解**
   - 表面的な作業内容と根本目的の区別
   - 「quick fix」vs「proper solution」の判定

2. **selectedSkills（適用スキル）を確認**
   - 選択されたスキルが適切か判断
   - 必要なセクションを読み込む

3. **metaCognitiveGuidance.pastFailures（過去の失敗）を認識**
   - 同じ失敗を繰り返さないよう注意
   - 提示された回避策を意識

4. **metaCognitiveGuidance.firstStep（初動アクション）を実行**
   - 推奨されたツールから開始
   - 計画的に進める

## Claude行動制御（失敗防止）

### 自動停止トリガー（必ず停止）
- **5ファイル以上の変更検出**：即座停止、影響範囲をユーザーに報告
  理由：大規模変更は事前計画とレビューが必要なため
- **同じエラー3回発生**：根本原因分析必須
  理由：対症療法ではなく根本解決が必要なため
- **unknown型多用検出**：型ガード設計再検討
  理由：型安全性の設計に問題がある可能性が高いため
- **3ファイル編集完了**: TodoWriteの更新を強制（更新しないと次のEditツール使用不可）
  理由：進捗確認と方向性の再確認が必要なため

### エラー修正衝動対処
1. エラー発見 → **一時停止**
2. rule-advisor再実行
3. 根本原因分析（なぜ？を5回繰り返して真因を特定）
4. 対処計画提示
5. ユーザー承認後に修正

### エスカレーション基準（ユーザー確認必須）
- アーキテクチャ変更（新レイヤー追加、責務変更）
- 外部依存追加（npmパッケージ、外部API）
- 破壊的変更（既存APIの変更、データ構造の変更）
- 複数の実装方法があり優劣が判断できない場合

### 集中時のルール無視防止
**測定可能な強制停止基準**：
- **連続エラー修正2回目**: 自動的にrule-advisor再実行をトリガー
- **Editツール5回使用**: 影響範囲レポートの作成を強制
- **同一ファイル3回編集**: リファクタリング検討の強制停止

### 一時ファイル作成ルール
作業中ファイルは`tmp/`ディレクトリ使用。完了時削除。

## 🔐 RLS（Row Level Security）実装方針

### 基本原則: Defense in Depth（多層防御）

```
認可は必ず2層で実施する:
1. アプリケーション層: 権限チェック（MemberAccess / CreatorAccess）と、全SQL文への series_id / user_id 条件
2. データベース層: RLSポリシー（最終防衛線）
```

**理由**: 片方に実装漏れがあっても、もう片方で防御できる

### データの持ち主は2種類

| 種類 | テーブル | 持ち主 | 判定 |
|------|---------|-------|------|
| シリーズのデータ | `series` とその子（`series_attendees`, `occurrences`, `agenda_topics`, `memory_items`, `knowledge`, `agendas`, `dictionary_entries`） | 定例シリーズ | `public.my_series_roles()` |
| 個人の資格情報 | `google_integrations`, `slack_integrations`, `oauth_states` | ユーザー | `auth.uid() = user_id` |

参加者の定義は `public.my_series_roles()` の1か所だけ。RLSポリシーもアプリ層の権限チェック（`member_access` / `creator_access`）もこの関数を使う。詳細は [ADR-0008](docs/adr/ADR-0008-team-owned-meeting-series.md) と [設計書](docs/design/team-owned-meeting-series.md)。

---

### 必須実装パターン

#### 1. Supabaseクライアントの使い分け

| 用途 | クライアント | RLS | 使用場面 |
|------|-------------|-----|---------|
| 通常API | `get_user_supabase_client` | ✅ 適用 | 認証済みユーザーの操作すべて |
| カレンダーミラー | `SeriesCalendarMirror`（内部で `get_supabase_client`） | ❌ バイパス | シリーズの作成、招待客と回の反映、参加時の招待客の読み直し。カレンダー由来のデータを書くのはここだけ |
| OAuth callback | `get_supabase_client` | ❌ バイパス | 外部サービスからのコールバック |
| バッチ処理 | `get_supabase_client` | ❌ バイパス | 管理タスク、マイグレーション |

上の表にない場所で `get_supabase_client` を使わない。2つのクライアントは型でも区別する（`supabase_client.py` の `UserClient` と `ServiceClient`）。リポジトリは受け取るクライアントの型を宣言し、取り違えは mypy と ty が検出する。

#### 2. シリーズのエンドポイントは権限チェックを依存関係で受け取る

```python
# ✅ 正しい: 参加者なら MemberAccess、作成者限定なら CreatorAccess
@router.get("/{series_id}/memory")
async def get_memory(access: MemberAccess = Depends(member_access), ...) -> TeamMemoryResponse: ...

@router.post("/{series_id}/occurrences/{occurrence_id}/agenda")
async def generate(access: CreatorAccess = Depends(creator_access), ...) -> GenerateAgendaResponse: ...
```

- パスの `series_id` をそのままユースケースに渡さない。必ず `access.series_id` を使う。
- 作成者限定のユースケースは型で `CreatorAccess` を要求する。
- 権限がなければ 404（存在を隠す）、参加者だが作成者でなければ 403。

#### 3. 全SQL文に持ち主の条件を付ける

```python
# ✅ シリーズのデータ: series_id で絞る
self._client.table("knowledge").select("*").eq("id", str(knowledge_id)).eq("series_id", str(access.series_id)).execute()

# ✅ 個人の資格情報: user_id で絞る
self._client.table("google_integrations").select("*").eq("id", str(integration_id)).eq("user_id", str(user_id)).execute()
```

#### 4. リポジトリのDIパターン

```python
# ✅ 正しい: コンストラクタでClientを受け取る
class MyRepositoryImpl:
    def __init__(self, client: Client) -> None:
        self._client = client

# ❌ 禁止: 内部でグローバル関数を呼び出す
class MyRepositoryImpl:
    def __init__(self) -> None:
        self._client = get_supabase_client()  # RLSバイパスのリスク
```

---

### 禁止パターン（アンチパターン）

#### ❌ 1. UPDATE/DELETEで持ち主の条件なし

```python
# ❌ 危険: 条件が id だけ
self._client.table("agendas").update(data).eq("occurrence_id", str(occurrence_id)).execute()

# ✅ 安全: series_id でも絞る
self._client.table("agendas").update(data).eq("occurrence_id", str(occurrence_id)).eq("series_id", str(access.series_id)).execute()
```

#### ❌ 2. service_roleクライアントを認証済みAPIで使用

カレンダーミラーとOAuth callback以外では禁止。

#### ❌ 3. リクエストの値を持ち主として信用する

```python
# ❌ 危険: リクエストボディの user_id / series_id / email を信用する
# ✅ 安全: user_id は JWT から、series_id は access から、参加者の判定は my_series_roles() から
```

#### ❌ 4. メールアドレスを本人確認に使う

`auth.users.email`、JWT の `email` クレーム、`google_integrations.email` は参加者の判定に使わない。使うのは `auth.identities` の Google 確認済みメールだけ（`my_series_roles()` の中に閉じている）。

---

### 新しいテーブルを足すとき

- シリーズのデータなら `series_id` 列と、`occurrences` への複合外部キー `(occurrence_id, series_id)` を持たせる。
- ポリシーは「参加者が読む」「作成者が書く」の2本を基本にする。参加者が書ける例外は、本人が作る行（`agenda_topics`）か SECURITY DEFINER の RPC（`set_memory_item_resolution`）に限る。
- カレンダー由来の列や表には `authenticated` への書き込み GRANT を与えない。
- SECURITY DEFINER 関数は `set search_path = ''` にし、`anon` と `public` から EXECUTE を取り消す。

### レビューチェックリスト

- [ ] リポジトリはコンストラクタで`Client`を受け取っているか
- [ ] エンドポイントは`get_user_supabase_client`と`member_access` / `creator_access`を使っているか
- [ ] 全SQL文に`series_id`（シリーズのデータ）または`user_id`（個人の資格情報）の条件があるか
- [ ] INSERTで使う`user_id`はJWT由来か
- [ ] `get_supabase_client`を上の表以外で使っていないか
- [ ] 新しいテーブルの全操作を`backend/tests/rls/`で検証したか

---

### テスト要件

認可のテストはモックではなく、ローカルの Supabase で実ユーザーと実 JWT を使う（`backend/tests/rls/`）。

```bash
make test-rls   # ローカルSupabaseが起動している必要がある
```

新しいテーブルや RPC には、少なくとも次を確かめるテストを書く。

1. 作成者、参加者、部外者のそれぞれが読めるもの
2. 部外者と参加者の UPDATE / DELETE が 0 行になる、またはエラーになること
3. 他人になりすました INSERT が拒否されること
4. 参加者が作成者の資格情報を読めないこと

---

### 関連ドキュメント

- [ADR-0008: 定例シリーズをチームの持ち物にする](docs/adr/ADR-0008-team-owned-meeting-series.md)
- [ADR-0004: RLSベースの認可アーキテクチャ](docs/adr/ADR-0004-rls-based-authorization.md)
- [Design Doc: 定例シリーズのチーム共有化](docs/design/team-owned-meeting-series.md)
- [RLSポリシーパターン](docs/design/rls-policy-patterns.md)

---

## 技術スタック

### バックエンド（backend/）
- **言語**: Python 3.12+
- **フレームワーク**: FastAPI
- **データベース**: Supabase (PostgreSQL + Auth + Storage)
- **マイグレーション**: Supabase CLI
- **AI**: AWS Bedrock (Claude Haiku 4.5, Titan Embeddings)
- **パッケージ管理**: uv

### フロントエンド（frontend/）
- **言語**: TypeScript
- **ビルドツール**: Vite
- **UIライブラリ**: React 19
- **スタイリング**: Tailwind CSS v4
- **テスト**: Vitest + React Testing Library
- **Lint/Format**: Biome
- **パッケージ管理**: npm

### インフラ
- **コンテナ**: Docker, Docker Compose

## 品質チェックコマンド

### バックエンド（backend/）
```bash
cd backend
uv run ruff check .       # Lint
uv run ruff format .      # Format
uv run mypy .             # 型チェック（静的解析）
uv run ty check .         # 型チェック（Ruff Type Checker - CI必須）
uv run pytest             # テスト
uv run pytest --cov       # カバレッジ
```

**注意**: `mypy`と`ty check`の両方を必ず実行すること（CIでは`ty`を使用）。

### フロントエンド（frontend/）
```bash
cd frontend
npm run check             # Biome (lint + format)
npm run type-check        # TypeScript型チェック
npm run test              # テスト
npm run test:coverage     # カバレッジ
npm run build             # 本番ビルド
```

### 開発環境（Makefile）
```bash
make dev              # Supabase + App 起動
make down             # 停止
make logs             # ログ確認
make supabase-status  # Supabaseステータス
```

### データベースマイグレーション (Supabase CLI)
```bash
make migrate          # 本番にマイグレーション適用（差分のみ）
make migrate-up       # ローカルに差分マイグレーション適用（推奨）
make migrate-reset    # ローカルDBリセット（⚠️ 全データ削除）
make migrate-new      # 新規マイグレーション作成
make migrate-status   # マイグレーション状態確認
```

マイグレーションファイルは `supabase/migrations/` に配置:
- ローカル: `supabase start` で自動適用
- 本番: `supabase db push` で適用

### 🚨 マイグレーション実行ルール（必須）

**通常のマイグレーション適用時:**
- ✅ `make migrate-up` を使用（差分のみ適用、データ保持）
- ❌ `make migrate-reset` は使用禁止（全データ削除される）

**migrate-resetを使用してよい場合（限定的）:**
- 初期セットアップ時
- スキーマを一から作り直す必要がある時
- ユーザーから明示的に指示された時

**本番環境での禁止事項:**
- ❌ `supabase db reset` の実行は絶対禁止
- ❌ `make migrate-reset` の実行は絶対禁止
- ✅ `make migrate`（= `supabase db push`）のみ使用可

### Supabase MCP（補助ツール）
- `mcp__supabase__list_tables` - テーブル一覧
- `mcp__supabase__execute_sql` - SQL実行
- `mcp__supabase__get_logs` - ログ確認

### Voice Notification Rules

- **全てのタスク完了時には必ずVOICEVOXの音声通知機能を使用すること**
- **重要なお知らせやエラー発生時にも音声通知を行うこと**
- **音声通知の設定: speaker=1, speedScale=1.3を使用すること**
- **英単語は適切にカタカナに変換してVOICEVOXに送信すること**
- **VOICEVOXに送信するテキストは不要なスペースを削除すること**
- **1回の音声通知は100文字以内でシンプルに話すこと**
- **以下のタイミングで細かく音声通知を行うこと：**
  - 命令受領時: 「了解です」「承知しました」
  - 作業開始時: 「〜を開始します」  
  - 作業中: 「調査中です」「修正中です」
  - 進捗報告: 「半分完了です」「もう少しです」
  - 完了時: 「完了です」「修正完了です」
- **詳しい技術的説明は音声通知に含めず、結果のみを簡潔に報告すること**
