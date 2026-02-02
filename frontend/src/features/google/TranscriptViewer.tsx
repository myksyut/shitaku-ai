/**
 * TranscriptViewer - トランスクリプト表示コンポーネント
 * AC16: 自動紐付け結果表示
 * AC17: 手動確認UI（信頼度<0.7）
 * AC10: 追加スコープ要求
 */
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { useDriveScopes, useGoogleIntegrations, useLinkTranscript, useSyncTranscripts, useTranscripts } from './hooks'
import type { MeetingTranscript } from './types'

function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

interface TranscriptCardProps {
  transcript: MeetingTranscript
  onLink: () => void
  isLinking: boolean
}

function TranscriptCard({ transcript, onLink, isLinking }: TranscriptCardProps) {
  const confidenceColor =
    transcript.match_confidence >= 0.7
      ? 'var(--color-success-600)'
      : transcript.match_confidence >= 0.5
        ? 'var(--color-warning-600)'
        : 'var(--color-error-600)'

  return (
    <Card style={{ marginBottom: 'var(--space-4)' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 'var(--space-3)',
        }}
      >
        <div>
          <h3
            style={{
              fontSize: 'var(--font-size-lg)',
              fontWeight: 700,
              color: 'var(--color-warm-gray-800)',
              marginBottom: 'var(--space-1)',
            }}
          >
            {formatDate(transcript.meeting_date)}
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <span
              style={{
                fontSize: 'var(--font-size-sm)',
                color: confidenceColor,
                fontWeight: 600,
              }}
            >
              信頼度: {formatConfidence(transcript.match_confidence)}
            </span>
            {transcript.is_auto_linked && (
              <span
                style={{
                  fontSize: 'var(--font-size-xs)',
                  background: 'var(--color-success-100)',
                  color: 'var(--color-success-700)',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                }}
              >
                自動紐付け
              </span>
            )}
          </div>
        </div>
        {transcript.needs_manual_confirmation && (
          <Button variant="primary" size="sm" onClick={onLink} isLoading={isLinking}>
            紐付け確認
          </Button>
        )}
      </div>

      {transcript.structured_data ? (
        <div
          style={{
            maxHeight: '200px',
            overflowY: 'auto',
            background: 'var(--color-cream-100)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-3)',
          }}
        >
          {transcript.structured_data.entries.slice(0, 5).map((entry, index) => (
            <div
              key={`${entry.timestamp}-${index}`}
              style={{
                marginBottom: 'var(--space-2)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-2)' }}>
                <span style={{ fontWeight: 600, color: 'var(--color-warm-gray-700)' }}>{entry.speaker}</span>
                <span style={{ color: 'var(--color-warm-gray-400)', fontSize: 'var(--font-size-xs)' }}>
                  {entry.timestamp}
                </span>
              </div>
              <p
                style={{
                  color: 'var(--color-warm-gray-600)',
                  margin: 'var(--space-1) 0 0 0',
                  lineHeight: 1.5,
                }}
              >
                {entry.text}
              </p>
            </div>
          ))}
          {transcript.structured_data.entries.length > 5 && (
            <p
              style={{
                color: 'var(--color-warm-gray-400)',
                fontSize: 'var(--font-size-sm)',
                marginTop: 'var(--space-2)',
              }}
            >
              ... 他 {transcript.structured_data.entries.length - 5} 件
            </p>
          )}
        </div>
      ) : (
        <p style={{ color: 'var(--color-warm-gray-500)', fontSize: 'var(--font-size-sm)' }}>
          構造化データなし（生テキストのみ）
        </p>
      )}
    </Card>
  )
}

export function TranscriptViewer() {
  const { meetingId } = useParams<{ meetingId: string }>()
  const navigate = useNavigate()

  const { data: integrations, isLoading: integrationsLoading } = useGoogleIntegrations()
  const selectedIntegration = integrations?.[0]

  const { data: driveScopes, isLoading: scopesLoading } = useDriveScopes(selectedIntegration?.id ?? null)
  const { data: transcripts, isLoading: transcriptsLoading } = useTranscripts(meetingId ?? null)

  const syncMutation = useSyncTranscripts()
  const linkMutation = useLinkTranscript()

  const handleSync = () => {
    if (!selectedIntegration?.id || !meetingId) return
    syncMutation.mutate({
      integrationId: selectedIntegration.id,
      recurringMeetingId: meetingId,
    })
  }

  const handleLink = (transcriptId: string) => {
    if (!meetingId) return
    linkMutation.mutate({
      transcriptId,
      recurringMeetingId: meetingId,
    })
  }

  const handleBack = () => {
    navigate(-1)
  }

  const handleRequestScopes = () => {
    if (!selectedIntegration?.id) return
    // 追加スコープ要求画面へ遷移（Google連携設定ページ）
    navigate('/settings/google')
  }

  if (!meetingId) {
    return (
      <div>
        <Button variant="ghost" onClick={handleBack} style={{ marginBottom: 'var(--space-4)' }}>
          ← 戻る
        </Button>
        <div className="alert alert-error">定例MTG IDが指定されていません</div>
      </div>
    )
  }

  const isLoading = integrationsLoading || scopesLoading || transcriptsLoading

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

  // AC10: Drive/Docsスコープが未許可の場合
  if (driveScopes && !driveScopes.has_drive_scopes) {
    return (
      <div style={{ maxWidth: '720px', margin: '0 auto' }}>
        <Button variant="ghost" onClick={handleBack} style={{ marginBottom: 'var(--space-4)' }}>
          ← 戻る
        </Button>

        <div style={{ marginBottom: 'var(--space-6)' }}>
          <h1
            style={{
              fontSize: 'var(--font-size-2xl)',
              fontWeight: 800,
              color: 'var(--color-warm-gray-800)',
              marginBottom: 'var(--space-2)',
            }}
          >
            トランスクリプト
          </h1>
        </div>

        <Card>
          <div
            style={{
              textAlign: 'center',
              padding: 'var(--space-6)',
            }}
          >
            <div
              style={{
                fontSize: '48px',
                marginBottom: 'var(--space-4)',
              }}
            >
              📄
            </div>
            <h3
              style={{
                fontSize: 'var(--font-size-lg)',
                fontWeight: 700,
                color: 'var(--color-warm-gray-800)',
                marginBottom: 'var(--space-2)',
              }}
            >
              追加の権限が必要です
            </h3>
            <p
              style={{
                color: 'var(--color-warm-gray-600)',
                marginBottom: 'var(--space-4)',
              }}
            >
              トランスクリプトを取得するには、Google Drive・ドキュメントへのアクセス許可が必要です。
            </p>
            <Button variant="primary" onClick={handleRequestScopes}>
              Google連携設定を開く
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '720px', margin: '0 auto' }}>
      <Button variant="ghost" onClick={handleBack} style={{ marginBottom: 'var(--space-4)' }}>
        ← 戻る
      </Button>

      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-6)',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 'var(--font-size-2xl)',
              fontWeight: 800,
              color: 'var(--color-warm-gray-800)',
              marginBottom: 'var(--space-1)',
            }}
          >
            トランスクリプト
          </h1>
          <p style={{ color: 'var(--color-warm-gray-500)', fontSize: 'var(--font-size-sm)' }}>
            会議の文字起こしを確認・管理できます
          </p>
        </div>
        <Button variant="secondary" onClick={handleSync} isLoading={syncMutation.isPending}>
          同期
        </Button>
      </div>

      {/* Error */}
      {syncMutation.isError && (
        <div className="alert alert-error" style={{ marginBottom: 'var(--space-4)' }}>
          同期に失敗しました。再度お試しください。
        </div>
      )}

      {/* Transcript List */}
      {transcripts && transcripts.length > 0 ? (
        <div>
          {transcripts.map((transcript) => (
            <TranscriptCard
              key={transcript.id}
              transcript={transcript}
              onLink={() => handleLink(transcript.id)}
              isLinking={linkMutation.isPending}
            />
          ))}
        </div>
      ) : (
        <Card>
          <div
            style={{
              textAlign: 'center',
              padding: 'var(--space-6)',
            }}
          >
            <div
              style={{
                fontSize: '48px',
                marginBottom: 'var(--space-4)',
              }}
            >
              📝
            </div>
            <h3
              style={{
                fontSize: 'var(--font-size-lg)',
                fontWeight: 700,
                color: 'var(--color-warm-gray-800)',
                marginBottom: 'var(--space-2)',
              }}
            >
              トランスクリプトがありません
            </h3>
            <p
              style={{
                color: 'var(--color-warm-gray-600)',
                marginBottom: 'var(--space-4)',
              }}
            >
              「同期」ボタンを押してGoogle Driveからトランスクリプトを取得してください。
            </p>
            <Button variant="primary" onClick={handleSync} isLoading={syncMutation.isPending}>
              トランスクリプトを同期
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
