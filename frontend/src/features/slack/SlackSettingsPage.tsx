import { useDeleteSlackIntegration, useSlackChannels, useSlackIntegrations, useStartSlackOAuth } from './hooks'
import type { SlackIntegration } from './types'

function WorkspaceItem({ integration }: { integration: SlackIntegration }) {
  const { data: channels, isLoading: channelsLoading } = useSlackChannels(integration.id)
  const deleteIntegration = useDeleteSlackIntegration()

  const handleDelete = () => {
    if (window.confirm(`${integration.workspace_name}との連携を解除しますか？`)) {
      deleteIntegration.mutate(integration.id)
    }
  }

  return (
    <div className="border rounded-lg p-4 mb-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-semibold">{integration.workspace_name}</h3>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleteIntegration.isPending}
          className="text-red-600 hover:text-red-800 disabled:opacity-50"
        >
          {deleteIntegration.isPending ? '解除中...' : '連携解除'}
        </button>
      </div>
      <div className="text-sm text-gray-500 mb-2">
        連携日時: {new Date(integration.created_at).toLocaleString('ja-JP')}
      </div>
      <div className="mt-3">
        <h4 className="text-sm font-medium mb-2">チャンネル一覧</h4>
        {channelsLoading ? (
          <div className="text-gray-500">読み込み中...</div>
        ) : channels && channels.length > 0 ? (
          <ul className="list-disc list-inside text-sm">
            {channels.map((channel) => (
              <li key={channel.id}>#{channel.name}</li>
            ))}
          </ul>
        ) : (
          <div className="text-gray-500 text-sm">チャンネルがありません</div>
        )}
      </div>
    </div>
  )
}

export function SlackSettingsPage() {
  const { data: integrations, isLoading, error } = useSlackIntegrations()
  const startOAuth = useStartSlackOAuth()

  const handleConnect = () => {
    startOAuth.mutate()
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Slack連携設定</h1>

      <div className="mb-6">
        <button
          type="button"
          onClick={handleConnect}
          disabled={startOAuth.isPending}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
        >
          {startOAuth.isPending ? '接続中...' : 'Slackワークスペースを連携'}
        </button>
        {startOAuth.isError && <div className="text-red-600 mt-2">連携の開始に失敗しました。再度お試しください。</div>}
      </div>

      <h2 className="text-xl font-semibold mb-4">連携済みワークスペース</h2>

      {isLoading ? (
        <div className="text-gray-500">読み込み中...</div>
      ) : error ? (
        <div className="text-red-600">連携情報の取得に失敗しました</div>
      ) : integrations && integrations.length > 0 ? (
        <div>
          {integrations.map((integration) => (
            <WorkspaceItem key={integration.id} integration={integration} />
          ))}
        </div>
      ) : (
        <div className="text-gray-500 border rounded-lg p-4">
          連携済みのワークスペースはありません。上のボタンからSlackワークスペースを連携してください。
        </div>
      )}
    </div>
  )
}
