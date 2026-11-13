import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterAll, afterEach, beforeAll } from 'vitest'
import type { MemoryItem, OccurrenceDetail, SeriesDetail } from '../features/series/types'

export const API = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1`
export const occurrence: OccurrenceDetail = {
  occurrence: {
    id: 'occurrence-1',
    start_at: '2099-01-15T10:00:00Z',
    is_cancelled: false,
    has_agenda: false,
    knowledge_count: 0,
    topic_count: 0,
    needs_extraction: false,
  },
  agenda: null,
  topics: [
    {
      id: 'mine',
      title: '自分の議題',
      details: null,
      author_label: '私',
      is_mine: true,
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'theirs',
      title: '他の参加者の議題',
      details: null,
      author_label: '同僚',
      is_mine: false,
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
  knowledge: [],
}
export const series: SeriesDetail = {
  id: 'series-1',
  title: '開発定例',
  role: 'member',
  rrule: 'FREQ=WEEKLY',
  attendees: [],
  occurrences: [occurrence.occurrence],
  settings: { description: null, minutes_count: 3, slack_message_days: 7 },
  slack: null,
  calendar: { integration_id: 'google-1', synced_at: '2026-01-01T00:00:00Z', error: null, google_connected: true },
}
export const actionItem: MemoryItem = {
  id: 'action-1',
  kind: 'action_item',
  body: '見積もりを共有する',
  origin_occurrence_id: 'occurrence-1',
  origin_start_at: '2026-01-01T10:00:00Z',
  extracted: true,
  assignee_email: 'member@example.com',
  due_on: null,
  resolution: null,
  closed_at: null,
  carry_over: 2,
}
export const server = setupServer(
  http.get(`${API}/series`, () => HttpResponse.json({ series: [] })),
  http.get(`${API}/series/series-1`, () => HttpResponse.json(series)),
  http.get(`${API}/series/series-1/memory`, () => HttpResponse.json({ items: [actionItem] })),
  http.get(`${API}/series/series-1/dictionary`, () => HttpResponse.json([])),
  http.get(`${API}/series/series-1/occurrences/occurrence-1`, () => HttpResponse.json(occurrence)),
  http.get(`${API}/google/integrations`, () =>
    HttpResponse.json([
      {
        id: 'google-1',
        email: 'creator@example.com',
        granted_scopes: ['https://www.googleapis.com/auth/calendar.readonly'],
        created_at: '',
        updated_at: null,
      },
    ]),
  ),
  http.get(`${API}/slack/integrations`, () => HttpResponse.json([])),
)
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

export function createQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
}
export function renderPage(element: ReactElement, route = '/') {
  const client = createQueryClient()
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[route]}>{element}</MemoryRouter>
      </QueryClientProvider>,
    ),
  }
}
