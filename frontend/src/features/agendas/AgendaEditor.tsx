/**
 * Agenda editor component with preview and edit modes
 */
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button, Textarea } from '../../components/ui'
import { useUpdateAgenda } from './hooks'
import type { Agenda } from './types'

// 編集機能の有効/無効フラグ（将来的な再有効化のため保持）
const ENABLE_EDIT_MODE = false

interface Props {
  agenda: Agenda
  onSaved: () => void
  onCancel: () => void
}

export function AgendaEditor({ agenda, onSaved, onCancel }: Props) {
  const [isEditing, setIsEditing] = useState(false)
  const [content, setContent] = useState(agenda.content)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [copied, setCopied] = useState(false)

  const updateMutation = useUpdateAgenda()

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('コピーに失敗しました')
    }
  }

  const handleSave = async () => {
    setError(null)

    if (!content.trim()) {
      setError('アジェンダ内容は必須です')
      return
    }

    try {
      await updateMutation.mutateAsync({
        id: agenda.id,
        data: { content: content.trim() },
      })
      setSaved(true)
      setIsEditing(false)

      // 保存成功後に少し待ってから閉じる
      setTimeout(() => {
        onSaved()
      }, 1500)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
    }
  }

  const handleCancel = () => {
    if (isEditing) {
      setContent(agenda.content)
      setIsEditing(false)
    } else {
      onCancel()
    }
  }

  return (
    <div>
      {/* Mode Toggle */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-4)',
        }}
      >
        <div
          style={{
            display: 'flex',
            gap: 'var(--space-2)',
          }}
        >
          <button
            type="button"
            onClick={() => setIsEditing(false)}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              fontFamily: 'var(--font-family)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              transition: 'all var(--transition-fast)',
              background: !isEditing ? 'var(--color-primary-100)' : 'transparent',
              color: !isEditing ? 'var(--color-primary-700)' : 'var(--color-warm-gray-500)',
            }}
          >
            プレビュー
          </button>
          {ENABLE_EDIT_MODE && (
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              disabled={saved}
              style={{
                padding: 'var(--space-2) var(--space-4)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 600,
                fontFamily: 'var(--font-family)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: saved ? 'not-allowed' : 'pointer',
                transition: 'all var(--transition-fast)',
                background: isEditing ? 'var(--color-primary-100)' : 'transparent',
                color: isEditing ? 'var(--color-primary-700)' : 'var(--color-warm-gray-500)',
                opacity: saved ? 0.5 : 1,
              }}
            >
              編集
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={handleCopy}
          style={{
            padding: 'var(--space-2) var(--space-3)',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            fontFamily: 'var(--font-family)',
            border: '1px solid var(--color-cream-300)',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            transition: 'all var(--transition-fast)',
            background: copied ? 'var(--color-success-100)' : 'var(--color-cream-50)',
            color: copied ? 'var(--color-success-700)' : 'var(--color-warm-gray-600)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-1)',
          }}
        >
          {copied ? (
            <>
              <span>✓</span>
              コピー済み
            </>
          ) : (
            <>
              <span>📋</span>
              コピー
            </>
          )}
        </button>
      </div>

      {/* Content Area */}
      {isEditing ? (
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={16}
          placeholder="マークダウン形式でアジェンダを編集..."
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            fontSize: 'var(--font-size-sm)',
            lineHeight: 1.7,
          }}
        />
      ) : (
        <div
          className="markdown-preview"
          style={{
            padding: 'var(--space-5)',
            background: 'var(--color-cream-50)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-cream-300)',
            fontSize: 'var(--font-size-sm)',
            lineHeight: 1.8,
            maxHeight: '70vh',
            overflowY: 'auto',
            color: 'var(--color-warm-gray-700)',
          }}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => (
                <h1
                  style={{
                    fontSize: '1.5em',
                    fontWeight: 700,
                    marginBottom: '0.5em',
                    marginTop: '1em',
                    color: 'var(--color-warm-gray-900)',
                  }}
                >
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2
                  style={{
                    fontSize: '1.25em',
                    fontWeight: 600,
                    marginBottom: '0.5em',
                    marginTop: '1em',
                    color: 'var(--color-warm-gray-800)',
                  }}
                >
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3
                  style={{
                    fontSize: '1.1em',
                    fontWeight: 600,
                    marginBottom: '0.5em',
                    marginTop: '0.75em',
                    color: 'var(--color-warm-gray-800)',
                  }}
                >
                  {children}
                </h3>
              ),
              ul: ({ children }) => (
                <ul style={{ marginLeft: '1.5em', marginBottom: '0.75em', listStyleType: 'disc' }}>{children}</ul>
              ),
              ol: ({ children }) => (
                <ol style={{ marginLeft: '1.5em', marginBottom: '0.75em', listStyleType: 'decimal' }}>{children}</ol>
              ),
              li: ({ children }) => <li style={{ marginBottom: '0.25em' }}>{children}</li>,
              p: ({ children }) => <p style={{ marginBottom: '0.75em' }}>{children}</p>,
              strong: ({ children }) => (
                <strong style={{ fontWeight: 600, color: 'var(--color-warm-gray-900)' }}>{children}</strong>
              ),
              em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
              code: ({ children }) => (
                <code
                  style={{
                    background: 'var(--color-cream-200)',
                    padding: '0.125em 0.375em',
                    borderRadius: '4px',
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    fontSize: '0.875em',
                  }}
                >
                  {children}
                </code>
              ),
              pre: ({ children }) => (
                <pre
                  style={{
                    background: 'var(--color-cream-200)',
                    padding: '1em',
                    borderRadius: '8px',
                    overflow: 'auto',
                    marginBottom: '0.75em',
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    fontSize: '0.875em',
                  }}
                >
                  {children}
                </pre>
              ),
              table: ({ children }) => (
                <table
                  style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    marginBottom: '0.75em',
                  }}
                >
                  {children}
                </table>
              ),
              th: ({ children }) => (
                <th
                  style={{
                    border: '1px solid var(--color-cream-300)',
                    padding: '0.5em',
                    background: 'var(--color-cream-200)',
                    fontWeight: 600,
                    textAlign: 'left',
                  }}
                >
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td
                  style={{
                    border: '1px solid var(--color-cream-300)',
                    padding: '0.5em',
                    textAlign: 'left',
                  }}
                >
                  {children}
                </td>
              ),
              blockquote: ({ children }) => (
                <blockquote
                  style={{
                    borderLeft: '4px solid var(--color-primary-300)',
                    paddingLeft: '1em',
                    marginLeft: 0,
                    marginBottom: '0.75em',
                    color: 'var(--color-warm-gray-600)',
                    fontStyle: 'italic',
                  }}
                >
                  {children}
                </blockquote>
              ),
              hr: () => (
                <hr
                  style={{
                    border: 'none',
                    borderTop: '1px solid var(--color-cream-300)',
                    marginTop: '1em',
                    marginBottom: '1em',
                  }}
                />
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="alert alert-error animate-fade-in" style={{ marginTop: 'var(--space-4)' }}>
          {error}
        </div>
      )}

      {/* Success */}
      {saved && (
        <div className="alert alert-success animate-fade-in" style={{ marginTop: 'var(--space-4)' }}>
          <span style={{ marginRight: 'var(--space-2)' }}>🎉</span>
          アジェンダを保存しました！
        </div>
      )}

      {/* Actions */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 'var(--space-3)',
          marginTop: 'var(--space-6)',
          paddingTop: 'var(--space-4)',
          borderTop: '1px solid var(--color-cream-300)',
        }}
      >
        <Button variant="secondary" onClick={handleCancel} disabled={updateMutation.isPending}>
          {isEditing ? 'キャンセル' : '閉じる'}
        </Button>
        {isEditing && (
          <Button variant="primary" onClick={handleSave} isLoading={updateMutation.isPending} disabled={saved}>
            保存する
          </Button>
        )}
      </div>
    </div>
  )
}
