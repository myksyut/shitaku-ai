import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { HttpResponse, http } from 'msw'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { SeriesPage } from '../features/series/SeriesPage'
import { API, server } from '../test/series'
import { ApiError, apiClient } from './api-client'
import { createAppQueryClient } from './query-client'

const queryKey = ['retry-probe']

describe('application query retry policy', () => {
  it.each([400, 401, 403, 404, 422, 499])('does not retry HTTP %i', async (status) => {
    let requests = 0
    server.use(
      http.get(`${API}/retry-probe`, () => {
        requests += 1
        return HttpResponse.json({ detail: 'Client error' }, { status })
      }),
    )
    const client = createAppQueryClient()
    await expect(
      client.fetchQuery({
        queryKey,
        queryFn: () => apiClient('/api/v1/retry-probe'),
        retryDelay: 0,
      }),
    ).rejects.toEqual(new ApiError(status, 'Client error'))
    expect(requests).toBe(1)
    client.clear()
  })

  it('shows the unavailable series message after the first 404', async () => {
    let requests = 0
    server.use(
      http.get(`${API}/series/series-1`, () => {
        requests += 1
        return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
      }),
    )
    const client = createAppQueryClient()
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/series/series-1']}>
          <Routes>
            <Route path="/series/:seriesId" element={<SeriesPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('定例が見つからないか、閲覧権限がありません')
    expect(requests).toBe(1)
    client.clear()
  })

  it('retains the default three retries for server errors', async () => {
    let requests = 0
    server.use(
      http.get(`${API}/retry-probe`, () => {
        requests += 1
        return HttpResponse.json({ detail: 'Unavailable' }, { status: 503 })
      }),
    )
    const client = createAppQueryClient()
    await expect(
      client.fetchQuery({
        queryKey,
        queryFn: () => apiClient('/api/v1/retry-probe'),
        retryDelay: 0,
      }),
    ).rejects.toEqual(new ApiError(503, 'Unavailable'))
    expect(requests).toBe(4)
    client.clear()
  })

  it('retains default retries for network failures', async () => {
    let requests = 0
    server.use(
      http.get(`${API}/retry-probe`, () => {
        requests += 1
        return requests <= 3 ? HttpResponse.error() : HttpResponse.json({ recovered: true })
      }),
    )
    const client = createAppQueryClient()
    await expect(
      client.fetchQuery({
        queryKey,
        queryFn: () => apiClient('/api/v1/retry-probe'),
        retryDelay: 0,
      }),
    ).resolves.toEqual({ recovered: true })
    expect(requests).toBe(4)
    client.clear()
  })
})
