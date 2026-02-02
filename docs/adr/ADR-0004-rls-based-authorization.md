# ADR-0004: RLSベースの認可アーキテクチャ

## ステータス

**Proposed** (2026-02-02)

## 経緯

現在のShitaku.aiバックエンドでは、Supabaseへのアクセスに`service_role`キーを使用しており、PostgreSQLのRow Level Security (RLS)がバイパスされている。認可はアプリケーション層でuser_idフィルタを明示的に付与する形で実装されているが、以下の問題が発生している。

### 現在の課題

1. **UPDATE操作におけるセキュリティリスク**
   - `agent_repository_impl.py`、`dictionary_repository_impl.py`、`slack_integration_repository_impl.py`、`google_integration_repository_impl.py`のupdate()メソッドでuser_idフィルタが欠落
   - 理論上、他ユーザーのデータを更新可能な脆弱性が存在

2. **認可ロジックの分散**
   - 各リポジトリ実装で個別にuser_idフィルタを実装する必要がある
   - 実装漏れのリスクが高く、一貫性の担保が困難

3. **防御の深さ（Defense in Depth）の欠如**
   - アプリケーション層のみで認可を制御
   - データベース層での最終防衛線がない

### 変更の契機

- セキュリティ監査でUPDATE操作の脆弱性を検出
- MVP公開前にセキュリティ基盤を確立する必要性
- 既存のRLSポリシー設計（`docs/design/rls-policy-patterns.md`）を活用可能

## 決定事項

**ユーザーJWTをバックエンドで活用し、RLSに認可を委譲するアーキテクチャへ移行する。**

### 決定の詳細

| 項目 | 内容 |
|-----|-----|
| **決定** | ユーザーJWTを使用してSupabaseクライアントを初期化し、RLSポリシーで行レベルの認可を実施 |
| **なぜ今か** | UPDATE操作の脆弱性がMVP公開前に発見され、セキュリティ基盤確立が急務 |
| **なぜこれか** | 既存RLSポリシー設計を活用でき、認可ロジックを一元化してヒューマンエラーを排除 |
| **既知の不確実性** | httpxクライアント生成のパフォーマンス影響（シングルトン化で軽減予定） |
| **撤回基準** | RLSポリシーの複雑化により管理不能になった場合 |

## 根拠

### 検討した選択肢

#### 1. 現状維持 + user_idフィルタ修正（不採用）

アプリケーション層で全UPDATE/DELETE操作にuser_idフィルタを追加。

- **メリット**:
  - 実装変更が最小限
  - 既存アーキテクチャを維持
- **デメリット**:
  - 今後の実装でも同様の漏れリスクが継続
  - 防御の深さが確保できない
  - コードレビューでの見落としリスク

#### 2. 全操作でuser_idフィルタを必須化（Lintルール追加）（不採用）

カスタムLintルールでuser_idフィルタの存在を検証。

- **メリット**:
  - 自動化された検証が可能
  - 既存アーキテクチャを維持
- **デメリット**:
  - Lintルールの実装・保守コスト
  - 複雑なクエリパターンへの対応困難
  - データベース層での防御がない

#### 3. RLSベースの認可（採用）

ユーザーJWTをSupabaseクライアントに設定し、RLSポリシーで認可を実施。

- **メリット**:
  - 認可ロジックの一元化（データベース層）
  - 実装漏れによる脆弱性を原理的に排除
  - 既存RLSポリシー設計を活用可能
  - 防御の深さを確保
- **デメリット**:
  - リクエストごとにSupabaseクライアント生成（パフォーマンス考慮必要）
  - 移行期間中の並行運用が必要
  - RLSポリシーのデバッグが複雑

## 影響

### ポジティブな影響

- **セキュリティ強化**: 認可をデータベース層に委譲し、アプリケーション層のバグによる脆弱性を防止
- **保守性向上**: 認可ロジックがRLSポリシーに集約され、リポジトリ実装がシンプル化
- **一貫性確保**: 全テーブルで統一された認可モデルを適用
- **監査容易性**: RLSポリシーがSQL定義として明示的に管理可能

### ネガティブな影響

- **パフォーマンスへの影響**: リクエストごとのクライアント初期化コスト（httpxシングルトン化で軽減）
- **移行コスト**: 既存リポジトリ実装の修正が必要
- **デバッグ複雑性**: RLSポリシーによる暗黙的なフィルタリングでトラブルシューティングが困難になる可能性

### 中立的な影響

- **テスト戦略の変更**: 統合テストでRLSポリシーの動作検証が必要
- **開発フロー変更**: RLSポリシーを意識した開発が必要

## 実装指針

### アーキテクチャ原則

1. **ユーザーコンテキストの明示的伝播**
   - FastAPI依存性注入でユーザーJWTを取得
   - リクエストスコープでユーザーコンテキスト付きSupabaseクライアントを生成

2. **httpxクライアントのシングルトン化**
   - アプリケーションライフサイクルで共有
   - クライアント生成コストを最小化

3. **リポジトリの依存性注入統一**
   - 全リポジトリでSupabaseクライアントをコンストラクタで受け取る
   - グローバル関数呼び出しを排除

4. **段階的移行**
   - 短期対策としてuser_idフィルタを即時修正
   - 中期対策としてRLS認可へ移行

### 認可の責務分担

| 層 | 責務 |
|---|------|
| Presentation層 | JWTからユーザーID抽出、ユーザーコンテキスト付きクライアント取得 |
| Application層 | ビジネスロジック実行（認可は委譲） |
| Infrastructure層 | ユーザーコンテキスト付きクライアントでDB操作 |
| Database層（RLS） | 行レベルの認可を実施 |

## 関連情報

- [ADR-0001: クリーンアーキテクチャ採用](./ADR-0001-clean-architecture-adoption.md)
- [Design Doc: RLS Policy Patterns](../design/rls-policy-patterns.md)
- [Supabase RLS Documentation](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase Token Security](https://supabase.com/docs/guides/auth/oauth-server/token-security)

## 参考資料

- [Row Level Security | Supabase Docs](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Token Security and Row Level Security | Supabase Docs](https://supabase.com/docs/guides/auth/oauth-server/token-security)
- [Using FastAPI Like a Pro with Singleton and Dependency Injection Patterns](https://medium.com/@hieutrantrung.it/using-fastapi-like-a-pro-with-singleton-and-dependency-injection-patterns-28de0a833a52)
- [Need Advice On How To Properly Use Supabase With FastAPI](https://github.com/orgs/supabase/discussions/33811)
- [Dependency Injection in FastAPI: 2026 Playbook](https://thelinuxcode.com/dependency-injection-in-fastapi-2026-playbook-for-modular-testable-apis/)
