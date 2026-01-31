/**
 * Agent list page component
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AgentForm } from './AgentForm'
import { useAgents, useDeleteAgent } from './hooks'
import type { Agent } from './types'

export function AgentsPage() {
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)

  const { data: agents, isLoading, error } = useAgents()
  const deleteMutation = useDeleteAgent()

  const handleDelete = async (id: string) => {
    if (window.confirm('このエージェントを削除しますか？関連する議事録・アジェンダも削除されます。')) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent)
    setIsFormOpen(true)
  }

  const handleCreate = () => {
    setEditingAgent(null)
    setIsFormOpen(true)
  }

  const handleFormClose = () => {
    setEditingAgent(null)
    setIsFormOpen(false)
  }

  if (isLoading) return <div className="p-4">読み込み中...</div>
  if (error) return <div className="p-4 text-red-500">エラーが発生しました</div>

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">MTGエージェント</h1>
        <button
          type="button"
          onClick={handleCreate}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          新規作成
        </button>
      </div>

      {/* エージェント一覧 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agents?.map((agent) => (
          <div key={agent.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
            <Link to={`/agents/${agent.id}`} className="font-bold text-lg hover:text-blue-500">
              {agent.name}
            </Link>
            {agent.description && <p className="text-sm text-gray-600 mt-1">{agent.description}</p>}
            {agent.slack_channel_id && <p className="text-xs text-gray-500 mt-2">Slack: #{agent.slack_channel_id}</p>}
            <div className="flex gap-2 mt-4">
              <button type="button" onClick={() => handleEdit(agent)} className="text-blue-500 hover:underline text-sm">
                編集
              </button>
              <button
                type="button"
                onClick={() => handleDelete(agent.id)}
                className="text-red-500 hover:underline text-sm"
                disabled={deleteMutation.isPending}
              >
                削除
              </button>
            </div>
          </div>
        ))}
      </div>

      {agents?.length === 0 && (
        <div className="text-center text-gray-500 py-8">エージェントがありません。新規作成してください。</div>
      )}

      {/* フォームモーダル */}
      {isFormOpen && <AgentForm agent={editingAgent} onClose={handleFormClose} />}
    </div>
  )
}
