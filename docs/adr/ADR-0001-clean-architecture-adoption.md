# ADR-0001: クリーンアーキテクチャ + DDD 採用

## ステータス

**Accepted** (2026-01-31)

## コンテキスト

Shitaku.aiバックエンドは現在、以下のフラット構造を採用している：

```
backend/app/
  api/v1/endpoints/  # APIエンドポイント
  crud/              # CRUD操作（ビジネスロジック混在）
  db/                # DB接続
  models/            # SQLAlchemyモデル
  schemas/           # Pydanticスキーマ
  services/          # サービス（未使用）
  config.py          # 設定
  main.py            # エントリポイント
```

### 現在の課題

1. **外部依存の分離不足**: SQLAlchemyモデルがビジネスロジックと密結合
2. **テスタビリティ低下**: CRUD層が直接DBアクセスし、ユニットテストが困難
3. **拡張性の制限**: 新機能追加時に既存コードへの影響が大きい

### 変更の契機

- **Supabase統合**: Auth + DBの外部サービス統合が必要
- **Bedrock統合**: Claude + Embeddingsの外部API統合が必要
- **将来機能**: アジェンダ生成、ユビキタス言語辞書などのドメインロジック追加予定

## 決定

**クリーンアーキテクチャ + DDDを採用し、4層構造へ移行する。**

### 移行先構造

```
backend/src/
  domain/              # ドメイン層（最内層）
    entities/          # エンティティ、値オブジェクト
    repositories/      # リポジトリインターフェース（抽象）
    services/          # ドメインサービス
  application/         # アプリケーション層
    use_cases/         # ユースケース（アプリケーションサービス）
    dto/               # データ転送オブジェクト
  infrastructure/      # インフラ層
    database/          # DB接続、SQLAlchemyモデル
    external/          # 外部API（Supabase, Bedrock）
    repositories/      # リポジトリ実装
  presentation/        # プレゼンテーション層（最外層）
    api/               # FastAPIエンドポイント
    schemas/           # リクエスト/レスポンススキーマ
  main.py              # エントリポイント
  config.py            # 設定
```

## 選択肢の比較

### 案A: 現状維持（フラット構造）

```
app/api/crud/models/schemas
```

| 観点 | 評価 |
|------|------|
| 学習コスト | ◎ なし |
| 移行コスト | ◎ なし |
| テスタビリティ | △ 統合テスト依存 |
| 外部依存分離 | × 困難 |
| スケーラビリティ | × 低い |

### 案B: サービス層追加

```
app/api/services/crud/models/schemas
```

| 観点 | 評価 |
|------|------|
| 学習コスト | ○ 低い |
| 移行コスト | ○ 段階的対応可能 |
| テスタビリティ | ○ 改善 |
| 外部依存分離 | △ 部分的 |
| スケーラビリティ | △ 中程度 |

### 案C: クリーンアーキテクチャ + DDD（採用）

```
src/domain/application/infrastructure/presentation
```

| 観点 | 評価 |
|------|------|
| 学習コスト | △ 高い |
| 移行コスト | △ 初期コスト高 |
| テスタビリティ | ◎ 高い（ドメイン層は外部依存なし） |
| 外部依存分離 | ◎ 完全分離 |
| スケーラビリティ | ◎ 高い |

## 採用理由

1. **外部依存の完全分離**: Supabase/Bedrockをインフラ層に閉じ込め、ドメインロジックを保護
2. **高テスタビリティ**: ドメイン層は純粋なPythonコードでユニットテスト可能
3. **依存性逆転**: リポジトリインターフェースをドメイン層で定義し、実装詳細を隠蔽
4. **将来の拡張性**: 新機能追加時の影響範囲を最小化

## 実装原則

### 依存性の方向

```
presentation → application → domain ← infrastructure
```

- 外側から内側への一方向のみ
- ドメイン層は他のどの層にも依存しない
- インフラ層はドメイン層のインターフェースを実装

### レイヤー間の通信

| From | To | 方法 |
|------|-----|------|
| Presentation | Application | DTO経由でユースケース呼び出し |
| Application | Domain | エンティティ、リポジトリインターフェース使用 |
| Infrastructure | Domain | リポジトリインターフェースの実装提供 |

### フレームワーク非依存

- ドメインエンティティはSQLAlchemy/Pydanticに依存しない
- FastAPI固有のコードはプレゼンテーション層のみ
- DB固有のコードはインフラ層のみ

## 結果と影響

### ポジティブ

- ドメインロジックの独立性確保
- ユニットテストカバレッジ向上
- 外部サービス変更時の影響最小化
- 新規メンバーのオンボーディング効率化（明確な責務分離）

### ネガティブ

- 初期移行コスト（既存コードの再配置）
- ボイラープレートコードの増加（インターフェース定義等）
- チーム全員の学習コスト

### リスク軽減策

- 段階的移行（新機能から適用、既存機能は徐々に移行）
- ドキュメント整備（各層の責務と実装例）
- コードレビューでのアーキテクチャ準拠確認

## 参考資料

- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design (Eric Evans)](https://www.domainlanguage.com/ddd/)
- [FastAPI with Clean Architecture](https://github.com/topics/fastapi-clean-architecture)
