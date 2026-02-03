/**
 * Authentication page with Google SSO
 */
import { useState } from 'react'
import { Button } from '../../components/ui'
import { supabase } from '../../lib/supabase'

export function AuthPage() {
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleGoogleSignIn = async () => {
    setError(null)
    setLoading(true)

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/`,
          scopes: 'https://www.googleapis.com/auth/calendar.readonly',
          queryParams: {
            access_type: 'offline',
            prompt: 'consent',
          },
        },
      })
      if (error) throw error
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました')
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-4)',
        background: `
          radial-gradient(ellipse at 20% 80%, var(--color-primary-100) 0%, transparent 50%),
          radial-gradient(ellipse at 80% 20%, var(--color-cream-400) 0%, transparent 45%),
          var(--color-cream-100)
        `,
      }}
    >
      <div
        className="animate-slide-up"
        style={{
          width: '100%',
          maxWidth: '420px',
        }}
      >
        {/* Logo & Welcome */}
        <div
          style={{
            textAlign: 'center',
            marginBottom: 'var(--space-8)',
          }}
        >
          <img
            src="/favicon.png"
            alt="Shitaku.ai"
            className="animate-float"
            style={{
              width: '80px',
              height: '80px',
              margin: '0 auto var(--space-4)',
              borderRadius: 'var(--radius-xl)',
              boxShadow: '0 8px 32px rgba(255, 153, 102, 0.35)',
            }}
          />
          <h1
            style={{
              fontSize: 'var(--font-size-3xl)',
              fontWeight: 800,
              color: 'var(--color-warm-gray-800)',
              margin: '0 0 var(--space-2)',
              letterSpacing: '-0.02em',
            }}
          >
            Shitaku.ai
          </h1>
          <p
            style={{
              fontSize: 'var(--font-size-base)',
              color: 'var(--color-warm-gray-500)',
              margin: 0,
            }}
          >
            あなたの専属AIエージェントが
            <br />
            MTGの支度を整えます
          </p>
        </div>

        {/* Auth Card */}
        <div
          className="card-clay"
          style={{
            padding: 'var(--space-8)',
          }}
        >
          <h2
            style={{
              fontSize: 'var(--font-size-xl)',
              fontWeight: 700,
              color: 'var(--color-warm-gray-800)',
              margin: '0 0 var(--space-6)',
              textAlign: 'center',
            }}
          >
            ログイン
          </h2>

          {error && (
            <div className="alert alert-error animate-fade-in" style={{ marginBottom: 'var(--space-4)' }}>
              {error}
            </div>
          )}

          <Button
            type="button"
            size="lg"
            isLoading={loading}
            onClick={handleGoogleSignIn}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 'var(--space-3)',
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" role="img" aria-label="Google">
              <title>Google</title>
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            Googleでログイン
          </Button>
        </div>

        {/* Footer */}
        <p
          style={{
            textAlign: 'center',
            marginTop: 'var(--space-6)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-warm-gray-400)',
          }}
        >
          sitaku.ai - MTGの準備をもっとスマートに
        </p>
      </div>
    </div>
  )
}
