/**
 * Agent create/edit form component
 */

import { useState } from 'react'
import { useCreateAgent, useUpdateAgent } from './hooks'
import type { Agent } from './types'

interface Props {
  agent: Agent | null
  onClose: () => void
}

export function AgentForm({ agent, onClose }: Props) {
  const [name, setName] = useState(agent?.name ?? '')
  const [description, setDescription] = useState(agent?.description ?? '')
  const [error, setError] = useState<string | null>(null)

  const createMutation = useCreateAgent()
  const updateMutation = useUpdateAgent()

  const isEditing = !!agent

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('エージェント名は必須です')
      return
    }

    try {
      if (isEditing) {
        await updateMutation.mutateAsync({
          id: agent.id,
          data: {
            name,
            description: description || null,
          },
        })
      } else {
        await createMutation.mutateAsync({
          name,
          description: description || null,
        })
      }
      onClose()
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">{isEditing ? 'エージェント編集' : 'エージェント作成'}</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="agent-name" className="block text-sm font-medium mb-1">
              エージェント名 <span className="text-red-500">*</span>
            </label>
            <input
              id="agent-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required
              maxLength={100}
              placeholder="週次定例MTG"
            />
          </div>

          <div>
            <label htmlFor="agent-description" className="block text-sm font-medium mb-1">
              説明
            </label>
            <textarea
              id="agent-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full border rounded px-3 py-2"
              maxLength={500}
              rows={3}
              placeholder="プロダクトチームの週次定例MTG"
            />
          </div>

          {error && <div className="text-red-500 text-sm">{error}</div>}

          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded hover:bg-gray-50">
              キャンセル
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {isEditing ? '更新' : '作成'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
