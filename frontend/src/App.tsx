/**
 * Main App component with warm, agent-centric design
 * Using react-router-dom for navigation
 */
import type { Session } from '@supabase/supabase-js'
import { useEffect, useRef, useState } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { Button, SlackIcon } from './components/ui'
import { GoogleIcon } from './components/ui/GoogleIcon'
import { AgentDetailPage, AgentsPage } from './features/agents'
import { AuthPage } from './features/auth'
import { GoogleIntegrationPage, TranscriptViewer } from './features/google'
import { syncProviderToken } from './features/google/api'
import { SlackSettingsPage } from './features/slack'
import { supabase } from './lib/supabase'

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
      <img
        className="animate-float"
        src="/favicon.png"
        alt="Shitaku.ai"
        style={{
          width: '64px',
          height: '64px',
          borderRadius: 'var(--radius-xl)',
        }}
      />
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
  onLogout: () => void
}

function Header({ email, onLogout }: HeaderProps) {
  const location = useLocation()
  const currentPath = location.pathname

  const isSlackSettings = currentPath === '/settings/slack'
  const isGoogleSettings = currentPath.startsWith('/settings/google')

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
      <Link
        to="/"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-3)',
          textDecoration: 'none',
        }}
      >
        <img
          src="/favicon.png"
          alt="Shitaku.ai"
          style={{
            width: '40px',
            height: '40px',
            borderRadius: 'var(--radius-md)',
          }}
        />
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
      </Link>

      {/* Navigation & User Menu */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
        }}
      >
        <Link to="/settings/slack" style={{ textDecoration: 'none' }}>
          <Button variant={isSlackSettings ? 'secondary' : 'ghost'} style={{ gap: 'var(--space-2)' }}>
            <SlackIcon size={16} />
            Slack連携
          </Button>
        </Link>
        <Link to="/settings/google" style={{ textDecoration: 'none' }}>
          <Button variant={isGoogleSettings ? 'secondary' : 'ghost'} style={{ gap: 'var(--space-2)' }}>
            <GoogleIcon size={16} />
            Google連携
          </Button>
        </Link>
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
  const tokenSyncAttempted = useRef(false)

  useEffect(() => {
    const syncGoogleToken = async (sess: Session) => {
      const email = sess.user?.email
      if (!email || !sess.provider_refresh_token) return

      try {
        await syncProviderToken({
          provider_token: sess.provider_token ?? '',
          provider_refresh_token: sess.provider_refresh_token,
          email,
          scopes: ['https://www.googleapis.com/auth/calendar.readonly'],
        })
      } catch (error) {
        console.error('Failed to sync Google token:', error)
      }
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
      if (session?.provider_refresh_token && !tokenSyncAttempted.current) {
        tokenSyncAttempted.current = true
        syncGoogleToken(session)
      }
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      setSession(session)
      if (event === 'SIGNED_IN' && session?.provider_refresh_token && !tokenSyncAttempted.current) {
        tokenSyncAttempted.current = true
        syncGoogleToken(session)
      }
      if (event === 'SIGNED_OUT') {
        tokenSyncAttempted.current = false
      }
    })

    return () => subscription.unsubscribe()
  }, [])

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
      <Header email={session.user.email ?? ''} onLogout={() => supabase.auth.signOut()} />

      {/* Main Content */}
      <main
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: 'var(--space-8) var(--space-6)',
        }}
      >
        <Routes>
          <Route path="/" element={<AgentsPage />} />
          <Route path="/agents/:agentId" element={<AgentDetailPage />} />
          <Route path="/settings/slack" element={<SlackSettingsPage />} />
          <Route path="/settings/google" element={<GoogleIntegrationPage />} />
          <Route path="/meetings/:meetingId/transcripts" element={<TranscriptViewer />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
