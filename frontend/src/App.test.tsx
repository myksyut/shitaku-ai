import type { AuthChangeEvent, Session } from '@supabase/supabase-js'
import { act, render, screen } from '@testing-library/react'
import { HttpResponse, http } from 'msw'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { supabase } from './lib/supabase'
import { API, server } from './test/series'

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

async function changeSession(event: AuthChangeEvent, next: Session | null) {
  vi.mocked(supabase.auth.getSession).mockResolvedValue({ data: { session: next }, error: null })
  await act(async () => {
    await authChange?.(event, next)
  })
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
  it('loads the login screen without an authenticated query client', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'ログイン' })).toBeInTheDocument()
  })

  it('preserves a user client across token refresh and replaces it on account changes and logout', async () => {
    const alice = session('alice')
    const bob = session('bob')
    const requests = { alice: 0, bob: 0 }
    server.use(
      http.get(`${API}/series`, ({ request }) => {
        const authorization = request.headers.get('authorization')
        expect(['Bearer token-alice', 'Bearer token-bob']).toContain(authorization)
        const user = authorization === 'Bearer token-alice' ? 'alice' : 'bob'
        requests[user] += 1
        return HttpResponse.json({
          series: [
            {
              id: 'series-1',
              title: `${user}の定例`,
              role: 'member',
              next_occurrence: null,
              open_action_items: 0,
              calendar_sync_error: null,
            },
          ],
        })
      }),
    )
    vi.mocked(supabase.auth.getSession).mockResolvedValue({ data: { session: alice }, error: null })
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )
    expect(await screen.findByRole('heading', { name: 'aliceの定例' })).toBeInTheDocument()

    await changeSession('TOKEN_REFRESHED', { ...alice, expires_in: 7200 })
    expect(screen.getByRole('heading', { name: 'aliceの定例' })).toBeInTheDocument()
    expect(requests).toEqual({ alice: 1, bob: 0 })

    await changeSession('SIGNED_IN', bob)
    expect(await screen.findByRole('heading', { name: 'bobの定例' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'aliceの定例' })).not.toBeInTheDocument()
    expect(requests).toEqual({ alice: 1, bob: 1 })

    await changeSession('SIGNED_OUT', null)
    expect(await screen.findByRole('heading', { name: 'ログイン' })).toBeInTheDocument()
    await changeSession('SIGNED_IN', bob)
    expect(await screen.findByRole('heading', { name: 'bobの定例' })).toBeInTheDocument()
    expect(requests).toEqual({ alice: 1, bob: 2 })
  })
})
