import { EventEmitter, once } from 'node:events'
import type { Session } from '@supabase/supabase-js'
import { type QueryClient, useQueryClient } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { useEffect } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { seriesKeys, useClaimSeries } from '../features/series/hooks'
import type { SeriesDetail } from '../features/series/types'
import { API, series, server } from '../test/series'
import { supabase } from './supabase'
import { UserQueryProvider } from './user-query-provider'

function ClaimControl({ captureClient }: { captureClient: (client: QueryClient) => void }) {
  const client = useQueryClient()
  const claim = useClaimSeries()
  useEffect(() => {
    captureClient(client)
  }, [captureClient, client])
  return (
    <button
      type="button"
      onClick={() =>
        claim.mutate({
          google_integration_id: 'google-alice',
          calendar_event_id: 'event-alice',
        })
      }
    >
      定例を追加
    </button>
  )
}

describe('user query isolation', () => {
  it('keeps a late claim response in Alice’s discarded client after switching to Bob', async () => {
    const alice: Session = {
      access_token: 'token-alice',
      refresh_token: '',
      expires_in: 3600,
      token_type: 'bearer',
      user: {
        id: 'alice',
        aud: 'authenticated',
        email: 'alice@example.com',
        app_metadata: {},
        user_metadata: {},
        created_at: '',
      },
    }
    const bob: Session = {
      ...alice,
      access_token: 'token-bob',
      user: { ...alice.user, id: 'bob', email: 'bob@example.com' },
    }
    const claimed: SeriesDetail = { ...series, title: 'アリスだけの定例', role: 'creator' }
    const gate = new EventEmitter()
    let received = false
    server.use(
      http.post(`${API}/series`, async ({ request }) => {
        expect(request.headers.get('authorization')).toBe('Bearer token-alice')
        expect(await request.json()).toEqual({
          google_integration_id: 'google-alice',
          calendar_event_id: 'event-alice',
        })
        received = true
        await once(gate, 'release')
        return HttpResponse.json({ outcome: 'created', series: claimed }, { status: 201 })
      }),
    )
    const clients: QueryClient[] = []
    const captureClient = (client: QueryClient) => {
      clients.push(client)
    }
    const surface = (userId: string) => (
      <UserQueryProvider userId={userId}>
        <ClaimControl captureClient={captureClient} />
      </UserQueryProvider>
    )
    vi.mocked(supabase.auth.getSession).mockResolvedValue({ data: { session: alice }, error: null })
    const { rerender } = render(surface('alice'))
    const aliceClient = clients[0]
    await userEvent.click(screen.getByRole('button', { name: '定例を追加' }))
    await waitFor(() => expect(received).toBe(true))
    const mutation = aliceClient.getMutationCache().getAll()[0]
    try {
      rerender(surface('alice'))
      expect(clients).toHaveLength(1)
      expect(mutation.state.status).toBe('pending')

      vi.mocked(supabase.auth.getSession).mockResolvedValue({ data: { session: bob }, error: null })
      rerender(surface('bob'))
      const bobClient = clients[1]
      expect(bobClient).not.toBe(aliceClient)
      bobClient.setQueryData(['bob-private'], 'Bob only')
      gate.emit('release')
      await waitFor(() => expect(mutation.state.status).toBe('success'))

      expect(aliceClient.getQueryData(seriesKeys.detail(claimed.id))).toEqual(claimed)
      expect(bobClient.getQueryData(seriesKeys.detail(claimed.id))).toBeUndefined()
      expect(
        bobClient
          .getQueryCache()
          .getAll()
          .map((query) => query.state.data),
      ).toEqual(['Bob only'])
      aliceClient.clear()
      bobClient.clear()
    } finally {
      gate.emit('release')
    }
  })
})
