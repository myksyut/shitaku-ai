// Meeting Notes Integration Test - Design Doc: mvp-core-features.md
// Generated: 2026-01-31 | Quota: 2/3 integration, 0/2 E2E
/**
 * 議事録アップロード + 正規化機能のフロントエンド統合テスト
 *
 * テスト対象: F3 議事録アップロード + 正規化
 * - テキストアップロードフォームとAPI連携
 * - 正規化前後の比較表示
 * - エラー時のフォールバック表示
 */

import { describe, it } from 'vitest'

describe('Meeting Notes Integration Test', () => {
  // AC: "When ユーザーがエージェントを選択して議事録テキストをアップロードすると、
  //      システムは辞書を参照して固有名詞を正規化し、DBに保存する"
  // Property: `meeting_notes.count == previous_count + 1`
  // ROI: 99/11 = 9.0 | ビジネス価値: 10 | 頻度: 9
  // 振る舞い: エージェント選択+テキスト入力 -> アップロード -> 正規化結果表示
  // @category: core-functionality
  // @dependency: MeetingNoteForm, NormalizationPreview, useUploadMeetingNote hook, API Client
  // @complexity: high
  //
  // 検証項目:
  // - テキストアップロードでAPI呼び出しが実行される
  // - 成功レスポンス後、正規化プレビューが表示される
  // - original_textとnormalized_textの差分が視覚的に表示される
  // - 議事録一覧が更新される
  it.todo('AC1: 議事録アップロードで正規化結果がプレビュー表示される')

  // AC: "If 正規化処理でLLM APIエラーが発生した場合、
  //      then システムは元テキストをそのまま保存し、ユーザーに警告を表示する"
  // ROI: 27/11 = 2.5 | ビジネス価値: 9 | 頻度: 2
  // 振る舞い: テキストアップロード -> LLMエラー -> 元テキスト保存 -> 警告表示
  // @category: edge-case
  // @dependency: MeetingNoteForm, WarningAlert, useUploadMeetingNote hook
  // @complexity: medium
  //
  // 検証項目:
  // - LLMエラー時に警告メッセージが表示される
  // - 元テキストが保存されていることが表示される
  // - 議事録一覧に追加される（エラーでも保存成功）
  it.todo('AC3: LLMエラー時に警告メッセージと元テキスト保存が表示される')
})
