.PHONY: setup dev build test lint clean help

# 初期セットアップ
setup:
	cd backend && uv sync
	cd frontend && npm install
	supabase start

# 環境切り替え
env-local:
	cp backend/.env.local backend/.env
	@echo "Switched to LOCAL environment"

env-prod:
	cp backend/.env.production backend/.env
	@echo "Switched to PRODUCTION environment"

# 開発環境起動（Supabase + App）
dev:
	cp backend/.env.local backend/.env
	supabase start
	docker-compose up

# 開発環境起動（バックグラウンド）
dev-d:
	cp backend/.env.local backend/.env
	supabase start
	docker-compose up -d

# 停止
down:
	docker-compose down
	supabase stop

# ログ確認
logs:
	docker-compose logs -f

# Supabaseステータス
supabase-status:
	supabase status

# 本番ビルド
build:
	docker-compose build --no-cache

# 全テスト実行
test:
	cd backend && uv run pytest
	cd frontend && npm run test

# テスト（カバレッジ付き）
test-cov:
	cd backend && uv run pytest --cov=src --cov-report=term-missing
	cd frontend && npm run test:coverage

# Lint
lint:
	cd backend && uv run ruff check .
	cd backend && uv run mypy .
	cd frontend && npm run check

# Format
format:
	cd backend && uv run ruff format .

# バックエンドのみ
backend-dev:
	cd backend && uv run uvicorn src.main:app --reload

backend-test:
	cd backend && uv run pytest

backend-lint:
	cd backend && uv run ruff check . && uv run mypy .

# フロントエンドのみ
frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm run test

frontend-lint:
	cd frontend && npm run check

# データベースマイグレーション（Supabase CLI）
# ⚠️ 注意: migrate-reset は全データを削除します。本番では絶対に使用しないこと！

migrate:
	supabase db push

migrate-up:
	supabase migration up

migrate-reset:
	@echo "⚠️  警告: このコマンドは全データを削除します！"
	@echo "本番環境では絶対に実行しないでください。"
	@read -p "本当に実行しますか？ (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		supabase db reset; \
	else \
		echo "キャンセルしました"; \
	fi

migrate-new:
	@read -p "Migration name: " name; \
	supabase migration new $$name

migrate-status:
	supabase migration list

# クリーンアップ
clean:
	docker-compose down -v
	supabase stop
	rm -rf backend/__pycache__ backend/.pytest_cache backend/.mypy_cache
	rm -rf frontend/node_modules

# ヘルプ
help:
	@echo "利用可能なコマンド:"
	@echo ""
	@echo "開発環境:"
	@echo "  make setup          - 初期セットアップ"
	@echo "  make dev            - 開発環境起動（Supabase + App）"
	@echo "  make dev-d          - 開発環境起動（バックグラウンド）"
	@echo "  make down           - 停止"
	@echo "  make logs           - ログ確認"
	@echo "  make supabase-status - Supabaseステータス確認"
	@echo ""
	@echo "テスト・品質:"
	@echo "  make test           - 全テスト実行"
	@echo "  make test-cov       - テスト（カバレッジ付き）"
	@echo "  make lint           - Lint"
	@echo "  make format         - Format"
	@echo ""
	@echo "マイグレーション:"
	@echo "  make migrate        - 本番にマイグレーション適用（差分のみ）"
	@echo "  make migrate-up     - ローカルに差分マイグレーション適用（推奨）"
	@echo "  make migrate-reset  - ローカルDBリセット（⚠️ 全データ削除）"
	@echo "  make migrate-new    - 新規マイグレーション作成"
	@echo "  make migrate-status - マイグレーション状態確認"
	@echo ""
	@echo "環境切り替え:"
	@echo "  make env-local      - ローカル環境に切り替え"
	@echo "  make env-prod       - 本番環境に切り替え"
	@echo ""
	@echo "その他:"
	@echo "  make build          - 本番ビルド"
	@echo "  make clean          - クリーンアップ"
