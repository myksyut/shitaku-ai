import type { Session } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'
import { AgendaGeneratePage } from './features/agendas'
import { AuthPage } from './features/auth'
import { DictionaryPage } from './features/dictionary'
import { supabase } from './lib/supabase'

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [showAgendaModal, setShowAgendaModal] = useState(false)
  const [testAgentId, setTestAgentId] = useState('')

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
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Agent ID (テスト用)"
              value={testAgentId}
              onChange={(e) => setTestAgentId(e.target.value)}
              className="px-2 py-1 text-sm text-gray-900 rounded"
            />
            <button
              type="button"
              onClick={() => setShowAgendaModal(true)}
              disabled={!testAgentId}
              className="text-sm bg-blue-500 px-3 py-1 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              アジェンダ生成
            </button>
          </div>
          <button type="button" onClick={() => supabase.auth.signOut()} className="text-sm hover:underline">
            ログアウト
          </button>
        </div>
      </header>
      <DictionaryPage />
      {showAgendaModal && <AgendaGeneratePage agentId={testAgentId} onClose={() => setShowAgendaModal(false)} />}
    </div>
  )
}

export default App
