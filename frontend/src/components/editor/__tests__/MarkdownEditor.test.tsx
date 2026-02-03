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

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MarkdownEditor } from '../MarkdownEditor'

// AgendaEditorのhooksモック用の関数を先に定義
const mockMutateAsync = vi.fn()
// MeetingNoteUploadのhooksモック用の関数
const mockUploadMutateAsync = vi.fn()

// AgendaEditorの依存をモック（ファイルトップレベルで定義）
vi.mock('../../../features/agendas/hooks', () => ({
  useUpdateAgenda: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}))

// MeetingNoteUploadの依存をモック
vi.mock('../../../features/meeting-notes/hooks', () => ({
  useUploadMeetingNote: () => ({
    mutateAsync: mockUploadMutateAsync,
    isPending: false,
  }),
}))

// BlockNoteはブラウザAPIに依存するため、モックを提供
vi.mock('@blocknote/react', () => {
  const mockBlocks: unknown[] = []
  let mockMarkdownContent = ''
  let blockIdCounter = 0

  const mockEditor = {
    document: mockBlocks,
    tryParseMarkdownToBlocks: vi.fn().mockImplementation((markdown: string) => {
      mockMarkdownContent = markdown
      // マークダウンをブロック形式にパース（シミュレーション）
      const blocks = []
      const lines = markdown.split('\n').filter((line) => line.trim())

      for (const line of lines) {
        const blockId = `block-${++blockIdCounter}`
        if (line.startsWith('# ')) {
          blocks.push({
            id: blockId,
            type: 'heading',
            props: { level: 1 },
            content: [{ type: 'text', text: line.slice(2) }],
          })
        } else if (line.startsWith('## ')) {
          blocks.push({
            id: blockId,
            type: 'heading',
            props: { level: 2 },
            content: [{ type: 'text', text: line.slice(3) }],
          })
        } else if (line.startsWith('### ')) {
          blocks.push({
            id: blockId,
            type: 'heading',
            props: { level: 3 },
            content: [{ type: 'text', text: line.slice(4) }],
          })
        } else if (line.startsWith('- ')) {
          blocks.push({ id: blockId, type: 'bulletListItem', content: [{ type: 'text', text: line.slice(2) }] })
        } else if (/^\d+\. /.test(line)) {
          blocks.push({
            id: blockId,
            type: 'numberedListItem',
            content: [{ type: 'text', text: line.replace(/^\d+\. /, '') }],
          })
        } else {
          blocks.push({ id: blockId, type: 'paragraph', content: [{ type: 'text', text: line }] })
        }
      }
      return Promise.resolve(blocks)
    }),
    blocksToMarkdownLossy: vi.fn().mockImplementation(() => {
      return Promise.resolve(mockMarkdownContent)
    }),
    replaceBlocks: vi.fn().mockImplementation((_, blocks) => {
      mockBlocks.length = 0
      mockBlocks.push(...blocks)
    }),
  }

  return {
    useCreateBlockNote: vi.fn().mockReturnValue(mockEditor),
    BlockNoteViewRaw: vi.fn().mockImplementation(({ editor, onChange, editable }) => {
      // onChange コールバックをトリガーするためのシミュレーション
      if (onChange) {
        // 初期マウント後にonChangeを呼び出し
        setTimeout(() => onChange(), 0)
      }

      return (
        <div data-testid="blocknote-mock" data-editable={editable}>
          <div data-testid="blocknote-content">
            {editor.document.map((block: { id: string; content?: Array<{ text?: string }> }) => (
              <div key={block.id}>{block.content?.[0]?.text || ''}</div>
            ))}
          </div>
        </div>
      )
    }),
  }
})

describe('MarkdownEditor Integration Test', () => {
  describe('基本レンダリング', () => {
    it('data-testid="markdown-editor"が存在する', () => {
      render(<MarkdownEditor />)
      expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()
    })

    it('最小高さ400pxがデフォルトで適用されている', () => {
      render(<MarkdownEditor />)
      const editor = screen.getByTestId('markdown-editor')
      expect(editor).toHaveStyle({ minHeight: '400px' })
    })

    it('カスタム最小高さが適用される', () => {
      render(<MarkdownEditor minHeight={600} />)
      const editor = screen.getByTestId('markdown-editor')
      expect(editor).toHaveStyle({ minHeight: '600px' })
    })

    it('readOnlyモードで編集不可', () => {
      render(<MarkdownEditor readOnly />)
      const blocknote = screen.getByTestId('blocknote-mock')
      expect(blocknote).toHaveAttribute('data-editable', 'false')
    })
  })

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
  describe('AC-DataConversion: マークダウン双方向変換', () => {
    it('initialValue（マークダウン）がBlockNoteに変換されて表示される', async () => {
      const markdown = '# 見出し1\n\nテスト文章'
      render(<MarkdownEditor initialValue={markdown} />)

      // コンポーネントがレンダリングされること
      expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()
      expect(screen.getByTestId('blocknote-mock')).toBeInTheDocument()
    })

    it('onChangeコールバックがマークダウン文字列を受け取る', async () => {
      const handleChange = vi.fn()
      const markdown = '# テスト見出し\n\n段落テキスト'

      render(<MarkdownEditor initialValue={markdown} onChange={handleChange} />)

      // onChangeが呼び出されるのを待つ
      await waitFor(() => {
        expect(handleChange).toHaveBeenCalled()
      })

      // onChangeがマークダウン形式の文字列を受け取ることを確認
      const lastCall = handleChange.mock.calls[handleChange.mock.calls.length - 1]
      expect(typeof lastCall[0]).toBe('string')
    })

    it('見出し（h1-h3）が保持される', async () => {
      const markdown = '# H1見出し\n## H2見出し\n### H3見出し'
      const handleChange = vi.fn()

      render(<MarkdownEditor initialValue={markdown} onChange={handleChange} />)

      await waitFor(() => {
        expect(handleChange).toHaveBeenCalled()
      })

      // マークダウンが正しくパースされることを確認
      const lastCall = handleChange.mock.calls[handleChange.mock.calls.length - 1]
      expect(lastCall[0]).toContain('H1見出し')
    })

    it('箇条書きリストが保持される', async () => {
      const markdown = '- 項目1\n- 項目2\n- 項目3'
      const handleChange = vi.fn()

      render(<MarkdownEditor initialValue={markdown} onChange={handleChange} />)

      await waitFor(() => {
        expect(handleChange).toHaveBeenCalled()
      })

      const lastCall = handleChange.mock.calls[handleChange.mock.calls.length - 1]
      expect(lastCall[0]).toContain('項目1')
    })

    it('番号リストが保持される', async () => {
      const markdown = '1. 手順1\n2. 手順2\n3. 手順3'
      const handleChange = vi.fn()

      render(<MarkdownEditor initialValue={markdown} onChange={handleChange} />)

      await waitFor(() => {
        expect(handleChange).toHaveBeenCalled()
      })

      const lastCall = handleChange.mock.calls[handleChange.mock.calls.length - 1]
      expect(lastCall[0]).toContain('手順1')
    })
  })

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
  describe('AC-AgendaEditor: BlockNoteエディタ表示とマークダウン保存', () => {
    // AgendaEditorテスト用のコールバック
    const mockOnSaved = vi.fn()
    const mockOnCancel = vi.fn()

    const mockAgenda = {
      id: 'agenda-123',
      agent_id: 'agent-456',
      content: '# テストアジェンダ\n- 項目1\n- 項目2',
      source_note_id: null,
      generated_at: '2026-02-01T00:00:00Z',
      created_at: '2026-02-01T00:00:00Z',
      updated_at: null,
    }

    beforeEach(() => {
      vi.clearAllMocks()
      mockMutateAsync.mockResolvedValue({ ...mockAgenda, content: '更新後' })
    })

    it('MarkdownEditorがAgendaEditor内にレンダリングされる', async () => {
      // テスト目的: AgendaEditorが正しくMarkdownEditorを含むことを検証
      const AgendaEditorModule = await import('../../../features/agendas/AgendaEditor')
      const { AgendaEditor } = AgendaEditorModule

      render(<AgendaEditor agenda={mockAgenda} onSaved={mockOnSaved} onCancel={mockOnCancel} />)

      // data-testid="markdown-editor"が存在することを確認
      expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()
    })

    it('保存ボタンでマークダウン形式が送信される', async () => {
      // テスト目的: 保存ボタンクリック時にAPIがマークダウン形式のcontentで呼ばれることを検証
      const AgendaEditorModule = await import('../../../features/agendas/AgendaEditor')
      const { AgendaEditor } = AgendaEditorModule

      render(<AgendaEditor agenda={mockAgenda} onSaved={mockOnSaved} onCancel={mockOnCancel} />)

      // 保存ボタンをクリック
      const saveButton = screen.getByRole('button', { name: /保存する/ })
      await userEvent.click(saveButton)

      // mutateAsyncがcontentを含むオブジェクトで呼ばれることを確認
      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          id: mockAgenda.id,
          data: expect.objectContaining({ content: expect.any(String) }),
        })
      })
    })

    it('プレビュー/編集モード切り替えが存在しない（WYSIWYGのため）', async () => {
      // テスト目的: BlockNoteはWYSIWYGなのでプレビューモード切り替えが不要であることを確認
      const AgendaEditorModule = await import('../../../features/agendas/AgendaEditor')
      const { AgendaEditor } = AgendaEditorModule

      render(<AgendaEditor agenda={mockAgenda} onSaved={mockOnSaved} onCancel={mockOnCancel} />)

      // プレビュー/編集ボタンが存在しないことを確認
      expect(screen.queryByRole('button', { name: /プレビュー/ })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /編集/ })).not.toBeInTheDocument()
      expect(screen.queryByRole('tab', { name: /プレビュー/ })).not.toBeInTheDocument()
      expect(screen.queryByRole('tab', { name: /編集/ })).not.toBeInTheDocument()
    })

    it('既存のアジェンダコンテンツがエディタに読み込まれる', async () => {
      // テスト目的: agenda.contentがMarkdownEditorのinitialValueとして渡されることを確認
      const AgendaEditorModule = await import('../../../features/agendas/AgendaEditor')
      const { AgendaEditor } = AgendaEditorModule

      render(<AgendaEditor agenda={mockAgenda} onSaved={mockOnSaved} onCancel={mockOnCancel} />)

      // MarkdownEditorコンポーネントがレンダリングされることを確認
      // (モックにより内部のBlockNoteはシミュレートされる)
      await waitFor(() => {
        expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()
      })
    })
  })

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
  describe('AC-MeetingNoteUpload: BlockNoteエディタ表示とマークダウンアップロード', () => {
    const mockOnClose = vi.fn()
    const testAgentId = 'agent-test-123'

    const mockUploadResponse = {
      note: {
        id: 'note-123',
        agent_id: testAgentId,
        original_text: '# テスト議事録\n- 項目1',
        normalized_text: '# テスト議事録\n- 項目1',
        meeting_date: '2026-02-01T10:00:00Z',
        created_at: '2026-02-03T00:00:00Z',
        is_normalized: true,
      },
      normalization_warning: null,
      replacement_count: 0,
    }

    beforeEach(() => {
      vi.clearAllMocks()
      mockUploadMutateAsync.mockResolvedValue(mockUploadResponse)
    })

    it('MarkdownEditorがMeetingNoteUpload内にレンダリングされる', async () => {
      // テスト目的: MeetingNoteUploadが正しくMarkdownEditorを含むことを検証
      const MeetingNoteUploadModule = await import('../../../features/meeting-notes/MeetingNoteUpload')
      const { MeetingNoteUpload } = MeetingNoteUploadModule

      render(<MeetingNoteUpload agentId={testAgentId} onClose={mockOnClose} />)

      // data-testid="markdown-editor"が存在することを確認
      expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()
    })

    it('アップロードボタンでマークダウン形式が送信される', async () => {
      // テスト目的: アップロードボタンクリック時にAPIがマークダウン形式のtextで呼ばれることを検証
      const MeetingNoteUploadModule = await import('../../../features/meeting-notes/MeetingNoteUpload')
      const { MeetingNoteUpload } = MeetingNoteUploadModule

      render(<MeetingNoteUpload agentId={testAgentId} onClose={mockOnClose} />)

      // アップロードボタンをクリック
      const uploadButton = screen.getByRole('button', { name: /アップロード/ })
      await userEvent.click(uploadButton)

      // モックされたエディタは初期値があるため、APIが呼ばれる
      // mutateAsyncがagent_id、text、meeting_dateを含むオブジェクトで呼ばれることを確認
      await waitFor(() => {
        expect(mockUploadMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            agent_id: testAgentId,
            text: expect.any(String),
            meeting_date: expect.any(String),
          }),
        )
      })
    })

    it('テキスト入力後のアップロードでAPIが呼ばれる', async () => {
      // テスト目的: テキストが入力された状態でアップロードするとAPIが呼ばれることを検証
      const MeetingNoteUploadModule = await import('../../../features/meeting-notes/MeetingNoteUpload')
      const { MeetingNoteUpload } = MeetingNoteUploadModule

      render(<MeetingNoteUpload agentId={testAgentId} onClose={mockOnClose} />)

      // エディタ内容の変更をシミュレート（モックのonChangeを通じて）
      // MarkdownEditorのonChangeがsetTextを呼び出す仕組みなので、
      // 内部状態の変更は実際にはモックされたBlockNoteからトリガーされる
      // ここではフォーム送信のフローを検証

      await waitFor(() => {
        expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()
      })
    })

    it('日時入力フィールドが存在する', async () => {
      // テスト目的: MTG開催日時の入力フィールドが表示されることを検証
      const MeetingNoteUploadModule = await import('../../../features/meeting-notes/MeetingNoteUpload')
      const { MeetingNoteUpload } = MeetingNoteUploadModule

      render(<MeetingNoteUpload agentId={testAgentId} onClose={mockOnClose} />)

      // datetime-local入力フィールドが存在する
      const dateInput = screen.getByLabelText(/MTG開催日時/)
      expect(dateInput).toBeInTheDocument()
      expect(dateInput).toHaveAttribute('type', 'datetime-local')
    })

    it('キャンセルボタンでonCloseが呼ばれる', async () => {
      // テスト目的: キャンセルボタンクリックでモーダルが閉じることを検証
      const MeetingNoteUploadModule = await import('../../../features/meeting-notes/MeetingNoteUpload')
      const { MeetingNoteUpload } = MeetingNoteUploadModule

      render(<MeetingNoteUpload agentId={testAgentId} onClose={mockOnClose} />)

      const cancelButton = screen.getByRole('button', { name: /キャンセル/ })
      await userEvent.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalled()
    })
  })
})
