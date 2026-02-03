/**
 * Agent list page - Dashboard with agent-centric design
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AgentAvatar, Button, Card, EmptyState, SlackIcon } from '../../components/ui'
import { useKnowledgeList } from '../knowledge/hooks'
import { AgentForm } from './AgentForm'
import { useAgents } from './hooks'
import type { Agent } from './types'

interface AgentCardProps {
  agent: Agent
  onClick: () => void
}

function AgentCard({ agent, onClick }: AgentCardProps) {
  const { data: knowledgeList } = useKnowledgeList(agent.id, 5)
  const knowledgeCount = knowledgeList?.length ?? 0

  return (
    <Card
      variant="clay"
      className="animate-fade-in card-interactive"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        cursor: 'pointer',
      }}
      onClick={onClick}
    >
      {/* Agent Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 'var(--space-4)',
          marginBottom: 'var(--space-4)',
        }}
      >
        <AgentAvatar name={agent.name} size="md" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3
            style={{
              fontSize: 'var(--font-size-lg)',
              fontWeight: 700,
              color: 'var(--color-warm-gray-800)',
              margin: '0 0 var(--space-1)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {agent.name}
          </h3>
          {agent.slack_channel_id && (
            <span
              className="badge"
              style={{
                fontSize: 'var(--font-size-xs)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <SlackIcon size={12} /> Slack連携中
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      {agent.description && (
        <p
          style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-warm-gray-600)',
            margin: '0 0 var(--space-4)',
            flex: 1,
            lineHeight: 1.6,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {agent.description}
        </p>
      )}

      {/* Stats */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-4)',
          paddingTop: 'var(--space-3)',
          borderTop: '1px solid var(--color-cream-300)',
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-warm-gray-500)',
        }}
      >
        <span>📝 ナレッジ {knowledgeCount}件</span>
      </div>
    </Card>
  )
}

export function AgentsPage() {
  const [isFormOpen, setIsFormOpen] = useState(false)
  const navigate = useNavigate()

  const { data: agents, isLoading, error } = useAgents()

  const handleViewAgent = (agentId: string) => {
    navigate(`/agents/${agentId}`)
  }

  const handleCreate = () => {
    setIsFormOpen(true)
  }

  const handleFormClose = () => {
    setIsFormOpen(false)
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

  if (error) {
    return (
      <div className="alert alert-error" style={{ margin: 'var(--space-4)' }}>
        エラーが発生しました。ページを再読み込みしてください。
      </div>
    )
  }

  return (
    <div>
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
              margin: '0 0 var(--space-1)',
            }}
          >
            あなたのAIエージェント
          </h1>
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warm-gray-500)',
              margin: 0,
            }}
          >
            MTGごとに専属の秘書がお手伝いします
          </p>
        </div>
        <Button variant="primary" onClick={handleCreate}>
          <span style={{ marginRight: 'var(--space-2)' }}>+</span>
          新しいエージェント
        </Button>
      </div>

      {/* Agent Grid */}
      {agents && agents.length > 0 ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: 'var(--space-6)',
          }}
        >
          {agents.map((agent, index) => (
            <div
              key={agent.id}
              className={`stagger-${Math.min(index + 1, 5)}`}
              style={{ opacity: 0, animation: 'fadeIn 0.4s ease-out forwards' }}
            >
              <AgentCard agent={agent} onClick={() => handleViewAgent(agent.id)} />
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<img src="/favicon.png" alt="Agent" style={{ width: '120px', height: '120px' }} />}
          title="まだエージェントがいません"
          description="最初のAIエージェントを作成して、MTGの準備を自動化しましょう"
          action={
            <Button variant="primary" onClick={handleCreate}>
              最初のエージェントを作成
            </Button>
          }
        />
      )}

      {/* Form Modal */}
      {isFormOpen && <AgentForm agent={null} onClose={handleFormClose} />}
    </div>
  )
}
