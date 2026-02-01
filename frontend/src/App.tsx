/**
 * Main App component with warm, agent-centric design
 */
import type { Session } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'
import { Button } from './components/ui'
import { AgendaGeneratePage } from './features/agendas'
import { AgentDetailPage, AgentsPage } from './features/agents'
import { AuthPage } from './features/auth'
import { SlackSettingsPage } from './features/slack'
import { supabase } from './lib/supabase'

type PageView = 'agents' | 'agent-detail' | 'slack-settings'

function LoadingScreen() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 'var(--space-4)',
        background: 'var(--color-cream-100)',
      }}
    >
      <div
        className="animate-float"
        style={{
          width: '64px',
          height: '64px',
          background: 'linear-gradient(145deg, var(--color-primary-400), var(--color-primary-500))',
          borderRadius: 'var(--radius-xl)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '28px',
          boxShadow: '0 8px 32px rgba(255, 153, 102, 0.35)',
        }}
      >
        🤖
      </div>
      <span
        style={{
          fontSize: 'var(--font-size-base)',
          fontWeight: 500,
          color: 'var(--color-warm-gray-500)',
        }}
      >
        読み込み中...
      </span>
    </div>
  )
}

interface HeaderProps {
  email: string
  currentPage: PageView
  onNavigate: (page: PageView) => void
  onLogout: () => void
}

function Header({ email, currentPage, onNavigate, onLogout }: HeaderProps) {
  return (
    <header
      className="glass"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        padding: 'var(--space-4) var(--space-6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid var(--color-cream-300)',
      }}
    >
      {/* Logo */}
      <button
        type="button"
        onClick={() => onNavigate('agents')}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-3)',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
        }}
      >
        <div
          style={{
            width: '40px',
            height: '40px',
            background: 'linear-gradient(145deg, var(--color-primary-400), var(--color-primary-500))',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            boxShadow: '0 4px 12px rgba(255, 153, 102, 0.25)',
          }}
        >
          🤖
        </div>
        <span
          style={{
            fontSize: 'var(--font-size-lg)',
            fontWeight: 800,
            color: 'var(--color-warm-gray-800)',
            letterSpacing: '-0.02em',
          }}
        >
          Shitaku.ai
        </span>
      </button>

      {/* Navigation & User Menu */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
        }}
      >
        <Button
          variant={currentPage === 'slack-settings' ? 'secondary' : 'ghost'}
          onClick={() => onNavigate('slack-settings')}
          style={{ gap: 'var(--space-2)' }}
        >
          <span style={{ fontSize: '16px' }}>💬</span>
          Slack連携
        </Button>
        <span
          style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-warm-gray-500)',
            marginLeft: 'var(--space-2)',
          }}
        >
          {email}
        </span>
        <Button variant="ghost" onClick={onLogout}>
          ログアウト
        </Button>
      </div>
    </header>
  )
}

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState<PageView>('agents')
  const [viewingAgentId, setViewingAgentId] = useState<string | null>(null)
  const [generatingAgendaForAgentId, setGeneratingAgendaForAgentId] = useState<string | null>(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  const handleViewAgent = (agentId: string) => {
    setViewingAgentId(agentId)
    setCurrentPage('agent-detail')
  }

  const handleBackToAgents = () => {
    setViewingAgentId(null)
    setCurrentPage('agents')
  }

  const handleNavigate = (page: PageView) => {
    if (page === 'agents') {
      setViewingAgentId(null)
    }
    setCurrentPage(page)
  }

  if (loading) {
    return <LoadingScreen />
  }

  if (!session) {
    return <AuthPage />
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: `
          radial-gradient(ellipse at 10% 90%, var(--color-primary-50) 0%, transparent 40%),
          radial-gradient(ellipse at 90% 10%, var(--color-cream-300) 0%, transparent 35%),
          var(--color-cream-100)
        `,
      }}
    >
      <Header
        email={session.user.email ?? ''}
        currentPage={currentPage}
        onNavigate={handleNavigate}
        onLogout={() => supabase.auth.signOut()}
      />

      {/* Main Content */}
      <main
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: 'var(--space-8) var(--space-6)',
        }}
      >
        {currentPage === 'agents' && <AgentsPage onViewAgent={handleViewAgent} />}
        {currentPage === 'agent-detail' && viewingAgentId && (
          <AgentDetailPage
            agentId={viewingAgentId}
            onBack={handleBackToAgents}
            onGenerateAgenda={() => setGeneratingAgendaForAgentId(viewingAgentId)}
          />
        )}
        {currentPage === 'slack-settings' && <SlackSettingsPage />}
      </main>

      {/* Agenda Generation Modal */}
      {generatingAgendaForAgentId && (
        <AgendaGeneratePage agentId={generatingAgendaForAgentId} onClose={() => setGeneratingAgendaForAgentId(null)} />
      )}
    </div>
  )
}

export default App
