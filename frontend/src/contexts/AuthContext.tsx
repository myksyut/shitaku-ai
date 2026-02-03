import type { Session, User } from '@supabase/supabase-js'
import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { syncProviderToken } from '../features/google/api'
import { supabase } from '../lib/supabase'

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const tokenSyncAttempted = useRef(false)

  useEffect(() => {
    const syncGoogleToken = async (session: Session) => {
      const email = session.user?.email
      if (!email || !session.provider_refresh_token) return

      try {
        await syncProviderToken({
          provider_token: session.provider_token ?? '',
          provider_refresh_token: session.provider_refresh_token,
          email,
          scopes: ['https://www.googleapis.com/auth/calendar.readonly'],
        })
      } catch (error) {
        console.error('Failed to sync Google token:', error)
      }
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
      // 初回セッション取得時にトークン同期を試行
      if (session?.provider_refresh_token && !tokenSyncAttempted.current) {
        tokenSyncAttempted.current = true
        syncGoogleToken(session)
      }
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
      // SIGNED_INイベントでトークン同期
      if (event === 'SIGNED_IN' && session?.provider_refresh_token && !tokenSyncAttempted.current) {
        tokenSyncAttempted.current = true
        syncGoogleToken(session)
      }
      // サインアウト時にフラグリセット
      if (event === 'SIGNED_OUT') {
        tokenSyncAttempted.current = false
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const signInWithGoogle = async () => {
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
  }

  const signOut = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  }

  return (
    <AuthContext.Provider value={{ user, session, loading, signInWithGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider')
  }
  return context
}
