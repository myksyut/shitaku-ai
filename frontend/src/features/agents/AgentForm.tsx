/**
 * Agent create/edit form component with warm design
 */
import { useState } from 'react'
import { AgentAvatar, Button, Input, Modal, Textarea } from '../../components/ui'
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
  const isPending = createMutation.isPending || updateMutation.isPending

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
    <Modal
      isOpen
      onClose={onClose}
      title={isEditing ? 'エージェントを編集' : '新しいエージェントを作成'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isPending}>
            キャンセル
          </Button>
          <Button variant="primary" onClick={handleSubmit} isLoading={isPending}>
            {isEditing ? '保存する' : '作成する'}
          </Button>
        </>
      }
    >
      {/* Preview Avatar */}
      {name && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-4)',
            marginBottom: 'var(--space-6)',
            padding: 'var(--space-4)',
            background: 'var(--color-cream-200)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <AgentAvatar name={name} size="lg" />
          <div>
            <p
              style={{
                fontSize: 'var(--font-size-xs)',
                color: 'var(--color-warm-gray-500)',
                margin: '0 0 var(--space-1)',
              }}
            >
              プレビュー
            </p>
            <p
              style={{
                fontSize: 'var(--font-size-lg)',
                fontWeight: 700,
                color: 'var(--color-warm-gray-800)',
                margin: 0,
              }}
            >
              {name}
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <Input
          label="エージェント名"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例：週次定例MTG"
          required
          maxLength={100}
          hint="MTGやプロジェクトの名前を入力してください"
        />

        <Textarea
          label="説明（オプション）"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="例：プロダクトチームの週次定例MTG。毎週月曜日に開催。"
          maxLength={500}
          rows={3}
          hint="エージェントの役割や担当するMTGについて"
        />

        {error && (
          <div className="alert alert-error animate-fade-in" style={{ marginTop: 'var(--space-4)' }}>
            {error}
          </div>
        )}
      </form>
    </Modal>
  )
}
