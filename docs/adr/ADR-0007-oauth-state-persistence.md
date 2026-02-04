# ADR-0007: OAuth State永続化 - インメモリからSupabaseへの移行

## ステータス

**Proposed** (2026-02-04)

## 経緯

本番環境（Vercel サーバーレス）でSlack/Google OAuth認証が失敗する問題が発生している。

### 現在の課題

1. **サーバーレス環境での状態消失**
   - OAuth stateが`_state_store: dict`でインメモリ管理されている
   - サーバーレス環境では認証開始（`/auth`）とコールバック（`/callback`）が異なるインスタンスで処理される
   - その結果、callbackでstate検証が失敗し「Invalid state parameter」エラーが発生

2. **影響範囲**
   - Slack連携: `backend/src/application/use_cases/slack_use_cases.py`の`_state_store`
   - Google連携: `backend/src/application/use_cases/google_auth_use_cases.py`の`_state_store`
   - 両方とも同じ問題を抱えており、本番環境でOAuth認証が完全に機能しない

3. **優先度: High（本番ブロッキングバグ）**
   - 本番環境でSlack/Google連携機能が使用不可
   - MVP機能の中核であるSlack履歴取得が不可能

### 現行実装

```python
# slack_use_cases.py / google_auth_use_cases.py
_state_store: dict[str, tuple[UUID, datetime]] = {}  # インメモリストア

class StartSlackOAuthUseCase:
    def execute(self, user_id: UUID) -> OAuthStartResult:
        state = secrets.token_urlsafe(32)
        _state_store[state] = (user_id, datetime.now())  # ここで保存
        ...

class HandleSlackCallbackUseCase:
    async def execute(self, code: str, state: str) -> SlackIntegration:
        if state not in _state_store:  # 別インスタンスでは存在しない
            raise ValueError("Invalid state parameter")
        ...
```

### 変更の契機

- 本番環境（Vercel）でのSlack OAuth認証失敗を検出
- サーバーレス環境での状態管理に関する根本的な設計問題
- MVP公開前に解決が必須

## 決定事項

**OAuth stateをSupabase（PostgreSQL）に永続化し、Slack/Google両方で共通のOAuthStateリポジトリを使用する。**

### 決定の詳細

| 項目 | 内容 |
|-----|-----|
| **決定** | OAuth stateをSupabaseテーブル`oauth_states`に保存し、RLSで保護 |
| **なぜ今か** | 本番ブロッキングバグであり、MVP公開前の解決が必須 |
| **なぜこれか** | 既存インフラ（Supabase）を活用しコスト増なし、Redisより運用シンプル |
| **既知の不確実性** | DB書き込み/読み込みによるレイテンシ増加（ミリ秒オーダー、実用上問題なし） |
| **撤回基準** | OAuth認証のレイテンシが1秒を超える場合、またはDBコネクション枯渇が発生した場合 |

## 根拠

### 検討した選択肢

#### 1. Redis（Vercel KV）

Vercel KVまたは外部Redisサービスを使用してstateを管理。

- **メリット**:
  - 高速なKey-Valueアクセス（ミリ秒以下）
  - TTL機能がネイティブでサポート
  - スケーラブル
- **デメリット**:
  - 追加の外部依存（Vercel KVまたはUpstash等）
  - 月額コスト発生（Vercel KV: Hobby無料枠あるが制限あり）
  - 新規インフラ学習・設定コスト
  - 「コストゼロ運用」のビジネス制約に反する可能性

#### 2. Supabase（PostgreSQL）（採用）

既存のSupabaseデータベースに`oauth_states`テーブルを追加。

- **メリット**:
  - 既存インフラを活用（追加コストなし）
  - RLS対応でセキュリティ確保
  - 既存のSupabaseクライアントパターンを踏襲
  - マイグレーション管理が既存フローに統合
  - トランザクション対応（必要に応じて）
- **デメリット**:
  - Redisより若干レイテンシが高い（実用上は問題なし：数十ミリ秒）
  - 短期間で削除されるデータをRDBに保存するオーバーヘッド

#### 3. セッションストレージ（Cookie/Session）

サーバーサイドセッションまたはCookieでstateを管理。

- **メリット**:
  - 追加インフラ不要
  - 従来のWebアプリケーションでは一般的
- **デメリット**:
  - サーバーレス環境ではセッション維持が困難
  - OAuth callbackはサードパーティからのリダイレクトであり、セッション継続が保証されない
  - FastAPIのセッション管理はステートフルサーバー前提

### 選択肢比較

| 観点 | Redis（Vercel KV） | Supabase（採用） | セッションストレージ |
|------|-------------------|-----------------|-------------------|
| 実装コスト | 中 | 低 | 高（サーバーレス対応困難） |
| 追加コスト | あり | なし | なし |
| 既存パターン一貫性 | 低 | 高 | 低 |
| レイテンシ | 最小 | 小 | - |
| RLS対応 | 不要 | 可能 | - |
| 運用シンプルさ | 中 | 高 | - |

## 影響

### ポジティブな影響

- **本番環境でのOAuth認証復旧**: サーバーレス環境でSlack/Google連携が正常動作
- **コスト増なし**: 既存Supabaseインフラを活用
- **統一されたデータ管理**: 他テーブルと同様にマイグレーション管理
- **RLSによるセキュリティ**: user_idベースのアクセス制御

### ネガティブな影響

- **DBアクセス増加**: OAuth開始時とcallback時にDBアクセスが発生（既存の認証フローに+2クエリ）
- **クリーンアップ戦略の単純化**: 期限切れstateのクリーンアップはcallback時のみ実施（バッチ処理は将来検討）

### 中立的な影響

- **テーブル追加**: `oauth_states`テーブルが増加（短期データ用）
- **コードパターン変更**: インメモリからリポジトリパターンへ移行

## 実装指針

### データモデル

`oauth_states`テーブル:

| カラム | 型 | 説明 |
|--------|------|------|
| id | UUID (PK) | 内部識別子 |
| state | TEXT (UNIQUE) | OAuth state token |
| user_id | UUID (FK) | users.idへの参照 |
| provider | TEXT | 'slack' または 'google' |
| scopes | TEXT[] | 要求スコープ（Google用） |
| expires_at | TIMESTAMPTZ | 有効期限（作成から5分後） |
| created_at | TIMESTAMPTZ | 作成日時 |

### RLSポリシー

```sql
-- SELECT: 自分のstateのみ参照可能
CREATE POLICY "Users can read own oauth states"
ON oauth_states FOR SELECT
USING (auth.uid() = user_id);

-- INSERT: 自分のstateのみ作成可能
CREATE POLICY "Users can create own oauth states"
ON oauth_states FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- DELETE: 自分のstateのみ削除可能
CREATE POLICY "Users can delete own oauth states"
ON oauth_states FOR DELETE
USING (auth.uid() = user_id);
```

**注意**: OAuth callbackはサービスロールで実行されるため、callback処理ではRLSをバイパスする（既存のSlack/Google連携と同様のパターン）。

### アーキテクチャ原則

1. **共通リポジトリパターン**
   - `OAuthStateRepository`インターフェースを定義
   - Slack/Google両方で同一リポジトリを使用
   - `provider`カラムで区別

2. **有効期限管理**
   - 作成時に`expires_at = now() + 5分`を設定
   - callback時に`expires_at > now()`を検証
   - callback処理後にstateレコードを削除

3. **クリーンアップ戦略**
   - callback処理時に該当stateを削除（確実な削除）
   - 将来的にバッチ削除を検討（期限切れstateの蓄積防止）

4. **ADR-0004（RLS認可）との整合性**
   - OAuth開始（`/auth`）: ユーザーコンテキスト付きクライアント
   - OAuth callback: サービスロールクライアント（外部サービスからのコールバック）

### 認証フローの変更

```
[Before: インメモリ]
1. /auth → state生成 → _state_store[state] = user_id → URL返却
2. /callback → _state_store.get(state) → 別インスタンスでは失敗

[After: Supabase永続化]
1. /auth → state生成 → oauth_states.insert({state, user_id, expires_at}) → URL返却
2. /callback → oauth_states.select(state) → 検証成功 → oauth_states.delete(state)
```

## 関連情報

- [ADR-0003: Google Workspace連携の認証方式](./ADR-0003-google-workspace-auth.md) - state管理の言及あり
- [ADR-0004: RLSベースの認可アーキテクチャ](./ADR-0004-rls-based-authorization.md) - RLSパターン
- [Slack OAuth 2.0](https://api.slack.com/authentication/oauth-v2)
- [Google OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Vercel Serverless Functions](https://vercel.com/docs/functions/serverless-functions)

## 参考資料

- [OAuth 2.0 State Parameter Best Practices](https://auth0.com/docs/secure/attack-protection/state-parameters) - state parameterの重要性と実装ガイドライン
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security) - RLSポリシー設計
- [Vercel Serverless Functions Limitations](https://vercel.com/docs/functions/serverless-functions/limitations) - サーバーレス環境での状態管理の制約
