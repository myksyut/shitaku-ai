/**
 * Agent detail page component
 */

import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAgent, useDeleteAgent } from './hooks'

export function AgentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const agentId = id ?? ''
  const { data: agent, isLoading, error } = useAgent(agentId)
  const deleteMutation = useDeleteAgent()

  const handleDelete = async () => {
    if (window.confirm('このエージェントを削除しますか？関連する議事録・アジェンダも削除されます。')) {
      await deleteMutation.mutateAsync(agentId)
      navigate('/agents')
    }
  }

  if (!id) return <div className="p-4">エージェントIDが指定されていません</div>
  if (isLoading) return <div className="p-4">読み込み中...</div>
  if (error) return <div className="p-4 text-red-500">エラーが発生しました</div>
  if (!agent) return <div className="p-4">エージェントが見つかりません</div>

  return (
    <div className="p-4">
      <div className="mb-4">
        <Link to="/agents" className="text-blue-500 hover:underline">
          ← エージェント一覧に戻る
        </Link>
      </div>

      <div className="bg-white rounded-lg border p-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold">{agent.name}</h1>
            {agent.description && <p className="text-gray-600 mt-2">{agent.description}</p>}
          </div>
          <button
            type="button"
            onClick={handleDelete}
            className="text-red-500 hover:underline"
            disabled={deleteMutation.isPending}
          >
            削除
          </button>
        </div>

        {agent.slack_channel_id && (
          <div className="mt-4 p-3 bg-gray-50 rounded">
            <span className="text-sm text-gray-500">Slackチャンネル:</span>
            <span className="ml-2">#{agent.slack_channel_id}</span>
          </div>
        )}

        <div className="mt-6 flex gap-4">
          <Link
            to={`/agents/${agent.id}/meeting-notes`}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            議事録一覧
          </Link>
          <Link
            to={`/agents/${agent.id}/agendas/generate`}
            className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
          >
            アジェンダ生成
          </Link>
        </div>
      </div>
    </div>
  )
}
