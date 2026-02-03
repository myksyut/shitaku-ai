/**
 * Meeting note upload form component
 */

import { useState } from 'react'
import { useUploadMeetingNote } from './hooks'

interface Props {
  agentId: string
  onClose: () => void
}

export function MeetingNoteUpload({ agentId, onClose }: Props) {
  const [text, setText] = useState('')
  const [meetingDate, setMeetingDate] = useState(() => {
    const now = new Date()
    return now.toISOString().slice(0, 16) // YYYY-MM-DDTHH:mm format
  })
  const [error, setError] = useState<string | null>(null)
  const [uploadResult, setUploadResult] = useState<{
    warning: string | null
    replacementCount: number
  } | null>(null)

  const uploadMutation = useUploadMeetingNote()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setUploadResult(null)

    if (!text.trim()) {
      setError('議事録テキストは必須です')
      return
    }

    try {
      const result = await uploadMutation.mutateAsync({
        agent_id: agentId,
        text: text.trim(),
        meeting_date: new Date(meetingDate).toISOString(),
      })

      setUploadResult({
        warning: result.normalization_warning,
        replacementCount: result.replacement_count,
      })

      // 成功したら少し待ってから閉じる
      setTimeout(() => {
        onClose()
      }, 2000)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">議事録アップロード</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="meeting-date" className="block text-sm font-medium mb-1">
              MTG開催日時 <span className="text-red-500">*</span>
            </label>
            <input
              id="meeting-date"
              type="datetime-local"
              value={meetingDate}
              onChange={(e) => setMeetingDate(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required
            />
          </div>

          <div>
            <label htmlFor="meeting-text" className="block text-sm font-medium mb-1">
              議事録テキスト <span className="text-red-500">*</span>
            </label>
            <textarea
              id="meeting-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="w-full border rounded px-3 py-2 font-mono text-sm"
              rows={15}
              required
              placeholder="議事録のテキストを貼り付けてください..."
            />
            <p className="text-xs text-gray-500 mt-1">辞書に登録された表記揺れは自動的に正規化されます</p>
          </div>

          {error && <div className="text-red-500 text-sm bg-red-50 p-3 rounded">{error}</div>}

          {uploadResult && (
            <div
              className={`p-3 rounded ${uploadResult.warning ? 'bg-yellow-50 text-yellow-800' : 'bg-green-50 text-green-800'}`}
            >
              {uploadResult.warning ? (
                <p>{uploadResult.warning}</p>
              ) : (
                <p>アップロード完了！{uploadResult.replacementCount}箇所を正規化しました。</p>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded hover:bg-gray-50"
              disabled={uploadMutation.isPending}
            >
              キャンセル
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
              disabled={uploadMutation.isPending || !!uploadResult}
            >
              {uploadMutation.isPending ? 'アップロード中...' : 'アップロード'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
