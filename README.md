# FastAPI + NextJS Boilerplate

本番環境で使用可能なFastAPI + NextJSのフルスタックボイラープレートです。Claude Code用のスキル・エージェント定義を含みます。

## 技術スタック

### バックエンド
- Python 3.12+
- FastAPI
- SQLAlchemy 2.0
- Alembic（マイグレーション）
- PostgreSQL 16
- uv（パッケージ管理）

### フロントエンド
- TypeScript
- NextJS 14 (App Router)
- React 18
- Tailwind CSS
- Biome（Lint/Format）

### インフラ
- Docker / Docker Compose

## クイックスタート

### 必要条件
- Docker & Docker Compose
- Node.js 20+
- Python 3.12+
- uv

### セットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd ai-coding-project-boilerplate-fastapi-nextjs

# 環境変数ファイルをコピー
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Docker Composeで起動
docker-compose up
```

アクセス先:
- フロントエンド: http://localhost:3000
- バックエンドAPI: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs

### ローカル開発（Docker なし）

```bash
# バックエンド
cd backend
uv sync
uv run uvicorn app.main:app --reload

# フロントエンド（別ターミナル）
cd frontend
npm install
npm run dev
```

## プロジェクト構造

```
.
├── backend/                 # FastAPI バックエンド
│   ├── app/
│   │   ├── api/            # APIエンドポイント
│   │   ├── core/           # コア機能
│   │   ├── db/             # データベース設定
│   │   ├── models/         # SQLAlchemyモデル
│   │   ├── schemas/        # Pydanticスキーマ
│   │   └── crud/           # CRUD操作
│   ├── alembic/            # マイグレーション
│   ├── tests/              # テスト
│   └── pyproject.toml
│
├── frontend/               # NextJS フロントエンド
│   ├── src/
│   │   ├── app/           # App Router
│   │   ├── components/    # コンポーネント
│   │   ├── lib/           # ユーティリティ
│   │   └── types/         # 型定義
│   ├── tests/             # テスト
│   └── package.json
│
├── docker/                 # Docker関連
├── .claude/               # Claude Code設定
│   ├── agents/            # エージェント定義
│   ├── commands/          # コマンド定義
│   └── skills/            # スキル定義
│       ├── backend/       # Python/FastAPI用
│       └── frontend/      # TypeScript/NextJS用
├── docker-compose.yml
├── Makefile
└── CLAUDE.md              # 開発ルール
```

## 開発コマンド

```bash
# 開発環境起動
make dev

# テスト実行
make test

# Lint
make lint

# Format
make format

# マイグレーション適用
make migrate

# マイグレーション生成
make migrate-gen
```

詳細は `make help` を参照してください。

## API エンドポイント

### ヘルスチェック
- `GET /api/v1/health` - ヘルスチェック

### ユーザー
- `GET /api/v1/users/` - ユーザー一覧
- `POST /api/v1/users/` - ユーザー作成
- `GET /api/v1/users/{id}` - ユーザー取得
- `PATCH /api/v1/users/{id}` - ユーザー更新
- `DELETE /api/v1/users/{id}` - ユーザー削除

## Claude Code スキル

このボイラープレートには、Claude Code用のスキル定義が含まれています。

### バックエンド用スキル
- `backend/python-rules` - Pythonコーディング規約
- `backend/python-testing` - pytestテスト規約
- `backend/fastapi-spec` - FastAPI技術仕様

### フロントエンド用スキル
- `frontend/typescript-rules` - TypeScriptコーディング規約
- `frontend/typescript-testing` - Vitestテスト規約
- `frontend/nextjs-spec` - NextJS技術仕様

## ライセンス

MIT License
