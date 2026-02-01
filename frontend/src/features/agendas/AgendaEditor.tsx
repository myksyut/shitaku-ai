/**
 * Agenda editor component with preview and edit modes
 */
import { useState } from 'react'
import { Button, Textarea } from '../../components/ui'
import { useUpdateAgenda } from './hooks'
import type { Agenda } from './types'

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

  const updateMutation = useUpdateAgenda()

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
        </div>
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
          style={{
            padding: 'var(--space-5)',
            background: 'var(--color-cream-50)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-cream-300)',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            fontSize: 'var(--font-size-sm)',
            lineHeight: 1.8,
            whiteSpace: 'pre-wrap',
            maxHeight: '400px',
            overflowY: 'auto',
            color: 'var(--color-warm-gray-700)',
          }}
        >
          {content}
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
