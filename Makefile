.PHONY: setup dev build test lint clean help

# 初期セットアップ
setup:
	docker-compose build
	cd backend && uv sync
	cd frontend && npm install

# 開発環境起動
dev:
	docker-compose up

# 開発環境起動（バックグラウンド）
dev-d:
	docker-compose up -d

# 停止
down:
	docker-compose down

# ログ確認
logs:
	docker-compose logs -f

# 本番ビルド
build:
	docker-compose build --no-cache

# 全テスト実行
test:
	cd backend && uv run pytest
	cd frontend && npm run test

# テスト（カバレッジ付き）
test-cov:
	cd backend && uv run pytest --cov=app --cov-report=term-missing
	cd frontend && npm run test:coverage

# Lint
lint:
	cd backend && uv run ruff check .
	cd backend && uv run mypy .
	cd frontend && npm run lint
	cd frontend && npm run check

# Format
format:
	cd backend && uv run ruff format .
	cd frontend && npm run format

# バックエンドのみ
backend-dev:
	cd backend && uv run uvicorn app.main:app --reload

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
	cd frontend && npm run lint && npm run check

# データベースマイグレーション
migrate:
	cd backend && uv run alembic upgrade head

migrate-gen:
	@read -p "Migration message: " msg; \
	cd backend && uv run alembic revision --autogenerate -m "$$msg"

migrate-down:
	cd backend && uv run alembic downgrade -1

# クリーンアップ
clean:
	docker-compose down -v
	rm -rf backend/__pycache__ backend/.pytest_cache backend/.mypy_cache
	rm -rf frontend/.next frontend/node_modules

# ヘルプ
help:
	@echo "利用可能なコマンド:"
	@echo "  make setup       - 初期セットアップ"
	@echo "  make dev         - 開発環境起動"
	@echo "  make dev-d       - 開発環境起動（バックグラウンド）"
	@echo "  make down        - 停止"
	@echo "  make logs        - ログ確認"
	@echo "  make test        - 全テスト実行"
	@echo "  make test-cov    - テスト（カバレッジ付き）"
	@echo "  make lint        - Lint"
	@echo "  make format      - Format"
	@echo "  make migrate     - マイグレーション適用"
	@echo "  make migrate-gen - マイグレーション生成"
	@echo "  make clean       - クリーンアップ"
