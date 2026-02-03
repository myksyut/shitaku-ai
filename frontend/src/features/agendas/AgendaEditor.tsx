/**
 * Agenda editor component with WYSIWYG markdown editing
 */
import { useState } from 'react'
import { MarkdownEditor } from '../../components/editor'
import { Button } from '../../components/ui'
import { useUpdateAgenda } from './hooks'
import type { Agenda } from './types'

interface Props {
  agenda: Agenda
  onSaved: () => void
  onCancel: () => void
}

export function AgendaEditor({ agenda, onSaved, onCancel }: Props) {
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
    onCancel()
  }

  return (
    <div>
      {/* WYSIWYG Markdown Editor */}
      <MarkdownEditor
        initialValue={content}
        onChange={setContent}
        minHeight={400}
        placeholder="アジェンダを入力してください..."
        readOnly={saved}
      />

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
          閉じる
        </Button>
        <Button variant="primary" onClick={handleSave} isLoading={updateMutation.isPending} disabled={saved}>
          保存する
        </Button>
      </div>
    </div>
  )
}
