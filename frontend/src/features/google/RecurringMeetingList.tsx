import { Button, Card } from '../../components/ui'
import { useGoogleIntegrations, useRecurringMeetings, useSyncRecurringMeetings } from './hooks'
import type { MeetingFrequency, RecurringMeeting } from './types'

function formatFrequency(frequency: MeetingFrequency): string {
  switch (frequency) {
    case 'weekly':
      return '毎週'
    case 'biweekly':
      return '隔週'
    case 'monthly':
      return '月次'
    default:
      return frequency
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  })
}

interface MeetingCardProps {
  meeting: RecurringMeeting
  onCreateAgent: (meeting: RecurringMeeting) => void
}

function MeetingCard({ meeting, onCreateAgent }: MeetingCardProps) {
  return (
    <Card style={{ marginBottom: 'var(--space-4)' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 'var(--space-4)',
        }}
      >
        <div style={{ flex: 1 }}>
          <h3
            style={{
              fontSize: 'var(--font-size-lg)',
              fontWeight: 700,
              color: 'var(--color-warm-gray-800)',
              marginBottom: 'var(--space-2)',
            }}
          >
            {meeting.title}
          </h3>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 'var(--space-3)',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warm-gray-500)',
            }}
          >
            <span
              style={{
                display: 'inline-block',
                padding: 'var(--space-1) var(--space-2)',
                background: 'var(--color-cream-200)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--color-warm-gray-700)',
              }}
            >
              {formatFrequency(meeting.frequency)}
            </span>
            <span>次回: {formatDate(meeting.next_occurrence)}</span>
            <span>参加者: {meeting.attendees.length}人</span>
          </div>
        </div>
        <div style={{ flexShrink: 0 }}>
          {meeting.agent_id ? (
            <span
              style={{
                display: 'inline-block',
                padding: 'var(--space-2) var(--space-3)',
                background: 'var(--color-success-50)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-success-600)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 500,
              }}
            >
              エージェント連携済み
            </span>
          ) : (
            <Button variant="primary" size="sm" onClick={() => onCreateAgent(meeting)}>
              エージェント作成
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}

interface RecurringMeetingListProps {
  onCreateAgent: (meetingId: string, title: string, attendees: string[]) => void
}

export function RecurringMeetingList({ onCreateAgent }: RecurringMeetingListProps) {
  const { data: integrations, isLoading: intLoading } = useGoogleIntegrations()
  const { data: meetings, isLoading: meetLoading, error } = useRecurringMeetings()
  const syncMeetings = useSyncRecurringMeetings()

  const selectedIntegration = integrations?.[0]

  const handleCreateAgent = (meeting: RecurringMeeting) => {
    onCreateAgent(meeting.id, meeting.title, meeting.attendees)
  }

  const handleSync = () => {
    if (selectedIntegration) {
      syncMeetings.mutate(selectedIntegration.id)
    }
  }

  if (intLoading || meetLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-warm-gray-500)' }}>
        読み込み中...
      </div>
    )
  }

  if (!selectedIntegration) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
          <p style={{ color: 'var(--color-warm-gray-600)', marginBottom: 'var(--space-2)' }}>Google連携が必要です</p>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
            Google連携設定から連携を行ってください
          </p>
        </div>
      </Card>
    )
  }

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-6)',
        }}
      >
        <div>
          <h2
            style={{
              fontSize: 'var(--font-size-xl)',
              fontWeight: 700,
              color: 'var(--color-warm-gray-800)',
              marginBottom: 'var(--space-1)',
            }}
          >
            定例MTG一覧
          </h2>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
            Googleカレンダーから取得した定例会議
          </p>
        </div>
        <Button variant="secondary" onClick={handleSync} isLoading={syncMeetings.isPending}>
          同期
        </Button>
      </div>

      {/* Error */}
      {error && (
        <Card style={{ marginBottom: 'var(--space-4)' }}>
          <div
            style={{
              padding: 'var(--space-3)',
              background: 'var(--color-error-50)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-error-600)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            定例MTGの取得に失敗しました
          </div>
        </Card>
      )}

      {/* Sync Success */}
      {syncMeetings.isSuccess && (
        <Card style={{ marginBottom: 'var(--space-4)' }}>
          <div
            style={{
              padding: 'var(--space-3)',
              background: 'var(--color-success-50)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-success-600)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            同期完了: {syncMeetings.data.created}件作成, {syncMeetings.data.updated}件更新
          </div>
        </Card>
      )}

      {/* Meeting List */}
      {meetings && meetings.length > 0 ? (
        <div>
          {meetings.map((meeting) => (
            <MeetingCard key={meeting.id} meeting={meeting} onCreateAgent={handleCreateAgent} />
          ))}
        </div>
      ) : (
        <Card>
          <div style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
            <p style={{ color: 'var(--color-warm-gray-600)', marginBottom: 'var(--space-2)' }}>
              定例MTGが見つかりません
            </p>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
              Googleカレンダーに繰り返し予定を登録して、上の「同期」ボタンを押してください
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}
