import type { Session } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'
import { AuthPage } from './features/auth'
import { DictionaryPage } from './features/dictionary'
import { supabase } from './lib/supabase'

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

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

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">読み込み中...</div>
  }

  if (!session) {
    return <AuthPage />
  }

  return (
    <div>
      <header className="bg-gray-800 text-white p-4 flex justify-between items-center">
        <span>{session.user.email}</span>
        <button type="button" onClick={() => supabase.auth.signOut()} className="text-sm hover:underline">
          ログアウト
        </button>
      </header>
      <DictionaryPage />
    </div>
  )
}

export default App
