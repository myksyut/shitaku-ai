# ADR-0006 Notion風WYSIWYGマークダウンエディタライブラリの選定

## ステータス

Accepted

## 経緯

議事録入力（TranscriptContentEditor）とアジェンダ編集（MeetingAgendaEditor）において、ユーザーがマークダウンを直接入力する際の体験に課題がある。現状では、マークダウン記法をプレビュー画面で確認する形式となっており、入力とプレビューが分離している。

ユーザーからは「Notionのように入力しながらリアルタイムでスタイルが適用されるWYSIWYG体験」と「大きめの入力ボックス」への要望がある。これにより、議事録やアジェンダの編集効率を向上させたい。

### 現在の技術スタック
- **React**: 19.2.0
- **TypeScript**: ~5.9.3
- **Tailwind CSS**: v4.1.18
- **ビルドツール**: Vite 7.2.4
- **テスト**: Vitest + React Testing Library

### 技術的制約
- React 19との互換性が必須（新しいReact機能を利用）
- TypeScriptの型安全性を重視（プロジェクト方針）
- バンドルサイズはできるだけ小さく保ちたい（Vercel Hobby無料枠でのデプロイを考慮）

## 決定事項

BlockNoteをNotion風WYSIWYGエディタライブラリとして採用する。

### 決定の詳細

| 項目 | 内容 |
|-----|-----|
| **決定** | BlockNote（@blocknote/react）を採用し、議事録入力とアジェンダ編集の両機能に統一的に適用する |
| **なぜ今か** | MVP開発フェーズでUX改善が求められており、エディタ体験はコア機能（F5: アジェンダ自動生成）の入力インターフェースとして重要 |
| **なぜこれか** | Notion風UIが即座に利用可能、React専用設計、TypeScript完全対応、学習コストが最も低い |
| **既知の不確実性** | 1. バンドルサイズが大きめ（約150KB gzip、Shiki込みで約340KB、言語ファイル設定次第で500KB以上の可能性あり）<br>2. 深いカスタマイズにはTipTap/ProseMirrorの知識が必要になる可能性<br>3. **React 19 StrictMode非互換問題**（後述） |
| **撤回基準** | バンドルサイズがVercel無料枠の制限に影響する場合、React 19で本番環境に影響する互換性問題が発生した場合、またはReact 19 StrictMode対応がADR承認から6ヶ月以内に完了しない場合 |

### React 19 StrictMode互換性問題について

**現状**: BlockNoteはReact 19のStrictModeと非互換の問題が報告されている（[GitHub Issue #1021](https://github.com/TypeCellOS/BlockNote/issues/1021)）。v0.42.0で修正を試みたが失敗し、現在Issue #2106で追跡中。

**影響範囲**:
- **開発環境のみ**: StrictModeは開発時のみ有効な機能であり、本番ビルドでは無効化される
- **本番環境**: 影響なし（正常に動作）

**対策**:
- 開発時はStrictModeを無効化して対応
- BlockNoteチームが修正を進めており、将来的には解決される見込み

**判断根拠**:
- StrictModeは開発時のデバッグ支援機能であり、本番品質には影響しない
- 工数面でのBlockNoteの優位性（1-2日 vs 5-7日）は維持される
- TipTapでも一部Pro拡張でReact 19互換性問題が存在（tippyjs-react依存）

## 根拠

BlockNoteは「Notion風ブロックエディタ」を最小限の実装コストで実現できる唯一の選択肢である。TipTapやProseMirrorをベースにしつつも、スラッシュメニュー、フローティングツールバー、ドラッグ&ドロップなどのNotion風UIコンポーネントが標準で組み込まれており、即座に利用可能。

React専用設計のため、React 19のConcurrent FeaturesやServer Componentsとの統合も将来的に期待できる。TypeScriptの型安全性も「フルTypeScript互換性を前提に設計」と明言されており、カスタムスキーマ拡張時も型補完が効く。

### 検討した選択肢

#### 1. 選択肢A: TipTap（ProseMirrorベース）

**概要**: ProseMirrorの上に構築されたヘッドレスエディタフレームワーク。拡張機能ベースのアーキテクチャで高度なカスタマイズが可能。

- **メリット**:
  - 最も成熟したエコシステム（1,328+ npm依存プロジェクト）
  - 豊富な拡張ライブラリ（Core、Pro、Cloud）
  - リアルタイムコラボレーション機能が充実
  - Notion風テンプレートを公式提供
  - v2.10.0でReact 19を正式サポート（2024年11月）
- **デメリット**:
  - ヘッドレス設計のため、Notion風UIは自前実装が必要
  - 基本的なUI構築に相当な工数が発生
  - 一部機能（Pro/Cloud）は有料
  - TypeScriptサポートに一部問題報告あり（module augmentation関連）
  - Pro拡張の一部（drag-handle等）でtippyjs-react依存によるReact 19互換性問題あり
- **バンドルサイズ**: 約50-70KB gzip（基本拡張込み）
- **工数見積もり**: 5-7日（Notion風UI実装含む）

#### 2. 選択肢B: BlockNote（TipTapベース）【採用】

**概要**: TipTap/ProseMirrorをベースにしたReact専用のNotion風ブロックエディタ。UIコンポーネントが標準装備。

- **メリット**:
  - Notion風UIが即座に利用可能（スラッシュメニュー、フローティングツールバー、アニメーション）
  - React専用設計でReactエコシステムとの親和性が高い
  - TypeScript完全対応（カスタムスキーマ時も型安全）
  - 学習コストが最も低い
  - Yjs対応のリアルタイムコラボレーション機能
  - AI機能統合のサポートあり
- **デメリット**:
  - TipTapの上の抽象化レイヤーのため、深いカスタマイズは複雑
  - 比較的新しいライブラリ（エコシステムは成長中）
  - バンドルサイズが大きめ（言語ファイル設定次第で500KB以上になる可能性）
  - 一部機能（DOCX/PDFエクスポーター）はクローズドソース製品では有料
  - **React 19 StrictMode非互換（開発環境のみ影響、本番環境は正常動作）**
- **バンドルサイズ**: 約150KB gzip（Shiki込みで約340KB、言語設定により増加）
- **工数見積もり**: 1-2日

#### 3. 選択肢C: Plate（Slateベース）

**概要**: Slate.jsベースのモジュラーなリッチテキストエディタフレームワーク。shadcn/ui、Radix UIコンポーネントと統合。

- **メリット**:
  - 高いモジュール性と拡張性
  - shadcn/ui統合でデザインシステムとの親和性
  - Slateの柔軟なデータモデル
  - PlateStaticで読み取り専用時のバンドルサイズ削減可能
- **デメリット**:
  - 学習コストが高い（Slateの概念理解が必要）
  - Notion風UIは自前実装が必要
  - コラボレーション機能の実装が複雑
  - 完成度はTipTapより劣る
- **バンドルサイズ**: 約80KB gzip（Slate-react含む、読み取り専用時は約300KB）
- **工数見積もり**: 7-10日

#### 4. 選択肢D: Lexical（Meta製）

**概要**: Meta（Facebook）が開発・維持する軽量なエディタフレームワーク。Facebook、Instagram、WhatsApp等で実運用。

- **メリット**:
  - 最小バンドルサイズ（コア約22KB gzip）
  - 高パフォーマンス（Meta規模での実運用実績）
  - 独自のDOM reconcilerによる効率的な更新
  - 遅延読み込みによるパフォーマンス最適化が容易
- **デメリット**:
  - Notion風UIは完全に自前実装
  - ドキュメントが不十分
  - 装飾ノードがドキュメントを変更する設計上の制約
  - Yjsコラボレーションにルートノード名の制約あり
  - セットアップが複雑
- **バンドルサイズ**: 約22KB gzip（コアのみ）、プラグイン追加で増加
- **工数見積もり**: 10-15日

### 比較マトリクス

| 評価軸 | TipTap | BlockNote | Plate | Lexical |
|--------|--------|-----------|-------|---------|
| **Notion風WYSIWYG対応度** | 中（要実装） | 高（標準装備） | 中（要実装） | 低（要実装） |
| **React 19互換性** | 高（v2.10.0で正式対応、一部Pro拡張に問題あり） | 中（StrictMode非互換、本番環境は正常） | 高 | 高 |
| **TypeScript対応** | 中-高 | 高 | 高 | 中 |
| **バンドルサイズ** | 中（50-70KB） | 大（150KB+、設定次第で500KB+） | 中（80KB） | 小（22KB） |
| **メンテナンス状況** | 活発 | 活発 | 中程度 | 活発 |
| **カスタマイズ性** | 高 | 中 | 高 | 高 |
| **学習コスト** | 中 | 低 | 高 | 高 |
| **実装工数** | 5-7日 | 1-2日 | 7-10日 | 10-15日 |
| **総合評価** | ○ | ◎ | △ | △ |

### 選定理由の詳細

1. **即座にNotion風体験を提供**: BlockNoteはスラッシュメニュー、フローティングツールバー、ブロックのドラッグ&ドロップなどが標準装備されており、追加実装なしでNotionライクな体験を提供できる

2. **React専用設計**: 他のライブラリがフレームワーク非依存を目指す中、BlockNoteはReactに特化している。React 19のStrictMode問題は開発環境のみの影響であり、本番環境では正常に動作する

3. **TypeScript完全対応**: カスタムスキーマ拡張時も型安全性が保証される設計思想は、プロジェクトのTypeScript重視方針と合致

4. **学習・実装コストの低さ**: MVP開発フェーズでは迅速な価値検証が重要。1-2日で実装可能な点は大きなメリット

5. **将来の拡張性**: TipTap/ProseMirrorベースのため、より深いカスタマイズが必要になった場合も下位レイヤーにアクセス可能

## 影響

### ポジティブな影響

- **UX向上**: Notion風WYSIWYGにより、議事録・アジェンダ編集の体験が大幅に向上
- **実装工数削減**: UIコンポーネント標準装備により、1-2日で実装完了見込み
- **型安全性**: TypeScript完全対応により、開発効率とコード品質が向上
- **将来の拡張**: AI機能統合、リアルタイムコラボレーションへの拡張パスが明確
- **統一的なエディタ体験**: 議事録とアジェンダで同一ライブラリを使用することで一貫したUX

### ネガティブな影響

- **バンドルサイズ増加**: 約150KB（gzip）の追加。Shiki（コードブロック構文ハイライト）を含めると約340KB。言語ファイル設定次第では500KB以上になる可能性あり
  - 対策: 遅延読み込み、コードブロック機能の無効化検討、言語ファイルの最小化
- **抽象化レイヤーの増加**: TipTap/ProseMirrorの上に構築されているため、深いカスタマイズ時に複雑性が増す
- **依存関係の増加**: @blocknote/core、@blocknote/reactおよび間接依存が追加
- **開発時のStrictMode制約**: React 19 StrictMode非互換のため、開発時はStrictModeを無効化する必要がある

### 中立的な影響

- **マークダウンデータ形式**: BlockNoteは独自のブロックJSON形式を使用。マークダウンとの相互変換機能は提供されているが、保存形式の設計判断が必要
- **スタイリング**: BlockNote独自のCSSが適用されるが、Tailwind CSSとの共存は可能

## 実装指針

### ライブラリ導入方針

- `@blocknote/core`と`@blocknote/react`をインストール
- Mantine依存を避けるため、デフォルトテーマの上書きを検討
- 遅延読み込みを活用してパフォーマンスを最適化

### React 19 StrictMode対策

開発環境でのStrictMode非互換問題に対応するため、以下の設定を行う:

```typescript
// vite.config.ts または next.config.ts
// Viteの場合: main.tsxでStrictModeを削除または無効化
// Next.jsの場合:
const nextConfig = {
  reactStrictMode: false,
  // ... other config
};
```

**注意**: StrictModeは開発時のバグ検出支援機能であり、無効化しても本番品質には影響しない。BlockNoteチームがIssue #2106で修正を進めており、将来的には有効化できる見込み。

### エディタ設定方針

- スラッシュメニューとフローティングツールバーを有効化
- 必要最小限のブロックタイプのみ有効化（paragraph、heading、bulletList、numberedList）
- コードブロック機能はShikiのバンドルサイズを考慮して無効化を検討

### バンドルサイズ最適化

- 言語ファイルは使用する言語のみに限定（デフォルトで全言語が含まれる可能性あり）
- Shiki（構文ハイライト）は不要であれば無効化
- 動的インポートによる遅延読み込みを実装

### データ形式方針

- エディタ内部はBlockNote独自のJSON形式
- 保存時はマークダウン形式に変換（既存データとの互換性維持）
- 読み込み時はマークダウンからBlockNote形式に変換

### スタイリング方針

- Tailwind CSSとBlockNoteスタイルの共存
- 高さ調整はCSSカスタムプロパティまたはラッパーコンポーネントで対応
- ダークモード対応はBlockNote組み込み機能を活用

## 関連情報

- [ADR-0001: クリーンアーキテクチャ採用](./ADR-0001-clean-architecture-adoption.md)
- [BlockNote公式ドキュメント](https://www.blocknotejs.org/)
- [BlockNote GitHub](https://github.com/TypeCellOS/BlockNote)

## 参考資料

- [Which rich text editor framework should you choose in 2025? | Liveblocks blog](https://liveblocks.io/blog/which-rich-text-editor-framework-should-you-choose-in-2025)
- [Top Notion-Style WYSIWYG Editors for React - Wisp CMS](https://www.wisp.blog/blog/top-notion-style-wysiwyg-editors-for-react)
- [BlockNote vs. Tiptap: Simplicity Meets Full Control](https://tiptap.dev/alternatives/blocknote-vs-tiptap)
- [10 Best React WYSIWYG Rich Text Editors in 2026 (Open Source) - ReactScript](https://reactscript.com/best-rich-text-editor/)
- [Best Rich Text Editor for react in 2025 - DEV Community](https://dev.to/codeideal/best-rich-text-editor-for-react-in-2025-3cdb)
- [Bundlephobia - @tiptap/core](https://bundlephobia.com/package/@tiptap/core)
- [Introduction | Lexical](https://lexical.dev/docs/intro)
- [BlockNote - Custom Schemas](https://www.blocknotejs.org/docs/custom-schemas)
- [TypeScript | Tiptap Editor Docs](https://tiptap.dev/docs/guides/typescript)
- [Plate - Build your rich-text editor](https://platejs.org/)
- [BlockNote React 19 StrictMode Issue #1021](https://github.com/TypeCellOS/BlockNote/issues/1021)
- [BlockNote with Next.js - StrictMode workaround](https://www.blocknotejs.org/docs/getting-started/nextjs)
- [TipTap React 19 Support - v2.10.0](https://x.com/tiptap_editor/status/1859521072636326333)
- [TipTap React Installation Guide](https://tiptap.dev/docs/editor/getting-started/install/react)
