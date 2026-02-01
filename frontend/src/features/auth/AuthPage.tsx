/**
 * Authentication page with warm, welcoming design
 */
import { useState } from 'react'
import { Button, Input } from '../../components/ui'
import { supabase } from '../../lib/supabase'

export function AuthPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSignUp, setIsSignUp] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (isSignUp) {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (error) throw error
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました')
    } finally {
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
            {isSignUp ? 'アカウントを作成' : 'おかえりなさい'}
          </h2>

          <form onSubmit={handleSubmit}>
            <Input
              label="メールアドレス"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />

            <Input
              label="パスワード"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="6文字以上"
              required
              minLength={6}
              autoComplete={isSignUp ? 'new-password' : 'current-password'}
            />

            {error && (
              <div className="alert alert-error animate-fade-in" style={{ marginBottom: 'var(--space-4)' }}>
                {error}
              </div>
            )}

            <Button type="submit" size="lg" isLoading={loading} style={{ width: '100%' }}>
              {isSignUp ? 'アカウントを作成' : 'ログイン'}
            </Button>
          </form>

          {/* Toggle auth mode */}
          <div
            style={{
              marginTop: 'var(--space-6)',
              textAlign: 'center',
            }}
          >
            <button
              type="button"
              onClick={() => {
                setIsSignUp(!isSignUp)
                setError(null)
              }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-primary-600)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'var(--font-family)',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = 'var(--color-primary-700)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = 'var(--color-primary-600)'
              }}
            >
              {isSignUp ? 'すでにアカウントをお持ちの方はこちら' : 'アカウントをお持ちでない方はこちら'}
            </button>
          </div>
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
