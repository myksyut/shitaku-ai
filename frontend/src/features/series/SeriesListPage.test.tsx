import { screen } from '@testing-library/react'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { API, occurrence, renderPage, series, server } from '../../test/series'
import { SeriesListPage } from './SeriesListPage'

describe('series list calendar errors', () => {
  it.each([
    ['member', 'scope_missing', 'カレンダー同期でエラーが発生しています（作成者に確認してください）'],
    ['creator', 'scope_missing', 'Googleカレンダーの権限が不足しています'],
    ['creator', 'new_backend_code', '同期でエラーが発生しました'],
  ] as const)('localizes %s calendar banner for %s', async (role, code, expected) => {
    server.use(
      http.get(`${API}/series`, () =>
        HttpResponse.json({
          series: [
            {
              id: series.id,
              title: series.title,
              role,
              next_occurrence: null,
              open_action_items: 0,
              calendar_sync_error: code,
            },
          ],
        }),
      ),
    )
    renderPage(<SeriesListPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent(expected)
    expect(screen.queryByText(code)).not.toBeInTheDocument()
  })
})

describe('series list extraction badges', () => {
  it.each([
    ['2099-01-15T10:00:00Z', false],
    ['2020-01-15T10:00:00Z', true],
  ] as const)('shows the extraction badge only after %s has started', async (startAt, visible) => {
    server.use(
      http.get(`${API}/series`, () =>
        HttpResponse.json({
          series: [
            {
              id: series.id,
              title: series.title,
              role: 'creator',
              next_occurrence: { ...occurrence.occurrence, start_at: startAt, needs_extraction: true },
              open_action_items: 0,
              calendar_sync_error: null,
            },
          ],
        }),
      ),
    )
    renderPage(<SeriesListPage />)
    await screen.findByRole('heading', { name: series.title })
    expect(screen.queryByText('未抽出') !== null).toBe(visible)
  })
})
