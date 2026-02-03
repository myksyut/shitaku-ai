/**
 * Agenda generation page - One button experience with warm design
 */
import { useState } from 'react'
import { Button, Modal } from '../../components/ui'
import { AgendaEditor } from './AgendaEditor'
import { useGenerateAgenda } from './hooks'
import type { Agenda, DataSourcesInfo } from './types'

interface Props {
  agentId: string
  onClose: () => void
}

function DataSourceBadge({ label, value, active }: { label: string; value: string; active: boolean }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        padding: 'var(--space-2) var(--space-3)',
        background: active ? 'var(--color-primary-50)' : 'var(--color-warm-gray-100)',
        borderRadius: 'var(--radius-md)',
        fontSize: 'var(--font-size-sm)',
      }}
    >
      <span
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: active ? 'var(--color-primary-400)' : 'var(--color-warm-gray-300)',
        }}
      />
      <span style={{ color: 'var(--color-warm-gray-600)' }}>{label}</span>
      <span style={{ fontWeight: 600, color: active ? 'var(--color-primary-700)' : 'var(--color-warm-gray-500)' }}>
        {value}
      </span>
    </div>
  )
}

export function AgendaGeneratePage({ agentId, onClose }: Props) {
  const [generatedAgenda, setGeneratedAgenda] = useState<Agenda | null>(null)
  const [dataSources, setDataSources] = useState<DataSourcesInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  const generateMutation = useGenerateAgenda()

  const handleGenerate = async () => {
    setError(null)
    setGeneratedAgenda(null)
    setDataSources(null)

    try {
      const result = await generateMutation.mutateAsync({ agent_id: agentId })
      setGeneratedAgenda(result.agenda)
      setDataSources(result.data_sources)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
    }
  }

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={generatedAgenda ? 'アジェンダが生成されました' : 'アジェンダを生成'}
      size="lg"
    >
      {!generatedAgenda ? (
        <div
          style={{
            textAlign: 'center',
            padding: 'var(--space-8) var(--space-4)',
          }}
        >
          {/* Illustration */}
          <div
            className={generateMutation.isPending ? 'animate-bounce' : 'animate-float'}
            style={{
              width: '100px',
              height: '100px',
              margin: '0 auto var(--space-6)',
              background: 'linear-gradient(145deg, var(--color-primary-100), var(--color-primary-200))',
              borderRadius: 'var(--radius-2xl)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '48px',
            }}
          >
            {generateMutation.isPending ? '🔮' : '✨'}
          </div>

          <h3
            style={{
              fontSize: 'var(--font-size-xl)',
              fontWeight: 700,
              color: 'var(--color-warm-gray-800)',
              margin: '0 0 var(--space-3)',
            }}
          >
            {generateMutation.isPending ? 'アジェンダを生成中...' : '次回のMTGを準備しましょう'}
          </h3>

          <p
            style={{
              fontSize: 'var(--font-size-base)',
              color: 'var(--color-warm-gray-500)',
              margin: '0 0 var(--space-6)',
              maxWidth: '400px',
              marginLeft: 'auto',
              marginRight: 'auto',
            }}
          >
            {generateMutation.isPending
              ? '過去のナレッジとSlack履歴を分析しています'
              : '過去のナレッジとSlack履歴を元に、次回MTGのアジェンダを自動生成します'}
          </p>

          {/* Error */}
          {error && (
            <div
              className="alert alert-error animate-fade-in"
              style={{
                maxWidth: '400px',
                margin: '0 auto var(--space-6)',
                textAlign: 'left',
              }}
            >
              {error}
            </div>
          )}

          {/* Loading state */}
          {generateMutation.isPending ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-4)',
                background: 'var(--color-cream-200)',
                borderRadius: 'var(--radius-lg)',
                maxWidth: '300px',
                margin: '0 auto',
              }}
            >
              <span className="spinner" style={{ color: 'var(--color-primary-500)' }} />
              <span
                style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-warm-gray-600)',
                }}
              >
                最大30秒ほどお待ちください
              </span>
            </div>
          ) : (
            /* Main CTA - One Button Experience */
            <Button size="lg" onClick={handleGenerate}>
              <span style={{ marginRight: 'var(--space-2)', fontSize: '20px' }}>✨</span>
              アジェンダを生成する
            </Button>
          )}
        </div>
      ) : (
        <div className="animate-fade-in">
          {/* Data Sources Summary */}
          {dataSources && (
            <div
              style={{
                marginBottom: 'var(--space-6)',
                padding: 'var(--space-4)',
                background: 'var(--color-cream-100)',
                borderRadius: 'var(--radius-lg)',
              }}
            >
              <p
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 600,
                  color: 'var(--color-warm-gray-700)',
                  margin: '0 0 var(--space-3)',
                }}
              >
                使用したデータソース
              </p>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 'var(--space-2)',
                }}
              >
                <DataSourceBadge
                  label="ナレッジ"
                  value={dataSources.has_knowledge ? '参照済' : 'なし'}
                  active={dataSources.has_knowledge}
                />
                <DataSourceBadge
                  label="議事録"
                  value={dataSources.has_transcripts ? `${dataSources.transcript_count}件` : 'なし'}
                  active={dataSources.has_transcripts}
                />
                <DataSourceBadge
                  label="Slackメッセージ"
                  value={dataSources.has_slack_messages ? `${dataSources.slack_message_count}件` : 'なし'}
                  active={dataSources.has_slack_messages}
                />
                <DataSourceBadge
                  label="辞書エントリ"
                  value={`${dataSources.dictionary_entry_count}件`}
                  active={dataSources.dictionary_entry_count > 0}
                />
              </div>
              {dataSources.slack_error && (
                <div
                  style={{
                    marginTop: 'var(--space-3)',
                    padding: 'var(--space-3)',
                    background: 'var(--color-warning-50)',
                    border: '1px solid var(--color-warning-200)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-warning-700)',
                  }}
                >
                  ⚠️ {dataSources.slack_error}
                </div>
              )}
            </div>
          )}

          {/* Editor */}
          <AgendaEditor agenda={generatedAgenda} onSaved={onClose} onCancel={onClose} />
        </div>
      )}
    </Modal>
  )
}
