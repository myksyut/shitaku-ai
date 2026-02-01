import { useMemo, useState } from 'react'
import { Button, Card, SlackIcon } from '../../components/ui'
import { useDeleteSlackIntegration, useSlackChannels, useSlackIntegrations, useStartSlackOAuth } from './hooks'
import type { SlackIntegration } from './types'

function WorkspaceItem({ integration }: { integration: SlackIntegration }) {
  const { data: channels, isLoading: channelsLoading } = useSlackChannels(integration.id)
  const deleteIntegration = useDeleteSlackIntegration()
  const [searchQuery, setSearchQuery] = useState('')

  const filteredChannels = useMemo(() => {
    if (!channels) return []
    if (!searchQuery.trim()) return channels
    const query = searchQuery.toLowerCase()
    return channels.filter((channel) => channel.name.toLowerCase().includes(query))
  }, [channels, searchQuery])

  const handleDelete = () => {
    if (window.confirm(`${integration.workspace_name}との連携を解除しますか？`)) {
      deleteIntegration.mutate(integration.id)
    }
  }

  return (
    <Card style={{ marginBottom: 'var(--space-4)' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              background: '#fff',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
            }}
          >
            <SlackIcon size={28} />
          </div>
          <div>
            <h3
              style={{
                fontSize: 'var(--font-size-lg)',
                fontWeight: 700,
                color: 'var(--color-warm-gray-800)',
                marginBottom: 'var(--space-1)',
              }}
            >
              {integration.workspace_name}
            </h3>
            <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
              連携日: {new Date(integration.created_at).toLocaleDateString('ja-JP')}
            </span>
          </div>
        </div>
        <Button variant="ghost" onClick={handleDelete} disabled={deleteIntegration.isPending}>
          {deleteIntegration.isPending ? '解除中...' : '連携解除'}
        </Button>
      </div>

      <div style={{ marginTop: 'var(--space-4)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 'var(--space-2)',
          }}
        >
          <h4
            style={{
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--color-warm-gray-600)',
            }}
          >
            チャンネル一覧
            {channels && channels.length > 0 && (
              <span style={{ fontWeight: 400, marginLeft: 'var(--space-2)' }}>({channels.length}件)</span>
            )}
          </h4>
        </div>
        {channels && channels.length > 10 && (
          <input
            type="text"
            placeholder="チャンネルを検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: 'var(--space-2) var(--space-3)',
              marginBottom: 'var(--space-3)',
              border: '1px solid var(--color-warm-gray-300)',
              borderRadius: 'var(--radius-md)',
              fontSize: 'var(--font-size-sm)',
              outline: 'none',
            }}
          />
        )}
        {channelsLoading ? (
          <span style={{ color: 'var(--color-warm-gray-500)' }}>読み込み中...</span>
        ) : channels && channels.length > 0 ? (
          <>
            {searchQuery && (
              <p
                style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-warm-gray-500)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                {filteredChannels.length}件のチャンネルが見つかりました
              </p>
            )}
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 'var(--space-2)',
                maxHeight: '200px',
                overflowY: 'auto',
              }}
            >
              {filteredChannels.map((channel) => (
                <span
                  key={channel.id}
                  style={{
                    display: 'inline-block',
                    padding: 'var(--space-1) var(--space-3)',
                    background: 'var(--color-cream-200)',
                    borderRadius: 'var(--radius-full)',
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-warm-gray-700)',
                  }}
                >
                  #{channel.name}
                </span>
              ))}
            </div>
          </>
        ) : (
          <span style={{ color: 'var(--color-warm-gray-500)', fontSize: 'var(--font-size-sm)' }}>
            チャンネルがありません
          </span>
        )}
      </div>
    </Card>
  )
}

export function SlackSettingsPage() {
  const { data: integrations, isLoading, error } = useSlackIntegrations()
  const startOAuth = useStartSlackOAuth()

  const handleConnect = () => {
    startOAuth.mutate()
  }

  return (
    <div style={{ maxWidth: '720px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 'var(--space-8)' }}>
        <h1
          style={{
            fontSize: 'var(--font-size-2xl)',
            fontWeight: 800,
            color: 'var(--color-warm-gray-800)',
            marginBottom: 'var(--space-2)',
          }}
        >
          Slack連携設定
        </h1>
        <p style={{ color: 'var(--color-warm-gray-500)' }}>
          SlackワークスペースとShitaku.aiを連携して、チャンネルの会話からアジェンダを自動生成できます。
        </p>
      </div>

      {/* Connect Button */}
      <Card style={{ marginBottom: 'var(--space-6)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 'var(--space-4)',
          }}
        >
          <div>
            <h3
              style={{
                fontSize: 'var(--font-size-base)',
                fontWeight: 600,
                color: 'var(--color-warm-gray-800)',
                marginBottom: 'var(--space-1)',
              }}
            >
              新しいワークスペースを連携
            </h3>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
              Slackの認証画面に遷移します
            </p>
          </div>
          <Button
            variant="primary"
            onClick={handleConnect}
            isLoading={startOAuth.isPending}
            leftIcon={<SlackIcon size={18} />}
          >
            Slackと連携
          </Button>
        </div>
        {startOAuth.isError && (
          <div
            style={{
              marginTop: 'var(--space-3)',
              padding: 'var(--space-3)',
              background: 'var(--color-error-50)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-error-600)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            連携の開始に失敗しました。再度お試しください。
          </div>
        )}
      </Card>

      {/* Connected Workspaces */}
      <h2
        style={{
          fontSize: 'var(--font-size-lg)',
          fontWeight: 700,
          color: 'var(--color-warm-gray-800)',
          marginBottom: 'var(--space-4)',
        }}
      >
        連携済みワークスペース
      </h2>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-warm-gray-500)' }}>
          読み込み中...
        </div>
      ) : error ? (
        <Card>
          <div style={{ textAlign: 'center', color: 'var(--color-error-600)' }}>連携情報の取得に失敗しました</div>
        </Card>
      ) : integrations && integrations.length > 0 ? (
        <div>
          {integrations.map((integration) => (
            <WorkspaceItem key={integration.id} integration={integration} />
          ))}
        </div>
      ) : (
        <Card>
          <div
            style={{
              textAlign: 'center',
              padding: 'var(--space-4)',
            }}
          >
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <SlackIcon size={48} />
            </div>
            <p style={{ color: 'var(--color-warm-gray-600)', marginBottom: 'var(--space-2)' }}>
              連携済みのワークスペースはありません
            </p>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
              上のボタンからSlackワークスペースを連携してください
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}
