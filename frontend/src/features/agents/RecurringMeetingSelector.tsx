import { useState } from 'react'
import { useLinkRecurringMeeting, useUnlinkedMeetings } from '../google/hooks'
import type { RecurringMeeting } from '../google/types'

interface RecurringMeetingSelectorProps {
  agentId: string
  isOpen: boolean
  onClose: () => void
  excludeMeetingIds?: string[]
  onSuccess?: () => void
}

function formatFrequency(frequency: string): string {
  switch (frequency) {
    case 'weekly':
      return '毎週'
    case 'biweekly':
      return '隔週'
    case 'monthly':
      return '毎月'
    default:
      return frequency
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('ja-JP', {
    month: 'short',
    day: 'numeric',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function RecurringMeetingSelector({
  agentId,
  isOpen,
  onClose,
  excludeMeetingIds = [],
  onSuccess,
}: RecurringMeetingSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedMeeting, setSelectedMeeting] = useState<RecurringMeeting | null>(null)

  const { data: meetings, isLoading } = useUnlinkedMeetings()
  const linkMutation = useLinkRecurringMeeting()

  // 未紐付けかつexcludeに含まれない定例のみ表示
  const filteredMeetings = meetings?.filter((meeting) => {
    const matchesSearch = meeting.title.toLowerCase().includes(searchQuery.toLowerCase())
    const notExcluded = !excludeMeetingIds.includes(meeting.id)
    return matchesSearch && notExcluded
  })

  const handleLink = async () => {
    if (!selectedMeeting) return

    try {
      await linkMutation.mutateAsync({
        agentId,
        recurringMeetingId: selectedMeeting.id,
      })
      onSuccess?.()
      onClose()
    } catch (error) {
      console.error('Failed to link meeting:', error)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">定例MTGを選択</h2>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="閉じる">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <input
          type="text"
          placeholder="定例を検索..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="mb-4 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        <div className="mb-4 max-h-64 overflow-y-auto">
          {isLoading ? (
            <div className="py-4 text-center text-gray-500">読み込み中...</div>
          ) : filteredMeetings?.length === 0 ? (
            <div className="py-4 text-center text-gray-500">
              {meetings?.length === 0 ? '紐付け可能な定例MTGがありません' : '検索結果がありません'}
            </div>
          ) : (
            <div className="space-y-2">
              {filteredMeetings?.map((meeting) => (
                <button
                  key={meeting.id}
                  type="button"
                  onClick={() => setSelectedMeeting(meeting)}
                  className={`w-full rounded-md border p-3 text-left transition-colors ${
                    selectedMeeting?.id === meeting.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="font-medium">{meeting.title}</div>
                  <div className="mt-1 flex items-center gap-2 text-sm text-gray-500">
                    <span>{formatFrequency(meeting.frequency)}</span>
                    <span>•</span>
                    <span>次回: {formatDate(meeting.next_occurrence)}</span>
                    <span>•</span>
                    <span>{meeting.attendees.length}名参加</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md px-4 py-2 text-gray-600 hover:bg-gray-100">
            キャンセル
          </button>
          <button
            type="button"
            onClick={handleLink}
            disabled={!selectedMeeting || linkMutation.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {linkMutation.isPending ? '紐付け中...' : '紐付ける'}
          </button>
        </div>
      </div>
    </div>
  )
}
