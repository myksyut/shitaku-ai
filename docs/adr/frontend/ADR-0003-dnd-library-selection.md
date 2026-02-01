# ADR-0003: ドラッグ&ドロップライブラリ選定

## ステータス

**Proposed**

## 経緯

Shitaku.aiのアジェンダ編集機能では、ユーザーがアジェンダ項目をドラッグ&ドロップで並べ替え、複数リスト間（「今回話す」「次回に回す」「保留」）で移動できる必要がある。現在のAgendaEditorはテキストエリアベースの編集UIであり、ドラッグ&ドロップ機能は未実装。

PRDの要件:
- 1つのリスト内での並べ替え
- 複数リスト間での項目移動
- ドラッグ中のビジュアルフィードバック（影、ハイライト）
- WCAG 2.1 AA準拠（キーボード操作による代替）
- バンドルサイズ増加: 現状比+50KB以内

技術的制約:
- React 19.2.0環境
- Tailwind CSS v4でのスタイリング
- コストゼロ運用（無料ライブラリのみ）

## 決定事項

**dnd-kit（@dnd-kit/react + @dnd-kit/helpers）を採用する。**

### 決定の詳細

| 項目 | 内容 |
|-----|-----|
| **決定** | dnd-kit（@dnd-kit/react 0.2.x + @dnd-kit/helpers）を使用してドラッグ&ドロップ機能を実装 |
| **なぜ今か** | アジェンダ編集のUX改善がPRD要件であり、テキストエリア編集からDnD UIへの移行が必要 |
| **なぜこれか** | 軽量（約10KB gzip）、React 19対応進行中、アクセシビリティ機能内蔵、メンテナンスが活発 |
| **既知の不確実性** | @dnd-kit/react 0.2.xはReact 19対応が進行中だが、Server Component使用時に`"use client"`ディレクティブ追加が必要になる可能性あり（[GitHub Issue #1654](https://github.com/clauderic/dnd-kit/issues/1654)） |
| **撤回基準** | React 19との重大な互換性問題が発生し、修正が3ヶ月以内に提供されない場合 |
| **ワークアラウンド** | Server Component互換性問題発生時: (1) DnDコンポーネントに`"use client"`ディレクティブを手動追加、(2) 問題解消しない場合は@dnd-kit/core 6.3.1へダウングレード |

## 根拠

### 検討した選択肢

#### 選択肢A: react-beautiful-dnd

- **概要**: Atlassianが開発した人気のDnDライブラリ
- **メリット**:
  - 豊富なドキュメントと事例
  - 複数リスト間移動の優れたサポート
  - アニメーションが美しい
- **デメリット**:
  - **メンテナンス終了**（Atlassianがpragmatic-drag-and-dropへ移行）
  - React 18以降の公式サポートなし
  - バンドルサイズが大きい（約30KB gzip）
  - StrictModeとの互換性問題

#### 選択肢B: @atlaskit/pragmatic-drag-and-drop

- **概要**: Atlassianが開発したreact-beautiful-dndの後継
- **メリット**:
  - Atlassianによるアクティブなメンテナンス
  - フレームワーク非依存（React/Vue/Vanilla JS対応）
  - 軽量かつモジュラー設計
- **デメリット**:
  - 比較的新しく、コミュニティリソースが限定的
  - React固有の最適化がdnd-kitより少ない
  - アクセシビリティは別途実装が必要

#### 選択肢C: dnd-kit（採用）

- **概要**: モダンで軽量なReact専用DnDツールキット
- **メリット**:
  - **軽量**: @dnd-kit/core約10KB gzip、新API（@dnd-kit/react）はさらに軽量
  - **React 19対応**: @dnd-kit/react 0.2.xでReact 19サポート進行中
  - **アクセシビリティ内蔵**: キーボード操作、スクリーンリーダー対応が標準機能
  - **複数コンテナ対応**: SortableContextで複数リスト間移動をサポート
  - **カスタマイズ性**: センサー、アニメーション、衝突検出アルゴリズムを柔軟に設定
  - **アクティブメンテナンス**: 定期的なアップデートとバグ修正
  - **ゼロ依存**: 外部依存なし
- **デメリット**:
  - @dnd-kit/react 0.2.xはまだ成熟途上（APIが安定していない可能性）
  - 複雑なカスタマイズには学習コストあり

#### 選択肢D: ネイティブHTML5 Drag and Drop API

- **概要**: ブラウザ標準のDnD APIを直接使用
- **メリット**:
  - 追加依存ゼロ
  - バンドルサイズ増加なし
  - ブラウザネイティブのパフォーマンス
- **デメリット**:
  - 複数リスト間移動の実装が複雑
  - モバイルタッチデバイスでの挙動が不安定
  - アクセシビリティの自前実装が必要
  - ドラッグプレビューのカスタマイズが困難
  - 実装工数が大幅に増加

## 比較マトリクス

| 評価軸 | react-beautiful-dnd | pragmatic-dnd | dnd-kit | Native API |
|--------|---------------------|---------------|---------|------------|
| バンドルサイズ | ~30KB | ~15KB | ~10KB | 0 |
| React 19対応 | 非対応 | 対応 | 対応(進行中) | N/A |
| アクセシビリティ | 内蔵 | 要実装 | 内蔵 | 要実装 |
| 複数リスト対応 | 優秀 | 良好 | 優秀 | 要実装 |
| メンテナンス状況 | 終了 | 活発 | 活発 | N/A |
| 学習コスト | 低 | 中 | 中 | 高 |
| 実装工数 | 低 | 中 | 低 | 高 |
| WCAG 2.1 AA対応 | 部分的 | 要実装 | 標準対応 | 要実装 |

## 影響

### ポジティブな影響

- WCAG 2.1 AA準拠のキーボード操作とスクリーンリーダー対応が標準で実現
- 軽量でバンドルサイズ増加を+50KB以内に抑制
- 複数リスト間のアジェンダ項目移動がスムーズに実装可能
- カスタムアニメーションとビジュアルフィードバックの実装が容易

### ネガティブな影響

- @dnd-kit/react 0.2.xはまだ成熟途上のためAPIが変更される可能性
- 既存のAgendaEditorコンポーネントの大幅な書き換えが必要
- dnd-kit固有の概念（センサー、衝突検出等）の学習が必要

### 中立的な影響

- package.jsonに新しい依存（@dnd-kit/react, @dnd-kit/helpers）が追加

## 実装指針

### アーキテクチャ方針

1. **DragDropProviderの配置**: アジェンダ編集画面のルートにDragDropProviderを配置
2. **Sortable実装**: 各リスト内のアジェンダ項目をSortableコンポーネントでラップ
3. **複数リスト対応**: useSortable hookとカスタムcollision detectionで複数コンテナ間移動を実装

### アクセシビリティ対応

1. **キーボード操作**:
   - Space/Enterでドラッグ開始
   - 矢印キーで移動
   - Escapeでキャンセル
2. **スクリーンリーダー**:
   - カスタムannouncements（日本語）を設定
   - ライブリージョンで状態変化を通知
3. **代替操作**:
   - 「上へ/下へ移動」ボタンをキーボード操作の代替として提供（WCAG 2.2 2.5.7対応）

### センサー設定

- PointerSensor: マウス/タッチ操作
- KeyboardSensor: キーボード操作

### 状態管理

- アジェンダ項目の順序と所属リストはコンポーネントローカルStateで管理
- 保存時にAPIへ送信

## 関連情報

- [PRD: フロントエンドUIデザイン全面刷新](../../prd/ui-design-refresh.md)
- [ADR-0002: デザインシステム基盤アーキテクチャ](./ADR-0002-design-system-architecture.md)
- [dnd-kit公式ドキュメント](https://docs.dndkit.com)
- [dnd-kit GitHubリポジトリ](https://github.com/clauderic/dnd-kit)

## References

- [dnd-kit Official Documentation](https://docs.dndkit.com) - 公式ドキュメント
- [@dnd-kit/react npm Package](https://www.npmjs.com/package/@dnd-kit/react) - 最新バージョン情報
- [dnd-kit Accessibility Guide](https://docs.dndkit.com/guides/accessibility) - アクセシビリティ実装ガイド
- [dnd-kit Keyboard Sensor Documentation](https://docs.dndkit.com/api-documentation/sensors/keyboard) - キーボードセンサー設定
- [dnd-kit Migration Guide](https://next.dndkit.com/react/guides/migration) - 新APIへの移行ガイド
- [WCAG 2.2 Success Criterion 2.5.7: Dragging Movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html) - ドラッグ操作のアクセシビリティ要件
- [WCAG 2.1 Success Criterion 2.1.1: Keyboard](https://www.w3.org/WAI/WCAG21/Understanding/keyboard.html) - キーボードアクセシビリティ要件
