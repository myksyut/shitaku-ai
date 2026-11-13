import type { Session } from '@supabase/supabase-js'
import { act, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { supabase } from './lib/supabase'
import { renderPage } from './test/series'

let authChange: Parameters<typeof supabase.auth.onAuthStateChange>[0] | undefined

function session(id: string): Session {
  return {
    access_token: `token-${id}`,
    refresh_token: 'refresh-token',
    expires_in: 3600,
    token_type: 'bearer',
    user: {
      id,
      email: `${id}@example.com`,
      aud: 'authenticated',
      app_metadata: {},
      user_metadata: {},
      created_at: '2026-01-01T00:00:00Z',
    },
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  authChange = undefined
  vi.mocked(supabase.auth.getSession).mockResolvedValue({ data: { session: null }, error: null })
  vi.mocked(supabase.auth.onAuthStateChange).mockImplementation((callback) => {
    authChange = callback
    return { data: { subscription: { id: 'subscription', callback, unsubscribe: vi.fn() } } }
  })
})

describe('App', () => {
  it('loads the login screen when signed out', async () => {
    renderPage(<App />)
    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'ログイン' })).toBeInTheDocument()
  })

  it('clears every account cache on user changes and logout, not on token refresh', async () => {
    const alice = session('alice')
    vi.mocked(supabase.auth.getSession).mockResolvedValue({ data: { session: alice }, error: null })
    const { client } = renderPage(<App />)
    expect(await screen.findByText('alice@example.com')).toBeInTheDocument()
    client.setQueryData(['private', 'memory'], 'Alice only')

    await act(async () => {
      await authChange?.('TOKEN_REFRESHED', alice)
    })
    expect(client.getQueryData(['private', 'memory'])).toBe('Alice only')

    const bob = session('bob')
    vi.mocked(supabase.auth.getSession).mockResolvedValue({ data: { session: bob }, error: null })
    await act(async () => {
      await authChange?.('SIGNED_IN', bob)
    })
    expect(await screen.findByText('bob@example.com')).toBeInTheDocument()
    expect(screen.queryByText('alice@example.com')).not.toBeInTheDocument()
    expect(client.getQueryData(['private', 'memory'])).toBeUndefined()

    client.setQueryData(['private', 'google'], 'Bob credentials')
    vi.mocked(supabase.auth.getSession).mockResolvedValue({ data: { session: null }, error: null })
    await act(async () => {
      await authChange?.('SIGNED_OUT', null)
    })
    await waitFor(() => expect(client.getQueryData(['private', 'google'])).toBeUndefined())
    expect(await screen.findByRole('heading', { name: 'ログイン' })).toBeInTheDocument()
  })
})
