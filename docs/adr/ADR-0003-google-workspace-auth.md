# ADR-0003: Google Workspace連携の認証・トークン管理方式

## ステータス

**Proposed** (2026-02-01)

## コンテキスト

Shitaku.aiにGoogle Workspace連携機能を追加し、以下の機能を実現する：

1. **Calendar API**: 定例MTGの自動検出（RRULE解析）
2. **Drive API + Docs API**: Google Meetトランスクリプトの取得
3. **カレンダー↔トランスクリプト紐付け**: 自動マッチング

### 技術的な課題

1. **OAuth 2.0認証**: Google APIへのアクセスにはOAuth 2.0認証が必要
2. **Incremental Authorization**: 初回は最小スコープ、機能利用時に追加スコープをリクエストする要件
3. **トークン管理**: Refresh Tokenの安全な保存と自動リフレッシュ
4. **既存システムとの一貫性**: Slack連携と同様のパターンで実装したい

### 要求スコープ

| フェーズ | スコープ | 用途 |
|----------|----------|------|
| 初回 | `openid, email, profile` | ログイン・ユーザー識別 |
| 初回 | `calendar.readonly` | 定例MTG検出 |
| 機能利用時 | `drive.readonly` | Meetトランスクリプト検索 |
| 機能利用時 | `documents.readonly` | Docsテキスト取得 |

## 決定

**Slack連携と同様のパターンを採用し、バックエンド直接実装 + Fernet暗号化で実装する。**

### 認証方式

- Google OAuth 2.0 Authorization Code Flow
- バックエンド（FastAPI）で直接実装
- httpxによる非同期トークン交換

### トークン暗号化

- Fernet（AES-128-CBC with HMAC）を継続使用
- 既存のSlack連携と同じ暗号化モジュール（`encryption.py`）を拡張

### Incremental Authorization

- `include_granted_scopes=true`パラメータを使用
- 既存スコープを保持しながら新規スコープを追加
- ユーザーのスコープ許可状況をDBに保存

## 選択肢の比較

### 案A: Supabase Auth + Google Provider

```
Supabase Auth → Google OAuth → Access Token
```

| 観点 | 評価 |
|------|------|
| 実装コスト | ◎ 低い（設定のみ） |
| Incremental Authorization | × 非対応 |
| スコープ制御 | △ Supabase側で固定 |
| 既存パターンとの一貫性 | × Slack連携と異なるパターン |
| トークンアクセス | △ Supabaseの制約を受ける |

### 案B: google-auth-oauthlib単独使用

```
google-auth-oauthlib → Access Token → アプリ側で管理
```

| 観点 | 評価 |
|------|------|
| 実装コスト | ○ 中程度 |
| Incremental Authorization | ◎ 完全対応 |
| スコープ制御 | ◎ 柔軟 |
| 既存パターンとの一貫性 | △ 別の認証パターン導入 |
| トークン管理 | △ 暗号化を別途実装 |

### 案C: バックエンド直接実装 + Fernet（採用）

```
FastAPI → Google OAuth → Fernet暗号化 → DB保存
```

| 観点 | 評価 |
|------|------|
| 実装コスト | △ 高い |
| Incremental Authorization | ◎ 完全対応 |
| スコープ制御 | ◎ 柔軟 |
| 既存パターンとの一貫性 | ◎ Slack連携と同一パターン |
| トークン管理 | ◎ 既存暗号化モジュール活用 |

## 採用理由

1. **既存パターンとの一貫性**: Slack連携と同じ認証フローを採用することで、コードベースの一貫性を保ち、保守性を向上
2. **Incremental Authorization対応**: Google固有の段階的スコープ拡張に完全対応
3. **既存モジュールの活用**: `encryption.py`の拡張で暗号化を実現（新規モジュール不要）
4. **フレキシビリティ**: トークンリフレッシュ、エラーハンドリングを完全制御

## 実装原則

### 認証フロー

```
1. ユーザー → 「Googleでログイン」ボタンクリック
2. Backend → Google OAuth認可URLを生成（state付き）
3. ユーザー → Googleの同意画面でスコープを許可
4. Google → Authorization CodeをBackend callback URLに返却
5. Backend → CodeをAccess Token + Refresh Tokenに交換
6. Backend → Refresh TokenをFernetで暗号化してDB保存
7. Backend → フロントエンドにリダイレクト（成功/失敗）
```

### データモデル

`google_integrations`テーブルを新設（Slack連携と同様の分離）:

| カラム | 型 | 説明 |
|--------|------|------|
| id | UUID (PK) | 内部識別子 |
| user_id | UUID (FK) | users.idへの参照 |
| email | TEXT | Googleアカウントのメール |
| encrypted_refresh_token | TEXT | Fernet暗号化済みRefresh Token |
| granted_scopes | TEXT[] | 許可済みスコープ一覧 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### トークンリフレッシュ戦略

- Access Tokenはメモリ上でのみ保持（有効期限1時間）
- API呼び出し前にAccess Tokenの有効期限を確認
- 有効期限5分前に自動リフレッシュ
- Refresh Token失効時はユーザーに再認証をリクエスト

### 暗号化キー管理

- 環境変数 `GOOGLE_TOKEN_ENCRYPTION_KEY` で管理
- Slack連携とは別のキーを使用（将来的に統一検討）
- 本番環境ではAWS Secrets Manager等での管理を推奨

### キーローテーション戦略

Fernetの[ベストプラクティス](https://cryptography.io/en/latest/fernet/#using-passwords-with-fernet)に基づき、将来的なキーローテーションに対応する設計を採用する。

**Phase 1（MVP）:**
- 単一キーでの運用
- キー漏洩時はDB内の全トークンを再暗号化するスクリプトを用意

**Phase 2以降（ユーザー数100超過時）:**
- `MultiFernet`の導入を検討
- 複数キーをサポートし、古いキーでの復号→新しいキーでの再暗号化を段階的に実施
- ローテーション判断基準:
  - キー使用期間が1年を超過した場合
  - セキュリティインシデント発生時
  - 暗号化アルゴリズムの脆弱性が発見された場合

**実装例（将来）:**
```python
from cryptography.fernet import Fernet, MultiFernet

# 新旧キーを保持
keys = [
    Fernet(settings.GOOGLE_TOKEN_ENCRYPTION_KEY_NEW),  # 新キー（暗号化に使用）
    Fernet(settings.GOOGLE_TOKEN_ENCRYPTION_KEY_OLD),  # 旧キー（復号のみ）
]
multi_fernet = MultiFernet(keys)
```

## 結果と影響

### ポジティブ

- Slack連携と同じパターンで実装でき、学習コスト低減
- Incremental Authorizationにより、ユーザーの心理的抵抗を軽減
- 既存の暗号化モジュールを活用し、新規依存を最小化

### ネガティブ

- Supabase Auth利用に比べ実装コストが高い
- state管理のために一時ストア（メモリ/Redis）が必要
- Google APIのレートリミット対応が必要

### リスク軽減策

- state管理はSlack連携と同じメモリストア実装（将来Redis移行）
- レートリミット対応はExponential Backoff実装
- トークンリフレッシュ失敗時のユーザー通知フロー整備

## 参考資料

- [Google Identity: OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google OAuth 2.0 Incremental Authorization](https://developers.google.com/identity/protocols/oauth2/web-server#incrementalAuth)
- [Slack連携実装: slack_use_cases.py](../backend/src/application/use_cases/slack_use_cases.py)
- [暗号化モジュール: encryption.py](../backend/src/infrastructure/external/encryption.py)
