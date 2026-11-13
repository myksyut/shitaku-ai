import type { Session } from '@supabase/supabase-js'
import { useEffect, useRef, useState } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { Button, SlackIcon } from './components/ui'
import { GoogleIcon } from './components/ui/GoogleIcon'
import { AuthPage } from './features/auth'
import { GoogleIntegrationPage } from './features/google'
import { syncProviderToken } from './features/google/api'
import { OccurrencePage, SeriesListPage, SeriesPage } from './features/series'
import { SlackSettingsPage } from './features/slack'
import { supabase } from './lib/supabase'
import { UserQueryProvider } from './lib/user-query-provider'

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

function AuthenticatedApp({ session }: { session: Session }) {
  const tokenSyncAttempted = useRef(false)

  useEffect(() => {
    const email = session.user.email
    if (!email || !session.provider_refresh_token || tokenSyncAttempted.current) return
    tokenSyncAttempted.current = true

    syncProviderToken({
      provider_token: session.provider_token ?? '',
      provider_refresh_token: session.provider_refresh_token,
      email,
      scopes: ['https://www.googleapis.com/auth/calendar.readonly'],
    }).catch((error) => {
      console.error('Failed to sync Google token:', error)
    })
  }, [session])

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

      <main
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: 'var(--space-8) var(--space-6)',
        }}
      >
        <Routes>
          <Route path="/" element={<SeriesListPage />} />
          <Route path="/series/:seriesId" element={<SeriesPage />} />
          <Route path="/series/:seriesId/occurrences/:occurrenceId" element={<OccurrencePage />} />
          <Route path="/settings/slack" element={<SlackSettingsPage />} />
          <Route path="/settings/google" element={<GoogleIntegrationPage />} />
          <Route
            path="*"
            element={
              <p>
                ページが見つかりません。<Link to="/">定例一覧へ戻る</Link>
              </p>
            }
          />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    let authChanged = false
    const applySession = (next: Session | null) => {
      if (!active) return
      setSession(next)
      setLoading(false)
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!active || authChanged) return
      applySession(session)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      authChanged = true
      applySession(session)
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [])

  if (loading) return <LoadingScreen />
  if (!session) return <AuthPage />

  return (
    <UserQueryProvider userId={session.user.id}>
      <AuthenticatedApp session={session} />
    </UserQueryProvider>
  )
}

export default App
