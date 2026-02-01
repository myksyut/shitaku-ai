# 開発進捗記録

## 完了済みフェーズ

### Phase 1: 認証基盤 ✅
- JWT認証ミドルウェア
- RLSポリシーマイグレーション
- フロントエンド認証フック

### Phase 2: 用語辞書 ✅
- Dictionary ドメイン/インフラ/API/フロントエンド

### Phase 3: MTGエージェント ✅
- **完了日**: 2026-02-01
- **PR**: https://github.com/myksyut/shitaku-ai/pull/2

#### 実装内容
| タスク | 内容 | 状態 |
|-------|------|------|
| task-03-01 | ドメイン層（Agent Entity, Repository IF） | ✅ |
| task-03-02 | インフラ層（Migration, Repository Impl） | ✅ |
| task-03-03 | API層（Schemas, Use Cases, Endpoints） | ✅ |
| task-03-04 | フロントエンド（一覧/フォーム/詳細画面） | ✅ |

#### 作成ファイル
- `backend/src/domain/entities/agent.py`
- `backend/src/domain/repositories/agent_repository.py`
- `backend/src/infrastructure/repositories/agent_repository_impl.py`
- `backend/src/application/use_cases/agent_use_cases.py`
- `backend/src/presentation/schemas/agent.py`
- `backend/src/presentation/api/v1/endpoints/agents.py`
- `backend/tests/domain/entities/test_agent.py`
- `frontend/src/features/agents/*` (7ファイル)
- `supabase/migrations/20260201013253_create_agents_table.sql`

---

## 未着手フェーズ

### Phase 4: 議事録管理
- task-04-01〜05

### Phase 5: Slack連携
- task-05-01〜05

### Phase 6: アジェンダ生成
- task-06-01〜04

### Phase 7: 統合テスト・E2E
- task-07-01〜02
