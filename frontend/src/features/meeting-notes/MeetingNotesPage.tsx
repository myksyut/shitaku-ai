/**
 * Meeting notes list page component
 */

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAgent } from '../agents/hooks'
import { useDeleteMeetingNote, useMeetingNotes } from './hooks'
import { MeetingNoteUpload } from './MeetingNoteUpload'
import { NormalizationDiff } from './NormalizationDiff'
import type { MeetingNote } from './types'

export function MeetingNotesPage() {
  const { agentId } = useParams<{ agentId: string }>()
  const [isUploadOpen, setIsUploadOpen] = useState(false)
  const [selectedNote, setSelectedNote] = useState<MeetingNote | null>(null)

  const { data: agent, isLoading: isAgentLoading } = useAgent(agentId ?? '')
  const { data: notes, isLoading: isNotesLoading, error } = useMeetingNotes(agentId ?? '')
  const deleteMutation = useDeleteMeetingNote()

  const handleDelete = async (id: string) => {
    if (window.confirm('このナレッジを削除しますか？')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (isAgentLoading || isNotesLoading) return <div className="p-4">読み込み中...</div>
  if (error) return <div className="p-4 text-red-500">エラーが発生しました</div>
  if (!agent) return <div className="p-4 text-red-500">エージェントが見つかりません</div>

  return (
    <div className="p-4">
      <div className="mb-4">
        <Link to="/agents" className="text-blue-500 hover:underline text-sm">
          ← エージェント一覧に戻る
        </Link>
      </div>

      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-2xl font-bold">{agent.name} - ナレッジ</h1>
          {agent.description && <p className="text-gray-600 text-sm mt-1">{agent.description}</p>}
        </div>
        <button
          type="button"
          onClick={() => setIsUploadOpen(true)}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          ナレッジアップロード
        </button>
      </div>

      {/* ナレッジ一覧 */}
      <div className="space-y-4">
        {notes?.map((note) => (
          <div key={note.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="text-sm text-gray-500 mb-2">MTG日: {formatDate(note.meeting_date)}</div>
                <p className="text-sm line-clamp-3">
                  {note.normalized_text.substring(0, 200)}
                  {note.normalized_text.length > 200 && '...'}
                </p>
                {note.is_normalized && (
                  <span className="inline-block mt-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                    正規化済み
                  </span>
                )}
              </div>
              <div className="flex gap-2 ml-4">
                <button
                  type="button"
                  onClick={() => setSelectedNote(note)}
                  className="text-blue-500 hover:underline text-sm"
                >
                  詳細
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(note.id)}
                  className="text-red-500 hover:underline text-sm"
                  disabled={deleteMutation.isPending}
                >
                  削除
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {notes?.length === 0 && (
        <div className="text-center text-gray-500 py-8">ナレッジがありません。アップロードしてください。</div>
      )}

      {/* アップロードモーダル */}
      {isUploadOpen && agentId && <MeetingNoteUpload agentId={agentId} onClose={() => setIsUploadOpen(false)} />}

      {/* 詳細モーダル */}
      {selectedNote && <NormalizationDiff note={selectedNote} onClose={() => setSelectedNote(null)} />}
    </div>
  )
}
