import { QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { delay, HttpResponse, http } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { API, actionItem, createQueryClient, server } from '../../test/series'
import { seriesKeys, useSetResolution } from './hooks'
import type { TeamMemoryResponse } from './types'

function setup() {
  const client = createQueryClient()
  client.setQueryData(seriesKeys.memory('series-1'), { items: [actionItem] })
  client.setQueryData(seriesKeys.list(), [])
  client.setQueryData(seriesKeys.occurrence('series-1', 'occurrence-1'), {})
  const hook = renderHook(() => useSetResolution('series-1'), {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  })
  return { client, ...hook }
}

describe('memory resolution', () => {
  it('updates immediately, then uses the returned board and invalidates the series', async () => {
    server.use(
      http.put(`${API}/series/series-1/memory/action-1/resolution`, async ({ request }) => {
        expect(await request.json()).toEqual({ resolution: 'done' })
        await delay(200)
        return HttpResponse.json({
          items: [
            { ...actionItem, body: 'サーバーで更新された内容', resolution: 'done', closed_at: '2026-11-13T00:00:00Z' },
          ],
        })
      }),
    )
    const { client, result } = setup()
    act(() => result.current.mutate({ itemId: 'action-1', resolution: 'done' }))
    await waitFor(() =>
      expect(client.getQueryData<TeamMemoryResponse>(seriesKeys.memory('series-1'))?.items[0].resolution).toBe('done'),
    )
    expect(result.current.isPending).toBe(true)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(client.getQueryData<TeamMemoryResponse>(seriesKeys.memory('series-1'))?.items[0].body).toBe(
      'サーバーで更新された内容',
    )
    expect(client.getQueryState(seriesKeys.list())?.isInvalidated).toBe(true)
    expect(client.getQueryState(seriesKeys.occurrence('series-1', 'occurrence-1'))?.isInvalidated).toBe(true)
  })

  it('restores the board if saving fails', async () => {
    server.use(
      http.put(`${API}/series/series-1/memory/action-1/resolution`, () =>
        HttpResponse.json({ detail: 'Forbidden' }, { status: 403 }),
      ),
    )
    const { client, result } = setup()
    act(() => result.current.mutate({ itemId: 'action-1', resolution: 'done' }))
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(client.getQueryData(seriesKeys.memory('series-1'))).toEqual({ items: [actionItem] })
  })
})
