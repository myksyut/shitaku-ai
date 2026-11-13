import { QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { delay, HttpResponse, http } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { API, actionItem, createQueryClient, occurrence, series, server } from '../../test/series'
import {
  seriesKeys,
  useGenerateAgenda,
  useOccurrence,
  useSetResolution,
  useTeamMemory,
  useTranscriptCandidates,
} from './hooks'
import type { TeamMemoryResponse } from './types'

function setup() {
  const client = createQueryClient()
  client.setQueryData(seriesKeys.memory('series-1'), { items: [actionItem] })
  client.setQueryData(seriesKeys.list(), [])
  client.setQueryData(seriesKeys.detail('series-1'), series)
  client.setQueryData(seriesKeys.transcriptCandidates('series-1', 'occurrence-1'), [])
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
    expect(client.getQueryState(seriesKeys.detail('series-1'))?.isInvalidated).toBe(true)
    expect(client.getQueryState(seriesKeys.memory('series-1'))?.isInvalidated).toBe(false)
    expect(client.getQueryState(seriesKeys.occurrence('series-1', 'occurrence-1'))?.isInvalidated).toBe(false)
    expect(client.getQueryState(seriesKeys.transcriptCandidates('series-1', 'occurrence-1'))?.isInvalidated).toBe(false)
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

describe('mutation query scope', () => {
  it('uses the returned memory board without refetching memory or live Drive candidates', async () => {
    let memoryReads = 0
    let driveReads = 0
    const board = { items: [{ ...actionItem, body: '更新済みのメモリ' }] }
    server.use(
      http.get(`${API}/series/series-1/memory`, () => {
        memoryReads += 1
        return HttpResponse.json({ items: [actionItem] })
      }),
      http.get(`${API}/series/series-1/occurrences/occurrence-1/transcript-candidates`, () => {
        driveReads += 1
        return HttpResponse.json({ candidates: [] })
      }),
      http.put(`${API}/series/series-1/memory/action-1/resolution`, () => HttpResponse.json(board)),
    )
    const client = createQueryClient()
    const { result } = renderHook(
      () => ({
        memory: useTeamMemory('series-1'),
        candidates: useTranscriptCandidates('series-1', 'occurrence-1', true),
        resolution: useSetResolution('series-1'),
      }),
      {
        wrapper: ({ children }: { children: ReactNode }) => (
          <QueryClientProvider client={client}>{children}</QueryClientProvider>
        ),
      },
    )
    await waitFor(() => expect(result.current.memory.isSuccess && result.current.candidates.isSuccess).toBe(true))
    await act(async () => {
      await result.current.resolution.mutateAsync({ itemId: actionItem.id, resolution: 'done' })
    })
    await waitFor(() => expect(result.current.memory.data).toEqual(board))
    expect(memoryReads).toBe(1)
    expect(driveReads).toBe(1)
  })

  it('refreshes only the occurrence after agenda generation, not its transcript candidates', async () => {
    let occurrenceReads = 0
    let driveReads = 0
    let generated = false
    const agenda = { occurrence_id: 'occurrence-1', content: '## 議題', generated_at: '', updated_at: 'generated' }
    server.use(
      http.get(`${API}/series/series-1/occurrences/occurrence-1`, () => {
        occurrenceReads += 1
        return HttpResponse.json({ ...occurrence, agenda: generated ? agenda : null })
      }),
      http.get(`${API}/series/series-1/occurrences/occurrence-1/transcript-candidates`, () => {
        driveReads += 1
        return HttpResponse.json({ candidates: [] })
      }),
      http.post(`${API}/series/series-1/occurrences/occurrence-1/agenda`, () => {
        generated = true
        return HttpResponse.json({
          agenda,
          sources: {
            topics: 0,
            carried_action_items: 0,
            open_issues: 0,
            knowledge: 0,
            slack_messages: 0,
            slack_error: null,
            calendar_error: null,
          },
        })
      }),
    )
    const client = createQueryClient()
    client.setQueryData(seriesKeys.detail('series-1'), series)
    client.setQueryData(seriesKeys.memory('series-1'), { items: [actionItem] })
    client.setQueryData(seriesKeys.dictionary('series-1'), [])
    client.setQueryData(seriesKeys.list(), [])
    const { result } = renderHook(
      () => ({
        occurrence: useOccurrence('series-1', 'occurrence-1'),
        candidates: useTranscriptCandidates('series-1', 'occurrence-1', true),
        generate: useGenerateAgenda('series-1', 'occurrence-1'),
      }),
      {
        wrapper: ({ children }: { children: ReactNode }) => (
          <QueryClientProvider client={client}>{children}</QueryClientProvider>
        ),
      },
    )
    await waitFor(() => expect(result.current.occurrence.isSuccess && result.current.candidates.isSuccess).toBe(true))
    await act(async () => {
      await result.current.generate.mutateAsync()
    })
    await waitFor(() => expect(result.current.occurrence.data?.agenda).toEqual(agenda))
    expect(occurrenceReads).toBe(2)
    expect(driveReads).toBe(1)
    for (const key of [
      seriesKeys.detail('series-1'),
      seriesKeys.memory('series-1'),
      seriesKeys.dictionary('series-1'),
      seriesKeys.list(),
    ]) {
      expect(client.getQueryState(key)?.isInvalidated).toBe(false)
    }
  })
})
