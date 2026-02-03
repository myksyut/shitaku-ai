// MarkdownEditor Integration Test - Design Doc: markdown-editor-ux-improvement.md
// Generated: 2026-02-03 | Quota: 3/3 integration, 1/2 E2E
/**
 * MarkdownEditor WYSIWYG Integration Test
 *
 * Test Target: BlockNote-based MarkdownEditor Component
 * - Data conversion (Markdown <-> BlockNote)
 * - AgendaEditor integration
 * - MeetingNoteUpload integration
 */

import { describe, it } from 'vitest'

describe('MarkdownEditor Integration Test', () => {
  // AC: "When 保存ボタンがクリックされると、エディタ内容がマークダウン形式に変換されて保存される"
  // AC: "When 既存のマークダウンデータを読み込むと、BlockNote形式に変換されてエディタに表示される"
  // ROI: 99 | Business Value: 10 | Frequency: 10
  // Behavior: Markdown input -> BlockNote display -> User edits -> Save button -> Markdown output
  // @category: core-functionality
  // @dependency: MarkdownEditor, blocksToMarkdown, markdownToBlocks
  // @complexity: high
  //
  // Verification:
  //   - initialValue (Markdown) is correctly converted and displayed
  //   - onChange callback receives valid Markdown string
  //   - Basic formats preserved: headings (h1-h3), bold, bullet list, numbered list
  it.todo('AC-DataConversion: Markdown is correctly converted bidirectionally')

  // AC: "When アジェンダ編集画面を開くと、BlockNoteエディタが表示される"
  // AC: "When 「保存する」ボタンをクリックすると、マークダウン形式で保存される"
  // ROI: 99 | Business Value: 10 | Frequency: 10
  // Behavior: AgendaEditor mounts -> MarkdownEditor renders -> User edits -> Save -> API receives Markdown
  // @category: integration
  // @dependency: AgendaEditor, MarkdownEditor, useUpdateAgenda hook
  // @complexity: high
  //
  // Verification:
  //   - MarkdownEditor is rendered within AgendaEditor
  //   - data-testid="markdown-editor" is present
  //   - Save button triggers onSave with Markdown format
  //   - No preview/edit mode toggle exists (WYSIWYG)
  it.todo('AC-AgendaEditor: BlockNote editor displays and saves in Markdown format')

  // AC: "When 議事録アップロードフォームを開くと、BlockNoteエディタが表示される"
  // AC: "When 「アップロード」ボタンをクリックすると、マークダウン形式で送信される"
  // ROI: 90 | Business Value: 10 | Frequency: 9
  // Behavior: MeetingNoteUpload mounts -> MarkdownEditor renders -> User inputs -> Upload -> API receives Markdown
  // @category: integration
  // @dependency: MeetingNoteUpload, MarkdownEditor, useUploadMeetingNote hook
  // @complexity: high
  //
  // Verification:
  //   - MarkdownEditor is rendered within MeetingNoteUpload
  //   - data-testid="markdown-editor" is present
  //   - Upload button triggers API call with Markdown content
  //   - Content is not empty when submitted
  it.todo('AC-MeetingNoteUpload: BlockNote editor displays and uploads in Markdown format')
})
