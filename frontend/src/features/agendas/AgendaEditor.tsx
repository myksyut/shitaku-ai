/**
 * Agenda editor component with preview and edit modes
 */

import { useState } from 'react'
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
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-medium">{isEditing ? '編集モード' : 'プレビュー'}</h3>
        {!isEditing && !saved && (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="text-sm text-blue-500 hover:text-blue-600"
          >
            編集する
          </button>
        )}
      </div>

      {isEditing ? (
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="w-full border rounded px-3 py-2 font-mono text-sm"
          rows={20}
          placeholder="マークダウン形式でアジェンダを編集..."
        />
      ) : (
        <div className="border rounded p-4 bg-gray-50 whitespace-pre-wrap font-mono text-sm max-h-96 overflow-y-auto">
          {content}
        </div>
      )}

      {error && <div className="text-red-500 text-sm bg-red-50 p-3 rounded">{error}</div>}

      {saved && <div className="text-green-800 text-sm bg-green-50 p-3 rounded">アジェンダを保存しました！</div>}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={handleCancel}
          className="px-4 py-2 border rounded hover:bg-gray-50"
          disabled={updateMutation.isPending}
        >
          {isEditing ? 'キャンセル' : '閉じる'}
        </button>
        {isEditing && (
          <button
            type="button"
            onClick={handleSave}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            disabled={updateMutation.isPending || saved}
          >
            {updateMutation.isPending ? '保存中...' : '保存'}
          </button>
        )}
      </div>
    </div>
  )
}
