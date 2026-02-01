# Shitaku AI

MTGアジェンダ自動生成ツール

## 技術スタック

- **バックエンド**: Python 3.12+ / FastAPI / Supabase
- **フロントエンド**: TypeScript / React 19 / Vite / Tailwind CSS v4
- **AI**: AWS Bedrock (Claude Haiku 4.5)
- **インフラ**: Docker / Docker Compose

## セットアップ

### 1. 依存関係のインストール

```bash
make setup
```

### 2. 環境変数の設定

`backend/.env.example` をコピーして `backend/.env` を作成：

```bash
cp backend/.env.example backend/.env
```

必要な環境変数を設定してください。

### 3. 開発環境の起動

```bash
make dev
```

これで以下が起動します：
- バックエンド: http://localhost:8001
- フロントエンド: http://localhost:5173
- ngrok: https://lanie-unrehearsed-worryingly.ngrok-free.dev

## Slack連携のセットアップ

### 1. Slack Appの作成

1. [Slack API Console](https://api.slack.com/apps) にアクセス
2. 「Create New App」→「From scratch」を選択
3. App名とワークスペースを設定

### 2. OAuth & Permissions設定

1. 左メニューから「OAuth & Permissions」を選択
2. 「Redirect URLs」に以下を追加：
   ```
   https://lanie-unrehearsed-worryingly.ngrok-free.dev/api/v1/slack/callback
   ```
3. 「Bot Token Scopes」に以下を追加：
   - `channels:read`
   - `channels:history`
   - `users:read`

### 3. 認証情報の取得

1. 「Basic Information」→「App Credentials」から以下をコピー：
   - Client ID
   - Client Secret

### 4. 環境変数の設定

`backend/.env` に以下を追加：

```bash
# ngrok
NGROK_AUTHTOKEN=<https://dashboard.ngrok.com/get-started/your-authtoken から取得>

# Slack OAuth
SLACK_CLIENT_ID=<取得したClient ID>
SLACK_CLIENT_SECRET=<取得したClient Secret>
SLACK_REDIRECT_URI=https://lanie-unrehearsed-worryingly.ngrok-free.dev/api/v1/slack/callback
SLACK_TOKEN_ENCRYPTION_KEY=<下記コマンドで生成>
```

暗号化キーの生成：
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Google連携のセットアップ

### 1. Google Cloud Projectの作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成、または既存のプロジェクトを選択

### 2. OAuth同意画面の設定

1. 「APIとサービス」→「OAuth同意画面」を選択
2. ユーザーの種類で「外部」を選択（内部テスト用なら「内部」）
3. アプリ情報を入力：
   - アプリ名: Shitaku.ai
   - ユーザーサポートメール: 自分のメールアドレス
   - デベロッパー連絡先: 自分のメールアドレス
4. スコープを追加：
   - `email`
   - `profile`
   - `openid`
   - `https://www.googleapis.com/auth/calendar.readonly`
5. テストユーザーに自分のGoogleアカウントを追加

### 3. OAuth 2.0クライアントの作成

1. 「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「OAuth クライアント ID」を選択
3. アプリケーションの種類: 「ウェブ アプリケーション」
4. 名前: 任意（例: Shitaku.ai Local）
5. 承認済みのリダイレクトURI:
   ```
   http://localhost:8001/api/v1/google/callback
   ```
6. 作成後、「クライアントID」と「クライアントシークレット」をコピー

### 4. 環境変数の設定

`backend/.env` に以下を追加：

```bash
# Google OAuth
GOOGLE_CLIENT_ID=<取得したクライアントID>
GOOGLE_CLIENT_SECRET=<取得したクライアントシークレット>
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/google/callback
GOOGLE_TOKEN_ENCRYPTION_KEY=<下記コマンドで生成>
```

暗号化キーの生成：
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. APIの有効化

「APIとサービス」→「ライブラリ」から以下のAPIを有効化：
- Google Calendar API
- Google Drive API（トランスクリプト機能用、Phase 1-3で使用）
- Google Docs API（トランスクリプト機能用、Phase 1-3で使用）

## 開発コマンド

```bash
make dev            # 開発環境起動（Supabase + App + ngrok）
make down           # 停止
make logs           # ログ確認
make test           # テスト実行
make lint           # Lint実行
make format         # コードフォーマット
```

## マイグレーション

```bash
make migrate        # 本番にマイグレーション適用
make migrate-local  # ローカルDBリセット＆適用
make migrate-new    # 新規マイグレーション作成
make migrate-status # マイグレーション状態確認
```
