# ADR-0002: デザインシステム基盤アーキテクチャ

## ステータス

**Proposed**

## 経緯

Shitaku.aiのフロントエンドは基本的なTailwind CSSユーティリティクラス（gray, blue系）で実装されており、以下の課題がある:

- **ビジュアルアイデンティティの欠如**: 標準的なグレー・ブルー配色で差別化されていない
- **デザイントークン未定義**: カラー・タイポグラフィ・スペーシングが一元管理されていない
- **クレイモーフィズムスタイル未対応**: PRDで要求される「ミニマル×温かみ」のnaniスタイルが実現できていない
- **スタイルの一貫性欠如**: 各コンポーネントでスタイルが個別定義され、統一感がない

現在のTailwind CSS v4（`@tailwindcss/vite 4.1.18`）は`@theme`ディレクティブによるCSS変数ベースのデザイントークン定義をサポートしており、この機能を活用してデザインシステム基盤を構築する。

## 決定事項

**Tailwind CSS v4の`@theme`ディレクティブを使用したCSS変数ベースのデザインシステムを採用する。**

### 決定の詳細

| 項目 | 内容 |
|-----|-----|
| **決定** | Tailwind CSS v4の`@theme`ディレクティブでデザイントークンを定義し、クレイモーフィズムスタイルをTailwindユーティリティで実現 |
| **なぜ今か** | PRDでUI刷新が要求されており、デザインシステム基盤なしでは一貫したスタイリングが困難 |
| **なぜこれか** | 既存のTailwind CSS v4環境をそのまま活用でき、追加依存なしでCSS変数ベースのデザイントークンが実現可能 |
| **既知の不確実性** | クレイモーフィズムの複雑なbox-shadow定義がパフォーマンスに与える影響は実測が必要 |
| **撤回基準** | LCP 2.5秒を超過する場合、またはbox-shadowのレンダリングが100ms以上かかる場合 |

## 根拠

### 検討した選択肢

#### 選択肢A: CSS-in-JS（Emotion/styled-components）

- **概要**: CSS-in-JSライブラリでデザイントークンをJavaScript変数として管理
- **メリット**:
  - TypeScriptとの親和性が高い
  - 動的スタイリングが容易
  - コンポーネントとスタイルのコロケーション
- **デメリット**:
  - バンドルサイズ増加（+15-30KB gzip）
  - ランタイムコストが発生
  - 既存のTailwind CSSとの併用が複雑
  - React 19のStreaming SSRとの互換性問題

#### 選択肢B: CSS Modules + CSS変数

- **概要**: CSS ModulesでスコープされたCSSと`:root`でのCSS変数定義
- **メリット**:
  - 追加依存なし
  - スコープされたスタイル
  - CSSの標準機能のみ使用
- **デメリット**:
  - Tailwind CSSのユーティリティクラスとの重複管理
  - クレイモーフィズムのスタイル再利用が困難
  - ビルド設定の変更が必要

#### 選択肢C: Tailwind CSS v4 `@theme`ディレクティブ（採用）

- **概要**: Tailwind CSS v4のCSS-First Configurationを活用し、`@theme`でデザイントークンを定義
- **メリット**:
  - 既存環境（Tailwind CSS 4.1.18）をそのまま活用
  - 追加依存ゼロ
  - CSS変数として公開され、カスタムCSSからも参照可能
  - Tree-shakingで未使用スタイルが除外される
  - クレイモーフィズム用のカスタムユーティリティを追加可能
- **デメリット**:
  - Tailwind CSS v4固有の機能に依存
  - 複雑なbox-shadow定義がやや冗長

## 比較マトリクス

| 評価軸 | CSS-in-JS | CSS Modules | Tailwind @theme |
|--------|-----------|-------------|-----------------|
| バンドルサイズ | +15-30KB | 0 | 0 |
| ランタイムコスト | あり | なし | なし |
| 既存環境との親和性 | 低 | 中 | 高 |
| デザイントークン管理 | JS変数 | CSS変数 | CSS変数 |
| 学習コスト | 中 | 低 | 低 |
| パフォーマンス | 中 | 高 | 高 |
| 移行コスト | 高（全面書き換え） | 中 | 低（漸進的適用） |

## 影響

### ポジティブな影響

- デザイントークンの一元管理によりスタイルの一貫性が向上
- CSS変数によりランタイムでの値参照が可能
- 追加依存なしでコストゼロ運用を維持
- 既存コンポーネントへの漸進的適用が可能

### ネガティブな影響

- Tailwind CSS v4固有機能への依存（将来のメジャーバージョンアップ時に影響）
- クレイモーフィズムのbox-shadow定義がやや複雑

### 中立的な影響

- `index.css`ファイルにデザイントークン定義が集約される
- カスタムユーティリティクラスの追加（clay-*系）

## 実装指針

### デザイントークン構造

1. **カラーパレット**:
   - プライマリ: シャーベットオレンジ/アプリコット系（`--color-primary-*`）
   - ニュートラル: ウォームホワイト、ウォームグレー（`--color-neutral-*`）
   - セマンティック: success, warning, error（`--color-semantic-*`）
   - WCAG 2.1 AAコントラスト比を満たす組み合わせのみ

2. **タイポグラフィ**:
   - フォントファミリー: 角丸サンセリフ体（Nunito等）
   - サイズスケール: 見出し・本文・キャプション

3. **スペーシング**:
   - 8pxベースのスケール

4. **形状**:
   - 大きな角丸（border-radius: 16px, 24px, 32px）
   - クレイモーフィズム用box-shadow定義

### クレイモーフィズム実装方針

- 内側シャドウ（inset）と外側シャドウの組み合わせ
- 上部に明るいハイライト、下部に暗いシャドウ
- 背景色は純粋な白ではなくウォームホワイト

### アクセシビリティ

- 全カラー組み合わせはWCAG 2.1 AAコントラスト比4.5:1以上
- フォーカス状態の明確な視覚表示

## 関連情報

- [PRD: フロントエンドUIデザイン全面刷新](../../prd/ui-design-refresh.md)
- [Tailwind CSS v4 Theme Variables](https://tailwindcss.com/docs/theme)
- [Claymorphism in User Interfaces](https://hype4.academy/articles/design/claymorphism-in-user-interfaces)
- [Implementing Claymorphism with CSS](https://blog.logrocket.com/implementing-claymorphism-css/)
- [Tailwind CSS 4 @theme: The Future of Design Tokens (A 2025 Guide)](https://medium.com/@sureshdotariya/tailwind-css-4-theme-the-future-of-design-tokens-at-2025-guide-48305a26af06)

## References

- [Tailwind CSS v4 Theme Variables Documentation](https://tailwindcss.com/docs/theme) - @themeディレクティブの公式ドキュメント
- [Tailwind CSS v4.0 Announcement](https://tailwindcss.com/blog/tailwindcss-v4) - CSS-First Configurationの発表
- [Adding Custom Styles in Tailwind CSS v4](https://tailwindcss.com/docs/adding-custom-styles) - カスタムスタイル追加の公式ガイド
- [Claymorphism CSS Generator](https://hype4.academy/tools/claymorphism-generator) - クレイモーフィズムCSS生成ツール
- [clay.css GitHub Repository](https://github.com/codeAdrian/clay.css) - クレイモーフィズム実装のリファレンス
