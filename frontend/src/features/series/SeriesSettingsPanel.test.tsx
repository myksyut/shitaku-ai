import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { API, renderPage, series, server } from '../../test/series'
import { SeriesPage } from './SeriesPage'
import { SeriesSettingsPanel } from './SeriesSettingsPanel'
import type { SeriesDetail } from './types'

const minutesError = '参照する議事録の件数は0〜10の整数で入力してください'
const daysError = 'Slackの参照日数は1〜30の整数で入力してください'

describe('series settings bounds', () => {
  it.each([
    ['参照する議事録の件数', '-1', minutesError],
    ['参照する議事録の件数', '11', minutesError],
    ['参照する議事録の件数', '1.5', minutesError],
    ['参照する議事録の件数', '', minutesError],
    ['Slackの参照日数', '0', daysError],
    ['Slackの参照日数', '31', daysError],
    ['Slackの参照日数', '1.5', daysError],
    ['Slackの参照日数', '', daysError],
  ])('rejects %s = %s with an inline error', async (label, value, error) => {
    const { client } = renderPage(<SeriesSettingsPanel series={{ ...series, role: 'creator' }} />)
    const user = userEvent.setup()
    const input = screen.getByRole<HTMLInputElement>('spinbutton', { name: label })
    await user.clear(input)
    if (value) await user.type(input, value)
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input.checkValidity()).toBe(false)
    expect(screen.getByText(error)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '設定を保存' })).toBeDisabled()
    if (!input.form) throw new Error('Settings input must belong to the settings form')
    fireEvent.submit(input.form)
    expect(client.getMutationCache().getAll()).toHaveLength(0)
  })

  it.each([
    [0, 1],
    [10, 30],
  ])('accepts boundary values %i minutes and %i days', async (minutes, days) => {
    server.use(
      http.put(`${API}/series/series-1/settings`, async ({ request }) => {
        expect(await request.json()).toEqual({
          google_integration_id: 'google-1',
          description: null,
          minutes_count: minutes,
          slack_message_days: days,
          slack: null,
        })
        return HttpResponse.json({
          ...series,
          settings: { description: null, minutes_count: minutes, slack_message_days: days },
        })
      }),
    )
    renderPage(<SeriesSettingsPanel series={{ ...series, role: 'creator' }} />)
    const user = userEvent.setup()
    const minutesInput = screen.getByRole('spinbutton', { name: '参照する議事録の件数' })
    const daysInput = screen.getByRole('spinbutton', { name: 'Slackの参照日数' })
    expect(minutesInput).toHaveAttribute('min', '0')
    expect(minutesInput).toHaveAttribute('max', '10')
    expect(daysInput).toHaveAttribute('min', '1')
    expect(daysInput).toHaveAttribute('max', '30')
    await user.clear(minutesInput)
    await user.type(minutesInput, String(minutes))
    await user.clear(daysInput)
    await user.type(daysInput, String(days))
    expect(screen.queryByText(minutesError)).not.toBeInTheDocument()
    expect(screen.queryByText(daysError)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '設定を保存' }))
    expect(await screen.findByText('設定を保存しました')).toBeInTheDocument()
  })
})

describe('series Google integration settings', () => {
  it('relinks a disconnected series to a readonly-capable account and can explicitly unlink it', async () => {
    let detail: SeriesDetail = {
      ...series,
      role: 'creator',
      calendar: { ...series.calendar, integration_id: null, google_connected: false, error: 'not_connected' },
    }
    const bindings: (string | null)[] = []
    server.use(
      http.get(`${API}/series/series-1`, () => HttpResponse.json(detail)),
      http.get(`${API}/google/integrations`, () =>
        HttpResponse.json([
          {
            id: 'google-full',
            email: 'full@example.com',
            granted_scopes: ['https://www.googleapis.com/auth/calendar'],
            created_at: '',
            updated_at: null,
          },
          {
            id: 'google-read',
            email: 'readonly@example.com',
            granted_scopes: ['https://www.googleapis.com/auth/calendar.readonly'],
            created_at: '',
            updated_at: null,
          },
        ]),
      ),
      http.put(`${API}/series/series-1/settings`, async ({ request }) => {
        const binding = bindings.length === 0 ? 'google-read' : null
        expect(await request.json()).toEqual({
          google_integration_id: binding,
          description: null,
          minutes_count: 3,
          slack_message_days: 7,
          slack: null,
        })
        bindings.push(binding)
        detail = {
          ...detail,
          calendar: { ...detail.calendar, integration_id: binding, google_connected: binding !== null, error: null },
        }
        return HttpResponse.json(detail)
      }),
    )
    renderPage(
      <Routes>
        <Route path="/series/:seriesId" element={<SeriesPage />} />
      </Routes>,
      '/series/series-1',
    )
    const user = userEvent.setup()
    await screen.findByRole('heading', { name: series.title })
    await user.click(screen.getByRole('button', { name: '設定', exact: true }))
    const selector = screen.getByLabelText('Google連携（カレンダー同期）')
    await screen.findByRole('option', { name: 'readonly@example.com' })
    expect(selector).toHaveValue('')
    expect(screen.getByRole('option', { name: /full@example.com/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'カレンダーを同期' })).toBeDisabled()
    await user.selectOptions(selector, 'google-read')
    await user.click(screen.getByRole('button', { name: '設定を保存' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'カレンダーを同期' })).toBeEnabled())
    expect(bindings).toEqual(['google-read'])
    expect(selector).toHaveValue('google-read')

    await user.selectOptions(selector, '')
    await user.click(screen.getByRole('button', { name: '設定を保存' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'カレンダーを同期' })).toBeDisabled())
    expect(bindings).toEqual(['google-read', null])
  })
})
