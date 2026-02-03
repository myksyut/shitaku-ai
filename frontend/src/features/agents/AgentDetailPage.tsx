/**
 * Agent detail page - Shows agent info, meeting notes, and Slack integration
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AgentAvatar, Button, Card, EmptyState, Modal, SlackIcon } from '../../components/ui'
import { AgendaGeneratePage } from '../agendas'
import { DictionarySection } from '../dictionary/DictionarySection'
import { useAgentRecurringMeetings, useUnlinkRecurringMeeting } from '../google/hooks'
// Import meeting notes components
import { useDeleteMeetingNote, useMeetingNotes, useUploadMeetingNote } from '../meeting-notes/hooks'
import type { MeetingNote } from '../meeting-notes/types'
import { useSlackChannels, useSlackIntegrations } from '../slack/hooks'
import { AgentForm } from './AgentForm'
import { useAgent, useDeleteAgent, useUpdateAgent } from './hooks'
import { RecurringMeetingSelector } from './RecurringMeetingSelector'
import type { Agent } from './types'

interface MeetingNoteCardProps {
  note: MeetingNote
  onDelete: () => void
  onView: () => void
  isDeleting: boolean
}

function MeetingNoteCard({ note, onDelete, onView, isDeleting }: MeetingNoteCardProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <Card style={{ marginBottom: 'var(--space-3)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              marginBottom: 'var(--space-2)',
            }}
          >
            <span style={{ fontSize: '16px' }}>📝</span>
            <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-warm-gray-700)' }}>
              {formatDate(note.meeting_date)}
            </span>
            {note.is_normalized && (
              <span
                style={{
                  fontSize: 'var(--font-size-xs)',
                  background: 'var(--color-success-100)',
                  color: 'var(--color-success-700)',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                }}
              >
                正規化済み
              </span>
            )}
          </div>
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warm-gray-600)',
              margin: 0,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              lineHeight: 1.5,
            }}
          >
            {note.normalized_text.substring(0, 150)}
            {note.normalized_text.length > 150 && '...'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)', marginLeft: 'var(--space-3)' }}>
          <Button variant="ghost" onClick={onView} style={{ padding: 'var(--space-2)' }}>
            詳細
          </Button>
          <Button
            variant="ghost"
            onClick={onDelete}
            disabled={isDeleting}
            style={{ padding: 'var(--space-2)', color: 'var(--color-error)' }}
          >
            削除
          </Button>
        </div>
      </div>
    </Card>
  )
}

interface MeetingNoteUploadModalProps {
  agentId: string
  isOpen: boolean
  onClose: () => void
}

function MeetingNoteUploadModal({ agentId, isOpen, onClose }: MeetingNoteUploadModalProps) {
  const [text, setText] = useState('')
  const [meetingDate, setMeetingDate] = useState(() => {
    const now = new Date()
    return now.toISOString().slice(0, 16)
  })
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const uploadMutation = useUploadMeetingNote()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!text.trim()) {
      setError('議事録テキストは必須です')
      return
    }

    try {
      await uploadMutation.mutateAsync({
        agent_id: agentId,
        text: text.trim(),
        meeting_date: new Date(meetingDate).toISOString(),
      })
      setSuccess(true)
      setTimeout(() => {
        setText('')
        setSuccess(false)
        onClose()
      }, 1500)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
    }
  }

  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="議事録をアップロード" size="lg">
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 'var(--space-4)' }}>
          <label
            htmlFor="meeting-date"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--color-warm-gray-700)',
              marginBottom: 'var(--space-2)',
            }}
          >
            MTG開催日時
          </label>
          <input
            id="meeting-date"
            type="datetime-local"
            value={meetingDate}
            onChange={(e) => setMeetingDate(e.target.value)}
            className="input"
            required
          />
        </div>

        <div style={{ marginBottom: 'var(--space-4)' }}>
          <label
            htmlFor="meeting-text"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--color-warm-gray-700)',
              marginBottom: 'var(--space-2)',
            }}
          >
            議事録テキスト
          </label>
          <textarea
            id="meeting-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="input"
            rows={12}
            required
            placeholder="議事録のテキストを貼り付けてください..."
            style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-sm)' }}
          />
          <p
            style={{
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-warm-gray-500)',
              marginTop: 'var(--space-1)',
            }}
          >
            辞書に登録された表記揺れは自動的に正規化されます
          </p>
        </div>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: 'var(--space-4)' }}>
            {error}
          </div>
        )}

        {success && (
          <div className="alert alert-success" style={{ marginBottom: 'var(--space-4)' }}>
            アップロード完了！
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-3)' }}>
          <Button variant="ghost" onClick={onClose} disabled={uploadMutation.isPending}>
            キャンセル
          </Button>
          <Button variant="primary" type="submit" isLoading={uploadMutation.isPending} disabled={success}>
            アップロード
          </Button>
        </div>
      </form>
    </Modal>
  )
}

interface MeetingNoteDetailModalProps {
  note: MeetingNote | null
  onClose: () => void
}

function MeetingNoteDetailModal({ note, onClose }: MeetingNoteDetailModalProps) {
  if (!note) return null

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

  return (
    <Modal isOpen={!!note} onClose={onClose} title="議事録詳細" size="lg">
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>MTG日時:</span>
        <span style={{ marginLeft: 'var(--space-2)', fontWeight: 600 }}>{formatDate(note.meeting_date)}</span>
      </div>

      <div>
        <h4
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 600,
            color: 'var(--color-warm-gray-700)',
            marginBottom: 'var(--space-2)',
          }}
        >
          正規化後のテキスト
        </h4>
        <div
          style={{
            background: 'var(--color-cream-200)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-4)',
            fontSize: 'var(--font-size-sm)',
            lineHeight: 1.7,
            whiteSpace: 'pre-wrap',
            maxHeight: '400px',
            overflowY: 'auto',
          }}
        >
          {note.normalized_text}
        </div>
      </div>
    </Modal>
  )
}

interface SlackChannelSelectorProps {
  agent: Agent
  onUpdate: (channelId: string | null) => void
  isUpdating: boolean
}

function SlackChannelSelector({ agent, onUpdate, isUpdating }: SlackChannelSelectorProps) {
  const { data: integrations, isLoading: integrationsLoading } = useSlackIntegrations()
  const firstIntegration = integrations?.[0]
  const { data: channels, isLoading: channelsLoading } = useSlackChannels(firstIntegration?.id ?? '')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredChannels = useMemo(() => {
    if (!channels) return []
    if (!searchQuery.trim()) return channels
    const query = searchQuery.toLowerCase()
    return channels.filter((channel) => channel.name.toLowerCase().includes(query))
  }, [channels, searchQuery])

  const selectedChannel = useMemo(() => {
    if (!agent.slack_channel_id || !channels) return null
    return channels.find((c) => c.id === agent.slack_channel_id)
  }, [agent.slack_channel_id, channels])

  const isLoading = integrationsLoading || channelsLoading

  if (isLoading) {
    return <div style={{ color: 'var(--color-warm-gray-500)', fontSize: 'var(--font-size-sm)' }}>読み込み中...</div>
  }

  if (!integrations || integrations.length === 0) {
    return (
      <div
        style={{
          padding: 'var(--space-4)',
          background: 'var(--color-cream-200)',
          borderRadius: 'var(--radius-md)',
          textAlign: 'center',
        }}
      >
        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-600)', margin: 0 }}>
          Slackワークスペースが連携されていません
        </p>
        <p
          style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-warm-gray-500)', marginTop: 'var(--space-1)' }}
        >
          ヘッダーの「Slack連携」から設定してください
        </p>
      </div>
    )
  }

  return (
    <div>
      {selectedChannel && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: 'var(--space-3)',
            background: 'var(--color-cream-200)',
            borderRadius: 'var(--radius-md)',
            marginBottom: 'var(--space-3)',
          }}
        >
          <span style={{ fontWeight: 600, color: 'var(--color-warm-gray-700)' }}>#{selectedChannel.name}</span>
          <Button
            variant="ghost"
            onClick={() => onUpdate(null)}
            disabled={isUpdating}
            style={{ padding: 'var(--space-1) var(--space-2)', fontSize: 'var(--font-size-sm)' }}
          >
            解除
          </Button>
        </div>
      )}
      {channels && channels.length > 10 && (
        <input
          type="text"
          placeholder="チャンネルを検索..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            width: '100%',
            padding: 'var(--space-2) var(--space-3)',
            marginBottom: 'var(--space-2)',
            border: '1px solid var(--color-warm-gray-300)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--font-size-sm)',
            outline: 'none',
          }}
        />
      )}
      {searchQuery && (
        <p
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-warm-gray-500)',
            marginBottom: 'var(--space-2)',
          }}
        >
          {filteredChannels.length}件のチャンネルが見つかりました
        </p>
      )}
      <div
        style={{
          maxHeight: '200px',
          overflowY: 'auto',
          border: '1px solid var(--color-warm-gray-200)',
          borderRadius: 'var(--radius-md)',
        }}
      >
        {filteredChannels.map((channel) => (
          <button
            type="button"
            key={channel.id}
            onClick={() => onUpdate(channel.id)}
            disabled={isUpdating || channel.id === agent.slack_channel_id}
            style={{
              display: 'block',
              width: '100%',
              padding: 'var(--space-2) var(--space-3)',
              textAlign: 'left',
              background: channel.id === agent.slack_channel_id ? 'var(--color-cream-300)' : 'transparent',
              border: 'none',
              borderBottom: '1px solid var(--color-warm-gray-100)',
              cursor: channel.id === agent.slack_channel_id ? 'default' : 'pointer',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warm-gray-700)',
            }}
          >
            #{channel.name}
          </button>
        ))}
        {filteredChannels.length === 0 && (
          <div
            style={{
              padding: 'var(--space-4)',
              textAlign: 'center',
              color: 'var(--color-warm-gray-500)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            チャンネルが見つかりません
          </div>
        )}
      </div>
      {agent.slack_channel_id && (
        <p
          style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-warm-gray-500)', marginTop: 'var(--space-2)' }}
        >
          このチャンネルの会話がアジェンダ生成に使用されます
        </p>
      )}
    </div>
  )
}

interface ReferenceSettingsSectionProps {
  agent: Agent
  onSave: (data: { transcript_count: number; slack_message_days: number }) => Promise<void>
  isSaving: boolean
}

function ReferenceSettingsSection({ agent, onSave, isSaving }: ReferenceSettingsSectionProps) {
  const [transcriptCount, setTranscriptCount] = useState<number>(agent.transcript_count)
  const [slackMessageDays, setSlackMessageDays] = useState<number>(agent.slack_message_days)
  const [transcriptCountError, setTranscriptCountError] = useState<string | null>(null)
  const [slackMessageDaysError, setSlackMessageDaysError] = useState<string | null>(null)

  useEffect(() => {
    setTranscriptCount(agent.transcript_count)
    setSlackMessageDays(agent.slack_message_days)
  }, [agent.transcript_count, agent.slack_message_days])

  const validateTranscriptCount = (value: number): boolean => {
    if (Number.isNaN(value) || value < 0 || value > 10) {
      setTranscriptCountError('0〜10の範囲で入力してください')
      return false
    }
    setTranscriptCountError(null)
    return true
  }

  const validateSlackMessageDays = (value: number): boolean => {
    if (Number.isNaN(value) || value < 1 || value > 30) {
      setSlackMessageDaysError('1〜30の範囲で入力してください')
      return false
    }
    setSlackMessageDaysError(null)
    return true
  }

  const handleSave = async () => {
    const isTranscriptValid = validateTranscriptCount(transcriptCount)
    const isSlackDaysValid = validateSlackMessageDays(slackMessageDays)

    if (!isTranscriptValid || !isSlackDaysValid) return

    await onSave({
      transcript_count: transcriptCount,
      slack_message_days: slackMessageDays,
    })
  }

  const hasValidationError = !!transcriptCountError || !!slackMessageDaysError

  return (
    <div style={{ marginTop: 'var(--space-6)' }}>
      <h2
        style={{
          fontSize: 'var(--font-size-lg)',
          fontWeight: 700,
          color: 'var(--color-warm-gray-800)',
          marginBottom: 'var(--space-4)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
        }}
      >
        <span style={{ fontSize: '20px' }}>&#x2699;&#xfe0f;</span> アジェンダ生成参照設定
      </h2>
      <Card>
        <p
          style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-warm-gray-600)',
            marginBottom: 'var(--space-4)',
          }}
        >
          アジェンダ生成時に参照するデータの範囲を設定できます
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {/* Transcript Count */}
          <div>
            <label
              htmlFor="transcript-count"
              style={{
                display: 'block',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 600,
                color: 'var(--color-warm-gray-700)',
                marginBottom: 'var(--space-1)',
              }}
            >
              トランスクリプト参照件数
            </label>
            <p
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--color-warm-gray-500)',
                marginBottom: 'var(--space-2)',
              }}
            >
              アジェンダ生成時に参照するトランスクリプトの件数（0〜10件）
            </p>
            <input
              id="transcript-count"
              type="number"
              min={0}
              max={10}
              value={transcriptCount}
              onChange={(e) => {
                const value = Number.parseInt(e.target.value, 10)
                setTranscriptCount(value)
                validateTranscriptCount(value)
              }}
              style={{
                width: '100px',
                padding: 'var(--space-2) var(--space-3)',
                border: '1px solid var(--color-warm-gray-300)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--font-size-sm)',
              }}
            />
            {transcriptCountError && (
              <p
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-error)',
                  marginTop: 'var(--space-1)',
                }}
              >
                {transcriptCountError}
              </p>
            )}
          </div>

          {/* Slack Message Days */}
          <div>
            <label
              htmlFor="slack-message-days"
              style={{
                display: 'block',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 600,
                color: 'var(--color-warm-gray-700)',
                marginBottom: 'var(--space-1)',
              }}
            >
              Slackメッセージ取得日数
            </label>
            <p
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--color-warm-gray-500)',
                marginBottom: 'var(--space-2)',
              }}
            >
              アジェンダ生成時に参照するSlackメッセージの日数（1〜30日）
            </p>
            <input
              id="slack-message-days"
              type="number"
              min={1}
              max={30}
              value={slackMessageDays}
              onChange={(e) => {
                const value = Number.parseInt(e.target.value, 10)
                setSlackMessageDays(value)
                validateSlackMessageDays(value)
              }}
              style={{
                width: '100px',
                padding: 'var(--space-2) var(--space-3)',
                border: '1px solid var(--color-warm-gray-300)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--font-size-sm)',
              }}
            />
            {slackMessageDaysError && (
              <p
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-error)',
                  marginTop: 'var(--space-1)',
                }}
              >
                {slackMessageDaysError}
              </p>
            )}
          </div>

          {/* Save Button */}
          <div style={{ marginTop: 'var(--space-2)' }}>
            <Button variant="secondary" onClick={handleSave} disabled={isSaving || hasValidationError}>
              {isSaving ? '保存中...' : '参照設定を保存'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

export function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>()
  const navigate = useNavigate()
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isUploadOpen, setIsUploadOpen] = useState(false)
  const [selectedNote, setSelectedNote] = useState<MeetingNote | null>(null)
  const [isAgendaModalOpen, setIsAgendaModalOpen] = useState(false)
  const [isMeetingSelectorOpen, setIsMeetingSelectorOpen] = useState(false)

  const { data: agent, isLoading, error } = useAgent(agentId ?? '')
  const { data: recurringMeetings, isLoading: meetingsLoading } = useAgentRecurringMeetings(agentId ?? null)
  const unlinkMeetingMutation = useUnlinkRecurringMeeting()

  const handleBack = () => {
    navigate('/')
  }

  const handleGenerateAgenda = () => {
    setIsAgendaModalOpen(true)
  }
  const { data: notes, isLoading: notesLoading } = useMeetingNotes(agentId ?? '')
  const deleteMutation = useDeleteAgent()
  const deleteNoteMutation = useDeleteMeetingNote()
  const updateMutation = useUpdateAgent()

  const handleDelete = async () => {
    if (!agentId) return
    if (window.confirm('このエージェントを削除しますか？関連する議事録・アジェンダも削除されます。')) {
      await deleteMutation.mutateAsync(agentId)
      handleBack()
    }
  }

  const handleDeleteNote = async (noteId: string) => {
    if (window.confirm('この議事録を削除しますか？')) {
      await deleteNoteMutation.mutateAsync(noteId)
    }
  }

  const handleSlackChannelUpdate = async (channelId: string | null) => {
    if (!agentId) return
    await updateMutation.mutateAsync({
      id: agentId,
      data: { slack_channel_id: channelId },
    })
  }

  const handleUnlinkMeeting = async (meetingId: string) => {
    if (!agentId) return
    if (window.confirm('定例MTGの紐付けを解除しますか？')) {
      await unlinkMeetingMutation.mutateAsync({ agentId, meetingId })
    }
  }

  if (!agentId) {
    return <div className="alert alert-error">エージェントIDが指定されていません</div>
  }

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '300px',
          gap: 'var(--space-3)',
          color: 'var(--color-warm-gray-500)',
        }}
      >
        <span className="spinner spinner-lg" style={{ color: 'var(--color-primary-400)' }} />
        <span style={{ fontSize: 'var(--font-size-base)', fontWeight: 500 }}>読み込み中...</span>
      </div>
    )
  }

  if (error || !agent) {
    return (
      <div>
        <Button variant="ghost" onClick={handleBack} style={{ marginBottom: 'var(--space-4)' }}>
          ← 戻る
        </Button>
        <div className="alert alert-error">エージェントが見つかりません</div>
      </div>
    )
  }

  return (
    <div>
      {/* Back Button */}
      <Button variant="ghost" onClick={handleBack} style={{ marginBottom: 'var(--space-4)' }}>
        ← エージェント一覧に戻る
      </Button>

      {/* Agent Header */}
      <Card variant="clay" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-4)' }}>
          <AgentAvatar name={agent.name} size="lg" />
          <div style={{ flex: 1 }}>
            <h1
              style={{
                fontSize: 'var(--font-size-2xl)',
                fontWeight: 800,
                color: 'var(--color-warm-gray-800)',
                margin: '0 0 var(--space-2)',
              }}
            >
              {agent.name}
            </h1>
            {agent.description && (
              <p
                style={{
                  fontSize: 'var(--font-size-base)',
                  color: 'var(--color-warm-gray-600)',
                  margin: 0,
                  lineHeight: 1.6,
                }}
              >
                {agent.description}
              </p>
            )}
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button variant="ghost" onClick={() => setIsFormOpen(true)}>
              編集
            </Button>
            <Button
              variant="ghost"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              style={{ color: 'var(--color-error)' }}
            >
              削除
            </Button>
          </div>
        </div>

        {/* Main CTA */}
        <Button
          variant="primary"
          onClick={handleGenerateAgenda}
          style={{
            width: '100%',
            marginTop: 'var(--space-6)',
            padding: 'var(--space-4)',
            fontSize: 'var(--font-size-lg)',
          }}
        >
          <span style={{ marginRight: 'var(--space-2)', fontSize: '20px' }}>✨</span>
          次回のアジェンダを提案して
        </Button>
      </Card>

      {/* Two Column Layout */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
          gap: 'var(--space-6)',
        }}
      >
        {/* Meeting Notes Section */}
        <div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 'var(--space-4)',
            }}
          >
            <h2
              style={{
                fontSize: 'var(--font-size-lg)',
                fontWeight: 700,
                color: 'var(--color-warm-gray-800)',
                margin: 0,
              }}
            >
              📝 過去の議事録
            </h2>
            <Button variant="secondary" onClick={() => setIsUploadOpen(true)}>
              アップロード
            </Button>
          </div>

          {notesLoading ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--color-warm-gray-500)' }}>
              読み込み中...
            </div>
          ) : notes && notes.length > 0 ? (
            <div>
              {notes.map((note) => (
                <MeetingNoteCard
                  key={note.id}
                  note={note}
                  onDelete={() => handleDeleteNote(note.id)}
                  onView={() => setSelectedNote(note)}
                  isDeleting={deleteNoteMutation.isPending}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              icon="📝"
              title="議事録がありません"
              description="過去の議事録をアップロードすると、より良いアジェンダを提案できます"
              action={
                <Button variant="secondary" onClick={() => setIsUploadOpen(true)}>
                  議事録をアップロード
                </Button>
              }
            />
          )}
        </div>

        {/* Slack Channel Section */}
        <div>
          <h2
            style={{
              fontSize: 'var(--font-size-lg)',
              fontWeight: 700,
              color: 'var(--color-warm-gray-800)',
              marginBottom: 'var(--space-4)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
            }}
          >
            <SlackIcon size={22} /> Slackチャンネル連携
          </h2>
          <Card>
            <p
              style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-warm-gray-600)',
                marginBottom: 'var(--space-4)',
              }}
            >
              Slackチャンネルを連携すると、チャンネル内の会話からアジェンダを自動生成できます
            </p>
            <SlackChannelSelector
              agent={agent}
              onUpdate={handleSlackChannelUpdate}
              isUpdating={updateMutation.isPending}
            />
          </Card>
        </div>
      </div>

      {/* Recurring Meeting Section */}
      <div style={{ marginTop: 'var(--space-6)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 'var(--space-4)',
          }}
        >
          <h2
            style={{
              fontSize: 'var(--font-size-lg)',
              fontWeight: 700,
              color: 'var(--color-warm-gray-800)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              margin: 0,
            }}
          >
            <span style={{ fontSize: '20px' }}>📅</span> 定例MTG連携
          </h2>
          <Button variant="secondary" onClick={() => setIsMeetingSelectorOpen(true)}>
            定例を追加
          </Button>
        </div>
        <Card>
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warm-gray-600)',
              marginBottom: 'var(--space-4)',
            }}
          >
            定例MTGを紐付けると、Google Meetの議事録から自動でアジェンダを生成できます
          </p>
          {meetingsLoading ? (
            <div style={{ color: 'var(--color-warm-gray-500)', fontSize: 'var(--font-size-sm)' }}>読み込み中...</div>
          ) : recurringMeetings && recurringMeetings.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {recurringMeetings.map((meeting) => (
                <div
                  key={meeting.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: 'var(--space-3)',
                    background: 'var(--color-cream-200)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--color-warm-gray-700)' }}>{meeting.title}</div>
                    <div
                      style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-warm-gray-500)', marginTop: '2px' }}
                    >
                      {meeting.frequency === 'weekly' && '毎週'}
                      {meeting.frequency === 'biweekly' && '隔週'}
                      {meeting.frequency === 'monthly' && '毎月'}
                      {' • '}
                      {meeting.attendees.length}名参加
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    onClick={() => handleUnlinkMeeting(meeting.id)}
                    disabled={unlinkMeetingMutation.isPending}
                    style={{ padding: 'var(--space-1) var(--space-2)', fontSize: 'var(--font-size-sm)' }}
                  >
                    {unlinkMeetingMutation.isPending ? '解除中...' : '解除'}
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--color-warm-gray-500)', fontSize: 'var(--font-size-sm)' }}>
              紐付けられた定例MTGはありません
            </div>
          )}
        </Card>
      </div>

      {/* Reference Settings Section */}
      <ReferenceSettingsSection
        agent={agent}
        onSave={async (data) => {
          await updateMutation.mutateAsync({
            id: agentId,
            data,
          })
        }}
        isSaving={updateMutation.isPending}
      />

      {/* Dictionary Section (full width) */}
      <div style={{ marginTop: 'var(--space-6)' }}>
        <DictionarySection agentId={agentId} />
      </div>

      {/* Modals */}
      {isFormOpen && <AgentForm agent={agent} onClose={() => setIsFormOpen(false)} />}
      <MeetingNoteUploadModal agentId={agentId} isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />
      <MeetingNoteDetailModal note={selectedNote} onClose={() => setSelectedNote(null)} />
      {isAgendaModalOpen && <AgendaGeneratePage agentId={agentId} onClose={() => setIsAgendaModalOpen(false)} />}
      <RecurringMeetingSelector
        agentId={agentId}
        isOpen={isMeetingSelectorOpen}
        onClose={() => setIsMeetingSelectorOpen(false)}
        excludeMeetingIds={recurringMeetings?.map((m) => m.id) ?? []}
      />
    </div>
  )
}
