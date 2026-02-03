import '@blocknote/core/fonts/inter.css'
import '@blocknote/react/style.css'

import { BlockNoteViewRaw, useCreateBlockNote } from '@blocknote/react'
import { useCallback, useEffect } from 'react'

export interface MarkdownEditorProps {
  /** 初期値（マークダウン形式） */
  initialValue?: string
  /** 変更時コールバック */
  onChange?: (markdown: string) => void
  /** プレースホルダーテキスト */
  placeholder?: string
  /** 最小高さ（px） */
  minHeight?: number
  /** 読み取り専用モード */
  readOnly?: boolean
}

export const MarkdownEditor = ({
  initialValue,
  onChange,
  placeholder,
  minHeight = 400,
  readOnly = false,
}: MarkdownEditorProps) => {
  const editor = useCreateBlockNote({
    domAttributes: {
      editor: {
        'data-testid': 'blocknote-editor',
      },
    },
  })

  // 初期値の読み込み
  useEffect(() => {
    if (initialValue && editor) {
      const loadInitialContent = async () => {
        try {
          const blocks = await editor.tryParseMarkdownToBlocks(initialValue)
          editor.replaceBlocks(editor.document, blocks)
        } catch (error) {
          console.error('Failed to parse markdown:', error)
        }
      }
      loadInitialContent()
    }
  }, [initialValue, editor])

  // 変更時のコールバック
  const handleChange = useCallback(async () => {
    if (onChange && editor) {
      try {
        const markdown = await editor.blocksToMarkdownLossy(editor.document)
        onChange(markdown)
      } catch (error) {
        console.error('Failed to convert to markdown:', error)
      }
    }
  }, [onChange, editor])

  return (
    <div data-testid="markdown-editor" style={{ minHeight: `${minHeight}px` }} className="markdown-editor-container">
      <BlockNoteViewRaw editor={editor} editable={!readOnly} onChange={handleChange} data-placeholder={placeholder} />
    </div>
  )
}
